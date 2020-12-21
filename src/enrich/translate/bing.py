# -*- coding: utf-8 -*-
import json
import logging
from collections import defaultdict

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import caches
from django.db.utils import IntegrityError

from enrich.apis.bing import BingAPI
from enrich.models import BingAPILookup, BingAPITranslation
from enrich.translate import Translator
from ndutils import lemma

logger = logging.getLogger(__name__)

LOOKUP_PATH = "/dictionary/lookup"
TRANSLAT_PATH = "/translate"


class BingTranslator(Translator, BingAPI):
    SHORT_NAME = "mst"
    FALLBACK_SHORT_NAME = "fbk"

    def __init__(self, config, transliterator):
        super().__init__(config)
        self._transliterator = transliterator
        self._inmem = config["inmem"]

    # override Translator
    @staticmethod
    def name():
        return BingTranslator.SHORT_NAME

    # public override methods
    def get_standardised_defs(self, token):
        result = self._ask_bing_lookup(lemma(token))
        jresult = json.loads(result)
        bing = jresult[0]["translations"]
        std_format = {}

        for trans in bing:
            if not trans["posTag"] in std_format:
                std_format[trans["posTag"]] = []
            defie = {
                "upos": trans["posTag"],
                "opos": trans["posTag"],
                "normalizedTarget": trans["normalizedTarget"],
                "confidence": trans["confidence"],
                "trans_provider": "BING",
            }
            defie["p"] = self._transliterator.transliterate(lemma(token))
            std_format[trans["posTag"]].append(defie)

        return std_format

    async def aget_standardised_defs(self, token):
        result = await self._aask_bing_lookup(lemma(token))
        try:
            jresult = json.loads(result)
        except json.decoder.JSONDecodeError:
            logger.error(result)
            raise
        bing = jresult[0]["translations"]
        std_format = {}

        for trans in bing:
            if not trans["posTag"] in std_format:
                std_format[trans["posTag"]] = []
            defie = {
                "upos": trans["posTag"],
                "opos": trans["posTag"],
                "normalizedTarget": trans["normalizedTarget"],
                "confidence": trans["confidence"],
                "trans_provider": "BING",
            }

            defie["p"] = await self._transliterator.atransliterate(lemma(token))
            std_format[trans["posTag"]].append(defie)

        return std_format

    def get_standardised_fallback_defs(self, token):
        result = self._ask_bing_translate(lemma(token), is_fallback=True)
        jresult = json.loads(result)

        std_format = [
            {
                "upos": "OTHER",
                "opos": "OTHER",
                "normalizedTarget": jresult[0]["translations"][0]["text"],
                "confidence": 0,
                "trans_provider": "BING-DEFAULT",
            }
        ]
        std_format[0]["p"] = self._transliterator.transliterate(lemma(token))

        return {"OTHER": std_format}

    async def aget_standardised_fallback_defs(self, token):
        result = await self._aask_bing_translate(lemma(token), is_fallback=True)

        try:
            jresult = json.loads(result)
        except json.decoder.JSONDecodeError:
            logger.error(f"{lemma(token)} is loaded with bing json {result=}")
            raise

        try:
            translation = jresult[0]["translations"][0]["text"]
        except IndexError:
            logger.error(f"{lemma(token)} is translated with bing json {result=}")
            raise

        std_format = [
            {
                "upos": "OTHER",
                "opos": "OTHER",
                "normalizedTarget": translation,
                "confidence": 0,
                "trans_provider": "BING-DEFAULT",
            }
        ]
        std_format[0]["p"] = await self._transliterator.atransliterate(lemma(token))

        return {"OTHER": std_format}

    # override ???
    def translate(self, text):
        result = self._ask_bing_translate(text, is_fallback=False)
        jresult = json.loads(result)

        translation = jresult[0]["translations"][0]["text"]
        logging.debug("Returning Bing translation '%s' for '%s'", translation, text)
        return translation, jresult[0]["translations"][0].get("alignment")

    # override ???
    async def atranslate(self, text):
        jresult = json.loads(await self._aask_bing_translate(text, is_fallback=False))

        translation = jresult[0]["translations"][0]["text"]
        logging.debug("Returning Bing translation '%s' for '%s'", translation, text)
        return translation, jresult[0]["translations"][0].get("alignment")

    def synonyms(self, token, std_pos, max_synonyms=5):
        """
        Return the Bing reverse translations (aka synonyms) for translations in the lookup
        that have at least X similarity and a frequency of at least Y for pos std_pos
        """
        MAX_REVERSE_TRANSLATION_SOURCES = 3

        # get the MAX_REVERSE_TRANSLATION_SOURCES most confident translations from db or cache
        # that have the POS we are looking for, in order of most confident
        jresult = json.loads(self._ask_bing_lookup(lemma(token)))
        same_pos = [x for x in jresult[0]["translations"] if x["posTag"] == std_pos]

        if not same_pos:
            return []  # or None?

        sorted_defs = sorted(same_pos, key=lambda i: i["confidence"], reverse=True)[:MAX_REVERSE_TRANSLATION_SOURCES]

        # From those upto MAX_REVERSE_TRANSLATION_SOURCES found, get the most frequent reverse translations,
        # with (hopefully? is my algo ok???) upto max_synonyms, but leaving a single spot free if we have
        # sources left... Basically, if we want 5 and MAX_REVERSE_TRANSLATION_SOURCES is 3, then get 3 from the
        # first and 1 each from sources two and three
        best_count = MAX_REVERSE_TRANSLATION_SOURCES
        best_synonyms = []
        i = 0
        sorted_bts = sorted(sorted_defs[0]["backTranslations"], key=lambda i: i["frequencyCount"], reverse=True)
        while len(best_synonyms) <= best_count and i < len(sorted_bts):
            word = sorted_defs[0]["backTranslations"][i]["normalizedText"]
            if word != lemma(token) and word not in best_synonyms:
                best_synonyms.append(word)
            i += 1

        best_count += 1
        if len(sorted_defs) > 1:
            i = 0
            while len(best_synonyms) <= best_count and i < len(sorted_defs[1]["backTranslations"]):
                word = sorted_defs[1]["backTranslations"][i]["normalizedText"]
                if word != lemma(token) and word not in best_synonyms:
                    best_synonyms.append(word)
                i += 1

        best_count += 1
        if len(sorted_defs) > 2:
            i = 0
            while len(best_synonyms) <= best_count and i < len(sorted_defs[2]["backTranslations"]):
                word = sorted_defs[2]["backTranslations"][i]["normalizedText"]
                if word != lemma(token) and word not in best_synonyms:
                    best_synonyms.append(sorted_defs[2]["backTranslations"][i]["normalizedText"])
                i += 1

        return best_synonyms

    async def apos_synonyms(self, token):  # noqa:C901
        """
        Return the Bing reverse translations (aka synonyms) for translations in the lookup
        """
        MAX_REVERSE_TRANSLATION_SOURCES = 3

        # get the MAX_REVERSE_TRANSLATION_SOURCES most confident translations from db or cache
        # that have the POS we are looking for, in order of most confident
        jresult = json.loads(await self._aask_bing_lookup(lemma(token)))
        if len(jresult[0]["translations"]) < 1:
            return {}

        translations_by_pos = defaultdict(list)

        for val in jresult[0]["translations"]:
            translations_by_pos[val["posTag"]].append(val)

        all_pos_synonyms = {}
        for pos, same_pos in translations_by_pos.items():
            sorted_defs = sorted(same_pos, key=lambda i: i["confidence"], reverse=True)[
                :MAX_REVERSE_TRANSLATION_SOURCES
            ]

            # From those upto MAX_REVERSE_TRANSLATION_SOURCES found, get the most frequent reverse translations,
            # with (hopefully? is my algo ok???) upto max_synonyms, but leaving a single spot free if we have
            # sources left... Basically, if we want 5 and MAX_REVERSE_TRANSLATION_SOURCES is 3, then get 3 from the
            # first and 1 each from sources two and three
            best_count = MAX_REVERSE_TRANSLATION_SOURCES
            best_synonyms = []
            i = 0
            sorted_bts = sorted(sorted_defs[0]["backTranslations"], key=lambda i: i["frequencyCount"], reverse=True)
            while len(best_synonyms) <= best_count and i < len(sorted_bts):
                word = sorted_defs[0]["backTranslations"][i]["normalizedText"]
                if word != lemma(token) and word not in best_synonyms:
                    best_synonyms.append(word)
                i += 1

            best_count += 1
            if len(sorted_defs) > 1:
                i = 0
                while len(best_synonyms) <= best_count and i < len(sorted_defs[1]["backTranslations"]):
                    word = sorted_defs[1]["backTranslations"][i]["normalizedText"]
                    if word != lemma(token) and word not in best_synonyms:
                        best_synonyms.append(word)
                    i += 1

            best_count += 1
            if len(sorted_defs) > 2:
                i = 0
                while len(best_synonyms) <= best_count and i < len(sorted_defs[2]["backTranslations"]):
                    word = sorted_defs[2]["backTranslations"][i]["normalizedText"]
                    if word != lemma(token) and word not in best_synonyms:
                        best_synonyms.append(sorted_defs[2]["backTranslations"][i]["normalizedText"])
                    i += 1

            if best_synonyms:
                all_pos_synonyms[pos] = best_synonyms

        return all_pos_synonyms

    def _translate_params(self):
        return {**self.default_params(), **{"includeAlignment": "true"}}

    def _ask_bing_lookup(self, content):
        if not content:  # calling the api with empty string will put rubbish in the DB
            return None

        val = None
        if self._inmem:
            val = caches["bing_lookup"].get(content)
            if val:
                return val

        found = BingAPILookup.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)
        logger.debug("Found %s elements in db for %s", len(found), content)
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, LOOKUP_PATH, self.default_params())
            bing = BingAPILookup(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            try:
                bing.save()
                val = bing.response_json
            except IntegrityError:
                # we just tried saving an entry that already exists, try to get again
                found = BingAPILookup.objects.filter(
                    source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
                )
                if found.count() > 0:
                    val = found.first().response_json
                else:
                    raise
        else:
            val = found.first().response_json  # TODO: be better, just being dumb for the moment

        if self._inmem:
            caches["bing_lookup"].set(content, val)
        return val

    def _ask_bing_translate(self, content, is_fallback=False):
        if not content:  # calling the api with empty string will put rubbish in the DB
            return None

        val = None
        if self._inmem and is_fallback:
            val = caches["bing_translate"].get(content)
            if val:
                return val

        found = BingAPITranslation.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)

        logger.debug("Found %s elements in db for %s", len(found), content)
        if len(found) == 0:

            bing_json = self._ask_bing_api(content, TRANSLAT_PATH, self._translate_params())
            bing = BingAPITranslation(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            bing.save()
            val = bing.response_json
        else:
            val = found.first().response_json  # TODO: be better, just being dumb for the moment

        if self._inmem and is_fallback:
            caches["bing_translate"].set(content, val)
        return val

    async def _aask_bing_lookup(self, content):
        if not content:  # calling the api with empty string will put rubbish in the DB
            return None

        val = None
        if self._inmem:
            val = caches["bing_lookup"].get(content)
            if val:
                return val

        found = BingAPILookup.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)
        found_count = await sync_to_async(found.count, thread_sensitive=settings.THREAD_SENSITIVE)()

        logger.debug("Found %s elements in db for %s", found_count, content)
        if found_count == 0:
            bing_json = await self._aask_bing_api(content, LOOKUP_PATH, self.default_params())
            bing = BingAPILookup(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            try:
                await sync_to_async(bing.save, thread_sensitive=settings.THREAD_SENSITIVE)()
                val = bing.response_json
            except IntegrityError:
                # we just tried saving an entry that already exists, try to get again
                logger.debug(
                    "Tried saving BingAPILookup for %s that already exists, try to get again", bing.source_text
                )
                found = BingAPILookup.objects.filter(
                    source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
                )
                if await sync_to_async(found.count, thread_sensitive=settings.THREAD_SENSITIVE)() > 0:
                    val = (await sync_to_async(found.first, thread_sensitive=settings.THREAD_SENSITIVE)()).response_json
                else:
                    raise
        else:
            val = (
                await sync_to_async(found.first, thread_sensitive=settings.THREAD_SENSITIVE)()
            ).response_json  # TODO: be better, just being dumb for the moment

        if self._inmem:
            caches["bing_lookup"].set(content, val)
        return val

    async def _aask_bing_translate(self, content, is_fallback=False):
        if not content:  # calling the api with empty string will put rubbish in the DB
            return None

        val = None
        if self._inmem and is_fallback:
            val = caches["bing_translate"].get(content)
            if val:
                return val

        found = BingAPITranslation.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)

        found_count = await sync_to_async(found.count, thread_sensitive=settings.THREAD_SENSITIVE)()

        logger.debug("Found %s elements in db for %s", found_count, content)

        if found_count == 0:
            bing_json = await self._aask_bing_api(content, TRANSLAT_PATH, self._translate_params())
            bing = BingAPITranslation(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            try:
                await sync_to_async(bing.save, thread_sensitive=settings.THREAD_SENSITIVE)()
                val = bing.response_json
            except IntegrityError:
                # we just tried saving an entry that already exists, try to get again
                logger.debug(
                    "Tried saving BingAPITranslation for %s that already exists, try to get again", bing.source_text
                )
                found = BingAPITranslation.objects.filter(
                    source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
                )
                if await sync_to_async(found.count, thread_sensitive=settings.THREAD_SENSITIVE)() > 0:
                    val = (await sync_to_async(found.first, thread_sensitive=settings.THREAD_SENSITIVE)()).response_json
                else:
                    raise
        else:
            val = (
                await sync_to_async(found.first, thread_sensitive=settings.THREAD_SENSITIVE)()
            ).response_json  # TODO: be better, just being dumb for the moment

        if self._inmem and is_fallback:
            caches["bing_translate"].set(content, val)
        return val

    # override Translator
    async def sound_for(self, token):
        return await self._transliterator.transliterate(token)
