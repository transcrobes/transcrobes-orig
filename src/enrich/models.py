# -*- coding: utf-8 -*-

from django.db import models

# TODO: probably these need a POS somewhere, possibly a list or maybe separate entries for different POS


class Translation(models.Model):
    source_text = models.CharField(max_length=2000, db_index=True)

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True


class JsonTranslation(Translation):
    response_json = models.CharField(max_length=25000)

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True


class BingAPIPersistence(JsonTranslation):
    from_lang = models.CharField(max_length=20, db_index=True, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, db_index=True, default="en")  # 20 is probably overkill

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True
        index_together = [
            ("source_text", "from_lang", "to_lang"),
        ]


class BingAPILookup(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_lkp"),
        ]


class BingAPITranslation(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tla"),
        ]


class BingAPITransliteration(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tli"),
        ]
