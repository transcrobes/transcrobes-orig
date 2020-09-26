# -*- coding: utf-8 -*-

"""
This file contains the conversion tables between CoreNLP POS tags (taken from the
Penn Treebank, so for English) and the various supported dictionaries for en
"""

import logging
import re

from enrich import Enricher
from enrich.lemmatize import WordLemmatizer

"""
see https://catalog.ldc.upenn.edu/docs/LDC99T42/tagguid1.pd://catalog.ldc.upenn.edu/docs/LDC99T42/tagguid1.pdf
for more info on the Penn Treebank tagset

Here taken from section three of the above PDF

1. CC Coordinating conjunction
2. CD Cardinal number
3. DT Determiner
4. EX Existential _there_
5. FW Foreign word
6. IN Preposition or subordinating conjunction
7. JJ Adjective
8. JJR Adjective, comparative
9. JJS Adjective, superlative
10. LS List item marker
11. MD Modal
12. NN Noun, singular or mass
13. NNS Noun, plural
14. NNP Proper noun, singular
15. NNPS Proper noun, plural
16. PDT Predeterminer
17. POS Possessive ending
18. PRP Personal pronoun
19. PRP$ Possessive pronoun
20. RB Adverb
21. RBR Adverb, comparitive
22. RBS Adverb, superlative
23. RP Particle
24. SYM Symbol
25. TO _to_
26. UH Interjection
27. VB Verb, base form
28. VBD Verb, past tense
29. VBG Verb, gerund or present participle
30. VBN Verb, past participle
31. VBP Verb, non-3rd person singular present
32. VBZ Verb, 3rd person singular present
33. WDT Wh-determiner
34. WP Wh-pronoun
35. WP$ Possessive wh-pronoun
36. WRB Wh-adverb
"""

# from spacy.lemmatizer import Lemmatizer
# from spacy.lang.en import LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES


logger = logging.getLogger(__name__)


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

EN_TB_POS_TO_SIMPLE_POS = {
    "CC": "CONJ",  # Coordinating conjunction
    "CD": "DET",  # Cardinal number
    "DT": "DET",  # Determiner
    "EX": "OTHER",  # Existential _there_
    "FW": "OTHER",  # Foreign word
    "IN": "PREP",  # Preposition or subordinating conjunction
    "JJ": "ADJ",  # Adjective
    "JJR": "ADJ",  # Adjective, comparative
    "JJS": "ADJ",  # Adjective, superlative
    "LS": "OTHER",  # List item marker
    "MD": "OTHER",  # Modal
    "NN": "NOUN",  # Noun, singular or mass
    "NNS": "NOUN",  # Noun, plural
    "NNP": "NOUN",  # Proper noun, singular
    "NNPS": "NOUN",  # Proper noun, plural
    "PDT": "DET",  # Predeterminer
    "POS": "OTHER",  # Possessive ending
    "PRP": "PRON",  # Personal pronoun
    "PRP$": "PRON",  # Possessive pronoun
    "RB": "ADV",  # Adverb
    "RBR": "ADV",  # Adverb, comparitive
    "RBS": "ADV",  # Adverb, superlative
    "RP": "OTHER",  # Particle
    "SYM": "OTHER",  # Symbol
    "TO": "PREP",  # _to_
    "UH": "UH",  # Interjection
    "VB": "VERB",  # Verb, base form
    "VBD": "VERB",  # Verb, past tense
    "VBG": "VERB",  # Verb, gerund or present participle
    "VBN": "VERB",  # Verb, past participle
    "VBP": "VERB",  # Verb, non-3rd person singular present
    "VBZ": "VERB",  # Verb, 3rd person singular present
    "WDT": "DET",  # Wh-determiner
    "WP": "PRON",  # Wh-pronoun
    "WP$": "PRON",  # Possessive wh-pronoun
    "WRB": "ADV",  # Wh-adverb
}

# TODO: English TB has no POS for punctuation and returns the graph as-is. This is a bit nasty
# because the Chinese version correctly identifies punctuation.

PUNCTUATION_POS = "PUNCT"


