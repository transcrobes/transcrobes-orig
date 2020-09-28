# -*- coding: utf-8 -*-
import json
import logging
import os
import time

import kafka
from django.db import connection

from . import create_temp_table_userword, update_db_userword

RUNNER_TYPE = "vocab"  # also kafka topic and group


def run_updates(broker, consumer_timeout_ms, stats_loop_sleep, max_poll_records):
    consumer = kafka.KafkaConsumer(
        RUNNER_TYPE, group_id=RUNNER_TYPE, max_poll_records=max_poll_records, bootstrap_servers=[broker]
    )

    temp_table = f"_{os.getpid()}_{int(time.time())}_{RUNNER_TYPE}"
    create_temp_table_userword(temp_table, connection)

    while True:
        data = {}
        for _tp, messages in consumer.poll(timeout_ms=consumer_timeout_ms).items():
            for message in messages:
                stats = json.loads(message.value.decode("utf-8"))
                user_id = stats["user_id"]
                if user_id not in data:
                    data[user_id] = {}
                token_stats = stats["tstats"]

                for k, v in token_stats.items():
                    if k not in data[user_id]:
                        data[user_id][k] = [0, v[1]]
                    data[user_id][k][0] += v[0]

        logging.info("Managing vocab events for users %s", [len(v) for k, v in data.items()])
        logging.debug(f"Vocab {data=}")
        update_db_userword(connection, data, temp_table)
        time.sleep(stats_loop_sleep)


# def update_db(conn, data, temp_table):
#     temp_file = io.StringIO()
#     writer = csv.writer(temp_file, delimiter="\t")
#     for user_id, words in data.items():
#         for word, stats in words.items():
#             writer.writerow([user_id, None, word, stats[0], stats[0] if stats[1] else 0])
#
#     temp_file.seek(0)
#     with conn.cursor() as cur:
#         cur.copy_from(temp_file, temp_table, null="")
#         cur.execute(
#             f"""UPDATE {temp_table}
#                             SET word_id = enrich_bingapilookup.id
#                             FROM enrich_bingapilookup
#                             WHERE word = enrich_bingapilookup.source_text"""
#         )
#
#         update_sql = f"""
#                 INSERT INTO data_userword (
#                     nb_seen,
#                     last_seen,
#                     nb_checked,
#                     last_checked,
#                     user_id,
#                     word_id,
#                     nb_seen_since_last_check,
#                     is_known
#                 ) SELECT
#                     tt.nb_seen,
#                     CURRENT_TIMESTAMP,
#                     CASE WHEN tt.nb_seen_since_last_check = 0 THEN tt.nb_seen ELSE 0 END,
#                     CASE WHEN tt.nb_seen_since_last_check = 0 THEN CURRENT_TIMESTAMP ELSE NULL END,
#                     tt.user_id,
#                     tt.word_id,
#                     tt.nb_seen_since_last_check,
#                     false
#                     FROM {temp_table} tt
#                 ON CONFLICT (user_id, word_id)
#                 DO
#                    UPDATE SET
#                         nb_seen = data_userword.nb_seen + EXCLUDED.nb_seen,
#                         last_seen = CURRENT_TIMESTAMP,
#                         nb_checked = data_userword.nb_checked + CASE WHEN EXCLUDED.nb_seen_since_last_check = 0
#                                                     THEN EXCLUDED.nb_seen
#                                                     ELSE 0
#                                                     END,
#                         last_checked = CASE WHEN EXCLUDED.nb_seen_since_last_check = 0
#                                         THEN CURRENT_TIMESTAMP
#                                         ELSE data_userword.last_checked
#                                         END,
#                         nb_seen_since_last_check =
#                             CASE WHEN EXCLUDED.nb_seen_since_last_check > 0
#                             THEN data_userword.nb_seen_since_last_check + EXCLUDED.nb_seen_since_last_check
#                             ELSE 0
#                             END"""
#
#         cur.execute(update_sql)
#         cur.execute(f"truncate table {temp_table}")
#         conn.commit()
