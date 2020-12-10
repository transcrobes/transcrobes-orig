# -*- coding: utf-8 -*-

from vcr_unittest import VCRTestCase

from enrich.data import managers


class ZHHANS_EN_ABCDictTranslatorTests(VCRTestCase):
    ##
    ## Tests for public override methods
    ##

    def setUp(self):
        super().setUp()
        self.dico = managers.get("zh-Hans:en").secondary()[0]  # 0 = ABC, 1 = CCC

    def test_load(self):
        """
        Tests that
        - we can load a representative file
        - that it contains the right number of entries
        - that the entries are of the right format
        """

        # FIXME: the "o" char here gets eaten by the pinyin decode_pinyin method
        # and should not. What on earth that character is is another question...
        # FIXME: fix this bug!!!
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

        # Note there are 86 entries in the dict test file but
        # only 79 unique characters, the others having several pronunciations, which we merge
        self.assertEqual(len(self.dico.dico.keys()), 79)

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
        # there are several "啊" in the file, here we just compare with the first one
        self.assertEqual(
            [self.dico.dico.get("啊")[0]],
            [
                {
                    "pinyin": "a*",
                    "definitions": [],
                    "els": [
                        ["", "ps", "m.p."],
                        ["", "psx", "used as phrase suffix"],
                        ["1", "psx", "in enumeration"],
                        ["1", "ex", "Qián ∼, shū ∼, biǎo ∼, wǒ dōu diū le."],
                        ["1", "hz", "钱∼, 书∼, 表∼, 我都丢了。"],
                        ["1", "tr", "Money, books, watch, I lost everything."],
                        ["2", "psx", "in direct address and exclamation"],
                        ["2", "ex", "Lǎo Wáng ∼, zhè kě bùxíng ∼!"],
                        ["2", "hz", "老王∼, 这可不行∼!"],
                        ["2", "tr", "Wang, this won't do!"],
                        ["3", "psx", "indicating obviousness/impatience"],
                        ["3", "ex", "Lái ∼!"],
                        ["3", "hz", "来∼!"],
                        ["3", "tr", "Come on!"],
                        ["4", "psx", "for confirmation"],
                        ["4", "ex", "Nǐ bù lái ∼?"],
                        ["4", "hz", "你不来∼?"],
                        ["4", "tr", "So you're not coming?"],
                    ],
                    "parents": {},
                    "char": "啊",
                    "gr": "A",
                    "ser": "1000000063",
                    "ref": "1",
                    "hh": "à [1000000548]",
                    "freq": "609.7 [XHPC:1102]",
                }
            ],
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
            self.dico.dico.get("忾然"),
            [
                {
                    "pinyin": "k\u00e0ir\u00e1n",
                    "definitions": [["", "v.p.", "sigh with deep feelings"]],
                    "els": [["", "ps", "v.p."], ["", "df", "sigh with deep feelings"]],
                    "parents": {},
                    "char": "\u5ffe\u7136",
                    "ser": "1006919849",
                    "gr": "*",
                    "ref": "vfe454b2",
                }
            ],
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
            self.dico.dico.get("卒业"),
            [
                {
                    "pinyin": "z\u00fay\u00e8",
                    "definitions": [["", "n.", "graduate study"]],
                    "els": [["", "ps", "n."], ["", "df", "graduate study"]],
                    "parents": {},
                    "char": "\u5352\u4e1a",
                    "ser": "1018513095",
                    "gr": "*",
                    "ref": "59734",
                }
            ],
        )

    def test_get_standardised_defs(self):
        # def get_standardised_defs(self, token, with_pinyin=False):

        # 啊
        # In dictionary but has no definitions (so no 'df' in the entry)
        # this can happen for grammatical words, where basically there are only examples
        # of usage
        # TODO: decide whether we want to return something here
        self.assertEqual(self.dico.get_standardised_defs({"word": "啊", "pos": "NN", "lemma": "啊"}), {})

        # 忾然
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "忾然", "pos": "NN", "lemma": "忾然"}),
            {
                "v.p.": [
                    {
                        "upos": "n.",
                        "opos": "v.p.",
                        "normalizedTarget": "sigh with deep feelings",
                        "confidence": 0,
                        "trans_provider": "ABCDICT",
                        "pinyin": "kàirán",
                    }
                ]
            },
        )

        # 卒业
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "卒业", "pos": "NN", "lemma": "卒业"}),
            {
                "n.": [
                    {
                        "upos": "n.",
                        "opos": "n.",
                        "normalizedTarget": "graduate study",
                        "confidence": 0.01,
                        "trans_provider": "ABCDICT",
                        "pinyin": "zúyè",
                    }
                ]
            },
        )

    def test_get_standardised_fallback_defs(self):
        # def get_standardised_fallback_defs(self, token, with_pinyin=False):

        # FIXME: need to also do versions with pinyin false, see bing translator above for example

        self.assertEqual(
            self.dico.get_standardised_defs({"word": "啊", "pos": "NN", "lemma": "啊"}),
            self.dico.get_standardised_fallback_defs({"word": "啊", "pos": "NN", "lemma": "啊"}),
        )

        # 忾然
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "忾然", "pos": "NN", "lemma": "忾然"}),
            self.dico.get_standardised_fallback_defs({"word": "忾然", "pos": "NN", "lemma": "忾然"}),
        )

        # 卒业
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "卒业", "pos": "NN", "lemma": "卒业"}),
            self.dico.get_standardised_fallback_defs({"word": "卒业", "pos": "NN", "lemma": "卒业"}),
        )


