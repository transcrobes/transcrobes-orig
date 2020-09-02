# -*- coding: utf-8 -*-
import json
import os

import requests_mock
from vcr_unittest import VCRTestCase

from enrich.apis import bing as bing_api
from enrich.data import managers

from . import asset_path
from .assets import enrichers  # noqa: F401  # pylint: disable=W0611


class HTTPCoreNLPProviderTests(VCRTestCase):

    ##
    ## Plumbing methods
    ##
    def setUp(self):
        super().setUp()
        self.nlp = managers.get("zh-Hans:en").parser()

    ##
    ## Tests for public override methods
    ##

    def test_parse(self):
        # def parse(self, input):

        intxt_file = asset_path("tests.assets.enrichers", os.path.join("nlp", "in.txt"))
        outmodel_file = asset_path("tests.assets.enrichers", os.path.join("nlp", "parsed.json"))

        with open(intxt_file) as intxt, open(outmodel_file) as outmodel:
            parsed_json = outmodel.read()
            intxt_txt = intxt.read()

            model = self.nlp.parse(intxt_txt)
            self.assertEqual(model, json.loads(parsed_json))

    @requests_mock.Mocker()
    def test_parse_badnlp(self, m):
        # def parse(self, input):

        intxt_file = asset_path("tests.assets.enrichers", os.path.join("nlp", "in.txt"))

        with open(intxt_file) as intxt:
            intxt_txt = intxt.read()
            m.post(self.nlp._config["base_url"], text="something that is not json")  # pylint: disable=W0212
            with self.assertRaises(json.decoder.JSONDecodeError):
                self.nlp.parse(intxt_txt)


class BingTranslatorTests(VCRTestCase):

    ##
    ## Plumbing methods
    ##
    def setUp(self):
        super().setUp()

        self.transliterator = managers.get("zh-Hans:en").transliterator()
        self.dico = managers.get("zh-Hans:en").default()

        self.api_base = f"{bing_api.URL_SCHEME}{self.dico._api_host}"  # pylint: disable=W0212

    ##
    ## Tests for public override methods
    ##

    def test_get_standardised_defs(self):

        # 一拥而上
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "一拥而上", "pos": "NN", "lemma": "一拥而上"}),
            {
                "VERB": [
                    {
                        "upos": "VERB",
                        "opos": "VERB",
                        "normalizedTarget": "swarmed",
                        "confidence": 1.0,
                        "trans_provider": "BING",
                        "pinyin": "yì yōng ér shàng",
                    }
                ]
            },
        )

        # 活人
        self.assertEqual(
            self.dico.get_standardised_defs({"word": "活人", "pos": "NN", "lemma": "活人"}),
            {
                "NOUN": [
                    {
                        "upos": "NOUN",
                        "opos": "NOUN",
                        "normalizedTarget": "living",
                        "confidence": 1.0,
                        "trans_provider": "BING",
                        "pinyin": "huó rén",
                    }
                ]
            },
        )

        # 龙门石窟
        # Here there is no corresponding lookup on bing (as at 2019-02-11)
        self.assertEqual(self.dico.get_standardised_defs({"word": "龙门石窟", "pos": "NN", "lemma": "龙门石窟"}), {})

    def test_get_standardised_fallback_defs(self):
        # 一拥而上
        self.assertEqual(
            self.dico.get_standardised_fallback_defs({"word": "一拥而上", "pos": "NN", "lemma": "一拥而上"}),
            {
                "OTHER": [
                    {
                        "upos": "OTHER",
                        "opos": "OTHER",
                        "normalizedTarget": "Swarmed.",
                        "confidence": 0,
                        "trans_provider": "BING-DEFAULT",
                        "pinyin": "yì yōng ér shàng",
                    }
                ]
            },
        )

        # 活人
        self.assertEqual(
            self.dico.get_standardised_fallback_defs({"word": "活人", "pos": "NN", "lemma": "活人"}),
            {
                "OTHER": [
                    {
                        "upos": "OTHER",
                        "opos": "OTHER",
                        "normalizedTarget": "Living.",
                        "confidence": 0,
                        "trans_provider": "BING-DEFAULT",
                        "pinyin": "huó rén",
                    }
                ]
            },
        )

        # 龙门石窟
        self.assertEqual(
            self.dico.get_standardised_fallback_defs({"word": "龙门石窟", "pos": "NN", "lemma": "龙门石窟"}),
            {
                "OTHER": [
                    {
                        "upos": "OTHER",
                        "opos": "OTHER",
                        "normalizedTarget": "Longmen Grotto.",
                        "confidence": 0,
                        "trans_provider": "BING-DEFAULT",
                        "pinyin": "lóng mén shí kū",
                    }
                ]
            },
        )

    def test_transliterate(self):
        # def transliterate(self, text):

        # 一拥而上
        self.assertEqual(self.transliterator.transliterate("一拥而上"), "yì yōng ér shàng")

        # 活人
        self.assertEqual(self.transliterator.transliterate("活人"), "huó rén")

        # 龙门石窟
        self.assertEqual(self.transliterator.transliterate("龙门石窟"), "lóng mén shí kū")


# FIXME: to implement
# class SocketCoreNLPProviderTests(TestCase):
#     def test_parse(self):
#         # def parse(self, text):
#         pass
