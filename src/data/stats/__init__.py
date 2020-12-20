# -*- coding: utf-8 -*-

import csv
import datetime
import io


def update_db_userword(conn, data, temp_table):  # pylint: disable=R0914

    # Get the data dictionary in CSV format, for easy/performant loading to the DB
    temp_file = io.StringIO()
    writer = csv.writer(temp_file, delimiter="\t")
    for user_id, words in data.items():
        for word, stats in words.items():
            word_id = None
            nb_seen = stats[0]
            nb_checked = stats[1]
            last_seen = datetime.datetime.fromtimestamp(stats[2] / 1000)  # use the kafka timestamp, which is in ms
            last_checked = last_seen if nb_checked else None

            nb_seen_since_last_check = 0 if nb_checked else nb_seen
            writer.writerow(
                [user_id, word_id, word, nb_seen, last_seen, nb_checked, last_checked, nb_seen_since_last_check]
            )

    temp_file.seek(0)  # will be empty otherwise!!!
    with conn.cursor() as cur:
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
                    is_known
                ) SELECT
                    tt.nb_seen,
                    tt.last_seen,
                    tt.nb_checked,
                    tt.last_checked,
                    tt.user_id,
                    tt.word_id,
                    tt.nb_seen_since_last_check,
                    false
                  FROM {temp_table} tt
                  WHERE tt.word_id is not null
                ON CONFLICT (user_id, word_id)
                DO
                   UPDATE SET
                        nb_seen = data_userword.nb_seen + EXCLUDED.nb_seen,
                        last_seen = EXCLUDED.last_seen,
                        nb_checked = data_userword.nb_checked + EXCLUDED.nb_checked,
                        last_checked = COALESCE(EXCLUDED.last_checked, data_userword.last_checked),
                        nb_seen_since_last_check =
                            CASE WHEN EXCLUDED.nb_seen_since_last_check > 0
                            THEN data_userword.nb_seen_since_last_check + EXCLUDED.nb_seen_since_last_check
                            ELSE 0
                            END"""

        cur.execute(update_sql)
        cur.execute(f"truncate table {temp_table}")
        conn.commit()


def create_temp_table_userword(temp_table, conn):
    TEMP_TABLE_CREATE = f"""
        CREATE TEMP TABLE {temp_table} (user_id integer not null,
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
