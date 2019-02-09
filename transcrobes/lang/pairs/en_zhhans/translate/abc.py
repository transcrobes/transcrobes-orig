# -*- coding: utf-8 -*-

import re
import os
import json
import logging
from collections import defaultdict

from en_zhhans.models import ABCENLookup
from enrich.data import PersistenceProvider
from enrich.translate import Translator

logger = logging.getLogger(__name__)


# TODO: This was a little arbitrary...
# see https://gitlab.com/Wenlin/WenlinTushuguan/blob/master/Help/abbrev.wenlin
# for the ABC abbrevs. The POS are actually quite dissimilar between CoreNLP and ABC
# with whole categories missing from one or the other (prefix vs preposition) :(

"""
ABC pos, only including values actually found in yinghan.u8
ab.             abbreviation   suōxiě 缩写
abbr.           or 'abbrev.' in docs - abbreviated   suōxiě de 缩写的
adj.            adjective   xíngróngcí 形容词
adv.            adverb   fùcí 副词
art.            article   guàncí 冠词
attr.           attributive   dìngyǔ 定语
aux.            auxiliary verb   zhùdòngcí 助动词
b.f.            bound form   niánzhuó císù 粘着词素
c.              erroneous 'n.u./n.c.' entered as 'n.u/c.' countable noun   kẹ̌shǔ míngcí 可数名词
cmp.            complement   bụ̌yǔ 补语, jiéguǒ bǔyǔcí 结果补语词
conj.           conjunction   liáncí 连词
f.e.            fixed expression   gùdìng cízǔ 固定词组
id.             idiomatic saying   xíyǔ 习语
intj.           interjection   gǎntàn 感叹
m.              measure   liàngcí 量词
n.              noun   míngcí 名词
n.c             duplicated - countable noun   kẹ̌shǔ míngcí 可数名词
n.c.            duplicated - countable noun   kẹ̌shǔ míngcí 可数名词
n.pl.           or 'n.p.' in docs - plural noun   fùshù míngcí 复数名词
n.sing.         singular noun   dānshù míngcí 单数名词
n.u.            uncountable noun   bùkẹ̌shǔ míngcí 不可数名词
num.            number   shùcí 数词
on.             onomatopoeia   xiàngshēngcí 象声词
pl.             plural   fùshù 复数
pr.             pronoun   dàicí 代词
pref.           prefix   qiánzhuì 前缀
prep.           preposition  - but not included in docs!!!
r.f.            reduplicated form   chóngdiécí 重叠词
suf.            suffix   hòuzhuì 后缀
u.              erroneous 'n.c./n.u.' entered as 'n.c/u.' uncountable noun   bùkẹ̌shǔ míngcí 不可数名词
v.              verb   dòngcí 动词
v.i.            intransitive verb   bùjíwù dòngcí 不及物动词
v.p.            verb phrase   dòngcí cízǔ 动词词组
v.t.            transitive verb   jíwù dòngcí 及物动词
"""

EN_TB_POS_TO_ABC_POS = {
    'CC'  :  'conj.',          # Coordinating conjunction
    'CD'  :  'num.',          # Cardinal number
    'DT'  :  'other',          # Determiner
    'EX'  :  'other',          # Existential _there_
    'FW'  :  'other',          # Foreign word
    'IN'  :  'prep.',          # Preposition or subordinating conjunction
    'JJ'  :  'adj.',          # Adjective
    'JJR' :  'adj.',          # Adjective, comparative
    'JJS' :  'adj.',          # Adjective, superlative
    'LS'  :  'other',          # List item marker
    'MD'  :  'other',          # Modal
    'NN'  :  'n.sing.',          # Noun, singular or mass
    'NNS' :  'n.pl.',          # Noun, plural
    'NNP' :  'n.sing.',          # Proper noun, singular
    'NNPS':  'n.pl.',          # Proper noun, plural
    'PDT' :  'other',          # Predeterminer
    'POS' :  'other',          # Possessive ending
    'PRP' :  'pr.',          # Personal pronoun
    'PRP$':  'pr.',          # Possessive pronoun
    'RB'  :  'adv.',          # Adverb
    'RBR' :  'adv.',          # Adverb, comparitive
    'RBS' :  'adv.',          # Adverb, superlative
    'RP'  :  'other',          # Particle
    'SYM' :  'other',          # Symbol
    'TO'  :  'prep.',          # _to_
    'UH'  :  'intj.',          # Interjection
    'VB'  :  'v.',          # Verb, base form
    'VBD' :  'v.',          # Verb, past tense
    'VBG' :  'v.',          # Verb, gerund or present participle
    'VBN' :  'v.',          # Verb, past participle
    'VBP' :  'v.',          # Verb, non-3rd person singular present
    'VBZ' :  'v.',          # Verb, 3rd person singular present
    'WDT' :  'other',          # Wh-determiner
    'WP'  :  'pr.',          # Wh-pronoun
    'WP$' :  'pr.',          # Possessive wh-pronoun
    'WRB' :  'adv.',          # Wh-adverb
}


