# -*- coding: utf-8 -*-

import json
import logging

from enrich.apis.bing import BingAPI
from enrich.models import BingAPILookup, BingAPITranslation
from enrich.translate import Translator

# from easy_cache import ecached  # weird, again, makes things SUPER slow


logger = logging.getLogger(__name__)

LOOKUP_PATH = "/dictionary/lookup"
TRANSLAT_PATH = "/translate"


class BingTranslator(Translator, BingAPI):
    def __init__(self, config, transliterator):
        super().__init__(config)
        self._transliterator = transliterator

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
        result = self._ask_bing_translate(token["lemma"])
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
        result = self._ask_bing_translate(text)
        jresult = json.loads(result)

        translation = jresult[0]["translations"][0]["text"]
        logging.debug("Returning Bing translation '%s' for '%s'", translation, text)
        return translation, jresult[0]["translations"][0].get("alignment")

    def _translate_params(self):
        return {**self.default_params(), **{"includeAlignment": True}}

    # @ecached('_ask_bing_lookup_{self.from_lang}_{self.to_lang}_{content}', settings.MODELS_CACHE_TIMEOUT)
    def _ask_bing_lookup(self, content):
        found = BingAPILookup.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)
        logger.debug("Found %s elements in db for %s", len(found), content)
        if len(found) == 0:
            print("looking up", content)
            bing_json = self._ask_bing_api(content, LOOKUP_PATH, self.default_params())
            bing = BingAPILookup(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )

            bing.save()
            # with open(f'{bing.pk}.{content}.json', 'w') as bing_lookup:
            #     bing_lookup.write(bing_json)

            return bing.response_json

        return found.first().response_json  # TODO: be better, just being dumb for the moment

    # @ecached('_ask_bing_translate_{self.from_lang}_{self.to_lang}_{content}', settings.MODELS_CACHE_TIMEOUT)
    def _ask_bing_translate(self, content):
        found = BingAPITranslation.objects.filter(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)
        logger.debug("Found %s elements in db for %s", len(found), content)
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, TRANSLAT_PATH, self._translate_params())
            bing = BingAPITranslation(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            bing.save()
            # with open(f'{bing.pk}.{content}.json', 'w') as bing_lookup:
            #     bing_lookup.write(bing_json)

            return bing.response_json

        return found.first().response_json
