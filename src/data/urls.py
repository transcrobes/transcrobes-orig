# -*- coding: utf-8 -*-

from django.conf import settings
from django.http.response import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

import stats

from . import views
from .schema import schema

router = DefaultRouter()
router.register(r"surveys", views.SurveyViewSet)
router.register(r"usersurveys", views.UserSurveyViewSet)
router.register(r"users", views.UserViewSet)

# app_name = "data"  # namespacing has advantages but needs confusing extra config with DRF

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/graphql", views.AsyncGraphQLView.as_view(schema=schema, graphiql=settings.DEBUG)),
]


def broadcast_test(request, pk):
    stats.KAFKA_PRODUCER.send("definitions", str(pk))
    return HttpResponse("hi here")


urlpatterns += [
    # testing
    # path("broadcast/<int:pk>/", broadcast_test, name="broadcast_test"),
    # path("test/", views.OnboardedTemplateView.as_view(template_name="data/test.html"), name="test"),
    # Service Worker template
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="data/sw.js",
            content_type="application/javascript",
        ),
        name="sw",
    ),
    ## API
    path("precache_urls/", views.precache_urls, name="precache_urls"),
    path("user_event/", views.user_event, name="user_event"),
    # Backoffice
    path("", views.HomeView.as_view(template_name="data/home.html"), name="home"),
    ## Data entry
    path(
        "vocab/",
        views.OnboardedTemplateView.as_view(template_name="data/apps/notrobes.html"),
        name="notrobes",
    ),
    path(
        "vocab/list/",
        views.OnboardedTemplateView.as_view(template_name="data/apps/listrobes.html"),
        name="listrobes",
    ),
    ## Active Learning
    path(
        "vocab/review/",
        views.OnboardedTemplateView.as_view(template_name="data/apps/srsrobes.html"),
        name="srsrobes",
    ),
    ## Meta-knowledge management
    # survey.js surveys
    path(
        "survey/<int:survey_id>/",
        views.SurveyView.as_view(template_name="data/apps/survey_detail.html"),
        name="ui_survey_detail",
    ),
    path("surveys/", views.UserSurveysView.as_view(template_name="data/crud/surveys.html"), name="ui_survey_list"),
    # basic cruds
    path(
        "import/create/", views.ImportCreate.as_view(template_name="data/crud/import_create.html"), name="import_create"
    ),
    path("import/list/", views.ImportList.as_view(template_name="data/crud/import_list.html"), name="import_list"),
    path(
        "import/detail/<int:pk>/",
        views.ImportDetail.as_view(template_name="data/crud/import_detail.html"),
        name="import_detail",
    ),
    path(
        "list/create/<int:from_import>/",
        views.ListCreate.as_view(template_name="data/crud/list_create.html"),
        name="list_create",
    ),
    path("list/list/", views.ListList.as_view(template_name="data/crud/list_list.html"), name="list_list"),
    path(
        "list/detail/<int:pk>/",
        views.ListDetail.as_view(template_name="data/crud/list_detail.html"),
        name="list_detail",
    ),
    path(
        "goal/create/<int:from_list>/",
        views.GoalCreate.as_view(template_name="data/crud/goal_create.html"),
        name="goal_create",
    ),
    path("goal/list/", views.GoalList.as_view(template_name="data/crud/goal_list.html"), name="goal_list"),
    path(
        "goal/detail/<int:pk>/",
        views.GoalDetail.as_view(template_name="data/crud/goal_detail.html"),
        name="goal_detail",
    ),
    path(
        "goal/update/<int:pk>/",
        views.GoalUpdate.as_view(template_name="data/crud/goal_update.html"),
        name="goal_update",
    ),
    # Media
    ## ebooks
    path("webpub/list/", views.WebpubList.as_view(template_name="data/crud/webpub_list.html"), name="webpub_list"),
    ### Reader
    path(
        "webpub/read/<int:pk>/",
        views.WebPubReadView.as_view(template_name="data/apps/webpub_read.html"),
        name="webpub_read",
    ),
    path("webpub/serve/<int:pk>/<path:resource_path>", views.WebPubServeView.as_view(), name="webpub_serve"),
    ## video subtitles
    path("video/list/", views.VideoList.as_view(template_name="data/crud/video_list.html"), name="video_list"),
    ### Media player
    path(
        "video/watch/<int:pk>/",
        views.VideoWatchView.as_view(template_name="data/apps/video_watch.html"),
        name="video_watch",
    ),
    # Settings and other user admin/management pages
    path(
        "coming_soon/",
        views.OnboardedTemplateView.as_view(template_name="data/settings/coming_soon.html"),
        name="coming_soon",
    ),
    path(
        "settings/", views.OnboardedTemplateView.as_view(template_name="data/settings/settings.html"), name="settings"
    ),
    path(
        "settings/profile",
        views.OnboardedTemplateView.as_view(template_name="data/settings/profile.html"),
        name="profile",
    ),
    path(
        "settings/reader",
        views.ReaderSettingsUpdate.as_view(template_name="data/settings/reader_settings.html"),
        name="reader_settings",
    ),
    path(
        "settings/media",
        views.MediaSettingsUpdate.as_view(template_name="data/settings/media_settings.html"),
        name="media_settings",
    ),
    path(
        "unsupported_browser/",
        views.TemplateView.as_view(template_name="data/settings/unsupported_browser.html"),
        name="unsupported_browser",
    ),
    path(
        "offline/",
        views.TemplateView.as_view(template_name="data/settings/offline.html"),
        name="offline",
    ),
    path(
        "initialisation/",
        views.InitialisationView.as_view(template_name="data/settings/initialisation.html"),
        name="initialisation",
    ),
    # FIXME: understand whether this must use dashes or can use underscores
    path(
        "change-password/",
        views.OnboardedTemplateView.as_view(template_name="registration/password_change_form.html"),
        name="change-password",
    ),
]
