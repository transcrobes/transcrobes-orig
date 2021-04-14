# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import os
from dataclasses import field
from datetime import datetime
from typing import List, Optional

import strawberry
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from strawberry.utils.str_converters import to_camel_case

from data import clean_broadcaster_string, models
from enrich import database_sync_to_async, latest_definitions_json_dir_path
from enrich.data import managers
from enrich.models import CachedDefinition

logger = logging.getLogger(__name__)


# @strawberry.enum
# class POSTag(Enum):
#     JJ = "ADJ"
#     ...

# @strawberry.enum
# class HSKLevel(Enum):
#     ONE = 1
#     TWO = 2
#     THREE = 3
#     FOUR = 4
#     FIVE = 5
#     SIX = 6


@strawberry.type
class HSKEntry:
    # levels: List[HSKLevel]
    levels: Optional[List[int]] = None  # field(default_factory=list)

    @staticmethod
    def from_dict(entries):
        if not entries:
            return HSKEntry(levels=[])
        return HSKEntry(levels=[int(v["hsk"]) for v in entries])


@strawberry.type
class FrequencyEntry:
    wcpm: str  # word count per million
    wcdp: str  # word count ??? percent -> basically the percentage of all subtitles that contain the word
    pos: str  # dot-separated list of parts of speech
    pos_freq: str  # dot-separated list of the frequencies of the above parts of speech

    @staticmethod
    def from_dict(entries):
        # there is a weird thing where there are values with no pinyin, but always just one
        # and there is always another entry that has a pinyin. No idea what this is...
        # Just get the first one with a pinyin
        if not entries:
            # return None
            return FrequencyEntry(wcpm="", wcdp="", pos="", pos_freq="")
        for v in entries:
            if v["pinyin"]:  # FIXME: this is brittle to making generic!
                return FrequencyEntry(wcpm=v["wcpm"], wcdp=v["wcdp"], pos=v["pos"], pos_freq=v["pos_freq"])
        return FrequencyEntry(
            wcpm=entries[0]["wcpm"], wcdp=entries[0]["wcdp"], pos=entries[0]["pos"], pos_freq=entries[0]["pos_freq"]
        )


@strawberry.type
class POSValuesSet:
    pos_tag: str  # this is the standardised tag
    values: List[str] = field(default_factory=list)  # is this a string or strings?


@strawberry.type
class ProviderTranslations:
    provider: str
    pos_translations: List[POSValuesSet] = field(default_factory=list)


@strawberry.type
class DefinitionSet:
    word_id: str
    graph: str
    sound: List[str]
    hsk: Optional[HSKEntry] = None  # TODO: make this generic???
    frequency: Optional[FrequencyEntry] = None  # TODO: make this generic???
    updated_at: Optional[float] = 0
    deleted: Optional[bool] = False  # for the moment, let's just assume it's not deleted :-)
    synonyms: List[POSValuesSet] = field(default_factory=list)
    provider_translations: List[ProviderTranslations] = field(default_factory=list)

    @staticmethod
    def from_model_asdict(definition, providers):
        # copied from python 3.9.2 with addition of to_camel_case, and made to pass pylint!
        def _asdict_inner(obj, dict_factory=dict):
            if hasattr(type(obj), "__dataclass_fields__"):
                result = []
                for f in dataclasses.fields(obj):
                    value = _asdict_inner(getattr(obj, f.name), dict_factory)
                    result.append((to_camel_case(f.name), value))
                return dict_factory(result)
            if isinstance(obj, tuple) and hasattr(obj, "_fields"):
                return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
            if isinstance(obj, (list, tuple)):
                return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
            if isinstance(obj, dict):
                return type(obj)(
                    (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory)) for k, v in obj.items()
                )
            return copy.deepcopy(obj)

        obj = DefinitionSet.from_model(definition, providers)
        dict_obj = _asdict_inner(obj)  # this doesn't work dict_obj = asdict(obj)
        del dict_obj["deleted"]
        return dict_obj

    @staticmethod
    def from_model(definition: CachedDefinition, providers: List[str]) -> DefinitionSet:
        stored = json.loads(definition.response_json)
        out_definition = DefinitionSet(
            word_id=str(definition.word_id),  # RxDB requires a str for the primary key of a collection
            graph=definition.source_text,
            updated_at=definition.cached_date.timestamp(),
            sound=stored["p"].split(),
            frequency=FrequencyEntry.from_dict(stored["metadata"]["frq"]),
            hsk=HSKEntry.from_dict(stored["metadata"]["hsk"]),
        )
        for pos, syns in stored["syns"].items():
            out_definition.synonyms.append(POSValuesSet(pos_tag=pos, values=syns))

        definitions = stored["defs"]
        for provider in providers:
            if provider not in definitions:
                continue
            sd = ProviderTranslations(provider=provider)
            for k2, v2 in definitions[provider].items():
                sd.pos_translations.append(POSValuesSet(pos_tag=k2, values=[entry["nt"] for entry in v2]))
            out_definition.provider_translations.append(sd)
        return out_definition


