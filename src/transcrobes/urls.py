# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView  # new
from rest_framework_simplejwt import views as jwt_views

from utils import TranscrobesTokenObtainPairView

from . import views

urlpatterns = [
    ## System paths
    path("admin/", admin.site.urls),
    # liveness
    path("hello", views.hello, name="hello"),
    # podname
    path("pod_name", views.pod_name, name="pod_name"),  # FIXME: why are there two of these?
    path("pname", views.pod_name, name="pname"),
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
    path("notes/", include("ankrobes.urls")),  # TODO: this should be renamed to `ankrobes`
    # FIXME: PILOT and new stuff
    path("", TemplateView.as_view(template_name="home.html"), name="home"),  # new
    path("data/", include("data.urls")),
    path("accounts/", include("accounts.urls")),  # new
    path("accounts/", include("django.contrib.auth.urls")),  # new
    # browable rest api
    path("api-auth/", include("rest_framework.urls")),
]

# if "survey" in settings.INSTALLED_APPS:
#     urlpatterns += [url(r"^survey/", include("survey.urls"))]
