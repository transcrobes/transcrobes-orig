# -*- coding: utf-8 -*-
from django.urls import path

from . import views

# from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path("enrich_json", views.enrich_json, name="enrich_json"),
    # path("word_definitions", csrf_exempt(views.word_definitions), name="word_definitions"),  # FIXME: ???
    path("word_definitions", views.word_definitions, name="word_definitions"),
    # debug stuff
    path("text_to_std_parsed", views.text_to_std_parsed, name="text_to_std_parsed"),
    path("lemma_defs", views.lemma_defs, name="lemma_defs"),
    path("bing/<str:method>", views.bing_api, name="bing"),
    # path('hello/', views.HelloView.as_view(), name='hello'),
]
