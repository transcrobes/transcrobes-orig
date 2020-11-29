# -*- coding: utf-8 -*-

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"surveys", views.SurveyViewSet)
router.register(r"usersurveys", views.UserSurveyViewSet)
router.register(r"users", views.UserViewSet)

# app_name = "data"  # namespacing has advantages but needs confusing extra config with DRF

urlpatterns = [
    path("api/", include(router.urls)),
]

urlpatterns += [
    # survey.js surveys
    path("survey/<int:survey_id>/", views.SurveyView.as_view(), name="ui_survey_detail"),
    path("surveys/", views.UserSurveysView.as_view(template_name="data/surveys.html"), name="ui_survey_list"),
    # AJAX endpoints, FIXME this should probably be in ankrobes
    path("update_model/", views.update_model, name="update_model"),
    path("update_model_add_notes/", views.update_model_add_notes, name="update_model_add_notes"),
    path("user_event/", views.user_event, name="user_event"),
    # Backoffice
    path("", views.OnboardedTemplateView.as_view(template_name="data/home.html"), name="home"),
    path("vocab/", views.VocabList.as_view(template_name="data/vocab_list.html"), name="vocab_list"),
    # path("list_import/", views.ImportCreate.as_view(template_name="data/list_import.html"), name="list_import"),
    # path("list_list/", views.ImportList.as_view(template_name="data/list_list.html"), name="list_list"),
    # path(
    #     "import_detail/<int:pk>/",
    #     views.ImportDetail.as_view(template_name="data/import_detail.html"),
    #     name="import_detail",
    # ),
    path(
        "coming_soon/", views.OnboardedTemplateView.as_view(template_name="data/coming_soon.html"), name="coming_soon"
    ),
    path("settings/", views.OnboardedTemplateView.as_view(template_name="data/settings.html"), name="settings"),
    # FIXME: understand whether this must use dashes or can use underscores
    path(
        "change-password/",
        views.OnboardedTemplateView.as_view(template_name="registration/password_change_form.html"),
        name="change-password",
    ),
]
