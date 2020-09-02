# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    # learner bootstrap
    path("bootstrap/vocab/", views.VocabList.as_view(), name="vocab_list"),
    # AJAX endpoints
    path("update_model/", views.update_model, name="update_model"),
]
