# -*- coding: utf-8 -*-
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes

from data.models import Survey, UserSurvey
from data.permissions import IsOwner
from data.serialisers import SurveySerialiser, UserSerialiser, UserSurveySerialiser
from data.utils import update_user_rules, update_user_words
from enrich.data import managers
from utils import default_definition

logger = logging.getLogger(__name__)


def surveys(request):
    # This should have some sort of algorithm to decide what should be shown to the user
    return render(request, "data/surveys.html", {"surveys": Survey.objects.all()})


def survey_detail(request, survey_id):
    survey = get_object_or_404(Survey, pk=survey_id)
    user_survey = request.user.usersurvey_set.filter(survey__id=survey_id).first()
    return render(request, "data/survey.html", {"survey": survey, "user_survey": user_survey})


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
    queryset = Survey.objects.all()
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
        update_user_words(voc, request.user)
        update_user_rules(rlz, request.user)

    data = {"status": "success"}
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# END PROD

# BOOTSTRAP INVESTIGATIONS


class VocabList(LoginRequiredMixin, TemplateView):
    template_name = "data/vocab_list.html"
    login_url = "/accounts/login/"

    def vocab_list(self, _list_type="SUB", start=0, window_size=100):
        username = self.request.user.username
        lang_pair = self.request.user.transcrober.lang_pair()
        manager = managers.get(lang_pair)
        if not manager:
            raise Exception(f"Server does not support language pair {lang_pair}")

        # TODO: the following
        # get list of words from list X that are not in username.notes with definitions from bingapilookup
        # ordered by list X

        # FIXME: sql injection fun!!! ???
        # FIXME: this should allow for re-running the tool!
        sql = fr"""
            select source_text from enrichers_zh_subtlexlookup sub
                left join {username}.notes n
                    on sub.source_text = regexp_replace(regexp_replace(substring(n.flds from 0 for position(chr(31) in n.flds)), E'(?x)<[^>]*?(\s alt \s* = \s* ([\\'"]) ([^>]*?) \\2) [^>]*? >', E'\\3'), E'(?x)(< [^>]*? >)', '', 'g')
            where regexp_replace(regexp_replace(substring(n.flds from 0 for position(chr(31) in n.flds)), E'(?x)<[^>]*?(\s alt \s* = \s* ([\\'"]) ([^>]*?) \\2) [^>]*? >', E'\\3'), E'(?x)(< [^>]*? >)', '', 'g') is null
            order by sub.id
            limit %(window_size)s
            offset %(start)s
        """  # noqa: E501

        page_words = None
        with connection.cursor() as cursor:
            cursor.execute(sql, {"window_size": window_size, "start": start})
            page_words = cursor.fetchall()

        data = []
        for pw in page_words:
            w = pw[0]
            data.append(default_definition(manager, w))
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["data"] = self.vocab_list()
        context["vocab"] = {x["Simplified"]: [0, 0] for x in context["data"]}
        context["post_ep"] = reverse("add_words")

        return context
