# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView

from utils import TranscrobesTokenObtainPairView, TranscrobesTokenRefreshView

from . import views

# from rest_framework_simplejwt import views as jwt_views


urlpatterns = [
    ## System paths
    path("admin/", admin.site.urls),
    # liveness
    path("hello", views.hello, name="hello"),
    # details of the pods
    path("pod_details", views.pod_details, name="pod_details"),
    # JWT auth
    path("api/token/", TranscrobesTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TranscrobesTokenRefreshView.as_view(), name="token_refresh"),
    # browsable rest api
    path("api-auth/", include("rest_framework.urls")),
    # metrics
    path("", include("django_prometheus.urls")),
    ## External app paths
    # djankiserv
    path("djs/", include("djankiserv.urls")),
    ## App paths
    # enricher
    path("enrich/", include("enrich.urls")),
    # ankrobes
    path("notes/", include("ankrobes.urls")),  # TODO: this should probably be renamed to `ankrobes`
    path("", include("data.urls")),
    path("accounts/", include("registration.backends.default.urls")),
    path("accounts/", include("django.contrib.auth.urls")),  # new
    path("tos/", TemplateView.as_view(template_name="registration/tos.html"), name="tos"),
]