def filter_cached_definitions(
    info, limit: int, word_id: Optional[str] = "", updated_at: Optional[float] = -1
) -> List[DefinitionSet]:
    user = get_user(info.context)
    manager = managers.get(user.transcrober.lang_pair())
    if not manager:
        raise ImproperlyConfigured(f"Server does not support language pair {user.transcrober.lang_pair()}")

    providers = user.transcrober.dictionary_ordering.split(",")
    qs = [Q(from_lang=user.transcrober.from_lang) & Q(to_lang=user.transcrober.to_lang)]
    # if word_id:  # FIXME: can we use this at all?
    #     qs.append(Q(word_id=int(word_id)))

    if not updated_at or updated_at <= 0:

        # FIXME: Here we get the last object from the most recent generated file. There is a small
        # chance that there has been a new file generated since the user downloaded their version
        # so that needs to be fixed. We will only regenarate once a week or so, so later...
        latest_name = os.path.basename(latest_definitions_json_dir_path(user))
        latest_cached_date = datetime.fromtimestamp(float(latest_name.split("-")[1]), timezone.utc)
        latest_word_id = int(latest_name.split("-")[2])

        try:
            return [
                # the order by is probably not necessary, but may be in the future
                DefinitionSet.from_model(
                    CachedDefinition.objects.filter(cached_date=latest_cached_date, word_id=latest_word_id)
                    .order_by("-cached_date", "-word_id")
                    .first(),
                    providers,
                )
            ]
        except Exception:
            logger.exception(f"Error getting DefinitionSet for {qs=}")
            raise

    updated_at_datetime = datetime.fromtimestamp(updated_at, timezone.utc)
    qs.append(
        (Q(cached_date__gt=updated_at_datetime) | (Q(cached_date=updated_at_datetime) & Q(word_id__gt=int(word_id))))
    )
    try:
        definitions_list = list(CachedDefinition.objects.order_by("cached_date", "word_id").filter(Q(*qs))[:limit])
        definitions = [DefinitionSet.from_model(word, providers) for word in definitions_list]
    except Exception:
        logger.exception(f"Error getting DefinitionSet for {qs=}")
        raise
    return definitions


@strawberry.type
class WordModelStats:
    word_id: str
    nb_seen: Optional[int] = 0
    nb_seen_since_last_check: Optional[int] = 0
    last_seen: Optional[float] = 0
    nb_checked: Optional[int] = 0
    last_checked: Optional[float] = 0
    nb_translated: Optional[int] = 0
    last_translated: Optional[float] = 0
    updated_at: Optional[float] = 0
    deleted: Optional[bool] = False

    @staticmethod
    def from_model(dj_model):
        ws = WordModelStats(
            word_id=dj_model.word_id,
            nb_seen=dj_model.nb_seen,
            nb_seen_since_last_check=dj_model.nb_seen_since_last_check,
            nb_checked=dj_model.nb_checked,
            nb_translated=dj_model.nb_translated,
            updated_at=dj_model.updated_at.timestamp(),
        )
        if dj_model.last_seen:
            ws.last_seen = dj_model.last_seen.timestamp()
        if dj_model.last_checked:
            ws.last_checked = dj_model.last_checked.timestamp()
        if dj_model.last_translated:
            ws.last_translated = dj_model.last_translated.timestamp()
        return ws


