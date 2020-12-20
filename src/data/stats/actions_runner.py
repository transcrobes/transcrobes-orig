# -*- coding: utf-8 -*-
import json
import logging
import os
import time

import kafka
from django.db import connection

import stats

from . import create_temp_table_userword, update_db_userword

RUNNER_TYPE = "actions"  # also kafka topic and group

logger = logging.getLogger(__name__)


def run_updates(broker, consumer_timeout_ms, stats_loop_sleep, max_poll_records):
    consumer = kafka.KafkaConsumer(
        RUNNER_TYPE, group_id=RUNNER_TYPE, max_poll_records=max_poll_records, bootstrap_servers=[broker]
    )

    temp_table = f"_{os.getpid()}_{int(time.time())}_{RUNNER_TYPE}"
    create_temp_table_userword(temp_table, connection)

    while True:
        data = {}
        for _topic, messages in consumer.poll(timeout_ms=consumer_timeout_ms).items():
            for message in messages:
                user_stats = json.loads(message.value.decode("utf-8"))

                # FIXME: decide how to properly distinguish between the various types, or at least
                # to store the info
                user_stats_mode = int(user_stats["user_stats_mode"])
                if user_stats_mode == stats.USER_STATS_MODE_IGNORE:
                    # We should probably never arrive here with USER_STATS_MODE_IGNORE, but if we do
                    continue

                # Only log if we are not ignoring, so must be after the guard!
                logger.debug(f"Processing action user_stats {user_stats=}")

                user_id = user_stats["user_id"]
                if user_id not in data:
                    data[user_id] = {}

                # FIXME: currently ignoring these as we don't have a home for the data yet
                if user_stats["type"] in ["add_note", "set_word_known", "bc_sentence_lookup"]:
                    continue

                if user_stats["type"] == "bc_word_lookup":
                    word = user_stats["data"]["target_word"]
                    if word not in data[user_id]:
                        data[user_id][word] = [0, 0, None]

                    data[user_id][word][0] += 1  # do we want to say it's looked at again? Always?
                    data[user_id][word][1] += 1
                    # currently we just overwrite with the last timestamp for this batch
                    data[user_id][word][2] = message.timestamp

        logger.info("Managing actions events for users %s", [len(v) for k, v in data.items()])
        logger.debug(f"Actions {data=}")
        update_db_userword(connection, data, temp_table)
        time.sleep(stats_loop_sleep)
