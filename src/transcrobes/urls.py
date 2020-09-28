# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt import views as jwt_views

from utils import TranscrobesTokenObtainPairView

from . import views

urlpatterns = [
    ## System paths
    path("admin/", admin.site.urls),
    # liveness
    path("hello", views.hello, name="hello"),
    # podname
    path("pod_name", views.pod_name, name="pod_name"),
    # JWT auth
    path("api/token/", TranscrobesTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
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
    # browsable rest api
    path("api-auth/", include("rest_framework.urls")),
    path("", include("django_prometheus.urls")),
]
