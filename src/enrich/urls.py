# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("exports.json", views.definitions_export_urls, name="exports_json_urls"),
    path("exports/<path:resource_path>", views.definitions_export_json, name="exports_json"),
    path("hzexports.json", views.hanzi_export_urls, name="hzexports_json_urls"),
    path("hzexports/<path:resource_path>", views.hanzi_export_json, name="hzexports_json"),
    path("word_definitions", views.word_definitions, name="word_definitions"),
    path("load_definitions_cache", views.load_definitions_cache, name="load_definitions_cache"),
    path("slim_def", views.slim_def, name="slim_def"),
    path("aenrich_json", views.aenrich_json, name="aenrich_json"),
    # debug stuff
    path("text_to_std_parsed", views.text_to_std_parsed, name="text_to_std_parsed"),
    path("lemma_defs", views.lemma_defs, name="lemma_defs"),
]
