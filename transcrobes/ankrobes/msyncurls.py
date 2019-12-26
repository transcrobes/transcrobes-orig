# -*- coding: utf-8 -*-
from ankisyncd.sync_app import SyncMediaHandler
from django.urls import path

from . import views

urlpatterns = []

for op in SyncMediaHandler.operations:
    urlpatterns.append(path(f"{op}", views.call, name="sync"))
