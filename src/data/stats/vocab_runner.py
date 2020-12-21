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

RUNNER_TYPE = "vocab"  # also kafka topic and group

logger = logging.getLogger(__name__)


def run_updates(broker, consumer_timeout_ms, stats_loop_sleep, max_poll_records):  # noqa: C901
    consumer = kafka.KafkaConsumer(
        RUNNER_TYPE, group_id=RUNNER_TYPE, max_poll_records=max_poll_records, bootstrap_servers=[broker]
    )

    logger.debug("Starting to process action vocab_runner")
    temp_table = f"_{os.getpid()}_{int(time.time_ns())}_{RUNNER_TYPE}"
    create_temp_table_userword(temp_table, connection)

    while True:
        try:
            data = defaultdict(dict)
            for _tp, messages in consumer.poll(timeout_ms=consumer_timeout_ms).items():
                logger.debug(f"Processing {len(messages)=} actions in vocab_runner")
                for message in messages:
                    user_stats = json.loads(message.value.decode("utf-8"))
                    user_id = user_stats["user_id"]
                    if user_id not in data:
                        data[user_id] = {}
                    token_stats = user_stats["tstats"]

                    # FIXME: decide how to properly distinguish between the various types, or at least
                    # to store the info.
                    if int(user_stats["user_stats_mode"]) == stats.USER_STATS_MODE_IGNORE:
                        # We should probably never arrive here with USER_STATS_MODE_IGNORE, but if we do
                        continue

                    # Only log if we are not ignoring, so must be after the guard!
                    logger.debug(f"Processing action vocab {user_stats=}")

                    for k, v in token_stats.items():
                        if k not in data[user_id]:
                            data[user_id][k] = [0, 0, None]
                        data[user_id][k][0] += v[0]
                        data[user_id][k][1] += v[1]
                        # currently we just overwrite with the last timestamp for this batch
                        data[user_id][k][2] = message.timestamp

            logger.info("Managing vocab events for users %s", [len(v) for k, v in data.items()])
            if not data:
                logger.debug("No vocab data to process")
            else:
                update_db_userword(connection, data, temp_table)
        except Exception:
            logger.exception("Exception running vocab")

        time.sleep(stats_loop_sleep)
