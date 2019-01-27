# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import http.client, urllib.parse, uuid
import json
import logging
import re
import os
import sys
import requests

from django.core.cache import cache
from django.conf import settings

from enrich.models import BingAPILookup, BingAPITranslation, BingAPITransliteration

logger = logging.getLogger(__name__)

PinyinToneMark = {
    0: "aoeiuv\u00fc",
    1: "\u0101\u014d\u0113\u012b\u016b\u01d6\u01d6",
    2: "\u00e1\u00f3\u00e9\u00ed\u00fa\u01d8\u01d8",
    3: "\u01ce\u01d2\u011b\u01d0\u01d4\u01da\u01da",
    4: "\u00e0\u00f2\u00e8\u00ec\u00f9\u01dc\u01dc",
}
pins = "/aoeiuv\u00fc\u0101\u014d\u0113\u012b\u016b\u01d6\u01d6\u00e1\u00f3\u00e9\u00ed\u00fa\u01d8\u01d8\u01ce\u01d2\u011b\u01d0\u01d4\u01da\u01da\u00e0\u00f2\u00e8\u00ec\u00f9\u01dc\u01dc"

def decode_pinyin(s):
    s = s.lower()
    r = ""
    t = ""
    for c in s:
        if (c >= 'a' and c <= 'z') or c in pins:
            t += c
        elif c == ':':
            assert t[-1] == 'u'
            t = t[:-1] + "\u00fc"
        else:
            if c >= '0' and c <= '5':
                tone = int(c) % 5
                if tone != 0:
                    m = re.search("[aoeiuv\u00fc]+", t)
                    if m is None:
                        t += c
                    elif len(m.group(0)) == 1:
                        t = t[:m.start(0)] + PinyinToneMark[tone][PinyinToneMark[0].index(m.group(0))] + t[m.end(0):]
                    else:
                        if 'a' in t:
                            t = t.replace("a", PinyinToneMark[tone][0])
                        elif 'o' in t:
                            t = t.replace("o", PinyinToneMark[tone][1])
                        elif 'e' in t:
                            t = t.replace("e", PinyinToneMark[tone][2])
                        elif t.endswith("ui"):
                            t = t.replace("i", PinyinToneMark[tone][3])
                        elif t.endswith("iu"):
                            t = t.replace("u", PinyinToneMark[tone][4])
                        else:
                            t += "!"
            r += t
            t = ""
    r += t
    return r

cedict = {}

def load_cedict():
    logger.info("Populating cedict")
    with open(settings.CCCEDICT_PATH, 'r') as data_file:
        for line in data_file:
            line = line.strip()
            if line.startswith('#'):
                continue
            regex = r"^(\S+)\s+(\S+)\s+(\[[^]]+\])\s+(\/.*\/)$"

            match = re.search(regex, line)
            if not match:
                continue
            if not match.group(2) in cedict:
                cedict[match.group(2)] = []

            cedict[match.group(2)].append({ "pinyin": match.group(3), "definitions": match.group(4).strip('/').split('/') })

    logger.info("Finished populating cedict, there are {} entries".format(len(list(cedict.keys()))))
    # TODO: find out why this doesn't work! Doesn't work means up to 0.5 secs for a cache access...
    # cache.set('cccedict', cedict, None)

abc_dict = {}
p = re.compile('^(\d*)(\w+)(\S*)\s+(.+)$')
p_entries = {}
h_entries = {}
cur_pos = ''
cur_en = ''

def load_abc():
    ignore = 0
    entry = None
    with open(settings.ABCEDICT_PATH, 'r') as data_file:
        for line in data_file:
            # ignore non-useful lines
            if line.strip() in ['cidian.wenlindb', '.-arc', '.-publish', '--meta--']: continue
            if not line.strip(): ignore = 0; continue
            if line.strip() == 'h': ignore = 1; continue
            if ignore == 1: continue

            # start a new entry
            if line.startswith('.py   '):
                uid = line[6:].strip()
                if entry:  # flush the previous entry
                    if entry['pinyin'] in p_entries: raise Exception("looks like we would squash, not good")

                    p_entries[entry['pinyin']] = entry

                    if entry['char'] in h_entries:
                        h_entries[entry['char']].append(entry)
                    else:
                        h_entries[entry['char']] = [entry]

                entry = {'pinyin': uid, 'definitions': [], 'els': [], 'parents': {}}
                cur_pos = ''
                cur_en = 'gen'
                continue

            m = p.match(line)

            if m.group(2) in ['rem']: continue  # comments

            if m.group(2) in ['ser', 'ref', 'freq', 'hh'] and not m.group(1):
                entry[m.group(2)] = m.group(4)
            elif m.group(2) in ['char']:
                entry[m.group(2)] = m.group(4).split('[')[0]  # only get simplified, traditional is in brackets after
            elif m.group(2) == 'gr' and not m.group(1):  # entry-level grade
                entry[m.group(2)] = m.group(4)
            elif m.group(2) in ['ps']:
                cur_pos = m.group(4)
                entry['els'].append([m.group(1), m.group(2), m.group(4)])
            elif m.group(2) in ['en']:
                cur_en = m.group(4)
                entry['els'].append([m.group(1), m.group(2), m.group(4)])
            else:
                entry['els'].append([m.group(1), m.group(2), m.group(4)])
                if m.group(2) in ['df']:
                    entry['definitions'].append([m.group(1), cur_pos, m.group(4)])

    logger.info("Finished populating abcdict, there are {} entries".format(len(list(abc_dict.keys()))))

