# -*- coding: utf-8 -*-

from django.apps import AppConfig


class DataConfig(AppConfig):
    name = "data"

    def ready(self):
        from . import signals  # noqa # pylint: disable=C0415,W0611
