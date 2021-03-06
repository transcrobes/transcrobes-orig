# -*- coding: utf-8 -*-

"""
This file contains the conversion tables between CoreNLP POS tags (taken from the
Penn Chinese Treebank) and the various supported dictionaries for zh-Hans
"""
import collections
import logging
import re
import unicodedata

import opencc

from enrich import Enricher, TransliterationException
from ndutils import lemma
from zhhans_en.translate.abc import ZH_TB_POS_TO_ABC_POS

logger = logging.getLogger(__name__)

"""
see http://www.cs.brandeis.edu/~clp/ctb/posguide.3rd.ch.pdf
for more info on the Penn Chinese Treebank tagset

Here taken from that paper's table of contents
Verb: VA, VC, VE, VV
2.1.1 Predicative adjective: VA
2.1.2 Copula: VC
2.1.3 you3 as the main verb: VE
2.1.4 Other verb: VV

2.2 Noun: NR, NT, NN
2.2.1 Proper Noun: NR
2.2.2 Temporal Noun: NT
2.2.3 Other Noun: NN

2.3 Localizer: LC

2.4 Pronoun: PN

2.5 Determiners and numbers: DT, CD, OD
2.5.1 Determiner: DT
2.5.2 Cardinal Number: CD
2.5.3 Ordinal Number: OD

2.6 Measure word: M

2.7 Adverb: AD

2.8 Preposition: P

2.9 Conjunctions: CC, CS
2.9.1 Coordinating conjunction: CC
2.9.2 Subordinating conjunction: CS

2.10 Particle: DEC, DEG, DER, DEV, AS, SP, ETC, MSP
2.10.1 de5 as a complementizer or a nominalizer: DEC
2.10.2 de5 as a genitive marker and an associative marker: DEG
2.10.3 Resultative de5: DER
2.10.4 Manner de5: DEV
2.10.5 Aspect Particle: AS
2.10.6 Sentence-final particle: SP
2.10.7 ETC
2.10.8 Other particle: MSP

2.11 Others: IJ, ON, LB, SB, BA, JJ, FW, PU
2.11.1 Interjection: IJ
2.11.2 Onomatopoeia: ON
2.11.3 bei4 in long bei-construction: LB
2.11.4 bei4 in short bei-construction: SB
2.11.5 ba3 in ba-construction: BA
2.11.6 other noun-modifier: JJ
2.11.7 Foreign Word: FW
2.11.8 Punctuation: PU
"""

"""
Bing/Simple POS
Tag name  Description
ADJ   Adjectives
ADV   Adverbs
CONJ  Conjunctions
DET   Determiners
MODAL Verbs
NOUN  Nouns
PREP  Prepositions
PRON  Pronouns
VERB  Verbs
OTHER Other
"""

# TODO: This was a little arbitrary...
# Chinese Penn Treebank to Bing
ZH_TB_POS_TO_SIMPLE_POS = {
    "AD": "ADV",  # adverb
    "AS": "OTHER",  # aspect marker
    "BA": "OTHER",  # in ba-construction ,
    "CC": "CONJ",  # coordinating conjunction
    "CD": "DET",  # cardinal number
    "CS": "CONJ",  # subordinating conjunction
    "DEC": "OTHER",  # in a relative-clause
    "DEG": "OTHER",  # associative
    "DER": "OTHER",  # in V-de const. and V-de-R
    "DEV": "OTHER",  # before VP
    "DT": "DET",  # determiner
    "ETC": "OTHER",  # for words , ,
    "FW": "OTHER",  # foreign words
    "IJ": "OTHER",  # interjection
    "JJ": "ADJ",  # other noun-modifier ,
    "LB": "OTHER",  # in long bei-const ,
    "LC": "OTHER",  # localizer
    "M": "OTHER",  # measure word
    "MSP": "OTHER",  # other particle
    "NN": "NOUN",  # common noun
    "NR": "NOUN",  # proper noun
    "NT": "NOUN",  # temporal noun
    "OD": "DET",  # ordinal number
    "ON": "OTHER",  # onomatopoeia ,
    "P": "PREP",  # preposition excl. and
    "PN": "PRON",  # pronoun
    "PU": "OTHER",  # punctuation
    "SB": "OTHER",  # in short bei-const ,
    "SP": "OTHER",  # sentence-final particle
    "VA": "ADJ",  # predicative adjective
    "VC": "VERB",
    "VE": "VERB",  # as the main verb
    "VV": "VERB",  # other verb
    # Others added since then
    "URL": "OTHER",
}

