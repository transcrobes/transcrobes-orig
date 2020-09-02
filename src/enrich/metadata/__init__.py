# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod


class Metadata(ABC):
    @staticmethod
    @abstractmethod
    def name():
        """
        This returns the name of the type of metadata so clients know how to manage it specifically.
        As this should probably be generic (see below), this should no longer be necessary at some
        point.
        """

    @abstractmethod
    def meta_for_word(self, lword):
        """
        Returns any known metadata for the word as json
        """
        # TODO: there should probably be a standard format for metadata, not like it is now
        # where the json format depends on the metadata provider.

    @abstractmethod
    def metas_as_string(self, lword):
        """
        Returns any known metadata for the word as string
        """
