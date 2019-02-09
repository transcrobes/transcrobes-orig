# -*- coding: utf-8 -*-

import json
import logging

from enrich.apis.bing import BingAPI
from enrich.models import BingAPITransliteration
from enrich.transliterate import Transliterator

logger = logging.getLogger(__name__)

TRANSLIT_PATH = '/transliterate'

class BingTransliterator(Transliterator, BingAPI):
    def __init__(self, config):
        super().__init__(config)

        self._from_script = config['from_script']
        self._to_script = config['to_script']

    # override Transliterator
    @staticmethod
    def name():
        return 'best'

    def translit_params(self):
        return {
            **self.default_params(),
            **{
                'language': self.from_lang,
                'fromScript': self._from_script,
                'toScript': self._to_script,
            }
        }

    # @ecached('_ask_bing_transliterate_{self.from_lang}_{self.to_lang}_{content}', settings.MODELS_CACHE_TIMEOUT)
    def _ask_bing_transliterate(self, content):
        found = BingAPITransliteration.objects.filter(source_text=content, from_lang=self.from_lang,
                                                      to_lang=self.to_lang)
        logger.debug("Found {} elements in db for {}".format(len(found), content))
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, TRANSLIT_PATH, self.translit_params())
            bing = BingAPITransliteration(source_text=content, response_json=bing_json,
                                          from_lang=self.from_lang, to_lang=self.to_lang)
            bing.save()
            return bing.response_json
        else:
            return found.first().response_json

    def transliterate(self, text):
        result = self._ask_bing_transliterate(text)
        jresult = json.loads(result)

        trans = jresult[0]['text']
        logging.debug("Returning Bing transliteration '{}' for '{}'".format(trans, text))
        return trans