hsk_dict = {}

def load_hsk_dict():
    ignore = 0
    entry = None
    for i in range(1, 7):
        with open(settings.HSKDICT_PATH.format(i), 'r') as data_file:
            for line in data_file:
                # 爱	愛	ai4	ài	love
                l = line.strip().split("\t")

                if not l[0] in hsk_dict:
                    hsk_dict[l[0]] = []
                hsk_dict[l[0]].append({ "pinyin": l[3], "hsk": i })


subtlex = {}

def load_subt():
    # see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch/webpage.doc
    # file slightly modified, see settings.py and the file path for modification details
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

    with open(settings.SUBLEX_FREQ_PATH, 'r') as data_file:
        for line in data_file:
            l = line.strip().split("\t")
            if not l[0] in subtlex:
                subtlex[l[0]] = []
            subtlex[l[0]].append({
                "pinyin": decode_pinyin(l[2]),  # can be several, separated by /
                "wcpm": l[5],  # word count per million
                "wcdp": l[8],  # % of film subtitles that had the char at least once
                "pos": l[12],  # all POS found, most frequent first
                "pos_freq": l[13],  # nb of occurences by POS
            })

            if not line.strip(): ignore = 0; continue


# See https://gitlab.com/transcrobes/transcrobes/issues/4 for what this should look like
if 'transcrobes.wsgi' in sys.argv or 'runserver' in sys.argv:
    logger.info('Loading any static dictionary files present')
    if os.path.isfile(settings.CCCEDICT_PATH): load_cedict()
    if os.path.isfile(settings.ABCEDICT_PATH): load_abc()
    if os.path.isfile(settings.HSKDICT_PATH.format(1)): load_hsk_dict()
    if os.path.isfile(settings.SUBLEX_FREQ_PATH): load_subt()
else:
    logger.info('Not running the web application, not loading the static dictionary files')

