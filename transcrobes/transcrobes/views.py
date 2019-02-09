# -*- coding: utf-8 -*-

from django.http import HttpResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(["GET"])
@permission_classes((AllowAny,))
def hello(request):
    return HttpResponse('Hello, World!')

