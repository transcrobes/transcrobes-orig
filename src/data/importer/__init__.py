# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import threading
from collections import Counter, defaultdict
from itertools import chain

import aiohttp
import magic
from django.conf import settings

from data.models import Import
from enrich.data import managers
from enrichers.zhhans import CORENLP_IGNORABLE_POS

logger = logging.getLogger(__name__)


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


def chunked(size, source):
    for i in range(0, len(source), size):
        yield source[i : i + size]


def text_from_text_file(contents):
    return contents


def text_from_import(an_import):
    # We should only have valid files here, but should probably add more checking anyway

    with open(an_import.import_file.path) as fh:
        contents = fh.read()
        tester = magic.Magic(mime=True, mime_encoding=True)
        file_type, _file_encoding = tester.from_buffer(contents[0 : settings.IMPORT_DETECT_CHUNK_SIZE_BYTES]).split(
            "; charset="
        )

        # FIXME: do some check that we have utf8 - and maybe also check that there are Chinese chars?
        # also check for only simplifieds?

        if file_type in ["text/plain", "application/csv"]:
            return text_from_text_file(contents)
        # elif file_type in ['application/pdf', ...]:
        #     return text_from_other...
        raise Exception(f"Attempt to import from unsupported file_type {file_type}")


class VocabularyCounter(Counter):  # pylint: disable=W0223
    pass


class GrammarRuleCounter(Counter):  # pylint: disable=W0223
    pass


async def vocabulary_from_model(model):
    # TODO: consider removing the first and last word if settings.IMPORT_PARSE_CHUNK_SIZE_BYTES
    # as it might have got half of a character (which can be more than one byte and we split on
    # bytes, not chars, at least for now!
    vocabulary = VocabularyCounter()
    for sentence in model["sentences"]:
        for token in sentence["tokens"]:
            if token["pos"] not in CORENLP_IGNORABLE_POS:  # TODO: consider making this configurable
                vocabulary[token["word"]] += 1
    return vocabulary


async def grammar_rules_from_model(_model):
    # TODO: Do, and don't forget to remove the first and last sentences if the size
    # of the block is the same as settings.IMPORT_PARSE_CHUNK_SIZE_BYTES because we will have split
    # sentences, which might have borked grammatical structures
    return None


async def get_model_elements(manager, chunk, process_type):
    logger.debug("Sending chunk to the parser %s", chunk[0:100])
    # FIXME: find some way to deal with process_type elegantly...
    # depparse is very expensive, only do if necessary
    annotators = "lemma" + (",depparse" if process_type in [2, 3] else "")
    params = f'{{"annotators":"{annotators}","outputFormat":"json"}}'

    model = await manager.parser().aparse(chunk, provider_parameters=params)

    awaitables = []
    if process_type in [1, 3]:
        awaitables.append(vocabulary_from_model(model))
    if process_type in [2, 3]:
        awaitables.append(grammar_rules_from_model(model))

    return asyncio.gather(*awaitables)


async def process(manager, contents, process_type):
    futures = await asyncio.gather(
        *(
            await gather_with_concurrency(
                settings.IMPORT_MAX_CONCURRENT_PARSER_QUERIES,
                *[get_model_elements(manager, chunk, process_type) for chunk in contents],
            )
        )
    )
    vocabulary = []
    grammar_rules = []
    for f in futures:
        for i in f:
            if isinstance(i, VocabularyCounter):
                vocabulary.append(i)
            elif isinstance(i, GrammarRuleCounter):
                grammar_rules.append(i)
    merged_vocabulary = VocabularyCounter(chain.from_iterable(vocabulary or []))
    merged_grammar_rules = GrammarRuleCounter(chain.from_iterable(grammar_rules or []))

    analysis = {}
    if process_type in [1, 3]:
        # TODO: optimise
        frequency_buckets = defaultdict(list)
        for k, v in sorted(merged_vocabulary.items()):
            frequency_buckets[v].append(k)

        frequency_counts = Counter({k: len(v) for k, v in frequency_buckets.items()})

        analysis["vocabulary"] = {
            "buckets": frequency_buckets,
            "counts": frequency_counts,
        }
    if process_type in [2, 3]:
        analysis["grammar_rules"] = merged_grammar_rules

    return analysis


def process_import(an_import):
    manager = managers.get(an_import.user.transcrober.lang_pair())
    if not manager:
        raise NotImplementedError(f"Server does not support language pair {an_import.user.transcrober.lang_pair()}")

    # synchronous get text from file into memory in chunks for later async parallel processing
    contents = list(chunked(settings.IMPORT_PARSE_CHUNK_SIZE_BYTES, text_from_import(an_import)))
    an_import.analysis = json.dumps(asyncio.run(process(manager, contents, an_import.process_type)), ensure_ascii=False)
    an_import.processed = True
    an_import.save()
