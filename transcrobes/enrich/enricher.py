# -*- coding: utf-8 -*-

import requests
import json
import sys
import re
import http.client, urllib.parse, uuid
import logging
import collections
import unicodedata

from django.conf import settings

from enrich.nlp.provider import CoreNLPProvider
from enrich.translate.translator import BingTranslator, CCCedictTranslator, Translator, ABCDictTranslator
from enrich.translate.translator import hsk_dict, subtlex
from ankrobes import AnkrobesServer
from utils import get_credentials

logger = logging.getLogger(__name__)

has_chinese_chars = re.compile('[\u4e00-\u9fa5]+')

def _get_transliteratable_sentence(tokens):
    t_sent = ""
    for t in tokens:
        w = t['originalText']
        t_sent += w if has_chinese_chars.match(w) else " {}".format(w)
    return t_sent

def _add_transliterations(sentence, transliterator):
    tokens = sentence['tokens']
    clean_text = _get_transliteratable_sentence(tokens)
    trans = transliterator.transliterate(clean_text)

    clean_trans = " "

    i = 0
    while i < len(trans):
        char_added = False
        if not unicodedata.category(trans[i]).startswith('L') or not unicodedata.category(trans[i-1]).startswith('L'):
            clean_trans += " "

        clean_trans += trans[i]
        i += 1

    clean_trans = " ".join(list(filter(None, clean_trans.split(' '))))

    deq = collections.deque(clean_trans.split(' '))

    for t in tokens:
        w = t['originalText']
        pinyin = []
        i = 0
        nc = ""
        while i < len(w):
            if unicodedata.category(w[i]) == ('Lo'):  # it's a Chinese char
                pinyin.append(deq.popleft())
            else:
                if not nc:
                    nc = deq.popleft()

                if w[i] != nc[0]:
                    raise Exception("{} should equal {} for '{}' and tokens '{}' with original {}".format(
                        w[i], nc, clean_trans, tokens, clean_text))
                pinyin.append(w[i])
                if len(nc) > 1:
                    nc = nc[1:]
                else:
                    nc = ""
            i += 1
        t['pinyin'] = pinyin


def _enrich_model(model, username, password):
    server = AnkrobesServer(username, password)
    server.hostKey(username, password)

    online_translator = BingTranslator()
    cedict = CCCedictTranslator()
    abcdict = ABCDictTranslator()

    for s in model['sentences']:
        _add_transliterations(s, online_translator)

        logger.debug("Looking for tokens to translate in {}".format(s))
        clean_sentence_text = ""
        for t in s['tokens']:
            # logger.info("Here is my tokie: {}".format(t))
            w = t['word']
            # logger.debug("Starting to check: {}".format(w))
            if w.startswith('<') and w.endswith('>'):  # html
                logger.debug("Looks like '{}' only has html, not adding to translatables".format(w))
                continue

            # From here we keep the words for the cleaned sentence (e.g., for translation)
            clean_sentence_text += w

            if t['pos'] in ['PU', 'OD', 'CD', 'NT', 'URL']:
                logger.debug("'{}' has POS '{}' so not adding to translatables".format(w, t['pos']))
                continue

            # TODO: decide whether to continue removing if doesn't contain any Chinese chars?
            # Sometimes yes, sometimes no!
            if not has_chinese_chars.match(w):
                continue

            # From here we attempt translation and create ankrobes entries
            ank_entry = _sanitise_ankrobes_entry(server.get_word(w))
            t["ankrobes_entry"] = ank_entry
            t["definitions"] = {
                'best': online_translator.get_standardised_defs(t),
                'second': abcdict.get_standardised_defs(t),
                'third': cedict.get_standardised_defs(t),
                'fallback': online_translator.get_standardised_fallback_defs(t)
            }
            t["normalized_pos"] = Translator.NLP_POS_TO_SIMPLE_POS[t["pos"]]

            # TODO: decide whether we really don't want to make a best guess for words we know
            # this might still be very useful though probably not until we have a best-trans-in-context SMT system
            # that is good
            # logger.debug("my ank_entry is {}".format(ank_entry))
            if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
                # get the best guess for the definition of the word given the context of the sentence
                _set_best_guess(s, t)

            t["stats"] = {
                'hsk': hsk_dict[w] if w in hsk_dict else None,
                'freq': subtlex[w] if w in subtlex else None,
            }


        s['cleaned'] = clean_sentence_text
        s['translation'] = online_translator.translate(clean_sentence_text)

def _sanitise_ankrobes_entry(entries):
    # we don't need the HTML here - we'll put the proper html back in later
    for entry in entries:
        entry['Simplified'] = re.sub("(?:<[^>]+>)*", '', entry['Simplified'], flags=re.MULTILINE)
        entry['Pinyin'] = re.sub("(?:<[^>]+>)*", '', entry['Pinyin'], flags=re.MULTILINE)
        entry['Meaning'] = re.sub("(?:<[^>]+>)*", '', entry['Meaning'], flags=re.MULTILINE)
    return entries

def _set_best_guess(sentence, token):
    # TODO: do something intelligent here
    # ideally this will translate the sentence using some sort of statistical method but get the best
    # translation for each individual word of the sentence, not the whole sentence, giving us the
    # most appropriate definition to show to the user

    best_guess = None
    others = []
    all_defs = []
    for t in ["best", "second", "third", "fallback"]:  # force the order
        for def_pos, defs in token["definitions"][t].items():
            if not defs:
                continue
            all_defs += defs
            if Translator.NLP_POS_TO_SIMPLE_POS[token["pos"]] == def_pos or Translator.NLP_POS_TO_ABC_POS[token["pos"]] == def_pos:
                # get the most confident for the right POs
                sorted_defs = sorted(defs, key = lambda i: i['confidence'], reverse=True)
                best_guess = sorted_defs[0]
                break
            elif def_pos == "OTHER":
                others += defs
        if best_guess:
            break

    if not best_guess and len(others) > 0:
        # it's bad
        logger.debug("No best_guess found for '{}', using the best 'other' POS defs {}".format(token["word"], others))

        best_guess = sorted(others, key = lambda i: i['confidence'], reverse=True)[0]

    if not best_guess and len(all_defs) > 0:
        # it's really bad
        best_guess = sorted(all_defs, key = lambda i: i['confidence'], reverse=True)[0]
        logger.debug("No best_guess found with the correct POS or OTHER for '{}', using the highest confidence with the wrong POS all_defs {}".format(
            token["word"], all_defs))

    logger.debug("Setting best_guess for '{}' POS {} to best_guess {}".format(token["word"], token["pos"], best_guess))
    token["best_guess"] = best_guess  # .split(',')[0].split(';')[0]


def enrich_to_json(html, username, password):
    # TODO: make this OOP with a factory method controlled from the settings
    model = CoreNLPProvider().parse(html)

    logging.debug("Attempting to enrich: '{}'".format(html))
    _enrich_model(model, username, password)

    return model
