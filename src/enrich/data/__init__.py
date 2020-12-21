# -*- coding: utf-8 -*-

import importlib
import inspect
import json
import logging
from abc import ABC, abstractmethod

from asgiref.sync import sync_to_async
from django.conf import settings

from enrich import Enricher
from enrich.lemmatize import WordLemmatizer
from enrich.metadata import Metadata
from enrich.parse import ParseProvider
from enrich.translate import Translator
from enrich.transliterate import Transliterator

logger = logging.getLogger(__name__)


class PersistenceProvider(ABC):
    def __init__(self, config):
        self._config = config
        self._inmem = self._config.get("inmem")
        self.dico = self._load() if self._inmem else None

    def __len__(self):
        if self._inmem:
            return len(self.dico.keys())

        return self.model_type.objects.count()

    def load_to_db(self, dico, force_reload=False):
        for lword, entry in dico.items():
            dbentries = self.model_type.objects.filter(source_text=lword)
            if len(dbentries) == 0:
                dbentry = self.model_type(source_text=lword, response_json=json.dumps(entry, ensure_ascii=False))
                dbentry.save()
            elif force_reload:
                dbentry = dbentries.first()  # TODO: what about having more than one... :-(
                dbentry.source_text = lword
                dbentry.response_json = json.dumps(entry, ensure_ascii=False)
                dbentry.save()

    def entry(self, lword):
        if self._inmem:
            return self.dico.get(lword)

        return self._from_db(lword)

    async def aentry(self, lword):
        if self._inmem:
            return self.dico.get(lword)

        return await self._afrom_db(lword)

    def _from_db(self, lword):
        dbentries = self.model_type.objects.filter(source_text=lword)
        # TODO: we can probably have duplicates if we don't make sure not to have
        # everything lowercased in the _dict and DB
        return json.loads(dbentries.first().response_json) if len(dbentries) > 0 else None

    async def _afrom_db(self, lword):
        dbentries = self.model_type.objects.filter(source_text=lword)
        # TODO: we can probably have duplicates if we don't make sure not to have
        # everything lowercased in the _dict and DB
        word = await sync_to_async(dbentries.first, thread_sensitive=settings.THREAD_SENSITIVE)()
        if word:
            return json.loads(word.response_json)

        return None

    def _get_def(self, lword):
        return self.entry(lword)

    async def _aget_def(self, lword):
        return await self.aentry(lword)

    @abstractmethod
    def _load(self):
        pass

    @staticmethod
    @abstractmethod
    def name():
        pass


managers = {}


# FIXME: consider reducing the number of instance attributes
class EnrichmentManager:  # pylint: disable=R0902
    @staticmethod
    def _fullname(c):
        module = c.__module__
        if module is None or module == str.__class__.__module__:
            return c.__name__
        return f"{module}.{c.__name__}"

    def _get_provider(self, classpath, parent, config, helper=None):
        logger.info(f"Loading class {classpath}")
        module_name, class_name = classpath.rsplit(".", 1)
        module = importlib.import_module(module_name.strip())
        class_ = getattr(module, class_name.strip())

        if parent not in inspect.getmro(class_):
            raise TypeError(f"All {class_name} MUST inherit from {self._fullname(parent)}")

        return class_(config) if helper is None else class_(config, helper)

    def __init__(self, name, config):
        self.from_lang = name.split(":")[0]
        self.to_lang = name.split(":")[1]
        self.config = config

        logger.info(f"Loading class enrich for {name}")
        self._enricher = self._get_provider(config["enrich"]["classname"], Enricher, config["enrich"]["config"])

        logger.info(f"Loading class parser for {name}")
        self._parser = self._get_provider(config["parse"]["classname"], ParseProvider, config["parse"]["config"])

        if "classname" in config["word_lemmatizer"]:
            logger.info(f"Loading class lemmatizer for {name}")
            self._word_lemmatizer = self._get_provider(
                config["word_lemmatizer"]["classname"], WordLemmatizer, config["word_lemmatizer"]["config"]
            )

        logger.info(f"Loading class transliterator for {name}")
        self._transliterator = self._get_provider(
            config["transliterate"]["classname"], Transliterator, config["transliterate"]["config"]
        )

        logger.info(f"Loading class metadata for {name}")
        self._metadata = []
        for provider in config["metadata"]:
            self._metadata.append(self._get_provider(provider["classname"], Metadata, provider["config"]))

        if "transliterator" in config["default"]:
            logger.info(f"Loading class transliterators for {name} for default")
            helper = self._get_provider(
                config["default"]["transliterator"]["classname"],
                Transliterator,
                config["default"]["transliterator"]["config"],
            )
            if helper is None:
                raise Exception(f"wtf for {config['default']['transliterator']['classname']}")
            logger.info(f"Loading class default for {name} with transliterator")
            self._default = self._get_provider(
                config["default"]["classname"], Translator, config["default"]["config"], helper
            )
        else:
            logger.info(f"Loading class default for {name} without transliterator")
            self._default = self._get_provider(config["default"]["classname"], Translator, config["default"]["config"])

        self._secondary = []
        for provider in config["secondary"]:
            if "transliterator" in provider:
                logger.info(f'Loading class transliterators for {name} for {provider["classname"]}')
                helper = self._get_provider(
                    provider["transliterator"]["classname"], Transliterator, provider["transliterator"]["config"]
                )
                logger.info(f'Loading class {provider["classname"]} for {name} with translit')
                self._secondary.append(
                    self._get_provider(provider["classname"], Translator, provider["config"], helper)
                )
            else:
                logger.info(f'Loading class {provider["classname"]} for {name} without transliterator')
                self._secondary.append(self._get_provider(provider["classname"], Translator, provider["config"]))

    def enricher(self):
        return self._enricher

    def parser(self):
        return self._parser

    def word_lemmatizer(self):
        return self._word_lemmatizer

    def default(self):
        return self._default

    def secondary(self):
        return self._secondary

    def metadata(self):
        return self._metadata

    def transliterator(self):
        return self._transliterator

    @property
    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"
