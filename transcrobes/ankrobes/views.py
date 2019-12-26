# -*- coding: utf-8 -*-
import logging
import re

from ankisyncd.sync_app import SyncApp
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.html import strip_tags
from django_wsgi.embedded_wsgi import call_wsgi_app
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from ankrobes import Ankrobes
from enrich.data import managers
from utils import default_definition, get_username_lang_pair

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
    if request.method == "POST":
        logger.debug(f"Received to notes set_word_known: {request.data}")

        username = request.user.username
        with Ankrobes(username) as userdb:
            ci = userdb.clean_inputs(request.data)
            status = userdb.set_word_known(
                simplified=ci["simplified"],
                pinyin=ci["pinyin"],
                meanings=ci["meanings"],
                tags=ci["tags"],
                review_in=review_in,
            )

        data = {"status": "ok" if status else "ko"}

        logger.debug(f"I got a {data} back from ankrobes")

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# PROD end

# BOOTSTRAP testing start
@api_view(["POST", "OPTIONS"])
def add_words_to_ankrobes(request):
    data = {}
    # print('I was going to try and save', request.data)

    if request.method == "POST":
        # logger.debug(f"Received to set_word_known: {request.data.decode('utf-8')}")

        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

        with Ankrobes(username) as userdb:
            words = request.data

            for w, cl in words.items():

                # TODO: decide how to best deal with when to next review
                review_in = 0 if cl[1] else 7  # v[0] is verified, v[1] is clicked

                defin = default_definition(manager, w)
                if not userdb.set_word_known(
                    simplified=defin["Simplified"],
                    pinyin=defin["Pinyin"],
                    meanings=[defin["Meaning"]],
                    tags=["bootstrap"],
                    review_in=review_in,
                ):
                    logger.error(f"Error setting the word_known status for {w} for user {username}")
                    raise Exception(f"Error updating the user database for {username}")

            logger.info(f"Set {words} for {username}")
        data = {"status": "ok"}

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# BOOTSTRAP testing end

# TESTING start
@api_view(["POST", "OPTIONS"])
def helloapi(request):
    data = {}
    if request.method == "POST":
        logger.debug(f"Received to notes helloapi: {request.data}")
        req_json = request.data

        fields = req_json
        simplified = fields["Simplified"]
        # TODO: make sure we have only one pinyin format - either 'là' or 'la4', not both!
        pinyin = fields["Pinyin"].strip(" ()")

        # TODO: this should support multiple meanings
        regex = r"(?:<style>.*</style>)"  # While using ODH - they force including css at the start of meanings...
        result = re.sub(regex, "", fields["Meaning"], 0, re.MULTILINE | re.DOTALL)
        # TODO: add my own (Hanping compatible???) tags here after stripping the existing entry stuff
        meanings = strip_tags(result).strip()

        username = request.user.username
        with Ankrobes(username) as userdb:
            status = userdb.add_ankrobes_note(simplified, pinyin, [meanings], ["chromecrobes"])

        data = {"status": "ok" if status else "ko"}

        logging.debug("I got a %s back from ankrobes", data)

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"

    return response


@api_view(["POST", "OPTIONS"])
def get_word(request):
    with Ankrobes(request.user.username) as userdb:
        w = request.data
        data = userdb.get_word(w)
        data = Ankrobes.sanitise_ankrobes_entry(data)
        return JsonResponse(data, safe=False)


# TESTING end
