# -*- coding: utf-8 -*-

import os
import logging
from collections import defaultdict

from django.conf import settings

from enrich.data import PersistenceProvider
from enrich.metadata import Metadata
from enrichers.models import EN_SubtlexLookup

logger = logging.getLogger(__name__)  # FIXME: add some logging

"""
see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch

The file used here is a straight, tab separated, no obligatory quotes, export using LibreOffice
from the xlsx file from
https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus/subtlexus1.zip

"""

EN_SUBTLEX_POS_ABBREVS = {
    'Adjective'     : 'a',
    'Adverb'        : 'adv',
    'Article'       : 'art',
    'Conjunction'   : 'con',
    'Determiner'    : 'd',
    'Ex'            : 'e',
    'Interjection'  : 'i',
    'Letter'        : 'l',
    '#N/A'          : '#na',
    'Name'          : 'na',
    'Not'           : 'no',
    'Noun'          : 'n',
    'Number'        : 'num',
    'Preposition'   : 'prp',
    'Pronoun'       : 'pr',
    'To'            : 'to',
    'Unclassified'  : 'u',
    'Verb'          : 'v',
}

class EN_SubtlexMetadata(PersistenceProvider, Metadata):
    model_type = EN_SubtlexLookup

    def _encode_pos(self, s):
        """
        To present to users we abbreviate the POS in the file. There is some rubbish but whatever

        Nb.   POS
        15166 Adjective     a
         2702 Adverb        adv
            6 Article       art
           61 Conjunction   con
           47 Determiner    d
            1 Ex            e
          211 Interjection  i
           27 Letter        l
          191 #N/A          #na
        14937 Name          na
            3 Not           no
        45470 Noun          n
          133 Number        num
          203 Preposition   prp
           82 Pronoun       pr
            5 To            to
          260 Unclassified  u
        23545 Verb          v
        """
        return '.'.join([ EN_SUBTLEX_POS_ABBREVS[x.strip()] for x in s.split('.') ])

    def _load(self):
        # see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus/overview.htm
        # Word                  - This starts with a capital when the word more often starts with an uppercase letter than with a lowercase letter.
        # FREQcount
        # CDcount
        # FREQlow
        # Cdlow
        # SUBTLWF               - This is the word frequency per million words
        # Lg10WF
        # SUBTLCD               - indicates in how many percent of the films the word appears
        # Lg10CD
        # Dom_PoS_SUBTLEX
        # Freq_dom_PoS_SUBTLEX
        # Percentage_dom_PoS
        # All_PoS_SUBTLEX       - All PoS observed for the entry
        # All_freqs_SUBTLEX     - The frequencies of each PoS
        # Zipf-value            - More information about the Zipf scale can be found http://crr.ugent.be/archives/1352

        dico = defaultdict(list)
        logger.info("Starting population of EN US subtlex")

        if os.path.exists(self._config['path']):
            with open(self._config['path'], 'r') as data_file:
                next(data_file) # skip the header line
                for line in data_file:
                    l = line.strip().split("\t")
                    w = l[0].lower()  # TODO: we are losing info here probably
                    dico[w].append({
                        # TODO: should a translit be put here?
                        "zipf": l[14][0:4],  # Zipf value
                        "wcpm": l[5],  # word count per million
                        "wcdp": l[7],  # % of film subtitles that had the char at least once
                        "pos": self._encode_pos(l[12]),  # all POS found, most frequent first
                        "pos_freq": l[13],  # nb of occurences by POS
                    })

                    if not line.strip(): ignore = 0; continue

        logger.info(f"Finished populating EN US subtlex, there are {len(list(dico.keys()))} entries")

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
                'metas': f"{e['zipf']}, {e['wcpm']}, {e['wcdp']}, {e['pos']}, {e['pos_freq']}"
            }

