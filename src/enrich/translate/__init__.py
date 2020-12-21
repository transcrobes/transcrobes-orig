# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod


class Translator(ABC):
    @staticmethod
    @abstractmethod
    def name():
        pass

    @abstractmethod
    def get_standardised_defs(self, token):
        pass

    @abstractmethod
    def get_standardised_fallback_defs(self, token):
        pass

    @abstractmethod
    def synonyms(self, token, std_pos, max_synonyms=5):
        pass

    @abstractmethod
    async def sound_for(self, token):  # FIXME: the entries should actually be able to do this per POS
        pass
