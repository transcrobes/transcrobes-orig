import copy
import json
import logging
import mimetypes
import os

import strawberry
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest
from django.http.response import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext, Template
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import reverse as r
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import DetailView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from strawberry.django.views import AsyncGraphQLView as StrawberryAsyncGraphQLView

import stats
from data.context import Context, get_broadcast
from data.models import (
    DATA_JS_SUFFIX,
    ENRICH_JSON_SUFFIX,
    FINISHED,
    MANIFEST_JSON,
    PARSE_JSON_SUFFIX,
    REQUESTED,
    WEBVTT_FILE,
    Content,
    Goal,
    Import,
    Survey,
    Transcrober,
    UserList,
    UserSurvey,
)
from data.permissions import IsOwner
from data.serialisers import SurveySerialiser, UserSerialiser, UserSurveySerialiser
from ndutils import do_response

logger = logging.getLogger(__name__)


class AsyncGraphQLView(StrawberryAsyncGraphQLView):
    async def get_context(self, request: HttpRequest) -> Context:
        broadcast = await get_broadcast()
        return Context(broadcast, request)

    # @staticmethod
    # def is_admin(user):
    #     return user.is_superuser

    def _render_graphiql(self, request: HttpRequest, context=None):
        if not self.graphiql:
            raise Http404()

        # # probably need to make upstream test and return inspect.isawaitable
        # if not self.is_admin(request.user):
        #     raise PermissionDenied("You do not have permission to access this page")

        try:
            template = Template(render_to_string("graphql/graphiql.html"))
        except TemplateDoesNotExist:
            template = Template(
                open(
                    os.path.join(
                        os.path.dirname(os.path.abspath(strawberry.__file__)),
                        "static/graphiql.html",
                    ),
                    "r",
                ).read()
            )

        context = context or {}
        # THIS enables subscriptions
        context.update({"SUBSCRIPTION_ENABLED": "true"})

        response = TemplateResponse(request=request, template=None, context=context)
        response.content = template.render(RequestContext(request, context))

        return response


class SurveyView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = get_object_or_404(Survey, pk=kwargs["survey_id"])
        context["user_survey"] = self.request.user.usersurvey_set.filter(survey__id=kwargs["survey_id"]).first()

        return context


class OnboardedView(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        ids = settings.USER_ONBOARDING_SURVEY_IDS
        return self.request.user.usersurvey_set.filter(survey__id__in=ids).count() == len(ids)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f"{super().get_login_url()}?next={self.request.path}")

        ids = copy.deepcopy(settings.USER_ONBOARDING_SURVEY_IDS)
        for user_survey in self.request.user.usersurvey_set.filter(survey__id__in=ids):
            ids.remove(user_survey.survey.id)

        if not ids:  # user is auth'ed and has answered all obligatory surveys, must be a perms issue
            raise PermissionDenied("You do not have permission to access this page")

        return redirect("ui_survey_detail", survey_id=ids[0])  # any obligatory survey will do!

    def get_login_url(self):
        if not self.request.user.is_authenticated:
            return super().get_login_url()
        return r("survey")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # this has the extra info, which we don't need here?
        # token = TranscrobesTokenObtainPairSerializer.get_token(self.request.user)
        token = RefreshToken.for_user(self.request.user)
        context["app_config"] = {
            "jwt_access": str(token.access_token),
            "jwt_refresh": str(token),
            "lang_pair": self.request.user.transcrober.lang_pair(),
            "username": self.request.user.username,
            "resource_root": static("data/css/"),  # FIXME: this is ugly
        }
        return context

        # context["jwt_access"] = str(token.access_token)
        # context["jwt_refresh"] = str(token)
        # context["lang_pair"] = self.request.user.transcrober.lang_pair()


class OnboardedOwnerView(OnboardedView):
    # FIXME: I should probably add an official parent here - self.get_object() could fail because OnboardedView
    # doesn't have that method - it really needs SingleObjectMixin but also one of the edit/update mixins...
    # How does one do both?
    def test_func(self):
        return super().test_func() and self.request.user == self.get_object().user


class OnboardedTemplateView(OnboardedView, TemplateView):
    pass


