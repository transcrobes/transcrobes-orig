# -*- coding: utf-8 -*-

import asyncio
import logging
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from data.importer import process_import
from data.models import Import

logger = logging.getLogger(__name__)

LOOP_CHECK_SLEEP_SECS = 5


class Command(BaseCommand):
    help = """Process the vocab stats from reading activities"""

    # TODO: This is currently a "least effort" way of doing things. For the beginning
    # we will just have a few types of event to consume and process, so just do it as
    # threads for each event type in a single management command
    # This will obviously not scale but until requirements are clearer, there is no point
    # wasting time on possibly poorly adapted solutions

    def handle(self, *args, **options):
        logger.info(f"Starting imports processors")

        # some_imports = Import.objects.filter(processed=False)
        # some_imports = Import.objects.filter(id=7)
        # for an_import in some_imports:
        #     process_import(an_import)

        # TODO: there is a small chance that parallel runners could take the same import, and end up
        # both doing work. The risk is pretty minuscule though, and the result only lost processor cycles,
        # so keeping simple for the moment
        while True:
            threads = []
            logger.info("Checking for imports to process")
            for an_import in Import.objects.filter(processed=False):
                an_import.processed = None
                an_import.save()
                logger.info(f"Starting import thread for import {an_import.title} for user {an_import.user.username}")
                # FIXME: the following is ridiculous, and obviously doesn't work as expected
                # there is a bug without it though, because
                threads.append(
                    threading.Thread(
                        name=an_import.title,
                        target=process_import,
                        args=(an_import,),
                    )
                )
            for importer in threads:
                importer.start()
            time.sleep(LOOP_CHECK_SLEEP_SECS)
