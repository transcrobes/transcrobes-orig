# -*- coding: utf-8 -*-

import json
import logging

from django.http import HttpResponse, JsonResponse

from rest_framework.decorators import api_view

from enrich.data import managers
from ankrobes import Ankrobes
from utils import get_username_lang_pair


logger = logging.getLogger(__name__)

# PROD API
@api_view(["POST", "OPTIONS"])
def enrich_json(request):
    logger.debug("Received to enrich json: {}".format(request.body.decode("utf-8")))
    outdata = {}
    if request.method == 'POST':
        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f'Server does not support language pair {lang_pair}', status=501)

        outdata = manager.enricher().enrich_to_json(request.body.decode("utf-8"), username, manager)

    response = JsonResponse(outdata)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

@api_view(["POST", "OPTIONS"])
def word_definitions(request):
    """
    Get the definitions from all configured dictionaries for the language pair of the user
    along with and existing note for the word. The input is in raw form (just the word, not json)
    """
    data = {}
    if request.method == 'POST':
        username = request.user.username
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return HttpResponse(f'Server does not support language pair {lang_pair}', status=501)

        w = request.body.decode("utf-8")
        t = {"word": w, "pos": "NN", "lemma": w }  # fake pos, here we don't care
        if not manager.enricher().needs_enriching(t):
            return JsonResponse({})

        # FIXME: iterate on all lookup providers for each lemma returned
        # (plus the original?)
        # lemmas = manager.word_lemmatizer().lemmatize(w)

        # get existing notes
        userdb = Ankrobes(username)
        notes = userdb.get_word(w)

        word_stats = []
        for m in manager.metadata():
            word_stats.append(m.metas_as_string(w))

        logger.debug("Received get json defs: {}".format(request.body.decode("utf-8")))
        data = {
            'defs': [_note_format(manager.default().get_standardised_defs(t), w)] + \
            [ _note_format(x.get_standardised_defs(t), w) for x in manager.secondary() ],
            'stats': word_stats,
            'fallback': _note_format(manager.default().get_standardised_fallback_defs(t), w),
            'notes': notes,
        }
        # print(data)

    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

def _note_format(std_format, chars):
    """
    This method, with unfortunately named variables...
    Basically groups the definitions by POS, so that when the client
    gets the json it can present the definitions grouped by POS.

    The idea is that it is unlikely that there will be lots of homographs
    that have the same POS and a different pronunciation, at least in Chinese

    When the pronunciation is different, two (or more) pseudo-notes (that can be added
    to the user DB) are created. The user is then presented with an option to add ONE
    of the options.
    Currently there is support for adding multiple notes with the same characters in
    about half the system. The rest will eventually need to be added, but the extra
    effort at this stage for little gain is too much to warrant it at the moment.
    """
    # TODO: The above will need to be validated!
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
@api_view(["POST", "OPTIONS"])
def text_to_std_parsed(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: {} to transform to model".format(data))

    outdata = {}
    if request.method == 'POST':
        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f'Server does not support language pair {lang_pair}', status=501)

        logging.info(f'{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}')
        outdata = json.dumps(manager.parser().parse(data), ensure_ascii=False)

    response = HttpResponse(outdata)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

@api_view(["POST", "OPTIONS"])
def bing_api(request, method):
    raise Exception('this is wrong, its supposed to call the api')

    username, lang_pair = get_username_lang_pair(request)
    manager = managers.get(lang_pair)
    if not manager:
        return HttpResponse(f'Server does not support language pair {lang_pair}', status=501)

    response = HttpResponse(manager.default().translate(request.body.decode("utf-8")))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response

@api_view(['POST', 'OPTIONS'])
def lemma_defs(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: {} to transform to model".format(data))

    outdata = {}
    if request.method == 'POST':
        username, lang_pair = get_username_lang_pair(request)
        manager = managers.get(lang_pair)
        if not manager:
            return HttpResponse(f'Server does not support language pair {lang_pair}', status=501)

        logging.info(f'{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}')

        # FIXME: iterate on all lookup providers for each lemma returned
        # (plus the original?)
        w = request.body.decode("utf-8")
        lemmas = manager.word_lemmatizer().lemmatize(w)
        print(f'lemmas are: {lemmas}')
        print(f'count of secondary is: {len(manager.secondary()[0])}')
        data = {}
        for lemma in lemmas:
            t = {"word": lemma, "pos": "NN", "lemma": lemma }  # fake pos, here we don't care

            data[lemma] = {
                'defs': [_note_format(manager.default().get_standardised_defs(t), w)] + \
                [ _note_format(x.get_standardised_defs(t), w) for x in manager.secondary() ],
                'fallback': _note_format(manager.default().get_standardised_fallback_defs(t), w),
            }
            data[f'{lemma}-raw'] = {
                'defs': [manager.default().get_standardised_defs(t)] + \
                [ x.get_standardised_defs(t) for x in manager.secondary() ],
                'fallback': manager.default().get_standardised_fallback_defs(t),
            }


    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response

# END TESTING

