# -*- coding: utf-8 -*-

from django.urls import path

from . import views

from ankisyncd.sync_app import SyncMediaHandler

urlpatterns = []

for op in SyncMediaHandler.operations:
    urlpatterns.append(path(f'{op}', views.call, name='sync'))