class HomeView(OnboardedTemplateView):
    MAX_GOALS_LIST = 6

    @staticmethod
    def get_goal_display_status(percent):
        # FIXME: there are clean solutions with things like pandas but... require pandas for this???
        # we may need it later but for the moment

        # TODO: decide whether "success" should correspond to 95% or 98%, which would mean "scientific" goodness

        if percent < 0.6:
            return "bg-danger"
        if percent < 0.75:
            return "bg-warning"
        if percent < 0.85:
            return "bg-primary"
        if percent < 0.93:
            return "bg-info"
        return "bg-success"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progresses = []
        for goal in Goal.objects.filter(user=self.request.user).active():
            if len(progresses) >= self.MAX_GOALS_LIST:
                break

            percent = goal.get_progress_percent()
            if percent:
                progresses.append(
                    {
                        "id": goal.id,
                        "name": goal.title,
                        "display_status": self.get_goal_display_status(goal.get_progress_percent()),
                        "progress_percent": percent,
                    }
                )
        context["goals_progress"] = progresses
        return context


class ReaderSettingsUpdate(SuccessMessageMixin, OnboardedView, UpdateView):
    model = Transcrober
    fields = ["default_glossing", "default_segment", "reading_mode", "font_size_percent"]
    success_message = "Settings updated successfully"

    def get_object(self, _queryset=None):
        return self.request.user.transcrober

    def get_success_url(self):
        return r("reader_settings")

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context["lang_pair"] = self.request.user.transcrober.lang_pair()
    #     return context


class MediaSettingsUpdate(SuccessMessageMixin, OnboardedView, UpdateView):
    model = Transcrober
    fields = [
        "subtitle_default_glossing",
        "subtitle_default_segment",
        "media_mode",
        "subtitle_font_size_percent",
        "subtitle_box_width_percent",
    ]
    success_message = "Settings updated successfully"

    def get_object(self, _queryset=None):
        return self.request.user.transcrober

    def get_success_url(self):
        return r("media_settings")


class VideoList(OnboardedView, ListView):
    model = Content

    def post(self, request, *_args, **_kwargs):
        content_id = request.POST.get("request_content_id")
        content = self.get_queryset().filter(id=content_id).first()
        if not content or content.processing:  # it has already been requested, for the moment no redos
            raise PermissionDenied("You are not permitted to perform this action")
        content.processing = REQUESTED
        content.save()
        return render(
            request,
            self.template_name,
            {
                "message": "Content enrichment request successful",
                "request_content_id": content_id,
                "object_list": self.get_queryset(),
            },
        )

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user, content_type=Content.VIDEO).order_by("-created")


class VideoWatchView(OnboardedOwnerView, DetailView):
    model = Content

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["content_id"] = self.object.id
        context["media_url"] = self.object.get_entry_point_url()
        context["transcrobes_model_url"] = self.object.get_entry_point_url() + ".data.js"

        # context["from_lang"] = self.request.user.transcrober.lang_pair().split(":")[0]
        # context["db_versions"] = self.request.user.transcrober.db_versions()
        context["glossing"] = self.request.user.transcrober.subtitle_default_glossing
        context["segment"] = "true" if self.request.user.transcrober.subtitle_default_segment else "false"
        context["reading_mode"] = self.request.user.transcrober.media_mode
        context["font_size_percent"] = self.request.user.transcrober.subtitle_font_size_percent
        context["sub_box_width_percent"] = self.request.user.transcrober.subtitle_box_width_percent
        return context


class WebpubList(OnboardedView, ListView):
    model = Content

    def post(self, request, *_args, **_kwargs):
        content_id = request.POST.get("request_content_id")
        content = self.get_queryset().filter(id=content_id).first()
        if not content or content.processing:  # it has already been requested, for the moment no redos
            raise PermissionDenied("You are not permitted to perform this action")
        content.processing = REQUESTED
        content.save()
        return render(
            request,
            self.template_name,
            {
                "message": "Content enrichment request successful",
                "request_content_id": content_id,
                "object_list": self.get_queryset(),
            },
        )

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user, content_type=Content.BOOK).order_by("-created")


