# -*- coding: utf-8 -*-

import datetime
import json
import logging
import os
import shutil
from tempfile import mkdtemp

from django.conf import settings

from data.models import Transcrober
from data.schema import DefinitionSet
from enrich import database_sync_to_async
from enrich.data import managers
from enrich.models import CachedDefinition, definition

logger = logging.getLogger(__name__)


def all_cached_definitions() -> list:
    return list(CachedDefinition.objects.order_by("cached_date", "word_id"))


async def refresh_cached_definitions(response_json_match_string: str, print_progress: bool = True) -> bool:
    manager = managers.get("zh-Hans:en")
    alldems = await database_sync_to_async(all_cached_definitions)()
    for i, d in enumerate(alldems):
        if print_progress and i % 100 == 0:
            logger.info(datetime.datetime.now(), d.id)
        if response_json_match_string not in d.response_json:
            continue
        await definition(manager, {"l": d.source_text, "pos": "NN"}, refresh=True)
    return True


def chunks(alist, n):
    """Yield successive n-sized chunks from the parameter list alist."""
    for i in range(0, len(alist), n):
        yield alist[i : i + n]


def regenerate_definitions_jsons_multi(fakelimit: int = 0) -> bool:
    # save a new file for each combination of providers
    for tc in Transcrober.objects.distinct("dictionary_ordering").all():
        providers = tc.dictionary_ordering.split(",")
        if fakelimit:
            cached_definitions = list(CachedDefinition.objects.order_by("cached_date", "word_id"))[-fakelimit:]
        else:
            cached_definitions = CachedDefinition.objects.order_by("cached_date", "word_id")
        export = [DefinitionSet.from_model_asdict(ds, providers) for ds in cached_definitions]
        logger.info("Loaded all definitions for %s, flusing to file", providers)

        last_new_definition = export[-1]
        ua = last_new_definition["updatedAt"]
        wid = last_new_definition["wordId"]
        provs = "-".join(providers)
        new_files_dir_path = os.path.join(settings.DEFINITIONS_CACHE_DIR, f"definitions-{ua}-{wid}-{provs}_json")
        tmppath = mkdtemp(dir=settings.DEFINITIONS_CACHE_DIR)
        for i, block in enumerate(chunks(export, 5000)):
            chunkpath = os.path.join(tmppath, f"{i:03d}.json")
            logger.info("Saving chunk to file %s", chunkpath)
            with open(chunkpath, "w") as definitions_file:
                json.dump(block, definitions_file)

        shutil.rmtree(new_files_dir_path, ignore_errors=True)
        os.rename(tmppath, new_files_dir_path)

        logger.info("Flushed all definitions for %s to file %s", providers, new_files_dir_path)
    return True
