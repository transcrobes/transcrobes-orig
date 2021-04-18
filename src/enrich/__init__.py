# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod

from asgiref.sync import SyncToAsync
from django.conf import settings
from django.db import close_old_connections
from django.template import Context, Template
from django.urls import reverse

from ndutils import lemma

default_app_config = "enrich.apps.EnrichConfig"
logger = logging.getLogger(__name__)

DEFINITIONS_JSON_CACHE_FILE_PREFIX_REGEX = r"definitions-\d{10}\.\d{1,8}-\d{1,8}-"
DEFINITIONS_JSON_CACHE_FILE_SUFFIX_REGEX = r"\.json"
DEFINITIONS_JSON_CACHE_DIR_SUFFIX_REGEX = r"\_json"
HANZI_JSON_CACHE_FILE_REGEX = r"hanzi-\d{3}\.json"


# START Stolen from https://github.com/django/channels/blob/ece488b31b4e20a55e52948f21622da3e38223cb/channels/db.py
class DatabaseSyncToAsync(SyncToAsync):
    """
    SyncToAsync version that cleans up old database connections when it exits.
    !!!
    """

    def thread_handler(self, loop, *args, **kwargs):
        close_old_connections()
        try:
            return super().thread_handler(loop, *args, **kwargs)
        finally:
            close_old_connections()


database_sync_to_async = DatabaseSyncToAsync
# END Stolen


def latest_definitions_json_dir_path(user) -> str:
    find_re = (
        DEFINITIONS_JSON_CACHE_FILE_PREFIX_REGEX
        + "-".join(user.transcrober.dictionary_ordering.split(","))
        + DEFINITIONS_JSON_CACHE_DIR_SUFFIX_REGEX
    )
    logger.debug(f"Looking for the latest definitions dir using regex: {find_re=}")
    try:
        return sorted(
            [f.path for f in os.scandir(settings.DEFINITIONS_CACHE_DIR) if f.is_dir() and re.match(find_re, f.name)]
        )[-1]
    except IndexError:
        logger.error(
            "Unable to find a definitions file for user %s using %s with re %s",
            user,
            user.transcrober.dictionary_ordering,
        )
    return ""


def definitions_json_paths(user) -> dict:
    jsons_path = latest_definitions_json_dir_path(user)
    find_re = r"\d{1,8}\.json"

    # os.path.join("/enrich/exports", os.path.basename(jsons_path))
    exports_base = reverse("exports_json", args=[os.path.basename(jsons_path)])
    logger.debug(f"Getting list of export files in dir: {exports_base=}")
    files = sorted(
        [
            os.path.join(exports_base, os.path.basename(f.path))
            for f in os.scandir(jsons_path)
            if f.is_file() and re.match(find_re, f.name)
        ]
    )
    logger.debug("The latest export files for user %s are %s", user, files)

    return files


def definitions_path_json(path) -> dict:
    json_path = os.path.join(settings.DEFINITIONS_CACHE_DIR, path)
    with open(json_path) as fh:
        return json.load(fh)


def hanzi_json_paths(user) -> dict:
    files = sorted(
        [
            reverse("hzexports_json", args=[os.path.basename(f.path)])
            for f in os.scandir(settings.HANZI_CACHE_DIR)
            if f.is_file() and re.match(HANZI_JSON_CACHE_FILE_REGEX, f.name)
        ]
    )
    logger.debug("The latest hanzi export files for user %s are %s", user, files)

    return files


def hanzi_path_json(path) -> dict:
    json_path = os.path.join(settings.HANZI_CACHE_DIR, path)
    with open(json_path) as fh:
        return json.load(fh)


class TransliterationException(Exception):
    pass


