# -*- coding: utf-8 -*-

import logging
import warnings

from django.apps import AppConfig
from django.conf import settings
from django.core.cache import CacheKeyWarning

from enrich import data

# we hold transliterations that have punctuation, which generates a warning
# if we move to memcached, this will hide errors!
warnings.simplefilter("ignore", CacheKeyWarning)

logger = logging.getLogger(__name__)


class EnrichConfig(AppConfig):
    name = "enrich"
    verbose_name = "Transcrobes Enricher"

    def ready(self):
        for name, pair in settings.LANG_PAIRS.items():
            data.managers[name] = data.EnrichmentManager(name, pair)
