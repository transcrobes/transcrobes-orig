# -*- coding: utf-8 -*-
import asyncio
import logging
from abc import ABC, abstractmethod

import stats
from ankrobes import Ankrobes

default_app_config = "enrich.apps.EnrichConfig"

logger = logging.getLogger(__name__)


async def _gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


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
        for token in sentence["tokens"]:
            text += token.get("before", "") + token["originalText"]
        text += sentence["tokens"][-1].get("after", "")
        return text

    def _enrich_model(self, model, user, manager):
        userdb = Ankrobes(user.username)
        token_stats = {}

        for sentence in model["sentences"]:
            self._add_transliterations(sentence, manager.transliterator())

            logger.debug("Looking for tokens to translate in %s", sentence)
            original_sentence = self._text_from_sentence(sentence).strip()
            sentence["translation"], sentence["alignment"] = manager.default().translate(original_sentence)
            sentence["cleaned"] = original_sentence  # used to be _cleaned_sentence

            for token in sentence["tokens"]:
                word = token["word"]
                if not self.is_clean(token) or not self.needs_enriching(token):
                    continue

                # From here we attempt translation and create ankrobes entries
                ank_entry = userdb.sanitise_ankrobes_entry(userdb.get_word(word))
                token["ankrobes_entry"] = ank_entry

                token["definitions"] = {}
                best = manager.default().get_standardised_defs(token)
                if best:
                    token["definitions"]["best"] = best

                for provider in manager.secondary():
                    secondary = provider.get_standardised_defs(token)
                    # Only add a definition if one is in the definition source
                    if secondary:
                        token["definitions"][provider.name()] = secondary

                token["definitions"]["fallback"] = manager.default().get_standardised_fallback_defs(token)
                token["normalized_pos"] = self.get_simple_pos(token)

                token["synonyms"] = manager.default().synonyms(token, token["normalized_pos"], max_synonyms=5)
                token["user_synonyms"] = user.transcrober.filter_known(
                    token["synonyms"], min_morpheme_known_count=2, prefer_whole_known_words=True
                )

                # TODO: decide whether we really don't want to make a best guess for words we know
                # this might still be very useful though probably not until we have a best-trans-in-context SMT system
                # that is good
                # logger.debug("my ank_entry is {}".format(ank_entry))

                if word not in token_stats:
                    token_stats[word] = [0, 0]
                token_stats[word][0] += 1
                if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
                    # get the best guess for the definition of the word given the context of the sentence
                    self._set_best_guess(sentence, token)
                    token_stats[word][1] += 1  # we are proactively showing a best guess, so nb_checked += 1

                token["stats"] = []
                for provider in manager.metadata():
                    token["stats"].append(provider.metas_as_string(word))

        return model, token_stats

    # FIXME: unused, DELETE
    def _aenrich_model(self, model, user, manager):
        userdb = Ankrobes(user.username)
        token_stats = {}

        for sentence in model["sentences"]:
            self._add_transliterations(sentence, manager.transliterator())

            logger.debug("Looking for tokens to translate in %s", sentence)
            original_sentence = self._text_from_sentence(sentence).strip()
            sentence["translation"], sentence["alignment"] = manager.default().translate(original_sentence)
            sentence["cleaned"] = original_sentence  # used to be _cleaned_sentence

            for token in sentence["tokens"]:
                word = token["word"]
                if not self.is_clean(token) or not self.needs_enriching(token):
                    continue

                # From here we attempt translation and create ankrobes entries
                ank_entry = userdb.sanitise_ankrobes_entry(userdb.get_word(word))
                token["ankrobes_entry"] = ank_entry

                token["definitions"] = {}
                best = manager.default().get_standardised_defs(token)
                if best:
                    token["definitions"]["best"] = best

                for provider in manager.secondary():
                    secondary = provider.get_standardised_defs(token)
                    # Only add a definition if one is in the definition source
                    if secondary:
                        token["definitions"][provider.name()] = secondary

                token["definitions"]["fallback"] = manager.default().get_standardised_fallback_defs(token)
                token["normalized_pos"] = self.get_simple_pos(token)

                # TODO: decide whether we really don't want to make a best guess for words we know
                # this might still be very useful though probably not until we have a best-trans-in-context SMT system
                # that is good
                # logger.debug("my ank_entry is {}".format(ank_entry))

                if word not in token_stats:
                    token_stats[word] = [0, 0]
                token_stats[word][0] += 1
                if not ank_entry or not ank_entry[0]["Is_Known"]:  # FIXME: Just using the first for now
                    # get the best guess for the definition of the word given the context of the sentence
                    self._set_best_guess(sentence, token)
                    token_stats[word][1] += 1  # we are proactively showing a best guess, so nb_checked += 1

                token["stats"] = []
                for provider in manager.metadata():
                    token["stats"].append(provider.metas_as_string(word))

        return model, token_stats

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

    def enrich_to_json(self, html, user, manager, stats_mode=stats.USER_STATS_MODE_IGNORE):
        logging.debug("Attempting to sync enrich: '%s'", html)

        model = manager.parser().parse(html)
        model, token_stats = self._enrich_model(model, user, manager)

        if stats_mode > stats.USER_STATS_MODE_IGNORE:
            stats.KAFKA_PRODUCER.send(
                "vocab", {"user_id": user.id, "tstats": token_stats, "user_stats_mode": stats_mode}
            )
        return model

    # FIXME: this does NOT yet work and is NOT yet used
    def aenrich_to_json(self, html, user, manager, stats_mode=stats.USER_STATS_MODE_IGNORE):
        logging.debug("Attempting to async enrich: '%s'", html)

        model = manager.parser().parse(html)
        model, token_stats = self._aenrich_model(model, user, manager)

        if stats_mode > stats.USER_STATS_MODE_IGNORE:
            stats.KAFKA_PRODUCER.send(
                "vocab", {"user_id": user.id, "tstats": token_stats, "user_stats_mode": stats_mode}
            )
        return model
