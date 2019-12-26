# -*- coding: utf-8 -*-
from ankisyncd.sync_app import SyncCollectionHandler
from django.urls import path

from . import views

urlpatterns = []

for op in SyncCollectionHandler.operations:
    urlpatterns.append(path(f"{op}", views.call, name="sync"))

# FIXME: try and get this in a variable on SyncApp upstream
for op in ["hostKey", "upload", "download"]:
    urlpatterns.append(path(f"{op}", views.call, name="sync"))
