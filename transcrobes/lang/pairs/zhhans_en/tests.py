# -*- coding: utf-8 -*-

from django.test import TestCase
from django.conf import settings

from zhhans_en.metadata import hsk, subtlex
from enrich.metadata import providers
from zhhans_en.translate import ccc
from zhhans_en.translate import abc


class ZHHANS_EN_CCCedictTranslatorTests(TestCase):
    ##
    ## Tests for public override methods
    ##

    # def get_standardised_defs(self, token, with_pinyin=False):
    def test_get_standardised_defs(self):
        # FIXME: need to also do versions with pinyin false, see bing translator above for example
        with self.settings(CCCEDICT_PATH='/opt/transcrobes/cedict.test.txt'):
            ccc.load()
            self.assertEqual(len(ccc.cedict.keys()), 241)
            dico = ccc.ZHHANS_EN_CCCedictTranslator()

            # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
            # print(dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "一拥而上", "pos": "NN" }, True),
                {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'to swarm around', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'yīyōngérshàng'}], 'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'flocking (to see)', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'yīyōngérshàng'}]}
            )

            # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
            # print(dico.get_standardised_defs({"word": "服满", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "服满", "pos": "NN" }, True),
                {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'to have completed the mourning period (traditional)', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'fúmǎn'}, {'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': "to have served one's time", 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'fúmǎn'}]}
            )

            # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
            # print(dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN" }, True),
                {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'lóngménshíkū'}]}
            )


    # def get_standardised_fallback_defs(self, token, with_pinyin=False):
    def test_get_standardised_fallback_defs(self):
        # FIXME: need to also do versions with pinyin false, see bing translator above for example
        with self.settings(CCCEDICT_PATH='/opt/transcrobes/cedict.test.txt'):
            ccc.load()
            dico = ccc.ZHHANS_EN_CCCedictTranslator()

            # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
            # print(dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN" }, True),
                {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'to swarm around', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'yīyōngérshàng'}], 'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'flocking (to see)', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'yīyōngérshàng'}]}
            )

            # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
            # print(dico.get_standardised_fallback_defs({"word": "服满", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "服满", "pos": "NN" }, True),
                {'VERB': [{'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': 'to have completed the mourning period (traditional)', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'fúmǎn'}, {'upos': 'VERB', 'opos': 'VERB', 'normalizedTarget': "to have served one's time", 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'fúmǎn'}]}
            )

            # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
            # print(dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN" }, True),
                {'OTHER': [{'upos': 'OTHER', 'opos': 'OTHER', 'normalizedTarget': 'Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan', 'confidence': 0, 'trans_provider': 'CEDICT', 'pinyin': 'lóngménshíkū'}]}
            )

    # FIXME:
    # This has a raise in the actual method
    # # def transliterate(self, text):
    # def test_transliterate(self):
    #     raise NotImplementedError
