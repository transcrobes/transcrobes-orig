# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt import views as jwt_views
from utils import TranscrobesTokenObtainPairView

from . import views

urlpatterns = [

    # TODO: Django admin, not yet used
    path('admin/', admin.site.urls),

    # enricher
    path('enrich/', include('enrich.urls')),

    # # auth
    # path('authget', views.authget, name='authget'),

    # liveness
    path('hello', views.hello, name='hello'),

    # podname
    path('pod_name', views.pod_name, name='pod_name'),
    path('pname', views.pod_name, name='pname'),

    # ankisyncd
    path('msync/', include('ankrobes.msyncurls')),
    path('sync/', include('ankrobes.syncurls')),

    # ankrobes
    path('notes/', include('ankrobes.urls')),  # TODO: this should be renamed to `ankrobes`

    # JWT
    path('api/token/', TranscrobesTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),

]
