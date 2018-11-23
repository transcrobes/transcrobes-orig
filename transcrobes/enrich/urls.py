# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    path('enrich_json', views.enrich_json, name='enrich_json'),
    path('text_to_corenlp', views.text_to_corenlp, name='text_to_corenlp'),
    path('word_definitions', views.word_definitions, name='word_definitions'),

    # debug stuff
    path('bing/<str:method>', views.bing_api, name='bing'),
    path('bing_lookup', views.bing_lookup, name='bing_lookup'),
]
