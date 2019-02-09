# -*- coding: utf-8 -*-

import os
import json
import re
import glob
from urllib.parse import urlencode
import tempfile

from django.conf import settings
from django.test import TestCase
from django.db import connection

import requests_mock

from ankrobes import dum
from enrich.enricher import _get_transliteratable_sentence
from enrich.enricher import _add_transliterations
from enrich.enricher import enrich_to_json
from enrich.enricher import _set_best_guess
from enrich.nlp.provider import CoreNLPProvider
from enrich import metadata
from enrich.translate import bing



class EnricherTests(TestCase):
    ##
    ## The main data for these tests was taken on 2019-02-09 from the 2nd paragraph of
    ## http://www.xinhuanet.com/2019-02/08/c_1124092961.htm
    ##
    ##

    ##
    ## Plumbing methods
    ##
    @classmethod
    def setUpClass(cls):
        super(EnricherTests, cls).setUpClass()
        # FIXME: move me
        # from zhhans_en.metadata import hsk
        # from zhhans_en.metadata import subtlex
        # hsk.load()
        # subtlex.load()
        # from zhhans_en.translate import abc
        # from zhhans_en.translate import ccc
        # abc.load()
        # ccc.load()


    _nsre = re.compile('([0-9]+)')

    def setUp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.dum = dum.DjangoUserManager(settings.ANKISYNCD_CONFIG())
            self.user = self.dum.add_user(username='toto', email='toto@transcrob.es', password='top_secret')

        self.assets = os.path.join(settings.BASE_DIR, 'enrich', 'test', 'assets')

    ##
    ## helper methods
    ###
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(EnricherTests._nsre, s)]
    ##
    ## Tests for public methods
    ##

    # _get_transliteratable_sentence
    def _get_transliteratable_sentence_from_res(self, text_type):
        with open(os.path.join(self.assets, f'{text_type}.json'), 'r') as f:
            json_text = f.read()
        tokens = json.loads(json_text)['sentences'][0]['tokens']

        return _get_transliteratable_sentence(tokens)


    def test_get_transliteratable_sentence_ascii(self):
        """
        _get_transliteratable_sentence returns ascii tokens preceded by spaces
        """
        self.assertEquals(self._get_transliteratable_sentence_from_res('ascii'),
                          ' RCS ( Rich Communication Services )')

    def test_get_transliteratable_sentence_chars(self):
        """
        _get_transliteratable_sentence returns char tokens not separated by spaces
        """
        self.assertEquals(self._get_transliteratable_sentence_from_res('chars'),
                          '文章提交注意事项')

    def test_get_transliteratable_sentence_mixed(self):
        """
        _get_transliteratable_sentence returns only ascii tokens not separated by spaces in mixed text
        """
        self.assertEquals(self._get_transliteratable_sentence_from_res('mixed'),
                          '科技 : NHK以特别版 《 2001太空奥德赛 》推出首个 8K电视频道')

    # def enrich_to_json(html, username, password):
    @requests_mock.Mocker()
    def test_enrich_to_json(self, m):
    # def test_enrich_to_json(self):
        intxt_file = os.path.join(self.assets, 'nlp', 'in.txt')
        parsed_file = os.path.join(self.assets, 'nlp', 'parsed.json')
        bing_base = os.path.join(self.assets, 'bing')
        enriched_no_notes_file = os.path.join(bing_base, 'enriched_model_no_notes.json')
        enriched_with_notes_file = os.path.join(bing_base, 'enriched_model_with_notes.json')

        # myhsk = metadata.providers['hsk']
        # self.assertEqual(len(myhsk), 44)

        with open(intxt_file) as intxt, open(parsed_file) as parsed, open(enriched_no_notes_file) as enriched:
            parsed_json = parsed.read()
            intxt_txt = intxt.read()

            m.post(settings.CORENLP_URL, text=parsed_json)

            all_returns = []
            # get the complete set of queries, ordered by query order and add to query dict
            for json_dir in [('lookup', bing.LOOKUP_PATH),
                             ('transliterate', bing.TRANSLIT_PATH),
                             ('translate', bing.TRANSLAT_PATH)]:
                files = glob.glob(os.path.join(bing_base, json_dir[0], '*'))
                files.sort(key=EnricherTests.natural_sort_key)
                all_returns = []
                for filename in files:
                    with open(filename) as fname:
                        all_returns.append({'text': fname.read()})

                m.register_uri('POST', json_dir[1], all_returns)

            # test with no known entries
            model = enrich_to_json(intxt_txt, self.user.username)
            with open(os.path.join(settings.BASE_DIR, 'enriched_model_model.json'), 'w') as emwj:
                emwj.write(json.dumps(model, sort_keys=True, indent=4, separators=(',', ': ')))
            enriched_obj = json.load(enriched)
            # value = { k : enriched_obj[k] for k in set(enriched_obj) - set(model) }
            # from jsondiff import diff
            # print(diff(model, enriched_obj))
            with open(os.path.join(settings.BASE_DIR, 'enriched_model_from_file.json'), 'w') as emwj:
                emwj.write(json.dumps(enriched_obj, sort_keys=True, indent=4, separators=(',', ': ')))

            self.assertDictEqual(model, enriched_obj)
            # self.assertDictEqual(
            #     json.dumps(model, sort_keys=True, indent=4, separators=(',', ': ')),
            #     json.dumps(enriched_obj, sort_keys=True, indent=4, separators=(',', ': '))
            # )


        # Now add various notes so they are present in the userdb, and ensure they are properly
        # included as 'ankrobes_entry's in the output
        added_notes = []
        for fname in glob.glob(os.path.join(self.assets, 'notes', '*')):
            from ankrobes import Ankrobes
            with Ankrobes(self.user.username) as userdb, open(fname) as json_file:
                in_note = json.load(json_file)
                added_notes.append(in_note)
                note_id = userdb.add_ankrobes_note(simplified=in_note['Simplified'],
                                               pinyin=in_note['Pinyin'],
                                               meanings=[in_note['Meaning']],
                                               tags=in_note['Tags'],
                                               review_in=0)

        with open(enriched_with_notes_file) as enriched_notes:
            model = enrich_to_json(intxt_txt, self.user.username)
            self.assertEqual(model, json.load(enriched_notes))

        # clean up
        with Ankrobes(self.user.username) as userdb:
            userdb.delete_note(in_note['Simplified'])

    ##
    ## Tests for private methods
    ##

    # def _add_transliterations(sentence, transliterator):
    @requests_mock.Mocker()
    def test__add_transliterations(self, m):
    # def test__add_transliterations(self):
        from enrich.translate import bing
        dico = bing.BingTranslator({ 'from': 'zh-Hans', 'to':'en' })
        with open(os.path.join(self.assets, 'nlp', 'parsed.json'), 'r') as f:
            json_text = f.read()
        sentences = json.loads(json_text)['sentences']

        rets = [
            {'text': '[{"text":"xí jìn píng zài hè diàn zhōng zhǐ chū ， zhōng pú yǒu yì yuán yuǎn liú cháng。","script":"Latn"}]'},
            {'text': '[{"text":"jiàn jiāo 40 nián lái ， shuāng fāng bǐng chí xiāng hù zūn zhòng 、 píng děng xiāng dài 、 hù lì gòng yíng de jīng shén tuī dòng shuāng biān guān xì jiàn kāng wěn dìng fā zhǎn。","script":"Latn"}]'},
            {'text': '[{"text":"1999 nián ， shuāng fāng tuǒ shàn jiě jué ào mén wèn tí ， shù lì le guó yǔ guó tōng guò yǒu hǎo xié shāng jiě jué lì shǐ yí liú wèn tí de diǎn fàn。","script":"Latn"}]'},
            {'text': '[{"text":"2005 nián zhōng pú jiàn lì quán miàn zhàn luè huǒ bàn guān xì yǐ lái ， shuāng fāng gāo céng hù fǎng pín fán ， zhèng zhì hù xìn bú duàn jiā shēn ， gè lǐng yù hù lì hé zuò chéng guǒ xiǎn zhù。","script":"Latn"}]'},
            {'text': '[{"text":"bù jiǔ qián ， wǒ chéng gōng fǎng wèn guì guó ， tóng nǐ jìn xíng shēn rù yǒu hǎo jiāo liú ， gòng tóng guī huà le zhōng pú guān xì fā zhǎn xīn de lán tú。","script":"Latn"}]'},
            {'text': '[{"text":"wǒ gāo dù zhòng shì zhōng pú guān xì fā zhǎn ， yuàn tóng nǐ yí dào nǔ lì ， yǐ liǎng guó jiàn jiāo 40 zhōu nián wéi xīn qǐ diǎn ， tuī dòng zhōng pú quán miàn zhàn luè huǒ bàn guān xì mài shàng xīn tái jiē ， gèng hǎo zào fú liǎng guó hé liǎng guó rén mín。","script":"Latn"}]'},
        ]

        translit_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.TRANSLIT_PATH}?{urlencode(dico.translit_params())}'
        m.register_uri('POST', translit_url, rets)

        ## asserts generated with the following code and json from enrich/test/assets/nlp/parsed.json
        # for i in range(0, len(sentences)):
        #     for t in sentences[i]['tokens']:
        #         toto = sentences[i]['tokens'][int(t['index'])-1]['pinyin']
        #         print(f"self.assertEqual(sentences[{i}]['tokens'][{int(t['index'])-1}]['pinyin'], {toto})")


        _add_transliterations(sentences[0], dico)

        self.assertEqual(sentences[0]['tokens'][0]['pinyin'], ['xí', 'jìn', 'píng'])
        self.assertEqual(sentences[0]['tokens'][1]['pinyin'], ['zài'])
        self.assertEqual(sentences[0]['tokens'][2]['pinyin'], ['hè', 'diàn'])
        self.assertEqual(sentences[0]['tokens'][3]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[0]['tokens'][4]['pinyin'], ['zhǐ', 'chū'])
        self.assertEqual(sentences[0]['tokens'][5]['pinyin'], ['，'])
        self.assertEqual(sentences[0]['tokens'][6]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[0]['tokens'][7]['pinyin'], ['pú'])
        self.assertEqual(sentences[0]['tokens'][8]['pinyin'], ['yǒu', 'yì'])
        self.assertEqual(sentences[0]['tokens'][9]['pinyin'], ['yuán', 'yuǎn', 'liú', 'cháng'])
        self.assertEqual(sentences[0]['tokens'][10]['pinyin'], ['。'])

        _add_transliterations(sentences[1], dico)
        self.assertEqual(sentences[1]['tokens'][0]['pinyin'], ['jiàn', 'jiāo'])
        self.assertEqual(sentences[1]['tokens'][1]['pinyin'], ['4', '0'])
        self.assertEqual(sentences[1]['tokens'][2]['pinyin'], ['nián'])
        self.assertEqual(sentences[1]['tokens'][3]['pinyin'], ['lái'])
        self.assertEqual(sentences[1]['tokens'][4]['pinyin'], ['，'])
        self.assertEqual(sentences[1]['tokens'][5]['pinyin'], ['shuāng', 'fāng'])
        self.assertEqual(sentences[1]['tokens'][6]['pinyin'], ['bǐng', 'chí'])
        self.assertEqual(sentences[1]['tokens'][7]['pinyin'], ['xiāng', 'hù'])
        self.assertEqual(sentences[1]['tokens'][8]['pinyin'], ['zūn', 'zhòng'])
        self.assertEqual(sentences[1]['tokens'][9]['pinyin'], ['、'])
        self.assertEqual(sentences[1]['tokens'][10]['pinyin'], ['píng', 'děng'])
        self.assertEqual(sentences[1]['tokens'][11]['pinyin'], ['xiāng', 'dài'])
        self.assertEqual(sentences[1]['tokens'][12]['pinyin'], ['、'])
        self.assertEqual(sentences[1]['tokens'][13]['pinyin'], ['hù', 'lì'])
        self.assertEqual(sentences[1]['tokens'][14]['pinyin'], ['gòng', 'yíng'])
        self.assertEqual(sentences[1]['tokens'][15]['pinyin'], ['de'])
        self.assertEqual(sentences[1]['tokens'][16]['pinyin'], ['jīng', 'shén'])
        self.assertEqual(sentences[1]['tokens'][17]['pinyin'], ['tuī', 'dòng'])
        self.assertEqual(sentences[1]['tokens'][18]['pinyin'], ['shuāng', 'biān'])
        self.assertEqual(sentences[1]['tokens'][19]['pinyin'], ['guān', 'xì'])
        self.assertEqual(sentences[1]['tokens'][20]['pinyin'], ['jiàn', 'kāng'])
        self.assertEqual(sentences[1]['tokens'][21]['pinyin'], ['wěn', 'dìng'])
        self.assertEqual(sentences[1]['tokens'][22]['pinyin'], ['fā', 'zhǎn'])
        self.assertEqual(sentences[1]['tokens'][23]['pinyin'], ['。'])

        _add_transliterations(sentences[2], dico)
        self.assertEqual(sentences[2]['tokens'][0]['pinyin'], ['1', '9', '9', '9', 'nián'])
        self.assertEqual(sentences[2]['tokens'][1]['pinyin'], ['，'])
        self.assertEqual(sentences[2]['tokens'][2]['pinyin'], ['shuāng', 'fāng'])
        self.assertEqual(sentences[2]['tokens'][3]['pinyin'], ['tuǒ', 'shàn'])
        self.assertEqual(sentences[2]['tokens'][4]['pinyin'], ['jiě', 'jué'])
        self.assertEqual(sentences[2]['tokens'][5]['pinyin'], ['ào', 'mén'])
        self.assertEqual(sentences[2]['tokens'][6]['pinyin'], ['wèn', 'tí'])
        self.assertEqual(sentences[2]['tokens'][7]['pinyin'], ['，'])
        self.assertEqual(sentences[2]['tokens'][8]['pinyin'], ['shù', 'lì'])
        self.assertEqual(sentences[2]['tokens'][9]['pinyin'], ['le'])
        self.assertEqual(sentences[2]['tokens'][10]['pinyin'], ['guó'])
        self.assertEqual(sentences[2]['tokens'][11]['pinyin'], ['yǔ'])
        self.assertEqual(sentences[2]['tokens'][12]['pinyin'], ['guó'])
        self.assertEqual(sentences[2]['tokens'][13]['pinyin'], ['tōng', 'guò'])
        self.assertEqual(sentences[2]['tokens'][14]['pinyin'], ['yǒu', 'hǎo'])
        self.assertEqual(sentences[2]['tokens'][15]['pinyin'], ['xié', 'shāng'])
        self.assertEqual(sentences[2]['tokens'][16]['pinyin'], ['jiě', 'jué'])
        self.assertEqual(sentences[2]['tokens'][17]['pinyin'], ['lì', 'shǐ'])
        self.assertEqual(sentences[2]['tokens'][18]['pinyin'], ['yí', 'liú'])
        self.assertEqual(sentences[2]['tokens'][19]['pinyin'], ['wèn', 'tí'])
        self.assertEqual(sentences[2]['tokens'][20]['pinyin'], ['de'])
        self.assertEqual(sentences[2]['tokens'][21]['pinyin'], ['diǎn', 'fàn'])
        self.assertEqual(sentences[2]['tokens'][22]['pinyin'], ['。'])

        _add_transliterations(sentences[3], dico)
        self.assertEqual(sentences[3]['tokens'][0]['pinyin'], ['2', '0', '0', '5', 'nián'])
        self.assertEqual(sentences[3]['tokens'][1]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[3]['tokens'][2]['pinyin'], ['pú'])
        self.assertEqual(sentences[3]['tokens'][3]['pinyin'], ['jiàn', 'lì'])
        self.assertEqual(sentences[3]['tokens'][4]['pinyin'], ['quán', 'miàn'])
        self.assertEqual(sentences[3]['tokens'][5]['pinyin'], ['zhàn', 'luè'])
        self.assertEqual(sentences[3]['tokens'][6]['pinyin'], ['huǒ', 'bàn'])
        self.assertEqual(sentences[3]['tokens'][7]['pinyin'], ['guān', 'xì'])
        self.assertEqual(sentences[3]['tokens'][8]['pinyin'], ['yǐ', 'lái'])
        self.assertEqual(sentences[3]['tokens'][9]['pinyin'], ['，'])
        self.assertEqual(sentences[3]['tokens'][10]['pinyin'], ['shuāng', 'fāng'])
        self.assertEqual(sentences[3]['tokens'][11]['pinyin'], ['gāo', 'céng'])
        self.assertEqual(sentences[3]['tokens'][12]['pinyin'], ['hù', 'fǎng'])
        self.assertEqual(sentences[3]['tokens'][13]['pinyin'], ['pín', 'fán'])
        self.assertEqual(sentences[3]['tokens'][14]['pinyin'], ['，'])
        self.assertEqual(sentences[3]['tokens'][15]['pinyin'], ['zhèng', 'zhì'])
        self.assertEqual(sentences[3]['tokens'][16]['pinyin'], ['hù', 'xìn'])
        self.assertEqual(sentences[3]['tokens'][17]['pinyin'], ['bú', 'duàn'])
        self.assertEqual(sentences[3]['tokens'][18]['pinyin'], ['jiā', 'shēn'])
        self.assertEqual(sentences[3]['tokens'][19]['pinyin'], ['，'])
        self.assertEqual(sentences[3]['tokens'][20]['pinyin'], ['gè'])
        self.assertEqual(sentences[3]['tokens'][21]['pinyin'], ['lǐng', 'yù'])
        self.assertEqual(sentences[3]['tokens'][22]['pinyin'], ['hù', 'lì'])
        self.assertEqual(sentences[3]['tokens'][23]['pinyin'], ['hé', 'zuò'])
        self.assertEqual(sentences[3]['tokens'][24]['pinyin'], ['chéng', 'guǒ'])
        self.assertEqual(sentences[3]['tokens'][25]['pinyin'], ['xiǎn', 'zhù'])
        self.assertEqual(sentences[3]['tokens'][26]['pinyin'], ['。'])

        _add_transliterations(sentences[4], dico)
        self.assertEqual(sentences[4]['tokens'][0]['pinyin'], ['bù', 'jiǔ', 'qián'])
        self.assertEqual(sentences[4]['tokens'][1]['pinyin'], ['，'])
        self.assertEqual(sentences[4]['tokens'][2]['pinyin'], ['wǒ'])
        self.assertEqual(sentences[4]['tokens'][3]['pinyin'], ['chéng', 'gōng'])
        self.assertEqual(sentences[4]['tokens'][4]['pinyin'], ['fǎng', 'wèn'])
        self.assertEqual(sentences[4]['tokens'][5]['pinyin'], ['guì', 'guó'])
        self.assertEqual(sentences[4]['tokens'][6]['pinyin'], ['，'])
        self.assertEqual(sentences[4]['tokens'][7]['pinyin'], ['tóng'])
        self.assertEqual(sentences[4]['tokens'][8]['pinyin'], ['nǐ'])
        self.assertEqual(sentences[4]['tokens'][9]['pinyin'], ['jìn', 'xíng'])
        self.assertEqual(sentences[4]['tokens'][10]['pinyin'], ['shēn', 'rù'])
        self.assertEqual(sentences[4]['tokens'][11]['pinyin'], ['yǒu', 'hǎo'])
        self.assertEqual(sentences[4]['tokens'][12]['pinyin'], ['jiāo', 'liú'])
        self.assertEqual(sentences[4]['tokens'][13]['pinyin'], ['，'])
        self.assertEqual(sentences[4]['tokens'][14]['pinyin'], ['gòng', 'tóng'])
        self.assertEqual(sentences[4]['tokens'][15]['pinyin'], ['guī', 'huà'])
        self.assertEqual(sentences[4]['tokens'][16]['pinyin'], ['le'])
        self.assertEqual(sentences[4]['tokens'][17]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[4]['tokens'][18]['pinyin'], ['pú'])
        self.assertEqual(sentences[4]['tokens'][19]['pinyin'], ['guān', 'xì'])
        self.assertEqual(sentences[4]['tokens'][20]['pinyin'], ['fā', 'zhǎn'])
        self.assertEqual(sentences[4]['tokens'][21]['pinyin'], ['xīn'])
        self.assertEqual(sentences[4]['tokens'][22]['pinyin'], ['de'])
        self.assertEqual(sentences[4]['tokens'][23]['pinyin'], ['lán', 'tú'])
        self.assertEqual(sentences[4]['tokens'][24]['pinyin'], ['。'])

        _add_transliterations(sentences[5], dico)
        self.assertEqual(sentences[5]['tokens'][0]['pinyin'], ['wǒ'])
        self.assertEqual(sentences[5]['tokens'][1]['pinyin'], ['gāo', 'dù'])
        self.assertEqual(sentences[5]['tokens'][2]['pinyin'], ['zhòng', 'shì'])
        self.assertEqual(sentences[5]['tokens'][3]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[5]['tokens'][4]['pinyin'], ['pú'])
        self.assertEqual(sentences[5]['tokens'][5]['pinyin'], ['guān', 'xì'])
        self.assertEqual(sentences[5]['tokens'][6]['pinyin'], ['fā', 'zhǎn'])
        self.assertEqual(sentences[5]['tokens'][7]['pinyin'], ['，'])
        self.assertEqual(sentences[5]['tokens'][8]['pinyin'], ['yuàn'])
        self.assertEqual(sentences[5]['tokens'][9]['pinyin'], ['tóng'])
        self.assertEqual(sentences[5]['tokens'][10]['pinyin'], ['nǐ'])
        self.assertEqual(sentences[5]['tokens'][11]['pinyin'], ['yí', 'dào'])
        self.assertEqual(sentences[5]['tokens'][12]['pinyin'], ['nǔ', 'lì'])
        self.assertEqual(sentences[5]['tokens'][13]['pinyin'], ['，'])
        self.assertEqual(sentences[5]['tokens'][14]['pinyin'], ['yǐ'])
        self.assertEqual(sentences[5]['tokens'][15]['pinyin'], ['liǎng'])
        self.assertEqual(sentences[5]['tokens'][16]['pinyin'], ['guó'])
        self.assertEqual(sentences[5]['tokens'][17]['pinyin'], ['jiàn', 'jiāo'])
        self.assertEqual(sentences[5]['tokens'][18]['pinyin'], ['4', '0'])
        self.assertEqual(sentences[5]['tokens'][19]['pinyin'], ['zhōu', 'nián'])
        self.assertEqual(sentences[5]['tokens'][20]['pinyin'], ['wéi'])
        self.assertEqual(sentences[5]['tokens'][21]['pinyin'], ['xīn'])
        self.assertEqual(sentences[5]['tokens'][22]['pinyin'], ['qǐ', 'diǎn'])
        self.assertEqual(sentences[5]['tokens'][23]['pinyin'], ['，'])
        self.assertEqual(sentences[5]['tokens'][24]['pinyin'], ['tuī', 'dòng'])
        self.assertEqual(sentences[5]['tokens'][25]['pinyin'], ['zhōng'])
        self.assertEqual(sentences[5]['tokens'][26]['pinyin'], ['pú'])
        self.assertEqual(sentences[5]['tokens'][27]['pinyin'], ['quán', 'miàn'])
        self.assertEqual(sentences[5]['tokens'][28]['pinyin'], ['zhàn', 'luè'])
        self.assertEqual(sentences[5]['tokens'][29]['pinyin'], ['huǒ', 'bàn'])
        self.assertEqual(sentences[5]['tokens'][30]['pinyin'], ['guān', 'xì'])
        self.assertEqual(sentences[5]['tokens'][31]['pinyin'], ['mài', 'shàng'])
        self.assertEqual(sentences[5]['tokens'][32]['pinyin'], ['xīn'])
        self.assertEqual(sentences[5]['tokens'][33]['pinyin'], ['tái', 'jiē'])
        self.assertEqual(sentences[5]['tokens'][34]['pinyin'], ['，'])
        self.assertEqual(sentences[5]['tokens'][35]['pinyin'], ['gèng', 'hǎo'])
        self.assertEqual(sentences[5]['tokens'][36]['pinyin'], ['zào', 'fú'])
        self.assertEqual(sentences[5]['tokens'][37]['pinyin'], ['liǎng'])
        self.assertEqual(sentences[5]['tokens'][38]['pinyin'], ['guó'])
        self.assertEqual(sentences[5]['tokens'][39]['pinyin'], ['hé'])
        self.assertEqual(sentences[5]['tokens'][40]['pinyin'], ['liǎng'])
        self.assertEqual(sentences[5]['tokens'][41]['pinyin'], ['guó'])
        self.assertEqual(sentences[5]['tokens'][42]['pinyin'], ['rén', 'mín'])
        self.assertEqual(sentences[5]['tokens'][43]['pinyin'], ['。'])


    # def _sanitise_ankrobes_entry(entries):
    def test__sanitise_ankrobes_entry(self):
        from enrich.enricher import _sanitise_ankrobes_entry

        ## original hanping-sourced entry
        # html in L2 only
        words = [{'Simplified': '<span class="cmn_tone4">看</span><span class="cmn_tone4">见</span>', 'Pinyin': 'kan4 jian4', 'Meaning': 'to see • to catch sight of', 'Is_Known': 1, 'Tags': ['ccfb', 'hj14', 'hsk1', 'lesson29', 'st23']}]
        cleaned_words = [{'Simplified': '看见', 'Pinyin': 'kan4 jian4', 'Meaning': 'to see • to catch sight of', 'Is_Known': 1, 'Tags': ['ccfb', 'hj14', 'hsk1', 'lesson29', 'st23']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), cleaned_words)

        # html in L2 and L1
        words = [{'Simplified': '<span class="cmn_tone3">母</span><span class="cmn_tone1">亲</span>', 'Pinyin': 'mu3 qin1', 'Meaning': 'mother • also pr.  (mǔ qin) • CL: <span class=chinese_word>個|个|ge4</span>', 'Is_Known': 1, 'Tags': ['ccfb', 'hsk4', 'lesson7', 'st9']}]
        cleaned_words = [{'Simplified': '母亲', 'Pinyin': 'mu3 qin1', 'Meaning': 'mother • also pr.  (mǔ qin) • CL: 個|个|ge4', 'Is_Known': 1, 'Tags': ['ccfb', 'hsk4', 'lesson7', 'st9']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), cleaned_words)

        ## cccedict-sourced entry
        words = [{'Simplified': '榴莲', 'Pinyin': 'liu2 lian2', 'Meaning': 'durian (fruit)', 'Is_Known': 1, 'Tags': ['class']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

        ## abcdict-sourced entry
        words = [{'Simplified': '交通', 'Pinyin': 'jiāotōng', 'Meaning': '(n.). traffic; communications; transportation, liaison (v.). be connected/linked, cross (of streets/etc.) (attr.). unobstructed', 'Is_Known': 1, 'Tags': ['ankrobes', 'chromecrobes']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

        words = [{'Simplified': '眼', 'Pinyin': 'yǎn', 'Meaning': '(NOUN). eyes, glance, sight, yan (ADJ). ocular, eyed, ophthalmic (1 char)', 'Is_Known': 1, 'Tags': ['ankrobes', 'chromecrobes']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

        # 摄影 - manually entered
        words = [{'Simplified': '摄影', 'Pinyin': 'she4 ying3', 'Meaning': 'photography; to take a picture (bis4)', 'Is_Known': 1, 'Tags': ['hj25']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

        # 出租汽车 - manually entered '(4 chars)'
        words = [{'Simplified': '出租汽车', 'Pinyin': 'chu1 zu1 qi4 che1', 'Meaning': 'taxi (4 chars)', 'Is_Known': 1, 'Tags': ['st15']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

        # ...另一个... - manually entered expression
        words = [{'Simplified': '...另一个...', 'Pinyin': 'ling4 yi2 ge4 ', 'Meaning': '...and the other is...', 'Is_Known': 1, 'Tags': ['class']}]
        self.assertEqual(_sanitise_ankrobes_entry(words), words)

    # def _set_best_guess(sentence, token):
    # @requests_mock.Mocker()
    # def test__set_best_guess(self, m):
    def test__set_best_guess(self):
        # def _set_best_guess(sentence, token):

        before_files = os.path.join(self.assets, 'guess', 'before', '*')
        after_dir = os.path.join(self.assets, 'guess', 'after')

        files_before = glob.glob(before_files)
        files_before.sort(key=EnricherTests.natural_sort_key)

        with open(os.path.join(self.assets, 'guess', 'sentence1.json')) as sentence:
            s = json.load(sentence)
            for fname in files_before:
                with open(fname) as in_json, open(os.path.join(after_dir, os.path.basename(fname))) as out_json:
                    t = json.load(in_json)

                    _set_best_guess(s, t)
                    self.assertEqual(t, json.load(out_json))


    ## TODO: This is not strictly necessary, given we extensively test `enrich_to_json`
    ## and that method simply calls CoreNLP and then this method.
    # def _enrich_model(model, username):
    # def test__enrich_model(self):
    #     raise NotImplementedError


class CoreNLPProviderTests(TestCase):
    ##
    ## Plumbing methods
    ##
    def setUp(self):
        self.nlp = CoreNLPProvider()
        self.assets = os.path.join(settings.BASE_DIR, 'enrich', 'test', 'assets')

    ##
    ## Tests for public override methods
    ##

    @requests_mock.Mocker()
    def test_parse(self, m):
        # def parse(self, input):
        intxt_file = os.path.join(self.assets, 'nlp', 'in.txt')
        outmodel_file = os.path.join(self.assets, 'nlp', 'parsed.json')

        with open(intxt_file) as intxt, open(outmodel_file) as outmodel:
            parsed_json = outmodel.read()
            intxt_txt = intxt.read()
            m.post(settings.CORENLP_URL, text='something that is not json')
            with self.assertRaises(json.decoder.JSONDecodeError):
                self.nlp.parse(intxt_txt)

            m.post(settings.CORENLP_URL, text=parsed_json)
            model = self.nlp.parse(intxt_txt)
            self.assertEqual(model, json.loads(parsed_json))

class BingTranslatorTests(TestCase):
    ##
    ## Tests for public override methods
    ##

    # def get_standardised_defs(self, token, with_pinyin=False):
    @requests_mock.Mocker()
    def test_get_standardised_defs(self, m):
    # def test_get_standardised_defs(self):
        from enrich.translate import bing
        dico = bing.BingTranslator({ 'from': 'zh-Hans', 'to':'en' })

        lookup_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.LOOKUP_PATH}?{urlencode(dico.default_params())}'
        translit_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.TRANSLIT_PATH}?{urlencode(dico.translit_params())}'

        ##
        ## Without pinyin
        ##

        # 一拥而上
        lookup_ret = '[{"normalizedSource":"一拥而上","displaySource":"一拥而上","translations":[{"normalizedTarget":"swarmed","displayTarget":"swarmed","posTag":"VERB","confidence":1.0,"prefixWord":"","backTranslations":[{"normalizedText":"一拥而上","displayText":"一拥而上","numExamples":5,"frequencyCount":14},{"normalizedText":"涌上","displayText":"涌上","numExamples":3,"frequencyCount":5},{"normalizedText":"蜂拥","displayText":"蜂拥","numExamples":5,"frequencyCount":5}]}]}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        # print(dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, False))
        self.assertEqual(
            dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, False),
            {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'swarmed', 'confidence': 1.0, 'trans_provider': 'BING'}]}
        )

        # 活人
        lookup_ret = '[{"normalizedSource":"活人","displaySource":"活人","translations":[{"normalizedTarget":"living","displayTarget":"living","posTag":"NOUN","confidence":1.0,"prefixWord":"","backTranslations":[{"normalizedText":"生活","displayText":"生活","numExamples":15,"frequencyCount":13482},{"normalizedText":"住","displayText":"住","numExamples":15,"frequencyCount":4568},{"normalizedText":"居住","displayText":"居住","numExamples":15,"frequencyCount":2059},{"normalizedText":"活","displayText":"活","numExamples":15,"frequencyCount":2042},{"normalizedText":"生存","displayText":"生存","numExamples":15,"frequencyCount":1229},{"normalizedText":"活 着","displayText":"活着","numExamples":5,"frequencyCount":803},{"normalizedText":"活生生","displayText":"活生生","numExamples":5,"frequencyCount":276},{"normalizedText":"活人","displayText":"活人","numExamples":5,"frequencyCount":96}]}]}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        # print(dico.get_standardised_defs({"word": "活人", "pos": "NN" }, False))
        self.assertEqual(
            dico.get_standardised_defs({"word": "活人", "pos": "NN" }, False),
            {'NOUN': [{'upos': 'NOUN', 'opos': 'NOUN', 'normalizedTarget': 'living', 'confidence': 1.0, 'trans_provider': 'BING'}]}
        )

        # 龙门石窟
        # Here there is no corresponding lookup result returned by bing (as at 2019-02-11)
        lookup_ret = '[{"normalizedSource":"龙门石窟","displaySource":"龙门石窟","translations":[]}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        # print(dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, False))
        self.assertEqual(dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, False), {})

        ##
        ## With pinyin
        ##

        # 一拥而上
        lookup_ret = '[{"normalizedSource":"一拥而上","displaySource":"一拥而上","translations":[{"normalizedTarget":"swarmed","displayTarget":"swarmed","posTag":"VERB","confidence":1.0,"prefixWord":"","backTranslations":[{"normalizedText":"一拥而上","displayText":"一拥而上","numExamples":5,"frequencyCount":14},{"normalizedText":"涌上","displayText":"涌上","numExamples":3,"frequencyCount":5},{"normalizedText":"蜂拥","displayText":"蜂拥","numExamples":5,"frequencyCount":5}]}]}]'
        translit_ret = '[{"text":"yì yōng ér shàng","script":"Latn"}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, True))
        self.assertEqual(
            dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, True),
            {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'swarmed', 'confidence': 1.0, 'trans_provider': 'BING', 'pinyin': 'yì yōng ér shàng'}]}
        )

        # 活人
        lookup_ret = '[{"normalizedSource":"活人","displaySource":"活人","translations":[{"normalizedTarget":"living","displayTarget":"living","posTag":"NOUN","confidence":1.0,"prefixWord":"","backTranslations":[{"normalizedText":"生活","displayText":"生活","numExamples":15,"frequencyCount":13482},{"normalizedText":"住","displayText":"住","numExamples":15,"frequencyCount":4568},{"normalizedText":"居住","displayText":"居住","numExamples":15,"frequencyCount":2059},{"normalizedText":"活","displayText":"活","numExamples":15,"frequencyCount":2042},{"normalizedText":"生存","displayText":"生存","numExamples":15,"frequencyCount":1229},{"normalizedText":"活 着","displayText":"活着","numExamples":5,"frequencyCount":803},{"normalizedText":"活生生","displayText":"活生生","numExamples":5,"frequencyCount":276},{"normalizedText":"活人","displayText":"活人","numExamples":5,"frequencyCount":96}]}]}]'
        translit_ret = '[{"text":"huó rén","script":"Latn"}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.get_standardised_defs({"word": "活人", "pos": "NN" }, True))
        self.assertEqual(
            dico.get_standardised_defs({"word": "活人", "pos": "NN" }, True),
            {'NOUN': [{'upos': 'NOUN', 'opos': 'NOUN', 'normalizedTarget': 'living', 'confidence': 1.0, 'trans_provider': 'BING', 'pinyin': 'huó rén'}]}
        )

        # 龙门石窟
        # Here there is no corresponding lookup on bing (as at 2019-02-11)
        lookup_ret = '[{"normalizedSource":"龙门石窟","displaySource":"龙门石窟","translations":[]}]'
        m.register_uri('POST', lookup_url, text=lookup_ret)
        # print(dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, True))
        self.assertEqual(dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, True), {})

    # def get_standardised_fallback_defs(self, token, with_pinyin=False):
    @requests_mock.Mocker()
    def test_get_standardised_fallback_defs(self, m):
    # def test_get_standardised_fallback_defs(self):
        from enrich.translate import bing
        dico = bing.BingTranslator({ 'from': 'zh-Hans', 'to':'en' })

        translat_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.TRANSLAT_PATH}?{urlencode(dico.default_params())}'
        translit_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.TRANSLIT_PATH}?{urlencode(dico.translit_params())}'

        ##
        ## Without pinyin
        ##

        # 一拥而上
        translat_ret = '[{"translations":[{"text":"Swarmed","to":"en"}]}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        # print(dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, False))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, False),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Swarmed', 'confidence': 0, 'trans_provider': 'BING-DEFAULT'}]}
        )

        # 活人
        translat_ret = '[{"translations":[{"text":"Living","to":"en"}]}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        # print(dico.get_standardised_fallback_defs({"word": "活人", "pos": "NN" }, False))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "活人", "pos": "NN" }, False),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Living', 'confidence': 0, 'trans_provider': 'BING-DEFAULT'}]}
        )

        # 龙门石窟
        # Here there is no corresponding lookup result returned by bing (as at 2019-02-11)
        translat_ret = '[{"translations":[{"text":"Longmen Grottoes","to":"en"}]}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        # print(dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, False))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, False),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Longmen Grottoes', 'confidence': 0, 'trans_provider': 'BING-DEFAULT'}]}
        )

        ##
        ## With pinyin
        ##

        # 一拥而上
        translat_ret = '[{"translations":[{"text":"Swarmed","to":"en"}]}]'
        translit_ret = '[{"text":"yì yōng ér shàng","script":"Latn"}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, True))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, True),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Swarmed', 'confidence': 0, 'trans_provider': 'BING-DEFAULT', 'pinyin': 'yì yōng ér shàng'}]}
        )

        # 活人
        translat_ret = '[{"translations":[{"text":"Living","to":"en"}]}]'
        translit_ret = '[{"text":"huó rén","script":"Latn"}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.get_standardised_fallback_defs({"word": "活人", "pos": "NN" }, True))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "活人", "pos": "NN" }, True),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Living', 'confidence': 0, 'trans_provider': 'BING-DEFAULT', 'pinyin': 'huó rén'}]}
        )

        # 龙门石窟
        translat_ret = '[{"translations":[{"text":"Longmen Grottoes","to":"en"}]}]'
        translit_ret = '[{"text":"lóng mén shí kū","script":"Latn"}]'
        m.register_uri('POST', translat_url, text=translat_ret)
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, True))
        self.assertEqual(
            dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, True),
            {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Longmen Grottoes', 'confidence': 0, 'trans_provider': 'BING-DEFAULT', 'pinyin': 'lóng mén shí kū'}]}
        )

    # # def transliterate(self, text):
    @requests_mock.Mocker()
    def test_transliterate(self, m):
    # def test_transliterate(self):
        from enrich.translate import bing
        dico = bing.BingTranslator({ 'from': 'zh-Hans', 'to':'en' })

        translit_url = f'{bing.URL_SCHEME}{settings.BING_API_HOST}{bing.TRANSLIT_PATH}?{urlencode(dico.translit_params())}'

        # 一拥而上
        translit_ret = '[{"text":"yì yōng ér shàng","script":"Latn"}]'
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.transliterate("一拥而上"))
        self.assertEqual(dico.transliterate("一拥而上"), 'yì yōng ér shàng')

        # 活人
        translit_ret = '[{"text":"huó rén","script":"Latn"}]'
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.transliterate("活人"))
        self.assertEqual(dico.transliterate("活人"), 'huó rén')

        # 龙门石窟
        translit_ret = '[{"text":"lóng mén shí kū","script":"Latn"}]'
        m.register_uri('POST', translit_url, text=translit_ret)
        # print(dico.transliterate("龙门石窟"))
        self.assertEqual(dico.transliterate("龙门石窟"), 'lóng mén shí kū')