class Translator(ABC):
    # See https://dkpro.github.io/dkpro-core/releases/1.9.0/docs/tagset-reference.html
    # for a complete list of papers that have POS for various languages!

    # We started with Bing, so are going to call their POS types "standard"
    #
    #
    # Bing POS types
    # https://docs.microsoft.com/en-us/azure/cognitive-services/translator/reference/v3-0-dictionary-lookup?tabs=curl
    # posTag: A string associating this term with a part-of-speech tag.
    #
    # Tag name  Description
    # ADJ   Adjectives
    # ADV   Adverbs
    # CONJ  Conjunctions
    # DET   Determiners
    # MODAL Verbs
    # NOUN  Nouns
    # PREP  Prepositions
    # PRON  Pronouns
    # VERB  Verbs
    # OTHER Other


    # the CoreNLP POS tags are from the Penn Chinese Treebank project, see
    # and http://www.cs.brandeis.edu/~clp/ctb/posguide.3rd.ch.pdf

    # Here taken from that paper's table of contents
    # Verb: VA, VC, VE, VV
    # 2.1.1 Predicative adjective: VA
    # 2.1.2 Copula: VC
    # 2.1.3 you3 as the main verb: VE
    # 2.1.4 Other verb: VV
    #
    # 2.2 Noun: NR, NT, NN
    # 2.2.1 Proper Noun: NR
    # 2.2.2 Temporal Noun: NT
    # 2.2.3 Other Noun: NN
    #
    # 2.3 Localizer: LC
    #
    # 2.4 Pronoun: PN
    #
    # 2.5 Determiners and numbers: DT, CD, OD
    # 2.5.1 Determiner: DT
    # 2.5.2 Cardinal Number: CD
    # 2.5.3 Ordinal Number: OD
    #
    # 2.6 Measure word: M
    #
    # 2.7 Adverb: AD
    #
    # 2.8 Preposition: P
    #
    # 2.9 Conjunctions: CC, CS
    # 2.9.1 Coordinating conjunction: CC
    # 2.9.2 Subordinating conjunction: CS
    #
    # 2.10 Particle: DEC, DEG, DER, DEV, AS, SP, ETC, MSP
    # 2.10.1 de5 as a complementizer or a nominalizer: DEC
    # 2.10.2 de5 as a genitive marker and an associative marker: DEG
    # 2.10.3 Resultative de5: DER
    # 2.10.4 Manner de5: DEV
    # 2.10.5 Aspect Particle: AS
    # 2.10.6 Sentence-final particle: SP
    # 2.10.7 ETC
    # 2.10.8 Other particle: MSP
    #
    # 2.11 Others: IJ, ON, LB, SB, BA, JJ, FW, PU
    # 2.11.1 Interjection: IJ
    # 2.11.2 Onomatopoeia: ON
    # 2.11.3 bei4 in long bei-construction: LB
    # 2.11.4 bei4 in short bei-construction: SB
    # 2.11.5 ba3 in ba-construction: BA
    # 2.11.6 other noun-modifier: JJ
    # 2.11.7 Foreign Word: FW
    # 2.11.8 Punctuation: PU


    # Tag name  Description
    # ADJ   Adjectives
    # ADV   Adverbs
    # CONJ  Conjunctions
    # DET   Determiners
    # MODAL Verbs
    # NOUN  Nouns
    # PREP  Prepositions
    # PRON  Pronouns
    # VERB  Verbs
    # OTHER Other

    # This was a little arbitrary...
    NLP_POS_TO_SIMPLE_POS = {
        'AD'  :  'ADV',       # adverb
        'AS'  :  'OTHER',     # aspect marker
        'BA'  :  'OTHER',     # in ba-construction ,
        'CC'  :  'CONJ',      # coordinating conjunction
        'CD'  :  'DET',       # cardinal number
        'CS'  :  'CONJ',      # subordinating conjunction
        'DEC' :  'OTHER',     # in a relative-clause
        'DEG' :  'OTHER',     # associative
        'DER' :  'OTHER',     # in V-de const. and V-de-R
        'DEV' :  'OTHER',     # before VP
        'DT'  :  'DET',       # determiner
        'ETC' :  'OTHER',     # for words , ,
        'FW'  :  'OTHER',     # foreign words
        'IJ'  :  'OTHER',     # interjection
        'JJ'  :  'ADJ',       # other noun-modifier ,
        'LB'  :  'OTHER',     # in long bei-const ,
        'LC'  :  'OTHER',     # localizer
        'M'   :  'OTHER',     # measure word
        'MSP' :  'OTHER',     # other particle
        'NN'  :  'NOUN',      # common noun
        'NR'  :  'NOUN',      # proper noun
        'NT'  :  'NOUN',      # temporal noun
        'OD'  :  'DET',       # ordinal number
        'ON'  :  'OTHER',     # onomatopoeia ,
        'P'   :  'PREP',      # preposition excl. and
        'PN'  :  'PRON',      # pronoun
        'PU'  :  'OTHER',     # punctuation
        'SB'  :  'OTHER',     # in short bei-const ,
        'SP'  :  'OTHER',     # sentence-final particle
        'VA'  :  'ADJ',       # predicative adjective
        'VC'  :  'VERB',
        'VE'  :  'VERB',      # as the main verb
        'VV'  :  'VERB',      # other verb
        # Others added since then
        'URL' :  'OTHER',
    }
    # see https://gitlab.com/Wenlin/WenlinTushuguan/blob/master/Help/abbrev.wenlin
    # for the ABC abbrevs. The POS are actually quite dissimilar between CoreNLP and ABC
    # with whole categories missing from one or the other (prefix vs preposition) :(
    NLP_POS_TO_ABC_POS = {
        'AD'  :  'adv.',       # adverb
        'AS'  :  'a.m.',     # aspect marker
        'BA'  :  'other',     # in ba-construction ,
        'CC'  :  'conj.',      # coordinating conjunction
        'CD'  :  'num.',       # cardinal number ???
        'CS'  :  'conj.',      # subordinating conjunction ???
        'DEC' :  'other',     # in a relative-clause ??? maybe 's.p.'
        'DEG' :  'other',     # associative ???
        'DER' :  'other',     # in V-de const. and V-de-R ???
        'DEV' :  'other',     # before VP
        'DT'  :  'pr.',       # determiner ??? always appear to be as pr in the ABC
        'ETC' :  'suf.',     # for words , ,
        'FW'  :  'other',     # foreign words
        'IJ'  :  'intj.',     # interjection
        'JJ'  :  'attr.',       # other noun-modifier ,
        'LB'  :  'other',     # in long bei-const ,
        'LC'  :  'other',     # localizer
        'M'   :  'm.',     # measure word
        'MSP' :  'other',     # other particle
        'NN'  :  'n.',      # common noun
        'NR'  :  'n.',      # proper noun
        'NT'  :  'n.',      # temporal noun
        'OD'  :  'num.',       # ordinal number
        'ON'  :  'on.',     # onomatopoeia ,
        'P'   :  'other',      # preposition excl. and
        'PN'  :  'pr.',      # pronoun
        'PU'  :  'other',     # punctuation
        'SB'  :  'other',     # in short bei-const ,
        'SP'  :  'other',     # sentence-final particle
        'VA'  :  's.v.',       # predicative adjective
        'VC'  :  'v.',
        'VE'  :  'v.',      # as the main verb
        'VV'  :  'v.',      # other verb
        # Others added since then
        'URL' :  'other',
    }

    @abstractmethod
    def get_standardised_defs(self, token, with_pinyin=False):
        pass

    @abstractmethod
    def get_standardised_fallback_defs(self, token, with_pinyin=False):
        pass

    @abstractmethod
    def transliterate(self, text):
        pass