def filter_word_model_stats(
    info, limit: int, word_id: Optional[str] = "", updated_at: Optional[float] = -1
) -> List[WordModelStats]:
    user = get_user(info.context)
    qs = [Q(user=user)]

    if updated_at and updated_at > 0:
        updated_at_datetime = datetime.fromtimestamp(updated_at, timezone.utc)
        base_query = Q(updated_at__gt=updated_at_datetime)
        if not word_id:
            qs.append(base_query)
        else:
            qs.append(base_query | (Q(updated_at=updated_at_datetime) & Q(word_id__gt=int(word_id))))
    try:
        lists_list = list(models.UserWord.objects.order_by("updated_at", "word_id").filter(Q(*qs))[:limit])
        word_stats = [WordModelStats.from_model(dj_model) for dj_model in lists_list]
    except Exception:
        logger.exception(f"Error getting WordModelStats for {qs=}")
        raise
    return word_stats


@strawberry.type
class WordList:
    list_id: str
    name: str
    word_ids: List[str]
    default: Optional[bool] = False
    updated_at: Optional[float] = 0
    deleted: Optional[bool] = False

    @staticmethod
    def from_model(dj_model):
        return WordList(
            list_id=dj_model.id,
            name=dj_model.title,
            default=dj_model.user is None,
            updated_at=dj_model.modified.timestamp(),
            word_ids=[
                str(w)
                for w in models.UserListWord.objects.filter(user_list__user=dj_model.user, user_list_id=dj_model.id)
                .order_by("default_order")
                .values_list("word_id", flat=True)
            ],
        )


def filter_word_list(info, limit: int, list_id: Optional[str] = "", updated_at: Optional[float] = -1) -> List[WordList]:
    user = get_user(info.context)
    # TODO: decide how to properly manage shared lists
    qs = [Q(user=user) | Q(Q(user__isnull=True) & Q(shared=True))]

    if updated_at and updated_at > 0:
        updated_at_datetime = datetime.fromtimestamp(updated_at, timezone.utc)
        base_query = Q(modified__gt=updated_at_datetime)
        if not list_id:
            qs.append(base_query)
        else:
            qs.append(base_query | (Q(modified=updated_at_datetime) & Q(id__gt=int(list_id))))

    try:
        lists_list = list(models.UserList.objects.order_by("modified", "id").filter(Q(*qs))[:limit])
        word_lists = [WordList.from_model(dj_model) for dj_model in lists_list]
    except Exception:
        logger.exception(f"Error getting WordList for {qs=}")
        raise
    return word_lists


@strawberry.type
class Card:
    card_id: str
    interval: Optional[int] = 0
    due_date: Optional[float] = 0  # should this have a default value???
    repetition: Optional[int] = 0
    efactor: Optional[float] = 2.5
    front: Optional[str] = ""
    back: Optional[str] = ""
    updated_at: Optional[float] = 0
    first_revision_date: Optional[float] = 0
    last_revision_date: Optional[float] = 0
    known: Optional[bool] = False
    suspended: Optional[bool] = False
    deleted: Optional[bool] = False

    @staticmethod
    def from_model(dj_card):
        out_card = Card(
            card_id=f"{dj_card.word_id}-{dj_card.card_type}",
            interval=dj_card.interval,
            repetition=dj_card.repetition,
            efactor=dj_card.efactor,
            front=dj_card.front,
            back=dj_card.back,
            known=dj_card.known,
            suspended=dj_card.suspended,
            updated_at=dj_card.updated_at.timestamp(),
            deleted=dj_card.deleted,
        )
        if dj_card.first_revision_date:
            out_card.first_revision_date = dj_card.first_revision_date.timestamp()
        if dj_card.last_revision_date:
            out_card.last_revision_date = dj_card.last_revision_date.timestamp()
        if dj_card.due_date:
            out_card.due_date = dj_card.due_date.timestamp()

        return out_card


@strawberry.input
class CardInput:
    card_id: str
    interval: Optional[int] = 0
    due_date: Optional[float] = 0
    repetition: Optional[int] = 0
    efactor: Optional[float] = 2.5
    front: Optional[str] = ""
    back: Optional[str] = ""
    updated_at: Optional[float] = 0
    first_revision_date: Optional[float] = 0
    last_revision_date: Optional[float] = 0
    known: Optional[bool] = False
    suspended: Optional[bool] = False
    deleted: Optional[bool] = False


