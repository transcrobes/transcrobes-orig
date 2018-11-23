# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    path('addNote', views.add_note_chromecrobes, name='add_note_chromecrobes'),
    path('add_note_chromecrobes', views.add_note_chromecrobes, name='add_note_chromecrobes'),
    path('set_word_known', views.set_word_known, name='set_word_known'),
    path('set_word', views.set_word, name='set_word'),

    # debug stuff
    path('helloapi', views.helloapi, name='helloapi'),
]
