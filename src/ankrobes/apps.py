from django.apps import AppConfig


class AnkrobesConfig(AppConfig):
    name = "ankrobes"

    def ready(self):
        from . import signals  # noqa # pylint: disable=C0415,W0611
