# -*- coding: utf-8 -*-

import asyncio
import bisect
import json
import logging
from collections import defaultdict

from django.conf import settings
from django.core import serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from data.models import UserWord
from data.schema import DefinitionSet
from enrich import definitions_json_paths, definitions_path_json, hanzi_json_paths, hanzi_path_json
from enrich.data import managers
from enrich.models import CachedDefinition, cached_definitions, definition, reload_definitions_cache
from ndutils import do_response, note_format

logger = logging.getLogger(__name__)


# FIXME: these should absolutely not be here!
HSK_INDEX = 0
SUBTLEX_INDEX = 1


def slim_definitions(fat_definitions, user):
    output = []
    for entry in fat_definitions:
        new_entry = {"w": entry["w"], "ts": entry["ts"], "syns": entry["syns"], "defs": defaultdict(dict)}
        for provider in user.transcrober.dictionary_ordering.split(","):
            v1 = entry["defs"][provider]
            for k2, v2 in v1.items():
                new_entry["defs"][provider][k2] = [entry["nt"] for entry in v2]
        output.append(new_entry)
    return output


class KeyifyList:
    # stolen from https://gist.github.com/ericremoreynolds/2d80300dabc70eebc790
    def __init__(self, inner, key):
        self.inner = inner
        self.key = key

    def __len__(self):
        return len(self.inner)

    def __getitem__(self, k):
        return self.key(self.inner[k])


def more_recent_cached_definitions(manager, max_timestamp, user):
    latest_definition = CachedDefinition.objects.latest("cached_date")
    if max_timestamp >= latest_definition.cached_date.timestamp():
        return []

    if not cached_definitions[manager.lang_pair]:
        reload_definitions_cache(manager.from_lang, manager.to_lang)
    else:
        # side effect is to make sure local cache (cached_definitions) is up-to-date with DB
        asyncio.run(definition(manager, {"lemma": latest_definition.source_text, "pos": "NN"}))

    cache_by_date = list(cached_definitions[manager.lang_pair].values())  # ordered by cached_date already
    missing_start = bisect.bisect(KeyifyList(cache_by_date, lambda x: x["ts"]), max_timestamp)
    return slim_definitions(cache_by_date[missing_start:], user)


# PROD API
@api_view(["GET"])
@permission_classes((AllowAny,))
def load_definitions_cache(request):
    outdata = {}
    for lang_pair in managers:
        manager = managers.get(lang_pair)
        if not cached_definitions[lang_pair] or (settings.DEBUG and request.data.get("force_reload")):
            logger.info("Loading cached_definitions for lang_pair %s", lang_pair)
            reload_definitions_cache(manager.from_lang, manager.to_lang)

        outdata = {"result": "success"}

    return do_response(Response(outdata))


