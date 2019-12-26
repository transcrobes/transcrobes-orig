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
