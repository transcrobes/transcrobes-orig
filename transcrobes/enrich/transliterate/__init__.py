# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod


class Transliterator(ABC):
    @abstractmethod
    def transliterate(self, text):
        pass

    @staticmethod
    @abstractmethod
    def name():
        pass