class BingTranslator(Translator):
    # public methods
    def get_standardised_defs(self, token, with_pinyin=False):
        result = self._ask_bing_lookup(token["word"])
        jresult = json.loads(result)
        bing = jresult[0]['translations']
        std_format = {}
        for trans in bing:
            if not trans["posTag"] in std_format:
                std_format[trans["posTag"]] = []
            defie = {
                "upos": trans["posTag"],
                "opos": trans["posTag"],
                "normalizedTarget": trans["normalizedTarget"],
                "confidence": trans["confidence"],
                "trans_provider": 'BING',
            }
            if with_pinyin:
                defie["pinyin"] = self.transliterate(token["word"])
            std_format[trans["posTag"]].append(defie)

        return std_format

    def get_standardised_fallback_defs(self, token, with_pinyin=False):
        result = self._ask_bing_translate(token["word"])
        jresult = json.loads(result)

        std_format = [{
            "upos": 'OTHER',
            "opos": 'OTHER',
            "normalizedTarget": jresult[0]['translations'][0]['text'],
            "confidence": 0,
            "trans_provider": 'BING-DEFAULT',
        }]
        if with_pinyin:
            std_format[0]["pinyin"] = self.transliterate(token["word"])

        return {"OTHER": std_format }

    def translate(self, text):
        result = self._ask_bing_translate(text)
        jresult = json.loads(result)

        translation = jresult[0]['translations'][0]['text']
        logging.debug("Returning Bing translation '{}' for '{}'".format(translation, text))
        return translation

    def transliterate(self, text):
        result = self._ask_bing_transliterate(text)
        jresult = json.loads(result)

        trans = jresult[0]['text']
        logging.debug("Returning Bing transliteration '{}' for '{}'".format(trans, text))
        return trans


    # private methods
    def _request_json(self, text):
        requestBody = [{
            'Text' : text,
        }]
        return json.dumps(requestBody, ensure_ascii=False)

    def _ask_bing_api(self, content, endpoint):
        req_json = self._request_json(content)
        params = {
            'api-version': '3.0',
            'from': 'zh-Hans',
            'to': 'en',
        }
        scheme = 'https://'
        logger.debug("Looking up '{}' in Bing using json: {}".format(content, req_json))
        if endpoint == 'lookup':
            path = '/dictionary/lookup'
        elif endpoint == 'transliterate':
            path = '/transliterate'
            params['language'] = 'zh-Hans'
            params['fromScript'] = 'Hans'
            params['toScript'] = 'Latn'
        else:
            path = '/translate'

        headers = {
            'Ocp-Apim-Subscription-Key': settings.BING_SUBSCRIPTION_KEY,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        r = requests.post("{}{}{}".format(scheme, settings.BING_API_HOST, path), data=req_json.encode('utf-8'),
                          params=params, headers=headers)
        logger.debug("Received '{}' back from Bing".format(r.text))
        r.raise_for_status()

        return r.text

    def _ask_bing_lookup(self, content):
        found = BingAPILookup.objects.filter(source_text=content)
        logger.debug("Found {} elements in db for {}".format(len(found), content))
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, 'lookup')
            bing = BingAPILookup(source_text=content, response_json=bing_json)
            bing.save()
            return bing.response_json
        else:
            return found.first().response_json  # TODO: be better, just being dumb for the moment

    def _ask_bing_translate(self, content):
        found = BingAPITranslation.objects.filter(source_text=content)
        logger.debug("Found {} elements in db for {}".format(len(found), content))
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, 'translate')  # .decode('utf-8')
            bing = BingAPITranslation(source_text=content, response_json=bing_json)
            bing.save()
            return bing.response_json
        else:
            return found.first().response_json


    def _ask_bing_transliterate(self, content):
        found = BingAPITransliteration.objects.filter(source_text=content)
        logger.debug("Found {} elements in db for {}".format(len(found), content))
        if len(found) == 0:
            bing_json = self._ask_bing_api(content, 'transliterate')  # .decode('utf-8')
            bing = BingAPITransliteration(source_text=content, response_json=bing_json)
            bing.save()
            return bing.response_json
        else:
            return found.first().response_json

