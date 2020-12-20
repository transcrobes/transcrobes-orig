# -*- coding: utf-8 -*-
import json
import logging

from django.core.cache import caches

from enrich.apis.bing import BingAPI
from enrich.models import BingAPILookup, BingAPITranslation
from enrich.translate import Translator

logger = logging.getLogger(__name__)

LOOKUP_PATH = "/dictionary/lookup"
TRANSLAT_PATH = "/translate"


class BingTranslator(Translator, BingAPI):
    def __init__(self, config, transliterator):
        super().__init__(config)
        self._transliterator = transliterator
        self._inmem = config["inmem"]

    # override Translator
    @staticmethod
    def name():
        return "best"

    # public override methods
    def get_standardised_defs(self, token):
        result = self._ask_bing_lookup(token["lemma"])
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
            defie["pinyin"] = self._transliterator.transliterate(token["lemma"])
            std_format[trans["posTag"]].append(defie)

        return std_format

    def get_standardised_fallback_defs(self, token):
        result = self._ask_bing_translate(token["lemma"], is_fallback=True)
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
        std_format[0]["pinyin"] = self._transliterator.transliterate(token["lemma"])

        return {"OTHER": std_format}

    # override ???
    def translate(self, text):
        result = self._ask_bing_translate(text, is_fallback=False)
        jresult = json.loads(result)

        translation = jresult[0]["translations"][0]["text"]
        logging.debug("Returning Bing translation '%s' for '%s'", translation, text)
        return translation, jresult[0]["translations"][0].get("alignment")

    def synonyms(self, token, std_pos, max_synonyms=5):
        """
        Return the Bing reverse translations (aka synonyms) for translations in the lookup
        that have at least X similarity and a frequency of at least Y
        """
        MAX_REVERSE_TRANSLATION_SOURCES = 3

        # get the MAX_REVERSE_TRANSLATION_SOURCES most confident translations from db or cache
        # that have the POS we are looking for, in order of most confident
        jresult = json.loads(self._ask_bing_lookup(token["lemma"]))
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
            if word != token["lemma"] and word not in best_synonyms:
                best_synonyms.append(word)
            i += 1

        best_count += 1
        if len(sorted_defs) > 1:
            i = 0
            while len(best_synonyms) <= best_count and i < len(sorted_defs[1]["backTranslations"]):
                word = sorted_defs[1]["backTranslations"][i]["normalizedText"]
                if word != token["lemma"] and word not in best_synonyms:
                    best_synonyms.append(word)
                i += 1

        best_count += 1
        if len(sorted_defs) > 2:
            i = 0
            while len(best_synonyms) <= best_count and i < len(sorted_defs[2]["backTranslations"]):
                word = sorted_defs[2]["backTranslations"][i]["normalizedText"]
                if word != token["lemma"] and word not in best_synonyms:
                    best_synonyms.append(sorted_defs[2]["backTranslations"][i]["normalizedText"])
                i += 1

        return best_synonyms

    def _translate_params(self):
        return {**self.default_params(), **{"includeAlignment": True}}

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
            bing.save()
            val = bing.response_json
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
