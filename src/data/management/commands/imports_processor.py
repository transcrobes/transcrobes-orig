# -*- coding: utf-8 -*-

import logging
import threading
import time

from django.core.management.base import BaseCommand

from data.importer import process_import, process_list
from data.models import Import, UserList

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
        logger.info("Starting imports processors")

        # TODO: there is a small chance that parallel runners could take the same import/list, and end up
        # both doing work. The risk is pretty minuscule though, and the result only lost processor cycles,
        # so keeping simple for the moment
        while True:
            threads = []
            logger.info("Checking for imports to process")
            for an_import in Import.objects.filter(processed=False):
                an_import.processed = None
                an_import.save()
                logger.info(f"Starting import thread for import {an_import.title} for user {an_import.user.username}")
                threads.append(
                    threading.Thread(
                        name=an_import.title,
                        target=process_import,
                        args=(an_import,),
                    )
                )

            logger.info("Checking for userlists to process")
            for a_list in UserList.objects.filter(processed=False):
                a_list.processed = None
                a_list.save()
                logger.info(f"Starting thread for UserList {a_list.title} for user {a_list.user.username}")
                threads.append(
                    threading.Thread(
                        name=a_list.title,
                        target=process_list,
                        args=(a_list,),
                    )
                )
            for runner in threads:
                runner.start()
            time.sleep(LOOP_CHECK_SLEEP_SECS)
