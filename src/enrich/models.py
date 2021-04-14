# -*- coding: utf-8 -*-

import datetime
import json
import logging
from collections import defaultdict

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
from django.db.utils import IntegrityError

import stats
from ndutils import clean_definitions, lemma

logger = logging.getLogger(__name__)

cached_definitions = defaultdict(dict)
cache_loading = False


class Translation(models.Model):
    source_text = models.CharField(max_length=2000, db_index=True)

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True


class JsonTranslation(Translation):
    response_json = models.CharField(max_length=25000)

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True


class BingAPIPersistence(JsonTranslation):
    cached_date = models.DateTimeField(auto_now=True)
    from_lang = models.CharField(max_length=20, db_index=True, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, db_index=True, default="en")  # 20 is probably overkill

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"

    def __str__(self):
        return str(self.source_text)

    class Meta:
        abstract = True
        index_together = [
            ("source_text", "from_lang", "to_lang"),
        ]


class BingAPILookup(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_lkp"),
        ]


class BingAPITranslation(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tla"),
        ]


class BingAPITransliteration(BingAPIPersistence):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tli"),
        ]


class CachedDefinition(BingAPIPersistence):
    VERSION = 1
    word = models.ForeignKey(BingAPILookup, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_cdef"),
        ]
        indexes = [
            models.Index(fields=["cached_date", "from_lang", "to_lang"]),
        ]


def reload_definitions_cache(from_lang, to_lang):
    return update_cache(from_lang, to_lang, 0)


def ensure_cache_preloaded(from_lang, to_lang):
    if not cached_definitions[f"{from_lang}:{to_lang}"]:
        reload_definitions_cache(from_lang, to_lang)


def update_cache(from_lang, to_lang, cached_max_timestamp):
    global cache_loading  # pylint: disable=W0603
    if not cached_definitions[f"{from_lang}:{to_lang}"] and cache_loading:
        raise Exception("Cache loading, please come again")

    cache_loading = True  # avoid trashing with a global flag to reduce the number of loads, saving the DB

    if cached_max_timestamp == 0 and cached_definitions[f"{from_lang}:{to_lang}"]:
        logger.error("For some reason trying to reload cache when it is already loaded")
        return

    definitions = CachedDefinition.objects.filter(
        from_lang=from_lang,
        to_lang=to_lang,
        cached_date__gt=datetime.datetime.utcfromtimestamp(cached_max_timestamp),
    ).order_by("cached_date")

    new_cache = {}
    for cached_entry in definitions:
        val = json.loads(cached_entry.response_json)
        val["ts"] = cached_entry.cached_date.timestamp()
        new_cache[cached_entry.source_text] = val

    if cached_definitions[f"{from_lang}:{to_lang}"] and new_cache:
        logger.warning(
            "The new_cache is not empty for ts %s, len %s, new_cache[:100] %s",
            cached_max_timestamp,
            len(new_cache),
            str(new_cache)[:100],
        )
    cached_definitions[f"{from_lang}:{to_lang}"] = cached_definitions[f"{from_lang}:{to_lang}"] | new_cache


async def definition(manager, token, refresh=False):  # noqa:C901  # pylint: disable=R0912
    # FIXME: Need to make cached_definitions cache language dependent!!!

    word = lemma(token)
    if not word:  # calling the api with empty string will put rubbish in the DB
        return None

    val = cached_definitions[f"{manager.from_lang}:{manager.to_lang}"].get(word)
    if val and not refresh:
        return val

    cached_entry = await sync_to_async(
        CachedDefinition.objects.filter(source_text=word, from_lang=manager.from_lang, to_lang=manager.to_lang).first,
        thread_sensitive=settings.THREAD_SENSITIVE,
    )()

    logger.debug("Found %s element in db for %s", cached_entry, word)
    if not cached_entry or refresh:
        # this will create the ref entry in the DB if not present
        # WARNING! Do NOT move
        default_definition = clean_definitions(await manager.default().aget_standardised_defs(token))
        fallback_definition = clean_definitions(await manager.default().aget_standardised_fallback_defs(token))

        bing_word = await sync_to_async(BingAPILookup.objects.get, thread_sensitive=settings.THREAD_SENSITIVE)(
            source_text=word, from_lang=manager.from_lang, to_lang=manager.to_lang
        )

        json_definition = {
            "w": word,
            "id": bing_word.id,
            "defs": {
                manager.default().name(): default_definition,
                manager.default().FALLBACK_SHORT_NAME: fallback_definition,
            },
            "syns": await manager.default().apos_synonyms(token),
        }

        sound = await manager.transliterator().atransliterate(word)
        for x in manager.secondary():
            if not sound:
                sound = await x.sound_for(token)
            json_definition["defs"][x.name()] = clean_definitions(await x.aget_standardised_defs(token))

        json_definition["p"] = sound

        json_definition["metadata"] = {}
        for meta in manager.metadata():
            json_definition["metadata"][meta.name()] = await sync_to_async(
                meta.meta_for_word, thread_sensitive=settings.THREAD_SENSITIVE
            )(word)

        definition_object = json.dumps(json_definition, separators=(",", ":"))
        cached_entry = cached_entry or CachedDefinition(
            word=bing_word,
            source_text=word,
            from_lang=manager.from_lang,
            to_lang=manager.to_lang,
        )
        cached_entry.response_json = definition_object
        try:
            logger.debug("Before cached_entry.save for %s", str(cached_entry.id))
            await sync_to_async(cached_entry.save, thread_sensitive=settings.THREAD_SENSITIVE)()
            logger.debug("After cached_entry.save, before publish broadcast definitions for  %s", str(cached_entry.id))
            # await (await get_broadcast()).publish(channel="definitions", message=str(cached_entry.id))
            stats.KAFKA_PRODUCER.send("definitions", str(cached_entry.id))
            logger.debug("Managed to submit broadcast definitions for  %s", str(cached_entry.id))
            if refresh:
                return cached_entry
        except IntegrityError:
            # we just tried saving an entry that already exists, try to get again
            # it was very likely created in the meanwhile, so we can discard the duplicate
            cached_entry = await sync_to_async(
                CachedDefinition.objects.filter(
                    word=bing_word, source_text=word, from_lang=manager.from_lang, to_lang=manager.to_lang
                ).first,
                thread_sensitive=settings.THREAD_SENSITIVE,
            )()
            if not cached_entry:
                raise

    try:
        # list(dict) appears to be O(n)
        # cached_max_timestamp = list(cached_definitions[f"{manager.from_lang}:{manager.to_lang}"].values())[-1]["ts"]

        # this next(reversed(dict.values())) appears to be O(1)-ish
        cached_max_timestamp = next(reversed(cached_definitions[f"{manager.from_lang}:{manager.to_lang}"].values()))[
            "ts"
        ]
    except StopIteration:
        logger.warning("Loading cache from scratch, it is completely empty")
        cached_max_timestamp = 0

    logger.debug("Just before update_cache at cached_max_timestamp %s", cached_max_timestamp)
    # await sync_to_async(update_cache)(manager.from_lang, manager.to_lang, cached_max_timestamp)
    await sync_to_async(update_cache, thread_sensitive=settings.THREAD_SENSITIVE)(
        manager.from_lang, manager.to_lang, cached_max_timestamp
    )
    logger.debug("Just after update_cache at cached_max_timestamp %s", cached_max_timestamp)
    return cached_definitions[f"{manager.from_lang}:{manager.to_lang}"][word]