class Enricher(ABC):
    ##
    ## Abstract methods
    ##
    @abstractmethod
    def needs_enriching(self, token):
        pass

    @abstractmethod
    def _add_transliterations(self, sentence, transliterator):
        pass

    @abstractmethod
    def _set_best_guess(self, sentence, token):
        pass

    @abstractmethod
    def _set_best_guess_async(self, sentence, token, token_definition):
        pass

    @abstractmethod
    def _cleaned_sentence(self, sentence):
        pass

    @abstractmethod
    def get_simple_pos(self, token):
        pass

    @abstractmethod
    def clean_text(self, text):
        pass

    ##
    ## Private/Protected methods
    ##
    @staticmethod
    def _text_from_sentence(sentence):
        text = ""
        tokens = sentence.get("t") or sentence["tokens"]
        for token in tokens:
            text += token.get("before", "") + (token.get("ot") or token.get("l") or token["originalText"])
        text += tokens[-1].get("after", "")
        return text

    ##
    ## Public methods
    ##
    def __init__(self, config):
        self._config = config

    @staticmethod
    def is_clean(token):
        word = lemma(token)
        if word.startswith("<") and word.endswith(">"):  # html
            logger.debug("Looks like '%s' only has html, not adding to translatables", word)
            return False
        return True

    async def aenrich_to_combined_json(self, text, manager, deep_transliterations=False):
        logging.debug("Attempting to async slim enrich: '%s'", text)

        clean_text = self.clean_text(text)
        combined = await self._aenrich_slim_model(
            manager.parser().parse_slim(clean_text), manager, deep_transliterations
        )

        ## Here we are still using the old way of generating which adds new properties in-place
        ## so we split to multiple files
        help_model = {"s": []}
        for sentence in combined:
            hsentence = []
            for token in sentence["t"]:
                if "p" in token:  # there is maybe a cleaner way to do this
                    hsentence.append(dict((d, token.pop(d)) for d in ["p", "bg"]))
                else:
                    hsentence.append({})
            help_model["s"].append({"t": hsentence, "l1": sentence.pop("l1")})

        parsed_model = {"s": combined}
        match = re.match(r"^\s+", text)
        if match:
            parsed_model["sws"] = match.group(0)
        match = re.search(r"\s+$", text)
        if match:
            parsed_model["ews"] = match.group(0)
        timestamp = time.time_ns()
        return [{timestamp: parsed_model}, {timestamp: help_model}]

    async def aenrich_parse_to_aids_json(self, timestamp, slim_model, manager, deep_transliterations=False):
        logging.debug("Attempting to async slim_model enrich: '%s'", slim_model)

        combined = await self._aenrich_slim_model(slim_model, manager, deep_transliterations)

        ## Here we are still using the old way of generating which adds new properties in-place
        ## so we split to multiple files
        aids_model = {"s": []}
        for sentence in combined:
            hsentence = []
            for token in sentence["t"]:
                if "p" in token:  # there is maybe a cleaner way to do this
                    hsentence.append(dict((d, token.pop(d)) for d in ["p", "bg"]))
                else:
                    hsentence.append({})
            aids_model["s"].append({"t": hsentence, "l1": sentence.pop("l1")})

        return {timestamp: aids_model}

    async def aenrich_to_json(self, text, manager, deep_transliterations=False):
        logging.debug("Attempting to async enrich: '%s'", text)

        clean_text = self.clean_text(text)
        model = {"s": await self._aenrich_model(manager.parser().parse(clean_text), manager, deep_transliterations)}
        match = re.match(r"^\s+", text)
        if match:
            model["sws"] = match.group(0)
        match = re.search(r"\s+$", text)
        if match:
            model["ews"] = match.group(0)

        # FIXME: we should be able to accept a list of fields to return, rather than filtering
        # via hardcode here
        for sentence in model["s"]:
            slim_tokens = []
            for token in sentence["tokens"]:
                new_token = {
                    "lemma": lemma(token),
                }
                # if "id" in token:
                if "bg" in token:
                    # new_token["id"] = token["id"]
                    new_token["p"] = token["pinyin"]
                    new_token["np"] = token["np"]
                    new_token["pos"] = token["pos"]
                    # new_token["bg"] = {"nt": token["bg"]["nt"]}
                    new_token["bg"] = token["bg"]["nt"]

                slim_tokens.append(new_token)
            sentence["tokens"] = slim_tokens
        model["id"] = time.time_ns()
        return model

    @staticmethod
    def enriched_text_fragment(text, model):
        # FIXME: this is probably dangerous, I am not escaping properly
        logging.debug("Attempting to async enrich to html: '%s'", text)
        template = Template("<enriched-text-fragment data-model='{{ model }}'>{{ text }}</enriched-text-fragment>")
        context = Context({"model": json.dumps(model), "text": text})
        return template.render(context)

    @staticmethod
    def _clean_token(token):
        for key in ["index", "word", "originalText", "characterOffsetBegin", "characterOffsetEnd", "pos"]:
            try:
                del token[key]
            except KeyError:
                pass

    def slim_parse(self, fat_model):
        slim_model = []
        for sentence in fat_model["sentences"]:
            slim_sentence = []
            for token in sentence["tokens"]:
                if self.is_clean(token) and self.needs_enriching(token):
                    slim_sentence.append({"l": token["lemma"], "pos": token["pos"]})
                else:
                    slim_sentence.append({"l": token["lemma"]})
            slim_model.append({"t": slim_sentence})
        return slim_model

    ##
    ## FIXME: move - put here for easy navigation
    async def _aenrich_model(self, model, manager, deep_transliterations):
        sentences = await asyncio.gather(
            *[self._aenrich_sentence(sentence, manager, deep_transliterations) for sentence in model["sentences"]],
        )
        return sentences

    async def _aenrich_sentence(self, sentence, manager, deep_transliterations):
        # FIXME: find out how to put this in the header without a circular dep
        from enrich.models import definition  # pylint: disable=C0415

        if deep_transliterations:
            # transliterate the sentence as a whole - this will almost always hit the external API and
            # the lift in accuracy is likely only for a few well known words - deep is definitely better
            # but much slower and actually costs real money
            # FIXME: actually we could check whether we've already transliterated the same/a similar sentence
            # rather than do a whole new attempt, still without using translation credit...
            await self._aadd_transliterations(sentence, manager.transliterator())
        else:
            for token in sentence["tokens"]:
                token["pinyin"] = (await manager.transliterator().atransliterate(token["originalText"])).split()

        logger.debug("Looking for tokens to translate in %s", sentence)
        original_sentence = self._text_from_sentence(sentence).strip()

        sentence["os"] = original_sentence  # used to be _cleaned_sentence
        # We aren't currently using the alignment, so ignore
        # sentence["l1"], sentence["al"] = await manager.default().atranslate(original_sentence)
        sentence["l1"], _ = await manager.default().atranslate(original_sentence)

        for token in sentence["tokens"]:
            if not self.is_clean(token) or not self.needs_enriching(token):
                continue
            token_definition = await definition(manager, token)
            token["id"] = token_definition["id"]  # BingAPILookup id
            token["np"] = self.get_simple_pos(token)  # Normalised POS

            # FIXME: maybe reenable the check - make sure this isn't too exp to do to all entries
            # if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
            # get the best guess for the definition of the word given the context of the sentence

            self._set_best_guess_async(sentence, token, token_definition["defs"])

        return sentence

    ##
    ## FIXME: move - put here for easy navigation
    async def _aenrich_slim_model(self, slim_model, manager, deep_transliterations):
        # FIXME: clean later
        model = slim_model["s"] if isinstance(slim_model, dict) else slim_model
        return await asyncio.gather(
            *[self._aenrich_slim_sentence(sentence, manager, deep_transliterations) for sentence in model],
        )

    async def _aenrich_slim_sentence(self, sentence, manager, deep_transliterations):
        # FIXME: find out how to put this in the header without a circular dep
        from enrich.models import definition  # pylint: disable=C0415

        if deep_transliterations:
            # transliterate the sentence as a whole - this will almost always hit the external API and
            # the lift in accuracy is likely only for a few well known words - deep is definitely better
            # but much slower and actually costs real money
            # FIXME: actually we could check whether we've already transliterated the same/a similar sentence
            # rather than do a whole new attempt, still without using translation credit...
            await self._aadd_slim_transliterations(sentence, manager.transliterator())

        logger.debug("Looking for tokens to translate in %s", sentence)

        original_sentence = self._text_from_sentence(sentence).strip()

        ## Can recreate in the client, storing here is just a waste
        # sentence["os"] = original_sentence  # used to be _cleaned_sentence

        # We aren't currently using the alignment, so ignore
        # sentence["l1"], sentence["al"] = await manager.default().atranslate(original_sentence)
        sentence["l1"], _ = await manager.default().atranslate(original_sentence)

        for token in sentence["t"]:
            if not self.is_clean(token) or not self.needs_enriching(token):
                continue
            if not deep_transliterations:
                transliteratable = token.get("ot") or token.get("l")
                token["p"] = (await manager.transliterator().atransliterate(transliteratable)).split()

            token_definition = await definition(manager, token)
            # token["id"] = token_definition["id"]  # BingAPILookup id
            # token["np"] = self.get_simple_pos(token)  # Normalised POS

            # FIXME: maybe reenable the check - make sure this isn't too exp to do to all entries
            # if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
            # get the best guess for the definition of the word given the context of the sentence

            self._set_slim_best_guess_async(sentence, token, token_definition["defs"])

        return sentence