@method_decorator(xframe_options_sameorigin, name="dispatch")
class WebPubServeView(SingleObjectMixin, OnboardedOwnerView, View):
    model = Content
    DATA_SUFFIX = ".data.js"

    def get(self, _request, *_args, **kwargs):  # pylint: disable=R0914
        output = self.get_object()
        if "resource_path" not in kwargs:
            raise Http404("No resource specified")

        destination = os.path.join(output.processed_path(), kwargs["resource_path"])
        if not os.path.isfile(destination.removesuffix(DATA_JS_SUFFIX)):
            raise Http404("Resource specified is not a file")

        if not destination.endswith(self.DATA_SUFFIX):
            response = FileResponse(open(destination, "rb"))
            response.content_type = mimetypes.guess_type(destination)[0]
            return response

        parse_path = f"{destination.removesuffix(DATA_JS_SUFFIX)}{PARSE_JSON_SUFFIX}"
        enrich_path = f"{destination.removesuffix(DATA_JS_SUFFIX)}{ENRICH_JSON_SUFFIX}"

        if not os.path.isfile(parse_path):
            raise Http404("Resource specified is not a file")

        with open(parse_path) as parse_file:
            combined = json.load(parse_file)

            if os.path.isfile(enrich_path):
                with open(enrich_path) as enrich_file:
                    enrich = json.load(enrich_file)
                    for parse_id, text_parse in combined.items():
                        for sindex, sentence in enumerate(text_parse["s"]):
                            sentence["l1"] = enrich[parse_id]["s"][sindex]["l1"]
                            for tindex, token in enumerate(sentence["t"]):
                                for prop, value in enrich[parse_id]["s"][sindex]["t"][tindex].items():
                                    token[prop] = value
            return HttpResponse(
                f'var transcrobesModel = {json.dumps(combined, separators=(",", ":"))};', content_type="text/javascript"
            )


class WebPubReadView(OnboardedOwnerView, DetailView):
    model = Content

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["media_url"] = self.object.get_entry_point_url()
        context["glossing"] = self.request.user.transcrober.default_glossing
        context["segment"] = "true" if self.request.user.transcrober.default_segment else "false"
        context["reading_mode"] = self.request.user.transcrober.reading_mode
        context["font_size_percent"] = self.request.user.transcrober.font_size_percent

        return context


class InitialisationView(OnboardedTemplateView):
    # FIXME: why do I need to call this?
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class UserSurveysView(OnboardedTemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["new_surveys"] = Survey.objects.exclude(usersurvey__user=self.request.user).filter(is_obligatory=False)
        context["answered_surveys"] = Survey.objects.filter(usersurvey__user=self.request.user).filter(
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

    permission_classes = [permissions.IsAdminUser | IsOwner]  # pylint: disable=E1131  # FIXME is this really correct?

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


class ImportCreate(OnboardedView, CreateView):
    model = Import
    exclude = ["user"]
    fields = ("title", "description", "status", "import_file", "process_type")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ImportList(OnboardedView, ListView):
    model = Import
    exclude = ["user"]

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).order_by("-modified")


class ImportDetail(OnboardedView, DetailView):
    model = Import


class ListCreate(OnboardedView, CreateView):
    model = UserList
    exclude = ["user"]
    fields = (
        "title",
        "status",
        "description",
        "the_import",
        "shared",
        "nb_to_take",
        "order_by",
        "only_dictionary_words",
        "minimum_doc_frequency",
        "minimum_abs_frequency",
        "words_are_known",
    )

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"].fields["the_import"].queryset = Import.objects.filter(
            user=self.request.user, processing=FINISHED
        )
        return context


class ListList(OnboardedView, ListView):
    model = UserList

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).order_by("-modified")


class ListDetail(OnboardedView, DetailView):
    model = UserList


class GoalCreate(OnboardedView, CreateView):
    model = Goal
    exclude = ["user"]
    fields = ("title", "description", "status", "user_list", "parent")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"].fields["user_list"].queryset = UserList.objects.filter(
            user=self.request.user, processing=FINISHED
        )
        return context


class GoalList(OnboardedView, ListView):
    model = Goal

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).order_by("-modified")


class GoalDetail(OnboardedView, DetailView):
    model = Goal

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["progress"] = self.object.get_progress()
        return context


class GoalUpdate(OnboardedView, UpdateView):
    model = Goal
    exclude = ["user"]
    fields = ("title", "description", "status", "user_list", "parent")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


