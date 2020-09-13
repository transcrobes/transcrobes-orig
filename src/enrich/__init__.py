# -*- coding: utf-8 -*-

import logging
from abc import ABC, abstractmethod

from ankrobes import Ankrobes

default_app_config = "enrich.apps.EnrichConfig"

logger = logging.getLogger(__name__)


class Enricher(ABC):
    ##
    ## Abstract methods
    ##
    @abstractmethod
    def needs_enriching(self, token):
        pass

    @abstractmethod
    def _add_transliterations(self, sentence, transliterator):
        pass

    @abstractmethod
    def _set_best_guess(self, sentence, token):
        pass

    @abstractmethod
    def _cleaned_sentence(self, sentence):
        pass

    @abstractmethod
    def get_simple_pos(self, token):
        pass

    ##
    ## Private/Protected methods
    ##
    @staticmethod
    def _text_from_sentence(sentence):
        text = ""
        for t in sentence["tokens"]:
            text += t.get("before", "") + t["originalText"]
        text += sentence["tokens"][-1].get("after", "")
        return text

    def _enrich_model(self, model, username, manager):
        userdb = Ankrobes(username)

        for s in model["sentences"]:
            self._add_transliterations(s, manager.transliterator())

            logger.debug("Looking for tokens to translate in %s", s)

            s["translation"], s["alignment"] = manager.default().translate(self._text_from_sentence(s).strip())

            for t in s["tokens"]:
                w = t["word"]
                if not self.is_clean(t):
                    continue

                if not self.needs_enriching(t):
                    continue

                # From here we attempt translation and create ankrobes entries
                ank_entry = userdb.sanitise_ankrobes_entry(userdb.get_word(w))
                t["ankrobes_entry"] = ank_entry
                t["definitions"] = {}
                best = manager.default().get_standardised_defs(t)
                if best:
                    t["definitions"]["best"] = best

                for p in manager.secondary():
                    sec = p.get_standardised_defs(t)
                    if sec:
                        t["definitions"][p.name()] = sec

                t["definitions"]["fallback"] = manager.default().get_standardised_fallback_defs(t)
                t["normalized_pos"] = self.get_simple_pos(t)

                # TODO: decide whether we really don't want to make a best guess for words we know
                # this might still be very useful though probably not until we have a best-trans-in-context SMT system
                # that is good
                # logger.debug("my ank_entry is {}".format(ank_entry))
                if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
                    # get the best guess for the definition of the word given the context of the sentence
                    self._set_best_guess(s, t)

                t["stats"] = []
                for p in manager.metadata():
                    t["stats"].append(p.metas_as_string(w))

    ##
    ## Public methods
    ##
    def __init__(self, config):
        self._config = config

    @staticmethod
    def is_clean(token):
        if token["word"].startswith("<") and token["word"].endswith(">"):  # html
            logger.debug("Looks like '%s' only has html, not adding to translatables", token["word"])
            return False
        return True

    def enrich_to_json(self, html, username, manager):
        model = manager.parser().parse(html)

        logging.debug("Attempting to enrich: '%s'", html)
        self._enrich_model(model, username, manager)

        return model
