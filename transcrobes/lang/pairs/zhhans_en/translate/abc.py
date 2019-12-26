# -*- coding: utf-8 -*-
import logging
import os
import re

from enrich.data import PersistenceProvider
from enrich.translate import Translator
from zhhans_en.models import ABCLookup
from zhhans_en.translate import decode_pinyin

# from zhhans_en.translate import ZHHANS_EN_Translator


logger = logging.getLogger(__name__)


# TODO: This was a little arbitrary...
# see https://gitlab.com/Wenlin/WenlinTushuguan/blob/master/Help/abbrev.wenlin
# for the ABC abbrevs. The POS are actually quite dissimilar between CoreNLP and ABC
# with whole categories missing from one or the other (prefix vs preposition) :(
ZH_TB_POS_TO_ABC_POS = {
    "AD": "adv.",  # adverb
    "AS": "a.m.",  # aspect marker
    "BA": "other",  # in ba-construction ,
    "CC": "conj.",  # coordinating conjunction
    "CD": "num.",  # cardinal number ???
    "CS": "conj.",  # subordinating conjunction ???
    "DEC": "other",  # in a relative-clause ??? maybe 's.p.'
    "DEG": "other",  # associative ???
    "DER": "other",  # in V-de const. and V-de-R ???
    "DEV": "other",  # before VP
    "DT": "pr.",  # determiner ??? always appear to be as pr in the ABC
    "ETC": "suf.",  # for words , ,
    "FW": "other",  # foreign words
    "IJ": "intj.",  # interjection
    "JJ": "attr.",  # other noun-modifier ,
    "LB": "other",  # in long bei-const ,
    "LC": "other",  # localizer
    "M": "m.",  # measure word
    "MSP": "other",  # other particle
    "NN": "n.",  # common noun
    "NR": "n.",  # proper noun
    "NT": "n.",  # temporal noun
    "OD": "num.",  # ordinal number
    "ON": "on.",  # onomatopoeia ,
    "P": "other",  # preposition excl. and
    "PN": "pr.",  # pronoun
    "PU": "other",  # punctuation
    "SB": "other",  # in short bei-const ,
    "SP": "other",  # sentence-final particle
    "VA": "s.v.",  # predicative adjective
    "VC": "v.",
    "VE": "v.",  # as the main verb
    "VV": "v.",  # other verb
    # Others added since then
    "URL": "other",
}

# p_entries = {}  p_entries was originally here to check for duplicates that we might squash


class ZHHANS_EN_ABCDictTranslator(PersistenceProvider, Translator):
    p = re.compile(r"^(\d*)(\w+)(\S*)\s+(.+)$")
    model_type = ABCLookup

    # FIXME: this definitely needs to be refactored!
    def _load(self):  # pylint: disable=R0912,R0915  # noqa:C901
        cur_pos = ""

        logger.info("Starting population of abcdict")
        ignore = 0
        entry = None
        dico = {}

        if os.path.exists(self._config["path"]):
            with open(self._config["path"], "r") as data_file:
                for line in data_file:
                    # ignore non-useful lines
                    if line.strip() in ["cidian.wenlindb", ".-arc", ".-publish", "--meta--"]:
                        continue
                    if not line.strip():
                        ignore = 0
                        continue
                    if line.strip() == "h":
                        ignore = 1
                        continue
                    if ignore == 1:
                        continue

                    # start a new entry
                    if line.startswith(".py   "):
                        uid = line[6:].strip()
                        if entry:  # flush the previous entry
                            # if entry['pinyin'] in p_entries: raise Exception("looks like we would squash, not good")
                            # p_entries[entry['pinyin']] = entry

                            if entry["char"] in dico:
                                dico[entry["char"]].append(entry)
                            else:
                                dico[entry["char"]] = [entry]

                        entry = {"pinyin": uid, "definitions": [], "els": [], "parents": {}}
                        cur_pos = ""
                        continue

                    m = self.p.match(line)

                    if m.group(2) in ["rem"]:
                        continue  # comments

                    if m.group(2) in ["ser", "ref", "freq", "hh"] and not m.group(1):
                        entry[m.group(2)] = m.group(4)
                    elif m.group(2) in ["char"]:
                        entry[m.group(2)] = m.group(4).split("[")[
                            0
                        ]  # only get simplified, traditional is in brackets after
                    elif m.group(2) == "gr" and not m.group(1):  # entry-level grade
                        entry[m.group(2)] = m.group(4)
                    elif m.group(2) in ["ps"]:
                        cur_pos = m.group(4)
                        entry["els"].append([m.group(1), m.group(2), m.group(4)])
                    elif m.group(2) in ["en"]:
                        entry["els"].append([m.group(1), m.group(2), m.group(4)])
                    else:
                        entry["els"].append([m.group(1), m.group(2), m.group(4)])
                        if m.group(2) in ["df"]:
                            entry["definitions"].append([m.group(1), cur_pos, m.group(4)])

                if entry:  # flush the last entry
                    # if entry['pinyin'] in p_entries: raise Exception("looks like we would squash, not good")
                    # p_entries[entry['pinyin']] = entry

                    if entry["char"] in dico:
                        dico[entry["char"]].append(entry)
                    else:
                        dico[entry["char"]] = [entry]

        logger.info("Finished populating abcdict, there are %s entries", len(list(dico.keys())))
        return dico

    # override Metadata
    @staticmethod
    def name():
        return "second"

    @staticmethod
    def _decode_pinyin(s):
        # TODO: don't use the generic method here
        return decode_pinyin(s)

    # TODO: fix the POS correspondences
    # override Translator
    def get_standardised_defs(self, token):
        std_format = {}

        entry = self._get_def(token["lemma"])
        if entry:
            logger.debug("'%s' is in abcdict cache", token["lemma"])
            for abc in entry:
                logger.debug("Iterating on '%s''s different definitions in abcdict cache", token["lemma"])
                for defin in abc["definitions"]:
                    token_pos = ZH_TB_POS_TO_ABC_POS[token["pos"]]

                    if not defin[1] in std_format:
                        std_format[defin[1]] = []

                    if token_pos == defin[1]:
                        confidence = 0.01
                    else:
                        confidence = 0

                    defie = {
                        "upos": token_pos,
                        "opos": defin[1],
                        "normalizedTarget": defin[2],
                        "confidence": confidence,
                        "trans_provider": "ABCDICT",
                    }
                    defie["pinyin"] = self._decode_pinyin(abc["pinyin"])
                    std_format[defin[1]].append(defie)

        logger.debug("Finishing looking up '%s' in abcedict", token["lemma"])
        return std_format

    # override Translator
    def get_standardised_fallback_defs(self, token):
        # TODO: do something better than this!
        return self.get_standardised_defs(token)
