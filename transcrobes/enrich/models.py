# -*- coding: utf-8 -*-

from django.db import models

# TODO: probably these need a POS somewhere, possibly a list or maybe separate entries for different POS

class Translation(models.Model):
    source_text = models.CharField(max_length=2000, db_index=True)

    def __str__(self):
        return self.source_text

    class Meta:
        abstract = True


class JsonTranslation(Translation):
    response_json = models.CharField(max_length=25000)

    def __str__(self):
        return self.source_text

    class Meta:
        abstract = True


class BingAPILookup(JsonTranslation):
    pass


class BingAPITranslation(JsonTranslation):
    pass


class BingAPITransliteration(JsonTranslation):
    pass
