# -*- coding: utf-8 -*-

import re
import json
import logging

from django.http import JsonResponse
from django.conf import settings
from django.utils.html import strip_tags
from django_wsgi.embedded_wsgi import call_wsgi_app
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from ankisyncd.sync_app import SyncApp

from ankrobes import Ankrobes


logger = logging.getLogger(__name__)

ankiserver = SyncApp(settings.ANKISYNCD_CONFIG())

# PROD start
## Wrapper around ankisyncd
@api_view(["POST"])
@permission_classes((AllowAny,))  # has its own auth
def call(request):
    return call_wsgi_app(ankiserver.__call__, request, request.path)

## Normal views
@api_view(["POST", "OPTIONS"])
def add_note_chromecrobes(request):
    return _push_note_to_ankrobes(request, review_in=0)

@api_view(["POST", "OPTIONS"])
def set_word_known(request):
    return _push_note_to_ankrobes(request, review_in=1)

@api_view(["POST", "OPTIONS"])
def set_word(request):
    return _push_note_to_ankrobes(request, review_in=-1)

def _push_note_to_ankrobes(request, review_in):
    data = {}
    if request.method == 'POST':
        logger.debug("Received to notes set_word_known: {}".format(request.body.decode("utf-8")))

        username = request.user.username
        with Ankrobes(username) as userdb:
            ci = userdb.clean_inputs(json.loads(request.body.decode("utf-8")))
            status = userdb.set_word_known(simplified=ci['simplified'], pinyin=ci['pinyin'],
                                           meanings=ci['meanings'], tags=ci['tags'],
                                           review_in=review_in)

        data = {"status": 'ok' if status else 'ko' }

        logger.debug("I got a {} back from ankrobes".format(data))

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response
# PROD end

# TESTING start
@api_view(["POST", "OPTIONS"])
def helloapi(request):
    data = {}
    if request.method == 'POST':
        logger.debug("Received to notes helloapi: {}".format(request.body.decode("utf-8")))
        inputj = request.body.decode("utf-8")
        req_json = json.loads(inputj)

        fields = req_json
        simplified = fields['Simplified']
        # TODO: make sure we have only one pinyin format - either 'là' or 'la4', not both!
        pinyin = fields['Pinyin'].strip(' ()')

        # TODO: this should support multiple meanings
        regex = r"(?:<style>.*</style>)"  # While using ODH - they force including css at the start of meanings...
        result = re.sub(regex, '', fields['Meaning'], 0, re.MULTILINE | re.DOTALL)
        # TODO: add my own (Hanping compatible???) tags here after stripping the existing entry stuff
        meanings = strip_tags(result).strip()

        username = request.user.username
        with Ankrobes(username) as userdb:
            status = userdb.add_ankrobes_note(simplified, pinyin, [meanings], ['chromecrobes'])

        data = {"status": 'ok' if status else 'ko' }

        logging.debug("I got a {} back from ankrobes".format(data))

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"

    return response

@api_view(["POST", "OPTIONS"])
def get_word(request):
    from enrich.enricher import _sanitise_ankrobes_entry

    username = request.user.username

    with Ankrobes(username) as userdb:
        w = request.body.decode("utf-8")
        data = userdb.get_word(w)
        data = _sanitise_ankrobes_entry(data)
        return JsonResponse(data, safe=False)

# TESTING end
