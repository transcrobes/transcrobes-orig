# -*- coding: utf-8 -*-

import logging
import threading
import time

from django.core.management.base import BaseCommand

from data.importer import process_content, process_import, process_list
from data.models import PROCESSING, REQUESTED, Content, Import, UserList
from enrich.models import ensure_cache_preloaded

logger = logging.getLogger(__name__)

LOOP_CHECK_SLEEP_SECS = 2


class Command(BaseCommand):
    help = """Process user file imports"""

    def handle(self, *args, **options):
        logger.info("Starting imports processors")

        # TODO: there is a small chance that parallel runners could take the same import/list, and end up
        # both doing work. The risk is pretty minuscule though, and the result only lost processor cycles,
        # so keeping simple for the moment
        lang_pairs = set()
        while True:
            threads = []
            logger.debug("Checking for imports to process")
            for an_import in Import.objects.filter(processing=REQUESTED):
                lang_pairs.add(an_import.user.transcrober.lang_pair())
                an_import.processing = PROCESSING
                an_import.save()
                logger.info(f"Starting import thread for import {an_import.title} for user {an_import.user.username}")
                threads.append(
                    threading.Thread(
                        name=an_import.title,
                        target=process_import,
                        args=(an_import,),
                    )
                )

            logger.debug("Checking for userlists to process")
            for a_list in UserList.objects.filter(processing=REQUESTED):
                lang_pairs.add(a_list.user.transcrober.lang_pair())
                a_list.processing = PROCESSING
                a_list.save()
                logger.info(f"Starting thread for UserList {a_list.title} for user {a_list.user.username}")
                threads.append(
                    threading.Thread(
                        name=a_list.title,
                        target=process_list,
                        args=(a_list,),
                    )
                )
            logger.debug("Checking for content to process")
            for content in Content.objects.filter(processing=REQUESTED):
                lang_pairs.add(content.user.transcrober.lang_pair())
                content.processing = PROCESSING
                content.save()
                logger.info(f"Starting thread for Content {content.title} for user {content.user.username}")
                threads.append(
                    threading.Thread(
                        name=content.title,
                        target=process_content,
                        args=(content,),
                    )
                )

            # Load caches before starting threads to avoid trashing
            for pair in lang_pairs:
                ensure_cache_preloaded(pair.split(":")[0], pair.split(":")[1])

            for runner in threads:
                runner.start()
            time.sleep(LOOP_CHECK_SLEEP_SECS)
