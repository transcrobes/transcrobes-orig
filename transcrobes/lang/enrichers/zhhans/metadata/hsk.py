# -*- coding: utf-8 -*-

import os
import logging

from django.conf import settings

from enrich.data import PersistenceProvider
from enrich.metadata import Metadata
from enrichers.models import ZH_HSKLookup

logger = logging.getLogger(__name__)  # FIXME: add some logging

"""
Load unmodified CC-Cedict files and make available either inmem or in the DB
see http://www.hskhsk.com/word-lists.html
data from http://data.hskhsk.com/lists/
files renamed "HSK Official With Definitions 2012 L?.txt" ->  hsk?.txt
"""

class ZH_HSKMetadata(PersistenceProvider, Metadata):
    model_type = ZH_HSKLookup

    def _load(self):
        dico = {}
        logger.info("Starting population of hsk")

        for i in range(1, 7):
            if not os.path.isfile(self._config['path'].format(i)): continue

            with open(self._config['path'].format(i), 'r') as data_file:
                for line in data_file:
                    # 爱	愛	ai4	ài	love
                    l = line.strip().split("\t")

                    if not l[0] in dico:
                        dico[l[0]] = []
                    dico[l[0]].append({ "pinyin": l[3], "hsk": i })

        logger.info("Finished populating hsk, there are {} entries".format(len(list(dico.keys()))))
        return dico


    # override Metadata
    @staticmethod
    def name():
        return 'hsk'

    # override Metadata
    def meta_for_word(self, lword):
        return self.entry(lword)

    # override Metadata
    def metas_as_string(self, lword):
        entries = self.entry(lword)
        if not entries:
            return { 'name': self.name(), 'metas': '' }
        else:
            e = entries[0]
            return {
                'name': self.name(),
                'metas': f"{e['pinyin']} HSK{e['hsk']}"
            }