def filter_cards(info, limit: int, card_id: Optional[str] = "", updated_at: Optional[float] = -1) -> List[Card]:
    logger.debug(f"{info=}, {limit=}, {card_id=}, {updated_at=} ")
    user = get_user(info.context)
    qs = [Q(user=user)]
    if updated_at and updated_at > 0:
        updated_at_datetime = datetime.fromtimestamp(updated_at, timezone.utc)
        base_query = Q(updated_at__gt=updated_at_datetime)
        if not card_id:
            qs.append(base_query)
        else:
            # FIXME: do I need the type here???
            word_id, card_type = map(int, card_id.split("-"))
            qs = [
                (
                    base_query
                    | (
                        (Q(updated_at=updated_at_datetime) & Q(word_id__gt=word_id))
                        | (Q(updated_at=updated_at_datetime) & Q(card_type__gt=card_type))
                    )
                )
            ]
    try:
        model_list = list(models.Card.objects.order_by("updated_at", "word_id", "card_type").filter(Q(*qs))[:limit])
        card_list = [Card.from_model(dj_card) for dj_card in model_list]
    except Exception:
        logger.exception(f"Error getting Cards for {qs=}")
        raise
    return card_list


@strawberry.type
class Query:
    @strawberry.field
    def hello() -> str:  # pylint: disable=E0211
        return "world"

    @strawberry.field
    async def feed_card(  # pylint: disable=E0213
        info, limit: int, card_id: Optional[str] = "", updated_at: Optional[float] = -1
    ) -> List[Card]:
        return await database_sync_to_async(filter_cards, thread_sensitive=settings.THREAD_SENSITIVE)(
            info, limit, card_id, updated_at
        )

    @strawberry.field
    async def feed_word_model_stats(  # pylint: disable=E0213
        info, limit: int, word_id: Optional[str] = "", updated_at: Optional[float] = -1
    ) -> List[WordModelStats]:
        mylist = await database_sync_to_async(filter_word_model_stats, thread_sensitive=settings.THREAD_SENSITIVE)(
            info, limit, word_id, updated_at
        )
        return mylist

    @strawberry.field
    async def feed_word_list(  # pylint: disable=E0213
        info, limit: int, list_id: Optional[str] = "", updated_at: Optional[float] = -1
    ) -> List[WordList]:
        mylist = await database_sync_to_async(filter_word_list, thread_sensitive=settings.THREAD_SENSITIVE)(
            info, limit, list_id, updated_at
        )
        return mylist

    @strawberry.field
    async def feed_definitions(  # pylint: disable=E0213
        info, limit: int, word_id: Optional[str] = "", updated_at: Optional[float] = -1
    ) -> List[DefinitionSet]:
        return await database_sync_to_async(filter_cached_definitions, thread_sensitive=settings.THREAD_SENSITIVE)(
            info, limit, word_id, updated_at
        )


def get_user(context):
    # FIXME: there is almost certain a way to get this done properly, so the context.request.user
    # is already authenticated when I get here from a jwt access token. This happens from the
    # chrome extension, where the django infra is not picking up a csrftoken (like it does with
    # the transcrob.es queries)
    if not context.request.user.is_anonymous:
        return context.request.user

    # FIXME: this will currently return an error that is not directly interpretable by js (it's not in json)
    # so better would be to make the GraphQL return a parsable json field. In the meantime, just look for
    # a string in the error string returned, like the nasty HackMeister that I am...
    user, _token = JWTAuthentication().authenticate(context.request)
    logger.debug(f"get_user user is {user=}")
    if not user or user.is_anonymous:
        raise PermissionError("You are not authorised to access this page")
    return user


