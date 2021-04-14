# -*- coding: utf-8 -*-

import glob
import json
import os
import pkgutil
import re
import sys
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APITransactionTestCase
from vcr_unittest import VCRMixin, VCRTestCase

import stats
from enrich.apis import bing as bing_api
from enrich.data import managers

# for finding assets path via the module
from .assets import zhhans_enrichers  # noqa: F401  # pylint: disable=W0611
from .assets.enrichers import notes  # noqa: F401  # pylint: disable=W0611
from .assets.enrichers.guess import after, before  # noqa: F401  # pylint: disable=W0611

_NSRE = re.compile("([0-9]+)")


class ZH_SubtlexMetadataTests(VCRTestCase):

    ##
    ## Plumbing methods
    ##
    def setUp(self):
        super().setUp()
        self.metadata = managers.get("zh-Hans:en").metadata()[1]  # 0 = HSK, 1 = Subtlex

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

    def test_load_subtlex_metadata(self):
        """
        Tests that
        - we can load a varied file
        - that it contains the right number of entries
        - that the entries are of the right format
        - that the pinyin gets transformed to classic pinyin properly
        """

        self.assertEqual(len(self.metadata.dico), 202)

        # line 1
        # 表演  2   biao3 yan3  biaoyan 6658    198.47  3.8233  1590    25.47   3.2014  vn  3998    .vn.v.  .3998.2660.  # noqa: E501  # pylint: disable=C0301
        self.assertEqual(
            self.metadata.meta_for_word("表演"),
            [{"pinyin": "biǎoyǎn", "wcpm": "198.47", "wcdp": "25.47", "pos": ".vn.v.", "pos_freq": ".3998.2660."}],
        )
        # line 100
        # 弗拉曼科  4   fu2 la1/la2/la3/la4 man4 ke1    fulamanke   4   0.12    0.6021  1   0.02    0   nr  4   .nr.    .4.  # noqa: E501  # pylint: disable=C0301
        self.assertEqual(
            self.metadata.meta_for_word("弗拉曼科"),
            [{"pinyin": "fúlā/lá/lǎ/làmànkē", "wcpm": "0.12", "wcdp": "0.02", "pos": ".nr.", "pos_freq": ".4."}],
        )

        # line 199 = last, we skip the header
        # 黑进显    3   hei1 jin4 xian3 heijinxian  1   0.03    0   1   0.02    0   nr  1   .nr.    .1.
        self.assertEqual(
            self.metadata.meta_for_word("黑进显"),
            [{"pinyin": "hēijìnxiǎn", "wcpm": "0.03", "wcdp": "0.02", "pos": ".nr.", "pos_freq": ".1."}],
        )


class ZH_HSKMetadataTests(VCRTestCase):
    ##
    ## Plumbing methods
    ##
    def setUp(self):
        super().setUp()
        self.metadata = managers.get("zh-Hans:en").metadata()[0]  # 0 = HSK, 1 = Subtlex

    def test_load_hsk_metadata(self):
        """
        Tests that
        - we can load all the files
        - that it contains the right number of entries
        - that the entries are of the right format
        """
        self.assertEqual(len(self.metadata.dico), 4995)
        # hsk2.txt line 1
        # 吧    吧  ba5 ba  particle indicating polite suggestion; | onomatopoeia | bar (serving drinks, providing internet access, etc.)  # noqa: E501  # pylint: disable=C0301
        self.assertEqual(self.metadata.meta_for_word("吧"), [{"hsk": 2, "pinyin": "ba"}])

        # hsk6.txt line 1250 - middle line of file
        # 免疫  免疫    mian3yi4    miǎnyì  immune
        self.assertEqual(self.metadata.meta_for_word("免疫"), [{"hsk": 6, "pinyin": "miǎnyì"}])

        # hsk4.txt line 600 - last line of file
        # 座位  座位    zuo4wei4    zuòwèi  seat; place
        self.assertEqual(self.metadata.meta_for_word("座位"), [{"hsk": 4, "pinyin": "zuòwèi"}])


