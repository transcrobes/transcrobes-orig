# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("enrich_json", views.enrich_json, name="enrich_json"),
    path("word_definitions", views.word_definitions, name="word_definitions"),
    # debug stuff
    path("text_to_std_parsed", views.text_to_std_parsed, name="text_to_std_parsed"),
    path("lemma_defs", views.lemma_defs, name="lemma_defs"),
]