class CCCedictTranslator(Translator):
    def _all_dict(self):
        return cedict

    # TODO: investigate git@github.com:wuliang/CedictPlus.git - it has POS. It also hasn't been updated in 6 years...
    def get_standardised_defs(self, token, with_pinyin=False):
        std_format = {}
        if token["word"] in cedict:
            logger.debug("'{}' is in cccedict cache".format(token["word"]))
            for cc in cedict[token["word"]]:
                logger.debug("Iterating on '{}''s different forms in cccedict cache".format(token["word"]))
                for defin in cc['definitions']:
                    logger.debug("Iterating on '{}''s different definitions in cccedict cache".format(
                        token["word"]))
                    logger.debug("Checking for POS hint for '{}' in cccedict".format(token["word"]))
                    token_pos = self.NLP_POS_TO_SIMPLE_POS[token["pos"]]

                    if defin.startswith('to '): defin_pos = 'VERB'
                    elif defin.startswith('a '): defin_pos = 'NOUN'
                    else: defin_pos = 'OTHER'

                    if not defin_pos in std_format: std_format[defin_pos] = []

                    confidence = 0

                    if (token_pos == 'VERB' and defin_pos == 'VERB') or (token_pos == 'NOUN' and defin_pos == 'NOUN'):
                        confidence = 0.01

                    defie = {
                        "upos": defin_pos,
                        "opos": defin_pos,
                        "normalizedTarget": defin,
                        "confidence": confidence,
                        "trans_provider": 'CEDICT'
                    }
                    if with_pinyin:
                        defie["pinyin"] = decode_pinyin(cc["pinyin"])
                    std_format[defin_pos].append(defie)

        logger.debug("Finishing looking up '{}' in cccedict".format(token["word"]))
        return std_format

    def get_standardised_fallback_defs(self, token, with_pinyin=False):
        # TODO: do something better than this!
        return self.get_standardised_defs(token, with_pinyin)

    def transliterate(self, text):
        raise NotImplementedError()


class ABCDictTranslator(Translator):

    def _all_dict(self):
        return h_entries

    # TODO: fix the POS correspondences
    def get_standardised_defs(self, token, with_pinyin=False):
        std_format = {}
        if token["word"] in h_entries:
            logger.debug("'{}' is in abcdict cache".format(token["word"]))
            for abc in h_entries[token["word"]]:
                logger.debug("Iterating on '{}''s different definitions in abcdict cache".format(token["word"]))
                for defin in abc['definitions']:
                    token_pos = self.NLP_POS_TO_ABC_POS[token["pos"]]

                    if not defin[1] in std_format: std_format[defin[1]] = []

                    confidence = 0
                    if token_pos == defin[1]:
                        confidence = 0.01
                    else:
                        confidence = 0

                    defie = {
                        "upos": token_pos,
                        "opos": defin[1],
                        "normalizedTarget": defin[2],
                        "confidence": confidence,
                        "trans_provider": 'ABCDICT'
                    }
                    if with_pinyin:
                        defie["pinyin"] = decode_pinyin(abc["pinyin"])
                    std_format[defin[1]].append(defie)

        logger.debug("Finishing looking up '{}' in cccedict".format(token["word"]))
        return std_format

    def get_standardised_fallback_defs(self, token, with_pinyin=False):
        # TODO: do something better than this!
        return self.get_standardised_defs(token, with_pinyin)

    def transliterate(self, text):
        raise NotImplementedError()
