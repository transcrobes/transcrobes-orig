# -*- coding: utf-8 -*-
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"surveys", views.SurveyViewSet)
router.register(r"usersurveys", views.UserSurveyViewSet)
router.register(r"users", views.UserViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]

urlpatterns += [
    path("survey/", views.surveys, name="surveys"),
    path("survey/<int:survey_id>/", views.survey_detail, name="survey"),
    # learner bootstrap
    path("bootstrap/vocab/", views.VocabList.as_view(), name="vocab_list"),
    # AJAX endpoints
    path("update_model/", views.update_model, name="update_model"),
]
