# -*- coding: utf-8 -*-
import json
import logging
import os
import time
from collections import defaultdict

import kafka
from django.db import connection

import stats

from . import create_temp_table_userword, update_db_userword

RUNNER_TYPE = "actions"  # also kafka topic and group

logger = logging.getLogger(__name__)


def run_updates(broker, consumer_timeout_ms, stats_loop_sleep, max_poll_records):  # noqa:C901
    consumer = kafka.KafkaConsumer(
        RUNNER_TYPE, group_id=RUNNER_TYPE, max_poll_records=max_poll_records, bootstrap_servers=[broker]
    )

    logger.debug("Starting to process action actions_runner")
    temp_table = f"_{os.getpid()}_{int(time.time_ns())}_{RUNNER_TYPE}"
    create_temp_table_userword(temp_table, connection)

    while True:
        try:
            data = defaultdict(dict)
            for _topic, messages in consumer.poll(timeout_ms=consumer_timeout_ms).items():
                # Only log if we are not ignoring, so must be after the guard!
                logger.debug(f"Processing {len(messages)=} actions in actions_runner")

                for message in messages:
                    user_stats = json.loads(message.value.decode("utf-8"))
                    user_id = user_stats["user_id"]

                    # FIXME: decide how to properly distinguish between the various types, or at least
                    # to store the info
                    user_stats_mode = int(user_stats.get("user_stats_mode") or stats.USER_STATS_MODE_IGNORE)
                    if user_stats_mode == stats.USER_STATS_MODE_IGNORE:
                        # We should probably never arrive here with USER_STATS_MODE_IGNORE, but if we do
                        continue

                    # Only log if we are not ignoring, so must be after the guard!
                    logger.debug(f"Processing action user_stats {user_stats=}")

                    # FIXME: currently only supporting one lookup type for stats here
                    if user_stats["type"] == "bc_word_lookup":
                        word = user_stats["data"]["target_word"]
                        # sentence = user_stats["data"]["target_sentence"]  # not currently used
                        if word not in data[user_id]:
                            data[user_id][word] = [0, 0, None]

                        data[user_id][word][0] += 1  # do we want to say it's looked at again? Always?
                        data[user_id][word][1] += 1
                        # currently we just overwrite with the last timestamp for this batch
                        data[user_id][word][2] = message.timestamp

            logger.info("Managing actions events for users %s", [len(v) for _k, v in data.items()])
            if not data:
                logger.debug("No actions data to process")
            else:
                update_db_userword(connection, data, temp_table)
        except Exception:
            logger.exception("Exception running actions")

        time.sleep(stats_loop_sleep)