class EN_ZHHANS_ABCDictTranslator(PersistenceProvider, Translator):
    """
    General comments:
    There are many multi-word expressions for '.hw' in the file, e.g,
    - as far as ... is concerned
    - as far as sb./sth. is concerned
    - as for/to
    Multi-word expressions usually (always???) have a 'subof' entry which refers to
    another single-word '.hw'

    There is no unique identifier line - '.hw' has many duplicate entries, e.g,
    - ascending (x2)
    - as a matter of fact (x2)
    - as busy as a bee (x2)


    Some values have a leading superscript, e.g,
    - ¹ash and ²ash
    Some do not, e.g,
    - ashes (x2)
    - ascending (x2)
    These duplicates appear to often refer to other 'proper root entries' via 'subof', 'infl'

    Plurals are often included as '.hw'

    """

    p = re.compile('^(\d*)(\w+)(\S*)\s+(.+)$')
    model_type = ABCENLookup

    # override Metadata
    @staticmethod
    def name():
        return 'second'

    def _load(self):
        merged_dict = defaultdict(list)

        if os.path.exists(self._config['path']):
            dico = self._preload()
            self._remove_infl_of(dico)
            self._remove_subof(dico)

            for k, v in dico.items():
                merged_dict[v[0]['hw'].encode('ascii', 'ignore').decode('utf-8')].append(v[0])

        return merged_dict


    def _preload(self):
        cur_pos = ''
        cur_en = ''
        ignore = 0
        entry = None

        dico = {}  # reset if we have already loaded
        with open(self._config['path'], 'r') as data_file:
            for line in data_file:
                # ignore non-useful lines
                if not line.strip(): ignore = 0; continue

                if line.startswith('.hw   '):
                    uid = line[6:].strip()
                    if entry:  # flush the previous entry
                        if entry['ser'] in dico:
                            dico[entry['ser']].append(entry)
                        else:
                            dico[entry['ser']] = [entry]

                    entry = {'hw': uid, 'definitions': [], 'els': []}
                    cur_pos = ''
                    cur_en = 'gen'
                    continue

                m = self.p.match(line)

                if m.group(2) in ['rem']: continue  # comments

                if m.group(2) in ['ser', 'ref', 'ipa'] and not m.group(1):
                    entry[m.group(2)] = m.group(4)
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

            if entry:  # flush the last entry
                if entry['ser'] in dico:
                    dico[entry['ser']].append(entry)
                else:
                    dico[entry['ser']] = [entry]

        return dico

    def _remove_infl_of(self, dico):
        i = 0
        bad = 0
        wdico = dico.copy()
        reg = re.compile(r".* of .*\[([0-9]+)\].*")
        for k, v in wdico.items():
            for ls in v[0]['els']:
                if ls[1] == 'infl':
                    m = reg.match(ls[2])
                    if m and m.group(1):
                        if 'infls' not in dico[m.group(1)][0]:
                            dico[m.group(1)][0]['infls'] = []
                        if k in dico:
                            if len(v[0]['definitions']) == 0:
                                dico[m.group(1)][0]['infls'].append(dico.pop(k))

    def _remove_subof(self, dico):
        i = 0
        wdico = dico.copy()
        reg = re.compile(r".*\[([0-9]+)\].*")
        for k, v in wdico.items():
            for ls in v[0]['els']:
                if ls[1] == 'subof':
                    m = reg.match(ls[2])
                    if m and m.group(1):
                        if m.group(1) not in dico:
                            continue
                        if 'subs' not in dico[m.group(1)][0]:
                            dico[m.group(1)][0]['subs'] = []
                        if k in dico:
                            if len(v[0]['definitions']) == 0 or len(v[0]['hw'].split()) > 0:
                                dico[m.group(1)][0]['subs'].append(dico.pop(k))


    # TODO: fix the POS correspondences
    # override Translator
    def get_standardised_defs(self, token):
        std_format = {}
        entry = self._get_def(token['lemma'])
        if entry:
            logger.debug("'{}' is in abcendict cache".format(token["lemma"]))
            for abc in entry:
                logger.debug("Iterating on '{}''s different definitions in abcendict cache".format(token["lemma"]))
                for defin in abc['definitions']:
                    token_pos = EN_TB_POS_TO_ABC_POS[token["pos"]]

                    if not defin[1] in std_format: std_format[defin[1]] = []

                    if token_pos == defin[1]:
                        confidence = 0.01
                    else:
                        confidence = 0

                    defie = {
                        "upos": token_pos,
                        "opos": defin[1],
                        "normalizedTarget": defin[2],
                        "confidence": confidence,
                        "trans_provider": 'ABCENDICT'
                    }
                    defie["pinyin"] = abc.get("ipa", 'unknown')
                    std_format[defin[1]].append(defie)

        logger.debug("Finishing looking up '{}' in abcendict".format(token["lemma"]))
        return std_format

    # override Translator
    def get_standardised_fallback_defs(self, token):
        # TODO: do something better than this!
        return self.get_standardised_defs(token)

