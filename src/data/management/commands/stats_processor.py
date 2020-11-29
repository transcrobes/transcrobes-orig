# -*- coding: utf-8 -*-

import logging
import threading

from django.conf import settings
from django.core.management.base import BaseCommand

from data.stats import actions_runner, vocab_runner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Process the vocab stats from reading activities"""

    # TODO: This is currently a "least effort" way of doing things. For the beginning
    # we will just have a few types of event to consume and process, so just do it as
    # threads for each event type in a single management command
    # This will obviously not scale but until requirements are clearer, there is no point
    # wasting time on possibly poorly adapted solutions

    def handle(self, *args, **options):
        logger.info(
            f"Starting stats processors with parameters {settings.KAFKA_BROKER=}, "
            f"{settings.KAFKA_CONSUMER_TIMEOUT_MS=}, "
            f"{settings.KAFKA_STATS_LOOP_SLEEP_SECS=}, "
            f"{settings.KAFKA_MAX_POLL_RECORDS=}"
        )
        threads = []

        for runner in [vocab_runner, actions_runner]:
            threads.append(
                threading.Thread(
                    name=runner.__name__,
                    target=runner.run_updates,
                    args=(
                        settings.KAFKA_BROKER,
                        settings.KAFKA_CONSUMER_TIMEOUT_MS,
                        settings.KAFKA_STATS_LOOP_SLEEP_SECS,
                        settings.KAFKA_MAX_POLL_RECORDS,
                    ),
                )
            )
        for runner in threads:
            runner.start()
