# -*- coding: utf-8 -*-

import logging
import requests
import json
import sys, os, io

from django.conf import settings

import anki.consts
# MUST be set before importing anki.sync or it gets overriden!!!!!!!
anki.consts.SYNC_BASE = settings.ANKROBES_ENDPOINT

from anki.utils import checksum
from anki.sync import RemoteServer

logger = logging.getLogger(__name__)


# TODO: this module really needs a lot of work - it's dumb, and needs to be really smart
class AnkrobesServer(RemoteServer):

    def __init__(self, username, password):
        anki.sync.RemoteServer.__init__(self, None, None)


    def _word_known(self, word):
        self.postVars = dict(
            k=self.hkey,
            s=self.skey,
        )

        bys = io.BytesIO(json.dumps(dict(word=word)).encode("utf8"))
        ret = self.req("word_known", bys, badAuthRaises=True).decode("utf8")
        logger.debug("The query ret is: {}".format(ret))
        return 1 if int(ret) else 0

    def is_known(self, token):
        # TODO: This method should take into account the POS but we'll need to implement that in Anki somehow
        # a tag is probably the logical solution
        return self.is_known_chars(token)


    def is_known_chars(self, token):
        return self._word_known(token['word'])

    def add_ankrobes_note(self, simplified, pinyin, meanings, tags):
        self.postVars = dict(
            k=self.hkey,
            s=self.skey,
        )
        note = dict(
            simplified=simplified.replace('"', "'"),
            pinyin=pinyin.replace('"', "'"),
            meanings=[x.replace('"', "'") for x in meanings],
            tags=tags
        )

        bys = io.BytesIO(json.dumps(note).encode("utf8"))
        ret = self.req("add_ankrobes_note", bys, badAuthRaises=True).decode("utf8")
        logger.debug("The add note ret is: {}".format(ret))
        return 1 if int(ret) else 0

    def get_word(self, word, deck_name='transcrobes'):
        self.postVars = dict(
            k=self.hkey,
            s=self.skey,
        )

        bys = io.BytesIO(json.dumps(dict(word=word)).encode("utf8"))
        ret = self.req("get_word", bys, badAuthRaises=True).decode("utf8")
        return json.loads(ret)


    def set_word_known(self, simplified, pinyin, meanings=[], tags=[], review_in=7):
        self.postVars = dict(
            k=self.hkey,
            s=self.skey,
        )
        # TODO: validate input data properly...
        if not (simplified and pinyin and meanings):
            raise Exception("Missing obligatory input date. Simplified, Pinyin and meanings fields are required")

        note = dict(
            simplified=simplified.replace('"', "'"),
            pinyin=pinyin.replace('"', "'"),
            meanings=[x.replace('"', "'") for x in meanings],
            tags=tags,
            review_in=review_in,
        )

        logger.debug("Sending to ankrobes to set_word_known date: {}".format(note))

        bys = io.BytesIO(json.dumps(note).encode("utf8"))
        ret = self.req("set_word_known", bys, badAuthRaises=True).decode("utf8")
        return json.loads(ret)
