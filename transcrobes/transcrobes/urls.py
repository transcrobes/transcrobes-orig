# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('enrich/', include('enrich.urls')),
    path('notes/', include('notes.urls')),
    path('admin/', admin.site.urls),

    path('auth', views.auth, name='auth'),
    path('authget', views.authget, name='authget'),
    path('hello', views.hello, name='hello'),
]
