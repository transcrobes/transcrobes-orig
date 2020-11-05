# -*- coding: utf-8 -*-
import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes

import stats
from ankrobes import Ankrobes  # FIXME: should probably not do the note creation here, as we are mixing modules...
from data.models import Survey, UserSurvey
from data.permissions import IsOwner
from data.serialisers import SurveySerialiser, UserSerialiser, UserSurveySerialiser
from data.utils import update_user_rules, update_user_words_known
from enrich.data import managers
from utils import default_definition

logger = logging.getLogger(__name__)


def user_onboarded(user, onboarding_survey_id):
    return user.usersurvey_set.filter(survey__id=onboarding_survey_id).first()


class SurveyView(LoginRequiredMixin, TemplateView):
    template_name = "data/survey_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = get_object_or_404(Survey, pk=kwargs["survey_id"])
        context["user_survey"] = self.request.user.usersurvey_set.filter(survey__id=kwargs["survey_id"]).first()

        return context


class OnboardedTemplateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    ONBOARDING_SURVEY_ID = 1  # TODO: this is hard-coded in a couple of places - NASTY!!!

    def test_func(self):
        return self.request.user.usersurvey_set.filter(survey__id=self.ONBOARDING_SURVEY_ID).exists()

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f"{super().get_login_url()}?next={self.request.path}")
        return redirect("ui-survey-detail", survey_id=self.ONBOARDING_SURVEY_ID)

    def get_login_url(self):
        if not self.request.user.is_authenticated:
            return super().get_login_url()
        return reverse("survey")


class SurveyListView(LoginRequiredMixin, ListView):
    queryset = Survey.objects.prefetch_related("usersurvey_set").filter(is_obligatory=False)
    paginate_by = 10
    template_name = "data/survey_list.html"
    context_object_name = "surveys"


class UserSurveysView(OnboardedTemplateView):
    template_name = "data/surveys.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["new_surveys"] = Survey.objects.exclude(usersurvey__user__id=self.request.user.id).filter(
            is_obligatory=False
        )
        context["answered_surveys"] = Survey.objects.filter(usersurvey__user__id=self.request.user.id).filter(
            is_obligatory=False
        )

        return context


class UserSurveyViewSet(viewsets.ModelViewSet):
    # not having the `.none()` and using `basename` in the urls.py on the router.register causes a
    # "Could not resolve URL for hyperlinked relationship using view name..." error
    # FIXME: there is some magic going on that needs to be understood
    queryset = UserSurvey.objects.none()
    serializer_class = UserSurveySerialiser
    filterset_fields = ["user__username", "survey__id"]

    permission_classes = [permissions.IsAdminUser | IsOwner]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserSurvey.objects.all()

        return self.request.user.usersurvey_set.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SurveyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Survey.objects.filter(is_obligatory=False)
    serializer_class = SurveySerialiser


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerialiser
    permission_classes = [permissions.IsAdminUser]


# PROD

# Ideas for improvements
# - instead of just recording the word as seen/checked, add POS for the actual tokens in the text
@permission_classes((permissions.IsAuthenticated,))
@api_view(["POST", "OPTIONS"])
def update_model(request):
    if request.method == "POST":
        voc = request.data["vocab"]
        rlz = request.data["rules"]
        update_user_words_known(voc, request.user)
        update_user_rules(rlz, request.user)

    data = {"status": "success"}
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


@permission_classes((permissions.IsAuthenticated,))
@api_view(["POST", "OPTIONS"])
def user_event(request):
    if request.method == "POST":
        stats.KAFKA_PRODUCER.send(
            "actions", {"user_id": request.user.id, "type": request.data["type"], "data": request.data["data"]}
        )

    data = {"status": "success"}
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# Ideas for improvements
# - instead of just recording the word as seen/checked, add POS for the actual tokens in the text
@permission_classes((permissions.IsAuthenticated,))
@api_view(["POST", "OPTIONS"])
def update_model_add_notes(request):
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            raise Exception(f"Server does not support language pair {request.user.transcrober.lang_pair()}")

        vocab = request.data["vocab"]
        clicked_means_known = request.data["clicked_means_known"]
        add_all_to_learning = request.data["add_all_to_learning"]

        # invert so that 1 always means knows and 0 means doesn't know
        if not int(clicked_means_known):
            for _k, v in vocab.items():
                v[3] ^= 1

        update_user_words_known(vocab, request.user)

        # FIXME: this should be done via async, probably by putting in a kafka or similar
        # it is actually quite slow!
        with Ankrobes(request.user.username) as userdb:
            for word, actions in vocab.items():
                if not add_all_to_learning and not actions[3]:
                    continue  # not adding all and we don't know the word so we are not adding it

                # TODO: decide how to best deal with when to next review
                review_in = 0

                defin = default_definition(manager, word)
                if not userdb.set_word_known(
                    simplified=defin["Simplified"],
                    pinyin=defin["Pinyin"],
                    meanings=[defin["Meaning"]],
                    tags=["bootstrap"],
                    review_in=review_in,
                ):
                    logger.error(f"Error setting the word_known status for {word} for user {request.user.username}")
                    raise Exception(f"Error updating the user database for {request.user.username}")

            logger.info(f"Set {vocab.keys()} for {request.user.username}")

    data = {"status": "success"}
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


class VocabList(OnboardedTemplateView):
    @staticmethod
    def vocab_list(user, manager, _list_type="SUB", start=0, window_size=100):
        # TODO: the following
        # get list of words from list X that are not in username.notes with definitions from bingapilookup
        # ordered by list X

        # FIXME: this should allow for re-running the tool!
        sql = r"""
            select sub.source_text, bal.id, w.user_id from enrichers_zh_subtlexlookup sub
                    inner join enrich_bingapilookup bal on sub.source_text = bal.source_text
                    left join data_userword w on w.word_id = bal.id and w.user_id = %(user_id)s
                where w.user_id is null
                order by sub.id
                limit %(window_size)s
                offset %(start)s
        """  # noqa: E501

        page_words = None
        with connection.cursor() as cursor:
            cursor.execute(sql, {"window_size": window_size, "start": start, "user_id": user.id})
            page_words = cursor.fetchall()

        data = []
        for pw in page_words:
            w = pw[0]
            data.append([default_definition(manager, w), pw[1]])
        return data

    def get_context_data(self, **kwargs):
        manager = managers.get(self.request.user.transcrober.lang_pair())
        if not manager:
            raise Exception(f"Server does not support language pair {self.request.user.transcrober.lang_pair()}")

        context = super().get_context_data(**kwargs)
        context["data"] = self.vocab_list(self.request.user, manager)
        context["vocab"] = {x[0]["Simplified"]: [x[1], 1, 0, 0] for x in context["data"]}
        context["selected_word_start"] = self.request.GET.get("selected_word_start") or "red"
        context["add_all_to_learning"] = (self.request.GET.get("add_all_to_learning") == "true") or False

        return context
