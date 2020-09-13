# -*- coding: utf-8 -*-
import json
import pkgutil

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from djankiserv.unki.collection import Collection


class Transcrober(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO: this should probably be a OneToMany, so we can have users
    # who use the system for more than one language. KISS for the moment
    from_lang = models.CharField(max_length=20, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, default="en")  # 20 is probably overkill

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"

    def init_collection(self):
        # FIXME: these files are currently for Chinese, need to make generic
        conf = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_collection_conf.json").decode("utf-8"))
        decks = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_deck.json").decode("utf-8"))
        deck_conf = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_deck_conf.json").decode("utf-8"))
        tmodels = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_model.json").decode("utf-8"))

        Collection(self.user.username, settings.DJANKISERV_DATA_ROOT).db.execute(
            f"update {self.user.username}.col set conf = %s, decks = %s, dconf = %s, models = %s",
            json.dumps(conf),
            json.dumps(decks),
            json.dumps(deck_conf),
            json.dumps(tmodels),
        )
