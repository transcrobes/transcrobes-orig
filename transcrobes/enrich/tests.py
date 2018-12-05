# -*- coding: utf-8 -*-

import os, json

from django.conf import settings
from django.test import TestCase

from enrich.enricher import _get_transliteratable_sentence


class EnricherTests(TestCase):

    # _get_transliteratable_sentence
    def _get_transliteratable_sentence_from_res(self, text_type):
        with open(os.path.join(settings.BASE_DIR, 'enrich/test/assets/{}.json'.format(text_type)), 'r') as f:
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

# def _add_transliterations(sentence, transliterator):
# def _enrich_model(model):
# def _sanitise_ankrobes_entry(entries):
# def _set_best_guess(sentence, token):
# def enrich_to_json(html):

