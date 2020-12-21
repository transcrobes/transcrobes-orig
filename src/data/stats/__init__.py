# -*- coding: utf-8 -*-

import csv
import datetime
import io
import logging

import stats

logger = logging.getLogger(__name__)


def push_user_word_stats_update_to_clients(user_ids):
    logger.debug(f"Sending word_model_stats updates to kafka for {user_ids=}")
    for user_id in user_ids:
        logger.debug(f"Sending word_model_stats update to kafka for {user_id=}")
        stats.KAFKA_PRODUCER.send("word_model_stats", str(user_id))
        # TODO: Find out why the following hangs and causes much head pain!!!
        # await broadcast.publish(channel="word_model_stats", message=str(user_id))


def update_db_userword(conn, data, temp_table):  # pylint: disable=R0914
    logger.debug("Aggregating stats updates and persisting to postgres with temp table %s to %s", temp_table, data)
    # Get the data dictionary in CSV format, for easy/performant loading to the DB
    temp_file = io.StringIO()
    writer = csv.writer(temp_file, delimiter="\t")
    for user_id, words in data.items():
        for word, stats_data in words.items():
            word_id = None
            nb_seen = stats_data[0]
            nb_checked = stats_data[1]
            last_seen = datetime.datetime.fromtimestamp(stats_data[2] / 1000)  # use the kafka timestamp, which is in ms
            last_checked = last_seen if nb_checked else None

            nb_seen_since_last_check = 0 if nb_checked else nb_seen
            writer.writerow(
                [user_id, word_id, word, nb_seen, last_seen, nb_checked, last_checked, nb_seen_since_last_check]
            )

    logger.debug("Stats aggregated to csv StringIO, pushing to a temp table")
    temp_file.seek(0)  # will be empty otherwise!!!
    with conn.cursor() as cur:
        # Clean the update table to start with a clean slate
        logger.debug(f"data_userword updated, truncating {temp_table=}")
        cur.execute(f"truncate table {temp_table}")
        # Fill database temp table from the CSV
        cur.copy_from(temp_file, temp_table, null="")
        # Get the ID for each word from the reference table (currently enrich_bingapilookup)
        cur.execute(
            f"""UPDATE {temp_table}
                SET word_id = enrich_bingapilookup.id
                FROM enrich_bingapilookup
                WHERE word = enrich_bingapilookup.source_text"""
        )
        # Update the "stats" table for user vocab
        update_sql = f"""
                INSERT INTO data_userword (
                    nb_seen,
                    last_seen,
                    nb_checked,
                    last_checked,
                    user_id,
                    word_id,
                    nb_seen_since_last_check,
                    is_known,
                    updated_at
                ) SELECT
                    tt.nb_seen,
                    tt.last_seen,
                    tt.nb_checked,
                    tt.last_checked,
                    tt.user_id,
                    tt.word_id,
                    tt.nb_seen_since_last_check,
                    false,
                    now()
                  FROM {temp_table} tt
                  WHERE tt.word_id is not null
                ON CONFLICT (user_id, word_id)
                DO
                   UPDATE SET
                        updated_at = now(),
                        nb_seen = data_userword.nb_seen + EXCLUDED.nb_seen,
                        last_seen = EXCLUDED.last_seen,
                        nb_checked = data_userword.nb_checked + EXCLUDED.nb_checked,
                        last_checked = COALESCE(EXCLUDED.last_checked, data_userword.last_checked),
                        nb_seen_since_last_check =
                            CASE WHEN EXCLUDED.nb_seen_since_last_check > 0
                            THEN data_userword.nb_seen_since_last_check + EXCLUDED.nb_seen_since_last_check
                            ELSE 0
                            END"""

        logger.debug("Aggregated stats in a temptable, updating data_userword")
        cur.execute(update_sql)
        conn.commit()
        logger.info(f"User statistics updated for users {data.keys()}")

        # TODO: async here doesn't seem to work...
        # asyncio.run(push_user_word_stats_update_to_clients(user_ids=data.keys()))
        push_user_word_stats_update_to_clients(user_ids=data.keys())


def create_temp_table_userword(temp_table, conn):
    logger.debug(f"Creating temp table {temp_table=}")
    TEMP_TABLE_CREATE = f"""
        CREATE TEMP TABLE {temp_table}
         (user_id integer not null,
         word_id int null,
         word text not null,
         nb_seen integer not null,
         last_seen timestamp with time zone,
         nb_checked integer not null,
         last_checked timestamp with time zone,
         nb_seen_since_last_check integer null
         )"""
    with conn.cursor() as cur:
        cur.execute(TEMP_TABLE_CREATE)


def create_temp_table_usersentence(temp_table, conn):
    raise NotImplementedError
    # TEMP_TABLE_CREATE = f"""
    #     CREATE TEMP TABLE {temp_table} (user_id integer not null,
    #                                     ...
    #                                     nb_seen_since_last_check integer null
    #                                     )"""
    # with conn.cursor() as cur:
    #     cur.execute(TEMP_TABLE_CREATE)
