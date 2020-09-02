# -*- coding: utf-8 -*-
import json
import logging

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view

from ankrobes import Ankrobes
from enrich.data import managers
from utils import get_username_lang_pair, note_format

logger = logging.getLogger(__name__)


def do_response(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# PROD API
@api_view(["POST", "OPTIONS"])
def enrich_json(request):
    logger.debug("Received to enrich json: %s", request.body.decode("utf-8"))
    outdata = {}
    if request.method == "POST":
        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

        outdata = manager.enricher().enrich_to_json(request.body.decode("utf-8"), username, manager)

    return do_response(JsonResponse(outdata))


@api_view(["POST", "OPTIONS"])
def word_definitions(request):
    """
    Get the definitions from all configured dictionaries for the language pair of the user
    along with an existing note for the word. The input is in raw form (just the word, not json)
    """
    data = {}
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return HttpResponse(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}", status=501
            )

        w = request.body.decode("utf-8")
        t = {"word": w, "pos": "NN", "lemma": w}  # fake pos, here we don't care
        if not manager.enricher().needs_enriching(t):
            return JsonResponse({})

        # FIXME: iterate on all lookup providers for each lemma returned
        # (plus the original?)
        # lemmas = manager.word_lemmatizer().lemmatize(w)

        # get existing notes
        userdb = Ankrobes(request.user.username)
        notes = userdb.get_word(w)

        word_stats = []
        for m in manager.metadata():
            word_stats.append(m.metas_as_string(w))

        logger.debug("Received get json defs: %s", request.body.decode("utf-8"))
        data = {
            "defs": [note_format(manager.default().get_standardised_defs(t), w)]
            + [note_format(x.get_standardised_defs(t), w) for x in manager.secondary()],
            "stats": word_stats,
            "fallback": note_format(manager.default().get_standardised_fallback_defs(t), w),
            "notes": notes,
        }

    return do_response(JsonResponse(data))


# END PROD API

# TESTING
@api_view(["POST", "OPTIONS"])
# FIXME: temp hack for pilot
def enrich_pilot_json(request):
    logger.debug("Received to enrich json: %s", request.body.decode("utf-8"))
    outdata = {}
    if request.method == "POST":
        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

        outdata = manager.enricher().enrich_to_json(request.body.decode("utf-8"), username, manager)

    return do_response(JsonResponse(outdata))


@api_view(["POST", "OPTIONS"])
def text_to_std_parsed(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: %s to transform to model", data)

    outdata = {}
    if request.method == "POST":
        _username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

        logging.info(f"{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}")
        outdata = json.dumps(manager.parser().parse(data), ensure_ascii=False)

    return do_response(HttpResponse(outdata))


@api_view(["POST", "OPTIONS"])
def bing_api(request, _method):
    # FIXME: what am I supposed to do here?
    raise Exception("this is wrong, its supposed to call the api")

    # username, lang_pair = get_username_lang_pair(request)
    # manager = managers.get(lang_pair)
    # if not manager:
    #     return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

    # response = HttpResponse(manager.default().translate(request.body.decode("utf-8")))
    # response["Access-Control-Allow-Origin"] = "*"
    # response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    # return response


@api_view(["POST", "OPTIONS"])
def lemma_defs(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: %s to transform to model", data)

    if request.method == "POST":
        _username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f"Server does not support language pair {lang_pair}", status=501)

        logging.info(f"{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}")

        # FIXME: iterate on all lookup providers for each lemma returned (plus the original?)
        w = request.body.decode("utf-8")
        lemmas = manager.word_lemmatizer().lemmatize(w)
        # print(f"lemmas are: {lemmas}")
        # print(f"count of secondary is: {len(manager.secondary()[0])}")
        data = {}
        for lemma in lemmas:
            t = {"word": lemma, "pos": "NN", "lemma": lemma}  # fake pos, here we don't care

            data[lemma] = {
                "defs": [note_format(manager.default().get_standardised_defs(t), w)]
                + [note_format(x.get_standardised_defs(t), w) for x in manager.secondary()],
                "fallback": note_format(manager.default().get_standardised_fallback_defs(t), w),
            }
            data[f"{lemma}-raw"] = {
                "defs": [manager.default().get_standardised_defs(t)]
                + [x.get_standardised_defs(t) for x in manager.secondary()],
                "fallback": manager.default().get_standardised_fallback_defs(t),
            }

    return do_response(JsonResponse(data))


# END TESTING
