# -*- coding: utf-8 -*-

import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import caches
from django.db.utils import IntegrityError

from enrich.apis.bing import BingAPI
from enrich.models import BingAPITransliteration
from enrich.transliterate import Transliterator

logger = logging.getLogger(__name__)

TRANSLIT_PATH = "/transliterate"


class BingTransliterator(Transliterator, BingAPI):
    def __init__(self, config):
        super().__init__(config)
        self._from_script = config["from_script"]
        self._to_script = config["to_script"]
        self._inmem = config["inmem"]

    # override Transliterator
    @staticmethod
    def name():
        return "best"

    def translit_params(self):
        return {
            **self.default_params(),
            **{"language": self.from_lang, "fromScript": self._from_script, "toScript": self._to_script},
        }

    def _ask_bing_transliterate(self, content):
        val = None
        if self._inmem:
            val = caches["bing_transliterate"].get(content)
            if val:
                return val

        found = BingAPITransliteration.objects.filter(
            source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
        )
        logger.debug("Found %s elements in db for %s", len(found), content)
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, TRANSLIT_PATH, self.translit_params())
            bing = BingAPITransliteration(
                source_text=content, response_json=bing_json, from_lang=self.from_lang, to_lang=self.to_lang
            )
            bing.save()
            val = bing.response_json
        else:
            val = found.first().response_json  # TODO: be better, just being dumb for the moment

        if self._inmem:
            caches["bing_transliterate"].set(content, val)
        return val

    async def _aask_bing_transliterate(self, content, refresh=False):
        val = None
        if self._inmem:
            val = caches["bing_transliterate"].get(content)
            if val is not None and not refresh:
                return val

        found = await sync_to_async(
            BingAPITransliteration.objects.filter(
                source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
            ).first,
            thread_sensitive=settings.THREAD_SENSITIVE,
        )()

        logger.debug("Found %s element in db for %s", found, content)

        if found is None or refresh:
            bing_json = await self._aask_bing_api(content, TRANSLIT_PATH, self.translit_params())
            bing = found or BingAPITransliteration(source_text=content, from_lang=self.from_lang, to_lang=self.to_lang)
            bing.response_json = bing_json

            try:
                await sync_to_async(bing.save, thread_sensitive=settings.THREAD_SENSITIVE)()
                val = bing.response_json
            except IntegrityError:
                # we just tried saving an entry that already exists, try to get again
                logger.debug(
                    "Tried saving BingAPITransliteration for %s that already exists, try to get again", bing.source_text
                )
                found = await sync_to_async(
                    BingAPITransliteration.objects.filter(
                        source_text=content, from_lang=self.from_lang, to_lang=self.to_lang
                    ).first,
                    thread_sensitive=settings.THREAD_SENSITIVE,
                )()
                if found:
                    val = found.response_json
                else:
                    raise
        else:
            val = found.response_json  # TODO: be better, just being dumb for the moment

        if self._inmem:
            caches["bing_transliterate"].set(content, val)
        return val

    def transliterate(self, text):
        result = self._ask_bing_transliterate(text)
        jresult = json.loads(result)
        trans = jresult[0]["text"]
        logging.debug("Returning Bing transliteration '%s' for '%s'", trans, text)
        return trans

    async def atransliterate(self, text, refresh=False):
        jresult = json.loads(await self._aask_bing_transliterate(text, refresh=refresh))
        logging.debug("Returning Bing transliteration '%s' for '%s'", jresult[0]["text"], text)
        return jresult[0]["text"]
