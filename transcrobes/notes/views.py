# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
from django.utils.html import strip_tags
from django.conf import settings

import logging
import json
import re

from notes.ankrobes import AnkrobesServer
from utils import get_credentials


logger = logging.getLogger(__name__)

# PROD start
@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def add_note_chromecrobes(request):
    return _push_note_to_ankrobes(request, review_in=0)


@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def set_word_known(request):
    return _push_note_to_ankrobes(request, review_in=1)


@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def set_word(request):
    return _push_note_to_ankrobes(request, review_in=-1)

def _push_note_to_ankrobes(request, review_in):
    data = {}
    if request.method == 'POST':
        logger.debug("Received to notes set_word_known: {}".format(request.body.decode("utf-8")))
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

        tags = ['chromecrobes'] + (fields['Tags'] if 'Tags' in fields else [])

        username, password = get_credentials(request)
        server = AnkrobesServer(username)

        status = server.set_word_known(simplified=simplified, pinyin=pinyin, meanings=[meanings],
                                       tags=tags, review_in=review_in)
        data = {"status": 'ok' if status else 'ko' }

        logger.debug("I got a {} back from ankrobes".format(data))

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

# PROD end
# TESTING start
@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
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

        username, password = get_credentials(request)
        server = AnkrobesServer(username)

        status = server.add_ankrobes_note(simplified, pinyin, [meanings], ['chromecrobes'])
        data = {"status": 'ok' if status else 'ko' }

        logging.debug("I got a {} back from ankrobes".format(data))

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"

    return response
# TESTING end
