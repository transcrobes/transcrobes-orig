# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

class Transliterator(ABC):
    @abstractmethod
    def transliterate(self):
        pass

    @abstractmethod
    def name():
        pass