@strawberry.type
class Mutation:
    # type Mutation {
    #   setCard(card: CreateCard): Card
    # }
    @strawberry.mutation
    async def set_card(self, info, card: CardInput = None) -> Card:
        user = await database_sync_to_async(get_user, thread_sensitive=settings.THREAD_SENSITIVE)(info.context)

        word_id, card_type = map(int, card.card_id.split("-"))
        try:
            dj_card = await database_sync_to_async(models.Card.objects.get, thread_sensitive=settings.THREAD_SENSITIVE)(
                word_id=word_id, card_type=card_type, user=user
            )
        except models.Card.DoesNotExist:
            dj_card = models.Card(word_id=word_id, card_type=card_type, user=user)

        if card.due_date:
            dj_card.due_date = datetime.fromtimestamp(card.due_date, timezone.utc)

        if card.first_revision_date:
            dj_card.first_revision_date = datetime.fromtimestamp(card.first_revision_date, timezone.utc)
        if card.last_revision_date:
            dj_card.last_revision_date = datetime.fromtimestamp(card.last_revision_date, timezone.utc)

        dj_card.interval = card.interval
        dj_card.repetition = card.repetition
        dj_card.efactor = card.efactor
        dj_card.front = card.front
        dj_card.back = card.back
        dj_card.known = card.known
        dj_card.suspended = card.suspended
        dj_card.updated_at = timezone.now()  # int(time.time())  # time_ns()? something else?
        dj_card.deleted = card.deleted

        try:
            await database_sync_to_async(dj_card.save, thread_sensitive=settings.THREAD_SENSITIVE)()
            await info.context.broadcast.publish(channel="cards", message=str(user.id))
        except Exception as e:
            logger.exception(f"Error saving updated card: {json.dumps(dataclasses.asdict(card))}")
            logger.error(e)
            raise

        return Card.from_model(dj_card)


@strawberry.type
class Subscription:
    # type Subscription {
    #   changedCard(token: String!): Card
    # }
    @strawberry.subscription
    async def changed_card(self, info, token: str) -> Card:
        try:
            user_id = JWTAuthentication().get_validated_token(token)["user_id"]  # raises if not valid
        except Exception as e:
            logger.error(e)
            raise
        logger.debug("Setting up card subscription for user %s", user_id)

        async with info.context.broadcast.subscribe(channel="cards") as subscriber:
            async for event in subscriber:
                if clean_broadcaster_string(event.message) == str(user_id):
                    logger.debug(f"Got a definitions subscription event for {user_id}")
                    yield {"cardId": "42"}

    # type Subscription {
    #   changedWordModelStats(token: String!): WordModelStats
    # }
    @strawberry.subscription
    async def changed_word_model_stats(self, info, token: str) -> WordModelStats:
        try:
            user_id = JWTAuthentication().get_validated_token(token)["user_id"]  # raises if not valid
        except Exception as e:
            logger.exception(e)
            raise
        logger.debug("Setting up word_model_stats subscription for user %s", user_id)

        async with info.context.broadcast.subscribe(channel="word_model_stats") as subscriber:
            async for event in subscriber:
                if clean_broadcaster_string(event.message) == str(user_id):
                    logger.debug(f"Got a word_model_stats subscription event for {user_id}")
                    yield {"wordId": "42"}

    # type Subscription {
    #   changedWordList(token: String!): WordList
    # }
    @strawberry.subscription
    async def changed_word_list(self, info, token: str) -> WordList:
        try:
            user_id = JWTAuthentication().get_validated_token(token)["user_id"]  # raises if not valid
        except Exception as e:
            logger.exception(e)
            raise
        logger.debug("Setting up word_list subscription for user %s", user_id)

        async with info.context.broadcast.subscribe(channel="word_list") as subscriber:
            async for event in subscriber:
                if clean_broadcaster_string(event.message) == str(user_id):
                    logger.debug(f"Got a word_list subscription event for {user_id}")
                    yield {"listId": "42"}

    # type Subscription {
    #   changedDefinition(token: String!): DefinitionSet
    # }
    @strawberry.subscription
    async def changed_definition(self, info, token: str) -> DefinitionSet:
        try:
            user_id = JWTAuthentication().get_validated_token(token)["user_id"]  # raises if not valid
        except Exception as e:
            logger.exception(e)
            raise
        logger.debug("Setting up definitions subscription for user %s", user_id)

        async with info.context.broadcast.subscribe(channel="definitions") as subscriber:
            async for event in subscriber:
                logger.debug(f"Got a definitions subscription event for {event.message}")
                yield {"wordId": "42"}


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
