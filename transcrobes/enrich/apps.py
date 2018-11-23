# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.core.cache import cache

import logging
import re


logger = logging.getLogger(__name__)


class EnrichConfig(AppConfig):
    name = 'enrich'

    def ready(self):
        pass