CORENLP_IGNORABLE_POS = ["PU", "OD", "CD", "NT", "URL", "FW"]
CORENLP_IGNORABLE_POS_SHORT = ["PU", "URL"]

_HAS_LANG_CHARS = re.compile(".*[\u4e00-\u9fff]+.*")


class CoreNLP_ZHHANS_Enricher(Enricher):
    def __init__(self, config):
        super().__init__(config)
        self.converter = opencc.OpenCC("t2s.json")

    @staticmethod
    def get_simple_pos(token):
        return ZH_TB_POS_TO_SIMPLE_POS[token["pos"]]

    @staticmethod
    def needs_enriching(token):
        word = lemma(token)
        if "pos" not in token:
            logger.debug("'%s' has not POS so not adding to translatables", word)
            return False
        # FIXME: this was previously the following, trying to change and see whether it's bad...
        # if token['pos'] in CORENLP_IGNORABLE_POS:
        if token["pos"] in CORENLP_IGNORABLE_POS_SHORT:
            logger.debug("'%s' has POS '%s' so not adding to translatables", word, token["pos"])
            return False

        # TODO: decide whether to continue removing if doesn't contain any Chinese chars?
        # Sometimes yes, sometimes no!
        if not _HAS_LANG_CHARS.match(word):
            logger.debug("Nothing to translate, exiting: %s", word)
            return False

        return True

    # override Enricher
    def _cleaned_sentence(self, sentence):
        out_string = ""
        for t in sentence["tokens"]:
            if self.is_clean(t):
                out_string += f'{t["originalText"]}'

        return out_string

    @staticmethod
    def _get_transliteratable_sentence(tokens):
        t_sent = ""
        for t in tokens:
            w = t.get("ot") or t.get("l") or t.get("originalText") or t.get("lemma")
            t_sent += w if _HAS_LANG_CHARS.match(w) else f" {w}"
        return t_sent

    # override Enricher
    # FIXME: make less complex to get rid of C901
    # FIXME: PROBABLY TO DELETE
    async def _aadd_transliterations(self, sentence, transliterator):  # noqa:C901  # pylint: disable=R0912
        tokens = sentence["tokens"]
        clean_text = self._get_transliteratable_sentence(tokens)
        trans = await transliterator.atransliterate(clean_text)

        clean_trans = " "

        i = 0
        while i < len(trans):
            if not unicodedata.category(trans[i]).startswith("L") or not unicodedata.category(trans[i - 1]).startswith(
                "L"
            ):
                clean_trans += " "
            clean_trans += trans[i]
            i += 1

        # ensure we have one and only one space between all word tokens
        clean_trans = " ".join(list(filter(None, clean_trans.split(" "))))

        deq = collections.deque(clean_trans.split(" "))
        try:
            for t in tokens:
                w = t["originalText"]
                pinyin = []
                i = 0
                nc = ""

                # originally
                # if w == '???':  # TODO: pure nastiness - this gets translit'ed as '...'
                #     t['pinyin'] = deq.popleft() + deq.popleft() + deq.popleft()
                #     continue
                if not w.replace("???", ""):  # only contains the ...
                    t["pinyin"] = deq.popleft()
                    while deq and deq[0] == ".":
                        t["pinyin"] += deq.popleft()
                    continue

                while i < len(w):
                    if unicodedata.category(w[i]) == ("Lo"):  # it's a Chinese char
                        pinyin.append(deq.popleft())
                    else:
                        if not nc:
                            nc = deq.popleft()
                        if w[i] != nc[0]:
                            logger.error(f"{w[i]} should equal {nc} for '{clean_trans}'")
                            raise TransliterationException(
                                f"{w[i]} should equal {nc} for '{clean_trans}' "
                                f"and tokens '{tokens}' with original {clean_text}"
                            )
                        pinyin.append(w[i])
                        if len(nc) > 1:
                            nc = nc[1:]
                        else:
                            nc = ""
                    i += 1
                t["pinyin"] = pinyin
            return True
        except Exception:  # pylint: disable=W0703
            logger.error(
                "Error calculating context-informed pinyin, trying from tokens "
                f"'{tokens}' with original {clean_text}"
            )
            for token in tokens:
                token["pinyin"] = (await transliterator.atransliterate(token["originalText"])).split()
            return False

    # override Enricher
    # FIXME: make less complex to get rid of C901
    async def _aadd_slim_transliterations(self, sentence, transliterator):  # noqa:C901  # pylint: disable=R0912
        tokens = sentence["t"]
        clean_text = self._get_transliteratable_sentence(tokens)
        trans = await transliterator.atransliterate(clean_text)

        clean_trans = " "

        i = 0
        while i < len(trans):
            if not unicodedata.category(trans[i]).startswith("L") or not unicodedata.category(trans[i - 1]).startswith(
                "L"
            ):
                clean_trans += " "
            clean_trans += trans[i]
            i += 1

        # ensure we have one and only one space between all word tokens
        clean_trans = " ".join(list(filter(None, clean_trans.split(" "))))

        deq = collections.deque(clean_trans.split(" "))
        try:
            for t in tokens:
                w = t.get("ot") or t.get("l") or t.get("originalText") or t.get("lemma")
                pinyin = []
                i = 0
                nc = ""

                # originally
                # if w == '???':  # TODO: pure nastiness - this gets translit'ed as '...'
                #     t['pinyin'] = deq.popleft() + deq.popleft() + deq.popleft()
                #     continue
                if not w.replace("???", ""):  # only contains the ...
                    t["p"] = deq.popleft()
                    while deq and deq[0] == ".":
                        t["p"] += deq.popleft()
                    continue

                while i < len(w):
                    if unicodedata.category(w[i]) == ("Lo"):  # it's a Chinese char
                        pinyin.append(deq.popleft())
                    else:
                        if not nc:
                            nc = deq.popleft()
                        if w[i] != nc[0]:
                            logger.error(f"{w[i]} should equal {nc} for '{clean_trans}'")
                            raise TransliterationException(
                                f"{w[i]} should equal {nc} for '{clean_trans}' "
                                f"and tokens '{tokens}' with original {clean_text}"
                            )
                        pinyin.append(w[i])
                        if len(nc) > 1:
                            nc = nc[1:]
                        else:
                            nc = ""
                    i += 1
                t["p"] = pinyin

            for token in tokens:
                if not self.is_clean(token) or not self.needs_enriching(token):
                    token.pop("p")

            return True
        except Exception:  # pylint: disable=W0703
            logger.error(
                "Error calculating context-informed pinyin, trying from tokens "
                f"'{tokens}' with original {clean_text}"
            )
            for token in tokens:
                if not self.is_clean(token) or not self.needs_enriching(token):
                    continue
                word = token.get("ot") or token.get("l") or token.get("originalText") or token["lemma"]
                token["p"] = (await transliterator.atransliterate(word)).split()
            return False

    # override Enricher
    # FIXME: make less complex to get rid of C901
    # FIXME: PROBABLY TO DELETE
    def _add_transliterations(self, sentence, transliterator):  # noqa:C901
        tokens = sentence["tokens"]
        clean_text = self._get_transliteratable_sentence(tokens)
        trans = transliterator.transliterate(clean_text)

        clean_trans = " "

        i = 0
        while i < len(trans):
            if not unicodedata.category(trans[i]).startswith("L") or not unicodedata.category(trans[i - 1]).startswith(
                "L"
            ):
                clean_trans += " "
            clean_trans += trans[i]
            i += 1

        # ensure we have one and only one space between all word tokens
        clean_trans = " ".join(list(filter(None, clean_trans.split(" "))))

        deq = collections.deque(clean_trans.split(" "))

        for t in tokens:
            w = t["originalText"]
            pinyin = []
            i = 0
            nc = ""

            # originally
            # if w == '???':  # TODO: pure nastiness - this gets translit'ed as '...'
            #     t['pinyin'] = deq.popleft() + deq.popleft() + deq.popleft()
            #     continue
            if not w.replace("???", ""):  # only contains the ...
                t["pinyin"] = deq.popleft()
                while deq and deq[0] == ".":
                    t["pinyin"] += deq.popleft()
                continue

            while i < len(w):
                if unicodedata.category(w[i]) == ("Lo"):  # it's a Chinese char
                    pinyin.append(deq.popleft())
                else:
                    if not nc:
                        nc = deq.popleft()
                    if w[i] != nc[0]:
                        raise Exception(
                            "{} should equal {} for '{}' and tokens '{}' with original {}".format(
                                w[i], nc, clean_trans, tokens, clean_text
                            )
                        )
                    pinyin.append(w[i])
                    if len(nc) > 1:
                        nc = nc[1:]
                    else:
                        nc = ""
                i += 1
            t["pinyin"] = pinyin

    # override Enricher
    def _set_best_guess(self, sentence, token):
        # TODO: do something intelligent here - sentence isn't used yet
        # ideally this will translate the sentence using some sort of statistical method but get the best
        # translation for each individual word of the sentence, not the whole sentence, giving us the
        # most appropriate definition to show (gloss) to the user

        # This could be bumped to the parent class but for the POS correspondance dicts
        # This is ugly and stupid

        best_guess = None
        others = []
        all_defs = []
        for t in token["definitions"].keys():
            for def_pos, defs in token["definitions"][t].items():
                if not defs:
                    continue
                all_defs += defs
                if def_pos in (  # pylint: disable=R1723
                    ZH_TB_POS_TO_SIMPLE_POS[token["pos"]],
                    ZH_TB_POS_TO_ABC_POS[token["pos"]],
                ):
                    # get the most confident for the right POs
                    sorted_defs = sorted(defs, key=lambda i: i["confidence"], reverse=True)
                    best_guess = sorted_defs[0]
                    break
                elif def_pos == "OTHER":
                    others += defs
            if best_guess:
                break

        if not best_guess and len(others) > 0:
            # it's bad
            logger.debug("No best_guess found for '%s', using the best 'other' POS defs %s", lemma(token), others)

            best_guess = sorted(others, key=lambda i: i["confidence"], reverse=True)[0]

        if not best_guess and len(all_defs) > 0:
            # it's really bad
            best_guess = sorted(all_defs, key=lambda i: i["confidence"], reverse=True)[0]
            logger.debug(
                """No best_guess found with the correct POS or OTHER for '%s',
                using the highest confidence with the wrong POS all_defs %s""",
                lemma(token),
                all_defs,
            )

        logger.debug("Setting best_guess for '%s' POS %s to best_guess %s", lemma(token), token["pos"], best_guess)
        token["best_guess"] = best_guess  # .split(',')[0].split(';')[0]

    # override Enricher
    def _set_best_guess_async(self, _sentence, token, token_definition):
        # TODO: do something intelligent here - sentence isn't used yet
        # ideally this will translate the sentence using some sort of statistical method but get the best
        # translation for each individual word of the sentence, not the whole sentence, giving us the
        # most appropriate definition to show (gloss) to the user

        # This could be bumped to the parent class but for the POS correspondance dicts
        # This is ugly and stupid

        best_guess = None
        others = []
        all_defs = []
        for t in token_definition.keys():
            # FIXME: currently the tokens are stored in keyed order of the "best" source, "fallback" and then the
            # secondary dictionaries. Actually only the "best" currently has any notion of confidence (cf)
            # and all the "fallback" are "OTHER", meaning the "fallback" will only be considered after
            # the secondaries. If anything changes in that, this algo may well not return the "best"
            # translation
            for def_pos, defs in token_definition[t].items():
                # {ZH_TB_POS_TO_SIMPLE_POS[token['pos']]=}, {ZH_TB_POS_TO_ABC_POS[token['pos']]=} {defs=}")
                if not defs:
                    continue
                all_defs += defs
                if def_pos in (  # pylint: disable=R1723
                    ZH_TB_POS_TO_SIMPLE_POS[token["pos"]],
                    ZH_TB_POS_TO_ABC_POS[token["pos"]],
                ):
                    # get the most confident for the right POS
                    sorted_defs = sorted(defs, key=lambda i: i["cf"], reverse=True)
                    best_guess = sorted_defs[0]
                    break
                elif def_pos == "OTHER":
                    others += defs
            if best_guess:
                break

        if not best_guess and len(others) > 0:
            # it's bad
            logger.debug("No best_guess found for '%s', using the best 'other' POS defs %s", lemma(token), others)

            best_guess = sorted(others, key=lambda i: i["cf"], reverse=True)[0]

        if not best_guess and len(all_defs) > 0:
            # it's really bad
            best_guess = sorted(all_defs, key=lambda i: i["cf"], reverse=True)[0]
            logger.debug(
                """No best_guess found with the correct POS or OTHER for '%s',
                using the highest confidence with the wrong POS all_defs %s""",
                lemma(token),
                all_defs,
            )

        logger.debug("Setting best_guess for '%s' POS %s to best_guess %s", lemma(token), token["pos"], best_guess)
        token["bg"] = best_guess

    def _set_slim_best_guess_async(self, sentence, token, token_definition):
        self._set_best_guess_async(sentence, token, token_definition)
        token["bg"] = token["bg"]["nt"]

    # override Enricher
    def clean_text(self, text):
        # Make sure it is simplified, so we don't pollute the DB
        return self.converter.convert(text)