class ZHHANS_EN_ABCDictTranslatorTests(TestCase):
    ##
    ## Tests for public override methods
    ##

    # def get_standardised_defs(self, token, with_pinyin=False):
    def test_get_standardised_defs(self):
        # FIXME: need to also do versions with pinyin false, see bing translator below for example
        with self.settings(ABCEDICT_PATH='/opt/transcrobes/abcdict.test.txt'):
            abc.load()
            self.assertEqual(len(abc.abc_dict.keys()), 216)
            dico = abc.ZHHANS_EN_ABCDictTranslator()

            # 啊
            # In dictionary but has no definitions (so no 'df' in the entry)
            # this can happen for grammatical words, where basically there are only examples
            # of usage
            # TODO: decide whether we want to return something here
            # print(dico.get_standardised_defs({"word": "啊", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "啊", "pos": "NN" }, True),
                {}
            )

            # 忾然
            # print(dico.get_standardised_defs({"word": "忾然", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "忾然", "pos": "NN" }, True),
                {'v.p.': [{'upos': 'n.', 'opos': 'v.p.', 'normalizedTarget': 'sigh with deep feelings', 'confidence': 0, 'trans_provider': 'ABCDICT', 'pinyin': 'kàirán'}]}
            )

            # 卒业
            # print(dico.get_standardised_defs({"word": "卒业", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_defs({"word": "卒业", "pos": "NN" }, True),
                {'n.': [{'upos': 'n.', 'opos': 'n.', 'normalizedTarget': 'graduate study', 'confidence': 0.01, 'trans_provider': 'ABCDICT', 'pinyin': 'zúyè'}]}
            )

    # def get_standardised_fallback_defs(self, token, with_pinyin=False):
    def test_get_standardised_fallback_defs(self):
        # FIXME: need to also do versions with pinyin false, see bing translator above for example
        with self.settings(ABCEDICT_PATH='/opt/transcrobes/abcdict.test.txt'):
            abc.load()
            self.assertEqual(len(abc.abc_dict.keys()), 216)
            dico = abc.ZHHANS_EN_ABCDictTranslator()

            # 啊
            # In dictionary but has no definitions (so no 'df' in the entry)
            # this can happen for grammatical words, where basically there are only examples
            # of usage
            # TODO: decide whether we want to return something here
            # print(dico.get_standardised_fallback_defs({"word": "啊", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "啊", "pos": "NN" }, True),
                {}
            )

            # 忾然
            # print(dico.get_standardised_fallback_defs({"word": "忾然", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "忾然", "pos": "NN" }, True),
                {'v.p.': [{'upos': 'n.', 'opos': 'v.p.', 'normalizedTarget': 'sigh with deep feelings', 'confidence': 0, 'trans_provider': 'ABCDICT', 'pinyin': 'kàirán'}]}
            )

            # 卒业
            # print(dico.get_standardised_fallback_defs({"word": "卒业", "pos": "NN" }, True))
            self.assertEqual(
                dico.get_standardised_fallback_defs({"word": "卒业", "pos": "NN" }, True),
                {'n.': [{'upos': 'n.', 'opos': 'n.', 'normalizedTarget': 'graduate study', 'confidence': 0.01, 'trans_provider': 'ABCDICT', 'pinyin': 'zúyè'}]}
            )

    # FIXME:
    # This has a raise in the actual method
    # # def transliterate(self, text):
    # def test_transliterate(self):
    #     raise NotImplementedError


