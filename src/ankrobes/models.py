# -*- coding: utf-8 -*-
import json
import pkgutil

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from djankiserv.unki.collection import Collection
from libgravatar import Gravatar


class Transcrober(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO: this should probably be a OneToMany, so we can have users
    # who use the system for more than one language. KISS for the moment
    from_lang = models.CharField(max_length=20, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, default="en")  # 20 is probably overkill

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"

    def get_gravatar(self):
        return Gravatar(self.user.email).get_image()[5:]  # remove the 'http:'

    def get_full_name(self):
        full_name = f"{self.user.first_name} {self.user.last_name}"
        return self.user.username if not full_name.strip() else full_name

    def init_collection(self):
        # FIXME: these files are currently for Chinese, need to make generic
        conf = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_collection_conf.json").decode("utf-8"))
        decks = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_deck.json").decode("utf-8"))
        deck_conf = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_deck_conf.json").decode("utf-8"))
        tmodels = json.loads(pkgutil.get_data("ankrobes.resources.json", "default_model.json").decode("utf-8"))

        with Collection(self.user.username, settings.DJANKISERV_DATA_ROOT) as col:
            col.db.execute(
                f"update {self.user.username}.col set conf = %s, decks = %s, dconf = %s, models = %s",
                json.dumps(conf),
                json.dumps(decks),
                json.dumps(deck_conf),
                json.dumps(tmodels),
            )
            # FIXME: this should definitely not be done here! But probably neither should
            # the above, so just leave this hack for the moment
            sql = f"""
            CREATE MATERIALIZED VIEW {self.user.username}.user_vocabulary AS
            SELECT c.id as card_id, n.id as note_id, c.type as type, simplified(n.flds) as word
                FROM json_each((SELECT decks FROM {self.user.username}.col)::json) a
                    INNER JOIN {self.user.username}.cards c on c.did = a.key::bigint
                    INNER JOIN {self.user.username}.notes n on c.nid = n.id
                WHERE json_extract_path_text(a.value, 'name') = 'transcrobes';
            """
            col.db.execute(sql)
            sql = f"""
            CREATE INDEX {self.user.username}_vocabulary_idx
                ON {self.user.username}.user_vocabulary (word)"""
            col.db.execute(sql)

            # this is so we can refresh "concurrently"
            sql = f"""
            CREATE UNIQUE INDEX {self.user.username}_vocabulary_card_idx
                ON {self.user.username}.user_vocabulary (card_id)"""
            col.db.execute(sql)

    def refresh_vocabulary(self):
        with Collection(self.user.username, settings.DJANKISERV_DATA_ROOT) as col:
            sql = f"""
            REFRESH MATERIALIZED VIEW CONCURRENTLY {self.user.username}.user_vocabulary"""
            col.db.execute(sql)
