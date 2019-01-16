# -*- coding: utf-8 -*-

import json
import logging

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth import authenticate

from utils import get_credentials

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def auth(request):
    # TODO: this needs some anti-flood stuff
    try:
        post_data = json.loads(request.body)
        username = post_data['username']
        password = post_data['password']
    except Exception as ex:
        logger.error("Failed attempt to authenticate, invalid request")
        raise SuspiciousOperation("Invalid request; see documentation for correct paramaters")

    user = authenticate(request, username=username, password=password)

    logger.debug("Validating username: {}; valid_user is {}".format(username, user is not None))

    return JsonResponse({'valid_user': user is not None })


@require_http_methods(["GET"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def authget(request):
    # TODO: this needs some anti-flood stuff
    try:
        username, password = get_credentials(request)
        if not username or not password:
            return HttpResponse('Unauthorized', status=401)
    except Exception as ex:
        logger.error("Failed attempt to authenticate, invalid request")
        raise SuspiciousOperation("Invalid request; see documentation for correct paramaters")

    user = authenticate(request, username=username, password=password)

    logger.debug("Validating username: {}; valid_user is {}".format(username, user is not None))
    if user is not None:
        return HttpResponse("{} is a valid user".format(user))
    else:
        return HttpResponse('Unauthorized', status=401)


@require_http_methods(["GET"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def hello(request):
    return HttpResponse('Hello, World!')