class ZHHANS_EN_TranslateTests(TestCase):
    ##
    ## Plumbing methods
    ##
    # def setUp(self):
    #     raise NotImplementedError

    # def tearDown(self):
    #     raise NotImplementedError


    ##
    ## Tests for public module methods
    ##

    # FIXME: this is a REALLY important test to do well!!!!!
    # unfortunately, the test should have been written when it was developed
    # so now the why is all forgotten... and the method is pretty obscure...
    # def decode_pinyin(s):
    # def test_decode_pinyin(self):
    #     t_digits = ["10 ge4 xiao3 shi2 qian2", "10 gè xiǎo shí qián"]
    #     pair = ["Jí'ěrjísīsītǎn", "Jí'ěrjísīsītǎn"]

    #     # it shouldn't change already valid text
    #     pair = ["Jí'ěrjísīsītǎn", "Jí'ěrjísīsītǎn"]


    #     self.assertEqual(decode_pinyin(pair[0]), pair[1])

    # # def sublext.load():
    def test_load_subtlex_metadata(self):
        """
        Tests that
        - we can load a varied file
        - that it contains the right number of entries
        - that the entries are of the right format
        - that the pinyin gets transformed to classic pinyin properly
        """
        # FIXME: don't use a hard-coded path, put the files in the test assets
        with self.settings(SUBLEX_FREQ_PATH='/opt/transcrobes/subtlex-ch.utf8.test.txt'):

            subtlex.load()
            subtlexp = providers[subtlex.SubtlexMetadata.name()]

            self.assertEqual(len(subtlexp), 198)

            # line 1
            # 表演  2   biao3 yan3  biaoyan 6658    198.47  3.8233  1590    25.47   3.2014  vn  3998    .vn.v.  .3998.2660.
            self.assertEqual(
                subtlexp.meta_for_word('表演'),
                [{'pinyin': 'biǎoyǎn', 'wcpm': '198.47', 'wcdp': '25.47', 'pos': '.vn.v.', 'pos_freq': '.3998.2660.'} ]
            )
            # line 100
            # 弗拉曼科  4   fu2 la1/la2/la3/la4 man4 ke1    fulamanke   4   0.12    0.6021  1   0.02    0   nr  4   .nr.    .4.
            self.assertEqual(
                subtlexp.meta_for_word('弗拉曼科'),
                [{'pinyin': 'fúlā/lá/lǎ/làmànkē', 'wcpm': '0.12', 'wcdp': '0.02', 'pos': '.nr.', 'pos_freq': '.4.'}]
            )

            # line 199 = last, we skip the header
            # 黑进显    3   hei1 jin4 xian3 heijinxian  1   0.03    0   1   0.02    0   nr  1   .nr.    .1.
            self.assertEqual(
                subtlexp.meta_for_word('黑进显'),
                [{'pinyin': 'hēijìnxiǎn', 'wcpm': '0.03', 'wcdp': '0.02', 'pos': '.nr.', 'pos_freq': '.1.'}]
            )


    # def hsk.load():
    def test_load_hsk_metadata(self):
        """
        Tests that
        - we can load all the files
        - that it contains the right number of entries
        - that the entries are of the right format
        """
        # FIXME: don't use a hard-coded path, put the files in the test assets
        with self.settings(HSKDICT_PATH='/opt/transcrobes/hsk{}.txt'):
            hsk.load()
            hskp = providers[hsk.HSKMetadata.name()]

            self.assertEqual(len(hskp), 4995)
            # hsk2.txt line 1
            # 吧    吧  ba5 ba  particle indicating polite suggestion; | onomatopoeia | bar (serving drinks, providing internet access, etc.)
            self.assertEqual(hskp.meta_for_word('吧'), [{'hsk': 2, 'pinyin': 'ba'}])

            # hsk6.txt line 1250 - middle line of file
            # 免疫  免疫    mian3yi4    miǎnyì  immune
            self.assertEqual(hskp.meta_for_word('免疫'), [{'hsk': 6, 'pinyin': 'miǎnyì'}])

            # hsk4.txt line 600 - last line of file
            # 座位  座位    zuo4wei4    zuòwèi  seat; place
            self.assertEqual(hskp.meta_for_word('座位'), [{'hsk': 4, 'pinyin': 'zuòwèi'}])

    # def abc.load():
    def test_load_abc(self):
        """
        Tests that
        - we can load a representative file
        - that it contains the right number of entries
        - that the entries are of the right format
        """
        # FIXME: don't use a hard-coded path, put the files in the test assets
        with self.settings(ABCEDICT_PATH='/opt/transcrobes/abcdict.test.txt'):
            abc.load()
            # FIXME: the "o" char here gets eaten by the pinyin decode_pinyin method
            # and should not. What on earth that character is is another question...
            """
.py   zọ̌nglǐ*
char   总理[總-]
gr   B
ser   1018310462
ref   59557
ps   n.
1df   premier; prime minister
2df@fe   president (of a political party, etc.)
3df@fe   Sun Yat-sen
freq   122.8 [XHPC:222]
rem@sarahbrahy_2017-09-13T21:47:14CEST   changed entry
            """
            # FIXME: fix the above bug!!!

            # Note there are 217 entries in the dict test file but
            # '中' has two pronunciations, so is merged to one entry
            self.assertEqual(len(abc.abc_dict.keys()), 216)

            """
            .py   a*
            char   啊
            gr   A
            rem@yy200307   Added gr A.
            ser   1000000063
            ref   1
            ps   m.p.
            psx   used as phrase suffix
            1psx   in enumeration
            1ex   Qián ∼, shū ∼, biǎo ∼, wǒ dōu diū le.
            1hz   钱∼, 书∼, 表∼, 我都丢了。
            1tr   Money, books, watch, I lost everything.
            2psx   in direct address and exclamation
            2ex   Lǎo Wáng ∼, zhè kě bùxíng ∼!
            2hz   老王∼, 这可不行∼!
            2tr   Wang, this won't do!
            rem@2004.05.24   ?missing: {wang} cw: Ignore. Proper N.
            3psx   indicating obviousness/impatience
            3ex   Lái ∼!
            3hz   来∼!
            3tr   Come on!
            4psx   for confirmation
            4ex   Nǐ bù lái ∼?
            4hz   你不来∼?
            4tr   So you're not coming?
            hh   ¹ā [1000000160]
            hh   á [1000000354]
            hh   ǎ [1000000451]
            hh   à [1000000548]
            freq   609.7 [XHPC:1102]
            """
            self.assertEqual(
                abc.abc_dict['啊'],
                [{'pinyin': 'a*', 'definitions': [], 'els': [['', 'ps', 'm.p.'], ['', 'psx', 'used as phrase suffix'], ['1', 'psx', 'in enumeration'], ['1', 'ex', 'Qián ∼, shū ∼, biǎo ∼, wǒ dōu diū le.'], ['1', 'hz', '钱∼, 书∼, 表∼, 我都丢了。'], ['1', 'tr', 'Money, books, watch, I lost everything.'], ['2', 'psx', 'in direct address and exclamation'], ['2', 'ex', 'Lǎo Wáng ∼, zhè kě bùxíng ∼!'], ['2', 'hz', '老王∼, 这可不行∼!'], ['2', 'tr', "Wang, this won't do!"], ['3', 'psx', 'indicating obviousness/impatience'], ['3', 'ex', 'Lái ∼!'], ['3', 'hz', '来∼!'], ['3', 'tr', 'Come on!'], ['4', 'psx', 'for confirmation'], ['4', 'ex', 'Nǐ bù lái ∼?'], ['4', 'hz', '你不来∼?'], ['4', 'tr', "So you're not coming?"]], 'parents': {}, 'char': '啊', 'gr': 'A', 'ser': '1000000063', 'ref': '1', 'hh': 'à [1000000548]', 'freq': '609.7 [XHPC:1102]'}]
            )

            """
            .py   kàirán
            char   忾然[愾-]
            ser   1006919849
            gr   *
            ref   vfe454b2
            ps   v.p.
            df   sigh with deep feelings
            """
            self.assertEqual(
                abc.abc_dict['忾然'],
                [{"pinyin": "k\u00e0ir\u00e1n", "definitions": [["", "v.p.", "sigh with deep feelings"]], "els": [["", "ps", "v.p."], ["", "df", "sigh with deep feelings"]], "parents": {}, "char": "\u5ffe\u7136", "ser": "1006919849", "gr": "*", "ref": "vfe454b2"}]
            )

            """
            .py   zúyè
            char   卒业[-業]
            ser   1018513095
            gr   *
            rem@yy1001   del class a
            ref   59734
            ps   n.
            df   graduate study
            """
            self.assertEqual(
                abc.abc_dict['卒业'],
                [{"pinyin": "z\u00fay\u00e8", "definitions": [["", "n.", "graduate study"]], "els": [["", "ps", "n."], ["", "df", "graduate study"]], "parents": {}, "char": "\u5352\u4e1a", "ser": "1018513095", "gr": "*", "ref": "59734"}]
            )


    # def ccc.load():
    def test_load_cedict(self):
        """
        Tests that
        - we can load a varied file
        - that it contains the right number of entries
        - that the entries are of the right format
        - that the pinyin gets transformed to classic pinyin properly
        """
        # FIXME: don't use a hard-coded path, put the files in the test assets
        with self.settings(CCCEDICT_PATH='/opt/transcrobes/cedict.test.txt'):
            ccc.load()

            self.assertEqual(len(ccc.cedict.keys()), 241)
            # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
            self.assertEqual(
                ccc.cedict['一拥而上'],
                [{'pinyin': '[yi1 yong1 er2 shang4]', 'definitions': ['to swarm around', 'flocking (to see)']}]
            )

            # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
            self.assertEqual(
                ccc.cedict['服满'],
                [{'pinyin': '[fu2 man3]', 'definitions': ['to have completed the mourning period (traditional)', "to have served one's time"]}]
            )

            # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
            self.assertEqual(
                ccc.cedict['龙门石窟'],
                [{'pinyin': '[Long2 men2 Shi2 ku1]', 'definitions': ['Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan']}]
            )