@api_view(["GET", "POST", "OPTIONS"])
def definitions_export_json(request, resource_path):
    # FIXME: this can raise if the file doesn't exist
    # FIXME: better perms checking for providers
    inmem_file = definitions_path_json(resource_path)
    if inmem_file:
        return Response(inmem_file)

    return Response(
        f"Server does not support user dictionaries for {request.user}",
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@api_view(["GET", "POST", "OPTIONS"])
def definitions_export_urls(request):
    inmem_file = definitions_json_paths(request.user)
    if inmem_file:
        return Response(inmem_file)

    return Response(
        f"Server does not support user dictionaries for {request.user}",
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@api_view(["GET", "POST", "OPTIONS"])
def hanzi_export_json(request, resource_path):
    # FIXME: this can raise if the file doesn't exist
    # FIXME: better perms checking for providers
    inmem_file = hanzi_path_json(resource_path)
    if inmem_file:
        return Response(inmem_file)

    return Response(
        f"Server does not support user character dictionaries for {request.user}",
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@api_view(["GET", "POST", "OPTIONS"])
def hanzi_export_urls(request):
    inmem_file = hanzi_json_paths(request.user)
    if inmem_file:
        return Response(inmem_file)

    return Response(
        f"Server does not support user character dictionaries for {request.user}",
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@api_view(["POST", "OPTIONS"])
def word_definitions(request):
    """
    Get the definitions from all configured dictionaries for the language pair of the user
    along with an existing note for the word. The input is in raw form (just the word, not json)
    """

    # FIXME: this method returns far too much useless data, and hits the DB when it doesn't
    # need to. It should also almost certainly be a direct hit to the graphql API, but that
    # will require some work and this "Just Works"...
    data = {}
    if request.method == "POST":
        transcrober = request.user.transcrober
        manager = managers.get(transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        w = request.data.get("data")
        if not w:
            return Response(
                'Incorrectly formed query, you must provide a JSON like { "data": "好" }"',
                status=status.HTTP_400_BAD_REQUEST,
            )
        t = {"word": w, "pos": "NN", "lemma": w}  # fake pos, here we don't care

        if not manager.enricher().needs_enriching(t) or manager.enricher().clean_text(w) != w:
            return Response({})

        # FIXME: iterate on all lookup providers for each lemma returned
        # (plus the original?)
        # lemmas = manager.word_lemmatizer().lemmatize(w)

        # this gives us the JSON version and ensures that it has been loaded to the DB
        json_definition = asyncio.run(definition(manager, t))

        providers = transcrober.dictionary_ordering.split(",")
        obj = CachedDefinition.objects.filter(
            source_text=w, from_lang=transcrober.from_lang, to_lang=transcrober.to_lang
        ).first()
        graphql_definition = DefinitionSet.from_model_asdict(obj, providers)

        modelStats = next(
            iter(
                json.loads(
                    serializers.serialize(
                        "json",
                        UserWord.objects.filter(user=request.user, word__source_text=w),
                        fields=("nb_seen", "last_seen", "nb_checked", "last_checked"),
                    )
                )
            ),
            None,
        )
        data = {
            "json_definition": json_definition,
            "definition": graphql_definition,
            "model_stats": [modelStats["fields"]] if modelStats else [],
        }

    return do_response(Response(data))


@api_view(["POST", "OPTIONS"])
def slim_def(request):
    logger.debug("Received to enrich json: %s", request.data)
    outdata = {}
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        word = request.data.get("data")
        if not word:
            return Response(
                'Incorrectly formed query, you must provide a JSON like { "data": "好" }"',
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = {"word": word, "pos": "NN", "lemma": word}  # fake pos, here we don't care
        if not manager.enricher().needs_enriching(token):
            return Response({})

        outdata = asyncio.run(definition(manager, token))

    return do_response(Response(outdata))


@api_view(["POST", "OPTIONS"])
def aenrich_json(request):
    logger.debug("Received to new enrich json: %s", request.data)
    outdata = {}
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        text = request.data.get("data")
        if not text:
            return Response(
                'Incorrectly formed query, you must provide a JSON like { "data": "好" }"',
                status=status.HTTP_400_BAD_REQUEST,
            )
        outdata = asyncio.run(manager.enricher().aenrich_to_json(text, manager, deep_transliterations=True))
    return do_response(Response(outdata))


# END PROD API


# TESTING API
@api_view(["POST", "OPTIONS"])
def lemma_defs(request):
    data = request.body.decode("utf-8")
    logger.debug("Received text: %s to transform to model", data)

    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        logging.info(f"{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}")

        # FIXME: iterate on all lookup providers for each lemma returned (plus the original?)
        w = request.body.decode("utf-8")
        lemmas = manager.word_lemmatizer().lemmatize(w)
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

    return do_response(Response(data))


@api_view(["POST", "OPTIONS"])
def text_to_std_parsed(request):

    # data = request.body.decode("utf-8")
    # logger.debug("Received text: %s to transform to model", data)

    outdata = {}
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        text = request.data.get("data")
        if not text:
            return Response(
                'Incorrectly formed query, you must provide a JSON like { "data": "好" }"',
                status=status.HTTP_400_BAD_REQUEST,
            )

        logging.info(f"{manager.from_lang} to {manager.to_lang} with {manager.parser().__class__.__name__}")
        # outdata = json.dumps(manager.parser().parse(data), ensure_ascii=False)
        outdata = manager.parser().parse(text)

    return do_response(Response(outdata))


@api_view(["POST", "OPTIONS"])
# FIXME: temp hack for pilot
def enrich_pilot_json(request):
    logger.debug("Received to enrich json: %s", request.body.decode("utf-8"))
    outdata = {}
    if request.method == "POST":
        manager = managers.get(request.user.transcrober.lang_pair())
        if not manager:
            return Response(
                f"Server does not support language pair {request.user.transcrober.lang_pair()}",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        outdata = manager.enricher().enrich_to_json(request.body.decode("utf-8"), request.user, manager)

    return do_response(Response(outdata))


# END TESTING