class CoreNLP_ZHHANS_EnricherMixin(VCRMixin):
    databases = "__all__"
    USERNAME = "a_username"
    EMAIL = "a_email@transcrob.es"
    PASSWORD = "top_secret"

    ##
    ## The main data for these tests was taken on 2019-02-09 from the 2nd paragraph of
    ## http://www.xinhuanet.com/2019-02/08/c_1124092961.htm
    ##
    ##

    ##
    ## helper methods
    ###
    @staticmethod
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(_NSRE, s)]

    ##
    ## Tests for public methods
    ##

    def _get_transliteratable_sentence_from_res(self, text_type):
        tokens = json.loads(pkgutil.get_data("tests.assets.enrichers", f"{text_type}.json").decode("utf-8"))[
            "sentences"
        ][0]["tokens"]

        return self.enricher._get_transliteratable_sentence(tokens)  # pylint: disable=W0212

    def test_get_transliteratable_sentence_ascii(self):
        """
        _get_transliteratable_sentence returns ascii tokens preceded by spaces
        """
        self.assertEquals(self._get_transliteratable_sentence_from_res("ascii"), " RCS ( Rich Communication Services )")

    def test_get_transliteratable_sentence_chars(self):
        """
        _get_transliteratable_sentence returns char tokens not separated by spaces
        """
        self.assertEquals(self._get_transliteratable_sentence_from_res("chars"), "文章提交注意事项")

    def test_get_transliteratable_sentence_mixed(self):
        """
        _get_transliteratable_sentence returns only ascii tokens not separated by spaces in mixed text
        """
        self.assertEquals(
            self._get_transliteratable_sentence_from_res("mixed"), "科技 : NHK以特别版 《 2001太空奥德赛 》推出首个 8K电视频道"
        )

    ##
    ## Tests for private methods
    ##

    def test__add_transliterations(self):
        # def _add_transliterations(sentence, transliterator):

        parsed_json = pkgutil.get_data("tests.assets.enrichers.nlp", "parsed.json").decode("utf-8")
        sentences = json.loads(parsed_json)["sentences"]

        ## asserts generated with the following code and json from enrich/test/assets/nlp/parsed.json
        pe_sentences = json.loads(
            pkgutil.get_data("tests.assets.enrichers.bing", "enriched_model_with_notes.json").decode("utf-8")
        )["sentences"]

        for i, s in enumerate(sentences):
            self.enricher._add_transliterations(s, self.transliterator)  # pylint: disable=W0212
            for j, t in enumerate(s["tokens"]):
                self.assertEqual(t["pinyin"], pe_sentences[i]["tokens"][j]["pinyin"])

    def test__set_best_guess(self):
        # def _set_best_guess(sentence, token):
        before_dir = os.path.dirname(sys.modules["tests.assets.enrichers.guess.before"].__file__)
        files_before = glob.glob(os.path.join(before_dir, "*.json"))
        files_before.sort(key=self.natural_sort_key)

        after_dir = os.path.dirname(sys.modules["tests.assets.enrichers.guess.after"].__file__)

        # 习近平在贺电中指出，中葡友谊源远流长。
        s = pkgutil.get_data("tests.assets.enrichers.guess", "sentence1.json").decode("utf-8")

        for fname in files_before:
            with open(fname) as in_json, open(os.path.join(after_dir, os.path.basename(fname))) as out_json:
                t = json.load(in_json)
                self.enricher._set_best_guess(s, t)  # pylint: disable=W0212
                self.assertEqual(t, json.load(out_json))

    # ## TODO: This is not strictly necessary, given we extensively test `enrich_to_json`
    # ## and that method simply calls CoreNLP and then this method.
    # # def _enrich_model(model, username):

    # ## FIXME: these should probably be implemented
    # # def test_get_simple_pos(self, token): pass
    # # def test_needs_enriching(self, token): pass
    # # @abstractmethod def needs_enriching(self, token): pass
    # # @abstractmethod def _cleaned_sentence(self, sentence): pass
    # # @abstractmethod def get_simple_pos(self, token): pass
    # # def _text_from_sentence(sentence):
    # # def is_clean(token):


class FullEnrichMixin(VCRMixin):
    @mock.patch("stats.KafkaProducer")
    def test_enrich_to_json(self, MockKafkaProducer):
        """
        This is the "big daddy" test that takes many seconds and tests a signficant proportion
        of the actively used code in the project. If this test passes, the project should basically "work"
        and if it doesn't, nothing useful will.
        """
        intxt_txt = pkgutil.get_data("tests.assets.enrichers.nlp", "in.txt").decode("utf-8")

        # test with no known entries
        model = self.manager.enricher().enrich_to_json(
            intxt_txt, self.user, self.manager, stats_mode=stats.GLOSSING_MODE_L1
        )
        enriched = pkgutil.get_data("tests.assets.enrichers.bing", "enriched_model_no_notes.json").decode("utf-8")

        self.assertEqual(model, json.loads(enriched))

        model = self.manager.enricher().enrich_to_json(
            intxt_txt, self.user, self.manager, stats_mode=stats.USER_STATS_MODE_L1
        )
        enriched_notes = pkgutil.get_data("tests.assets.enrichers.bing", "enriched_model_with_notes.json").decode(
            "utf-8"
        )

        self.assertEqual(model, json.loads(enriched_notes))

        # Here we can't just compare the calls, as there will be a user_id in there. This user_id
        # will change depending on when in the test run the users are created, so will break tests
        # with reordering them, adding, etc. Here we go into the call and pull out the invariant bit

        self.assertEqual("vocab", MockKafkaProducer.mock_calls[1][1][0])

        self.assertEqual(
            MockKafkaProducer.mock_calls[1][1][1]["tstats"],
            json.loads(pkgutil.get_data("tests.assets.zhhans_enrichers", "stats_no_notes.json").decode("utf-8")),
        )

        self.assertEqual("vocab", MockKafkaProducer.mock_calls[2][1][0])

        self.assertEqual(
            MockKafkaProducer.mock_calls[2][1][1]["tstats"],
            json.loads(pkgutil.get_data("tests.assets.zhhans_enrichers", "stats_w_notes.json").decode("utf-8")),
        )


class SetupAPITransactionTestCase(APITransactionTestCase):
    databases = "__all__"
    USERNAME = "a_username"
    EMAIL = "a_email@transcrob.es"
    PASSWORD = "top_secret"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username=self.USERNAME, email=self.EMAIL, password=self.PASSWORD)
        self.manager = managers.get("zh-Hans:en")
        self.api_base = f"{bing_api.URL_SCHEME}{self.manager.default()._api_host}"  # pylint: disable=W0212

        self.enricher = managers.get("zh-Hans:en").enricher()
        self.transliterator = managers.get("zh-Hans:en").transliterator()

    def tearDown(self):
        self.user.delete()


class FullEnrichTest(FullEnrichMixin, SetupAPITransactionTestCase):
    pass


class CoreNLP_ZHHANS_EnricherTest(CoreNLP_ZHHANS_EnricherMixin, SetupAPITransactionTestCase):
    pass