class CoreNLP_EN_Enricher(Enricher):
    _has_lang_chars = re.compile("[A-z]+")

    def get_simple_pos(self, token):
        return EN_TB_POS_TO_SIMPLE_POS.get(token["pos"], PUNCTUATION_POS)

    def needs_enriching(self, token):
        # FIXME: copied from Chinese - review POS and use English ones
        if token["pos"] in ["PU", "OD", "CD", "NT", "URL"] + ["."]:
            logger.debug("'%s' has POS '%s' so not adding to translatables", token["word"], token["pos"])
            return False

        # TODO: decide whether to continue removing if doesn't contain any lang-specific chars?
        # Sometimes yes, sometimes no!
        if not self._has_lang_chars.match(token["word"]):
            logger.debug("Nothing to translate, exiting: %s", token["word"])
            return False

        return True

    def _cleaned_sentence(self, sentence):
        out_string = ""
        for t in sentence["tokens"]:
            if self.is_clean(t):
                out_string += f' {t["originalText"]}'
        return out_string

    def _get_transliteratable_sentence(self, tokens):
        # FIXME: remove this from Enricher abstract class
        raise NotImplementedError

    def _add_transliterations(self, sentence, transliterator):
        # We don't use/need and online transliterator for English (ok, so maybe it would be better!)

        # FIXME: actually here we should provide a list of alternative pronunciations.
        # Currently the token['pinyin'] field has a list of pinyin for each character in a word
        # that obviously makes no sense for non-character-based languages
        # And it probably shouldn't be called 'pinyin' either :-)
        for t in sentence["tokens"]:
            if not self.needs_enriching(t):
                continue
            # for now we just use the first returned

            t["pinyin"] = [transliterator.transliterate(t["originalText"])]

    def _set_best_guess(self, sentence, token):
        # TODO: do something intelligent here - sentence isn't used yet

        if "alignment" in sentence:
            ## FIXME: using alignments is actually pretty complicated...
            ## It may be better to get the alignments and then ONLY use them
            ## if there is a corresponding entry that we find in one of the
            ## dictionaries - sometimes the alignments given can correspond
            ## to multiple tokens, and we don't know which one to chose.
            ## We could also add a second filter of there needing to be a
            ## POS correspondance if we still don't get reliable correspondances.
            ## That would (probably) be highly reliable, though what the hit rate
            ## will be is certainly a matter for investigation!

            # start = sentence['tokens'][0]['characterOffsetBegin']
            # alignments = { a.split('-')[0]: a.split('-')[1] for a in sentence['alignment']['proj'].split(' ') }
            # skey = f'{token["characterOffsetBegin"] - start}:{token["characterOffsetEnd"] - start - 1}'

            # if skey in alignments:
            #     # TODO: If we don't have an exact correspondance then the parsing is different
            #     # for the parser and MT. For the moment we'll believe the parser

            #     # FIXME: this will require changing the clients to just get the 'best_guess'
            #     # rather than getting the value for the 'normalizedTarget' key from a dict it is currently
            #     # {"upos": "ADJ", "opos": "ADJ", "normalizedTarget": "\u4f1f\u5927",
            #     # "confidence": 0.2688, "trans_provider": "BING", "pinyin": ""}
            #     bgstart = int(alignments[skey].split(':')[0])
            #     bgend = int(alignments[skey].split(':')[1]) + 1
            #     bg = sentence['translation'][bgstart:bgend]
            #     token["best_guess"] = { 'normalizedTarget': bg }
            # else:

            best_guess = None
            others = []
            all_defs = []
            for t in token["definitions"].keys():
                for def_pos, defs in token["definitions"][t].items():
                    if not defs:
                        continue
                    all_defs += defs
                    if self.get_simple_pos(token) == def_pos:  # pylint: disable=R1723  # i'm pretty sure this is a bug
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
                logger.debug("No best_guess found for '%s', using the best 'other' POS defs %s", token["word"], others)

                best_guess = sorted(others, key=lambda i: i["confidence"], reverse=True)[0]

            if not best_guess and len(all_defs) > 0:
                # it's really bad
                best_guess = sorted(all_defs, key=lambda i: i["confidence"], reverse=True)[0]
                logger.debug(
                    """No best_guess found with the correct POS or OTHER for '%s',
                    using the highest confidence with the wrong POS all_defs %s""",
                    token["word"],
                    all_defs,
                )

            logger.debug("Setting best_guess for '%s' POS %s to best_guess %s", token["word"], token["pos"], best_guess)
            token["best_guess"] = best_guess


class SpaCy_EN_WordLemmatizer(WordLemmatizer):
    _POS = ["NOUN", "VERB", "ADJ"]

    def __init__(self, config):
        self._config = config
        # self._lemmatizer = Lemmatizer(LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES)

    # override Lemmatizer
    def lemmatize(self, lword):
        lemmas = set()
        for pos in self._POS:
            lemmas.update(self._lemmatizer(lword, pos))
        return lemmas
