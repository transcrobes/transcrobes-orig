# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
from django.conf import settings

import logging
import json
import time
import re

from enrich.nlp.provider import OpenNLPProvider
from enrich.translate.translator import BingTranslator, ABCDictTranslator, CCCedictTranslator, hsk_dict, subtlex
from enrich.enricher import enrich_to_json
from ankrobes import AnkrobesServer


logger = logging.getLogger(__name__)
has_chinese_chars = re.compile('[\u4e00-\u9fa5]+')

# PROD API
@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def enrich_json(request):
    logger.debug("Received to enrich json: {}".format(request.body.decode("utf-8")))
    data = {}
    if request.method == 'POST':
        data = enrich_to_json(request.body.decode("utf-8"))

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def text_to_corenlp(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: {} to transform to model".format(data))

    corenlp = OpenNLPProvider()

    response = HttpResponse(json.dumps(corenlp.parse(data), ensure_ascii=False))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt  # TODO: this doesn't work so I had to disable csrf - FIXME
def word_definitions(request):
    data = {}
    if request.method == 'POST':
        w = request.body.decode("utf-8")
        t = {"word": w, "pos": "NN" }  # fake pos, here we don't care
        if not has_chinese_chars.match(t["word"]):
            logger.debug("Nothing to translate, exiting: {}".format(w))
            return JsonResponse({})

        # get existing notes
        # TODO: the settings shouldn't be here, they should probably be done in the class
        server = AnkrobesServer(settings.ANKROBES_USERNAME, settings.ANKROBES_PASSWORD)
        server.hostKey(settings.ANKROBES_USERNAME, settings.ANKROBES_PASSWORD)
        notes = server.get_word(w)

        online_translator = BingTranslator()
        cedict = CCCedictTranslator()
        abcdict = ABCDictTranslator()
        word_stats = {
            'hsk': hsk_dict[w] if w in hsk_dict else None,
            'freq': subtlex[w] if w in subtlex else None,
        }

        logger.debug("Received get json defs: {}".format(request.body.decode("utf-8")))
        data = {
            'defs': [_note_format(online_translator.get_standardised_defs(t, True), w),
                     _note_format(abcdict.get_standardised_defs(t, True), w),
                      _note_format(cedict.get_standardised_defs(t, True), w)],
            'stats': word_stats,
            'fallback': _note_format(online_translator.get_standardised_fallback_defs(t, True), w),
            'notes': notes,
        }

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

def _note_format(std_format, chars):
    by_py = {}
    for pos, defs in std_format.items():
        for defie in defs:
            if not defie['pinyin'] in by_py:
                by_py[defie['pinyin']] = {}
            if not defie['opos'] in by_py[defie['pinyin']]:
                by_py[defie['pinyin']][defie['opos']] = []
            by_py[defie['pinyin']][defie['opos']].append(defie)

    json_notes = []
    for py, defs in by_py.items():
        json_note = {
            'Simplified': chars,
            'Pinyin': py,
        }
        ds = []
        for pos, defies in defs.items():
            ds.append("{} {}".format(pos, ", ".join(d['normalizedTarget'] for d in defies)))

        json_note['Meaning'] = "; ".join(ds)
        json_notes.append(json_note)
    return json_notes
# END PROD API

# TESTING
def bing_api(request, method):

    translator = BingTranslator()

    response = HttpResponse(translator._ask_bing_api(request.body.decode("utf-8"), method))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response

def bing_lookup(request):

    translator = BingTranslator()

    response = HttpResponse(translator._ask_bing_lookup(request.body.decode("utf-8")))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response

# END TESTING
