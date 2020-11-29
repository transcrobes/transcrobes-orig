# -*- coding: utf-8 -*-
import json
import logging
import os
import time

import kafka
from django.db import connection

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
                print("great action ts", message.timestamp)
                stats = json.loads(message.value.decode("utf-8"))
                user_id = stats["user_id"]
                if user_id not in data:
                    data[user_id] = {}

                event_type = stats["type"]
                event_data = stats["data"]

                # FIXME: currently ignoring these as we don't have a home for the data yet
                if event_type in ["add_note", "set_word_known", "bc_sentence_lookup"]:
                    continue

                if event_type == "bc_word_lookup":
                    word = event_data["target_word"]
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
