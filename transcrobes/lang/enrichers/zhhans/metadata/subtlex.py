# -*- coding: utf-8 -*-

import os
import logging
from collections import defaultdict

from django.conf import settings

from enrich.data import PersistenceProvider
from enrich.metadata import Metadata
from enrichers.models import ZH_SubtlexLookup
from zhhans_en.translate import decode_pinyin  # FIXME: decode_pinyin should not be in a lang_pair

logger = logging.getLogger(__name__)  # FIXME: add some logging

"""
see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch
following file adapted from subtlexch131210.zip, basically removed useless cedict translations
and fixed incorrect pinyin 'ue:' -> 'u:e'
"""

class ZH_SubtlexMetadata(PersistenceProvider, Metadata):
    model_type = ZH_SubtlexLookup

    def _decode_pinyin(self, s):
        # FIXME: don't use the generic decode_pinyin
        return decode_pinyin(s)

    def _load(self):
        # see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch/webpage.doc
        # file slightly modified, see above
        # Word
        # Length
        # Pinyin
        # Pinyin.Input
        # WCount
        # W.million
        # log10W
        # W-CD
        # W-CD%
        # log10CD
        # Dominant.PoS
        # Dominant.PoS.Freq
        # All.PoS
        # All.PoS.Freq

        # Peking University classification
        # see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch/webpage.doc
        # a         adjective
        # ad        adjective as adverbial
        # ag        adjective morpheme
        # an        adjective with nominal function
        # b          non-predicate adjective
        # c           conjunction
        # d           adverb
        # dg         adverb morpheme
        # e           interjection
        # f            directional locality
        # g           morpheme
        # h           prefix
        # i            idiom
        # j            abbreviation
        # k           suffix
        # l            fixed expressions
        # m         numeral
        # mg       numeric morpheme
        # n           common noun
        # ng         noun morpheme
        # nr          personal name
        # ns         place name
        # nt          organization name
        # nx         nominal character string
        # nz         other proper noun
        # o           onomatopoeia
        # p           preposition
        # q           classifier
        # r            pronoun
        # rg          pronoun morpheme
        # s           space word
        # t            time word
        # tg          time word morpheme
        # u           auxiliary
        # v           verb
        # vd         verb as adverbial
        # vg         verb morpheme
        # vn         verb with nominal function
        # w          symbol and non-sentential punctuation
        # x           unclassified items
        # y           modal particle
        # z           descriptive

        dico = defaultdict(list)
        logger.info("Starting population of ZH subtlex")

        if os.path.exists(self._config['path']):
            with open(self._config['path'], 'r') as data_file:
                next(data_file) # skip the header line
                for line in data_file:
                    l = line.strip().split("\t")
                    w = l[0]
                    dico[w].append({
                        "pinyin": decode_pinyin(l[2]),  # can be several, separated by /
                        "wcpm": l[5],  # word count per million
                        "wcdp": l[8],  # % of film subtitles that had the char at least once
                        "pos": l[12],  # all POS found, most frequent first
                        "pos_freq": l[13],  # nb of occurences by POS
                    })

                    if not line.strip(): ignore = 0; continue

        logger.info(f"Finished populating ZH subtlex, there are {len(list(dico.keys()))} entries")

        return dico

    # override Metadata
    @staticmethod
    def name():
        return 'freq'

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
                'metas': f"{e['pinyin']}, {e['wcpm']}, {e['wcdp']}, {e['pos']}, {e['pos_freq']}"
            }

