# -*- coding: utf-8 -*-

import json
import logging
import hashlib

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth import authenticate
from django.conf import settings
from django.core.cache import cache

from utils import get_credentials

logger = logging.getLogger(__name__)

def validate(request):
    # TODO: this needs some anti-flood stuff, at least for IPs
    try:
        username, password = get_credentials(request)
        if not username or not password:
            return False
    except Exception as ex:
        logger.exception("Failed attempt to authenticate, invalid request")
        raise SuspiciousOperation("Invalid request; see documentation for correct paramaters")

    userpass = hashlib.sha256((username + password).encode('utf-8')).hexdigest()
    if cache.get(username) == userpass:
        return True
    elif cache.get(username) == "":  # we cached an invalid user attempt
        # If a user attempts with an incorrect password, this will continue to fail, even with
        # a good password, until the cache expires because we have set their hash to ""
        return False
    else:
        user = authenticate(request, username=username, password=password)
        logger.debug("Validating username: {}; valid_user is {}".format(username, user is not None))
        if user:
            cache.set(username, userpass, settings.USER_CACHE_TIMEOUT)
            return True
        else:
            cache.set(username, "", settings.USER_CACHE_TIMEOUT)  # if no password fails above
            return False


@require_http_methods(["GET"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def authget(request):
    if validate(request):
        return HttpResponse("valid user")
    else:
        return HttpResponse('Unauthorized', status=401)


@require_http_methods(["GET"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def hello(request):
    return HttpResponse('Hello, World!')
