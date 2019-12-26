# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView  # new
from rest_framework_simplejwt import views as jwt_views

from utils import TranscrobesTokenObtainPairView

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # enricher
    path("enrich/", include("enrich.urls")),
    # liveness
    path("hello", views.hello, name="hello"),
    # podname
    path("pod_name", views.pod_name, name="pod_name"),
    path("pname", views.pod_name, name="pname"),
    # ankisyncd
    path("msync/", include("ankrobes.msyncurls")),
    path("sync/", include("ankrobes.syncurls")),
    # ankrobes
    path("notes/", include("ankrobes.urls")),  # TODO: this should be renamed to `ankrobes`
    # JWT
    path("api/token/", TranscrobesTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    # FIXME: PILOT
    path("accounts/", include("accounts.urls")),  # new
    path("accounts/", include("django.contrib.auth.urls")),  # new
    path("", TemplateView.as_view(template_name="home.html"), name="home"),  # new
    path("data/", include("data.urls")),
]

if "survey" in settings.INSTALLED_APPS:
    urlpatterns += [url(r"^survey/", include("survey.urls"))]
