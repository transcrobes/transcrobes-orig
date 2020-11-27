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
    path("survey/<int:survey_id>/", views.SurveyView.as_view(), name="ui-survey-detail"),
    path("surveys/", views.UserSurveysView.as_view(template_name="data/surveys.html"), name="ui-survey-list"),
    # AJAX endpoints, FIXME this should probably be in ankrobes
    path("update_model/", views.update_model, name="update_model"),
    path("update_model_add_notes/", views.update_model_add_notes, name="update_model_add_notes"),
    path("user_event/", views.user_event, name="user_event"),
    # Backoffice
    path("", views.OnboardedTemplateView.as_view(template_name="data/home.html"), name="home"),
    path("vocab/", views.VocabList.as_view(template_name="data/vocab-list.html"), name="vocab-list"),
    path(
        "coming-soon/", views.OnboardedTemplateView.as_view(template_name="data/coming-soon.html"), name="coming-soon"
    ),
    path("settings/", views.OnboardedTemplateView.as_view(template_name="data/settings.html"), name="settings"),
    path(
        "change-password/",
        views.OnboardedTemplateView.as_view(template_name="registration/password_change_form.html"),
        name="change-password",
    ),
]