class ZHHANS_EN_CCCedictTranslatorTests(VCRTestCase):
    def setUp(self):
        super().setUp()
        self.dico = managers.get("zh-Hans:en").secondary()[1]  # 0 = ABC, 1 = CCC

    def tearDown(self):
        pass

    def test_load(self):
        """
        Tests that
        - we can load a varied file
        - that it contains the right number of entries
        - that the entries are of the right format
        - that the pinyin gets transformed to classic pinyin properly
        """

        self.assertEqual(len(self.dico.dico.keys()), 71)

        # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
        self.assertEqual(
            self.dico.dico.get("一拥而上"),
            [{"pinyin": "[yi1 yong1 er2 shang4]", "definitions": ["to swarm around", "flocking (to see)"]}],
        )

        # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
        self.assertEqual(
            self.dico.dico.get("服满"),
            [
                {
                    "pinyin": "[fu2 man3]",
                    "definitions": [
                        "to have completed the mourning period (traditional)",
                        "to have served one's time",
                    ],
                }
            ],
        )

        # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
        self.assertEqual(
            self.dico.dico.get("龙门石窟"),
            [
                {
                    "pinyin": "[Long2 men2 Shi2 ku1]",
                    "definitions": ["Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan"],
                }
            ],
        )

    ##
    ## Tests for public override methods
    ##

    def test_get_standardised_defs(self):
        # def get_standardised_defs(self, token, with_pinyin=False):

        # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "一拥而上", "pos": "NN", "lemma": "一拥而上"}),
            {
                "VERB": [
                    {
                        "upos": "VERB",
                        "opos": "VERB",
                        "normalizedTarget": "to swarm around",
                        "confidence": 0,
                        "trans_provider": "CEDICT",
                        "pinyin": "yīyōngérshàng",
                    }
                ],
                "OTHER": [
                    {
                        "upos": "OTHER",
                        "opos": "OTHER",
                        "normalizedTarget": "flocking (to see)",
                        "confidence": 0,
                        "trans_provider": "CEDICT",
                        "pinyin": "yīyōngérshàng",
                    }
                ],
            },
        )

        # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "服满", "pos": "NN", "lemma": "服满"}),
            {
                "VERB": [
                    {
                        "upos": "VERB",
                        "opos": "VERB",
                        "normalizedTarget": "to have completed the mourning period (traditional)",
                        "confidence": 0,
                        "trans_provider": "CEDICT",
                        "pinyin": "fúmǎn",
                    },
                    {
                        "upos": "VERB",
                        "opos": "VERB",
                        "normalizedTarget": "to have served one's time",
                        "confidence": 0,
                        "trans_provider": "CEDICT",
                        "pinyin": "fúmǎn",
                    },
                ]
            },
        )

        # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN", "lemma": "龙门石窟"}),
            {
                "OTHER": [
                    {
                        "upos": "OTHER",
                        "opos": "OTHER",
                        "normalizedTarget": "Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan",
                        "confidence": 0,
                        "trans_provider": "CEDICT",
                        "pinyin": "lóngménshíkū",
                    }
                ]
            },
        )

    def test_get_standardised_fallback_defs(self):
        # def get_standardised_fallback_defs(self, token):

        # 一擁而上 一拥而上 [yi1 yong1 er2 shang4] /to swarm around/flocking (to see)/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "一拥而上", "pos": "NN", "lemma": "一拥而上"}),
            self.dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN", "lemma": "一拥而上"}),
        )

        # 服滿 服满 [fu2 man3] /to have completed the mourning period (traditional)/to have served one's time/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "服满", "pos": "NN", "lemma": "服满"}),
            self.dico.get_standardised_fallback_defs({"word": "服满", "pos": "NN", "lemma": "服满"}),
        )

        # 龙门石窟 [Long2 men2 Shi2 ku1] /Longmen Grottoes at Luoyang 洛陽|洛阳[Luo4 yang2], Henan/
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN", "lemma": "龙门石窟"}),
            self.dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN", "lemma": "龙门石窟"}),
        )
