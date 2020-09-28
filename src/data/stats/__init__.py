# -*- coding: utf-8 -*-
import csv
import io


def update_db_userword(conn, data, temp_table):

    # FIXME: TODO: using CURRENT_TIMESTAMP instead of an app datetime was a STUPID idea! What about
    # events that live in the queue for a while and don't get processed for 30 minutes? 3h? 3d? !!!
    # While getting the datetime from js or python might be overkill (probably not!) at least moving
    # to the kafka event queue timestamp is a reasonable and light-weight solution

    # Get the data dictionary in CSV format, for easy/performant loading to the DB
    temp_file = io.StringIO()
    writer = csv.writer(temp_file, delimiter="\t")
    for user_id, words in data.items():
        for word, stats in words.items():
            word_id = None
            nb_seen = stats[0]
            nb_checked = stats[1]
            nb_seen_since_last_check = nb_seen if nb_checked else 0
            writer.writerow([user_id, word_id, word, nb_seen, nb_seen_since_last_check])

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
                    CURRENT_TIMESTAMP,
                    CASE WHEN tt.nb_seen_since_last_check = 0 THEN tt.nb_seen ELSE 0 END,
                    CASE WHEN tt.nb_seen_since_last_check = 0 THEN CURRENT_TIMESTAMP ELSE NULL END,
                    tt.user_id,
                    tt.word_id,
                    tt.nb_seen_since_last_check,
                    false
                    FROM {temp_table} tt
                ON CONFLICT (user_id, word_id)
                DO
                   UPDATE SET
                        nb_seen = data_userword.nb_seen + EXCLUDED.nb_seen,
                        last_seen = CURRENT_TIMESTAMP,
                        nb_checked = data_userword.nb_checked + CASE WHEN EXCLUDED.nb_seen_since_last_check = 0
                                                    THEN EXCLUDED.nb_seen
                                                    ELSE 0
                                                    END,
                        last_checked = CASE WHEN EXCLUDED.nb_seen_since_last_check = 0
                                        THEN CURRENT_TIMESTAMP
                                        ELSE data_userword.last_checked
                                        END,
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
                                        nb_seen_since_last_check integer null
                                        )"""
    with conn.cursor() as cur:
        cur.execute(TEMP_TABLE_CREATE)


def create_temp_table_usersentence(temp_table, conn):
    TEMP_TABLE_CREATE = f"""
        CREATE TEMP TABLE {temp_table} (user_id integer not null,
                                        word_id int null,
                                        word text not null,
                                        nb_seen integer not null,
                                        nb_seen_since_last_check integer null
                                        )"""
    with conn.cursor() as cur:
        cur.execute(TEMP_TABLE_CREATE)
