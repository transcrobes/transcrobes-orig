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
    path("", views.HomeView.as_view(template_name="data/home.html"), name="home"),
    path("vocab/", views.VocabList.as_view(template_name="data/vocab_list.html"), name="vocab_list"),
    path("import_create/", views.ImportCreate.as_view(template_name="data/import_create.html"), name="import_create"),
    path("import_list/", views.ImportList.as_view(template_name="data/import_list.html"), name="import_list"),
    path(
        "import_detail/<int:pk>/",
        views.ImportDetail.as_view(template_name="data/import_detail.html"),
        name="import_detail",
    ),
    path(
        "list_create/<int:from_import>/",
        views.ListCreate.as_view(template_name="data/list_create.html"),
        name="list_create",
    ),
    path("list_list/", views.ListList.as_view(template_name="data/list_list.html"), name="list_list"),
    path(
        "list_detail/<int:pk>/",
        views.ListDetail.as_view(template_name="data/list_detail.html"),
        name="list_detail",
    ),
    path(
        "goal_create/<int:from_list>/",
        views.GoalCreate.as_view(template_name="data/goal_create.html"),
        name="goal_create",
    ),
    path("goal_list/", views.GoalList.as_view(template_name="data/goal_list.html"), name="goal_list"),
    path(
        "goal_detail/<int:pk>/",
        views.GoalDetail.as_view(template_name="data/goal_detail.html"),
        name="goal_detail",
    ),
    path("goal_update/<int:pk>/", views.GoalUpdate.as_view(template_name="data/goal_update.html"), name="goal_update"),
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