def submit_event(event, user):
    if "data" not in event:
        logger.warning("Received empty %s event type for user %s", event["type"], user)
        return False

    if "userStatsMode" in event:
        stats_mode = int(event["userStatsMode"])
    else:
        stats_mode = stats.USER_STATS_MODE_IGNORE

    try:
        if event["type"] == "bulk_vocab":
            stats.KAFKA_PRODUCER.send(
                "vocab",
                {
                    "user_id": user.id,
                    "tstats": event["data"],
                    "source": event.get("source"),
                    "user_stats_mode": stats_mode,
                },
            )
        else:
            stats.KAFKA_PRODUCER.send(
                "actions",
                {
                    "user_id": user.id,
                    "type": event["type"],
                    "data": event["data"],
                    "source": event.get("source"),
                    "user_stats_mode": stats_mode,
                },
            )
        return True
    except Exception:
        logger.error("Unable to submit event: %s", event)
        raise


@permission_classes((permissions.IsAuthenticated,))
@api_view(["POST", "OPTIONS"])
def user_event(request):
    output = {}
    if request.method == "POST":
        if not isinstance(request.data, list):  # we check specifically for lists, because dicts are iterable
            submit_event(request.data, request.user)
        else:
            for event in request.data:
                submit_event(event, request.user)
        output = {"status": "success"}

    return do_response(Response(output))


@api_view(["GET", "POST", "OPTIONS"])
@permission_classes((permissions.IsAuthenticated,))
def precache_urls(request):
    user = request.user
    with_content = request.GET.get("with_content", "").lower() == "true"

    output = {}
    if request.method == "GET" or request.method == "POST":
        home_urls = [
            r("home"),
            r("settings"),
            r("reader_settings"),
            r("media_settings"),
            r("profile"),
            r("coming_soon"),
            r("listrobes"),
            r("notrobes"),
            r("srsrobes"),
        ]

        list_urls = [
            r("list_list"),
            r("list_create", args=[0]),
        ]
        list_urls += [r("list_detail", args=[ul.id]) for ul in UserList.objects.filter(user=user)]
        import_urls = [
            r("import_list"),
            r("import_create"),
        ]
        import_urls += [r("import_detail", args=[i.id]) for i in Import.objects.filter(user=user)]
        goal_urls = [
            r("goal_list"),
            r("goal_create", args=[0]),
        ]
        goal_urls += [r("goal_detail", args=[g.id]) for g in Goal.objects.filter(user=user)]
        goal_urls += [r("goal_update", args=[g.id]) for g in Goal.objects.filter(user=user)]

        webpub_urls = [
            r("webpub_list"),
        ]
        webpub_urls += [
            r("webpub_read", args=[g.id]) for g in Content.objects.filter(user=user, content_type=Content.BOOK)
        ]

        video_urls = [
            r("video_list"),
        ]
        video_urls += [
            r("video_watch", args=[g.id]) for g in Content.objects.filter(user=user, content_type=Content.VIDEO)
        ]

        # Transcrobed Content
        if with_content:
            webpub_urls += [
                r("webpub_serve", args=[g.id, MANIFEST_JSON])
                for g in Content.objects.filter(user=user, content_type=Content.BOOK)
            ]

            for book in Content.objects.filter(user=user, content_type=Content.BOOK):
                destination = os.path.join(book.processed_path(), MANIFEST_JSON)
                with open(destination, "r") as manifest:
                    for webfile in json.load(manifest)["resources"]:
                        webpub_urls += [r("webpub_serve", args=[book.id, webfile["href"]])]
                        webpub_urls += [r("webpub_serve", args=[book.id, webfile["href"] + DATA_JS_SUFFIX])]
            video_urls += [
                r("webpub_serve", args=[g.id, WEBVTT_FILE])
                for g in Content.objects.filter(user=user, content_type=Content.VIDEO)
            ]
            video_urls += [
                r("webpub_serve", args=[g.id, WEBVTT_FILE + DATA_JS_SUFFIX])
                for g in Content.objects.filter(user=user, content_type=Content.VIDEO)
            ]

        output = home_urls + list_urls + goal_urls + import_urls + webpub_urls + video_urls

    return do_response(Response(output))
