# -*- coding: utf-8 -*-

import logging

from django.apps import AppConfig
from django.conf import settings

from enrich import data

logger = logging.getLogger(__name__)


class EnrichConfig(AppConfig):
    name = "enrich"
    verbose_name = "Transcrobes Enricher"

    def ready(self):
        for name, pair in settings.LANG_PAIRS.items():
            data.managers[name] = data.EnrichmentManager(name, pair)
