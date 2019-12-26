# -*- coding: utf-8 -*-

import json
import os
import tempfile

from django.conf import settings
from django.test import TestCase

from ankrobes import Ankrobes, InvalidNoteFields, dum

# FIXME: there are some @staticmethods in the TestCase classes. This is likely just a copy/paste error and should be
# fixed


class AnkrobesTests(TestCase):

    ##
    ## Plumbing methods
    ##
    def setUp(self):
        # FIXME: remember why you need the tempdirectory
        with tempfile.TemporaryDirectory() as _tmpdir:  # noqa:F841
            self.dum = dum.DjangoUserManager(settings.ANKISYNCD_CONFIG())
            self.user = self.dum.add_user(username="toto", email="toto@transcrob.es", password="top_secret")

    def tearDown(self):
        self.dum.del_user(self.user.username, keep_data=False)

    ##
    ## Helper methods
    ##

    def _set_word_known_tester(self, review_in, in_note):

        with Ankrobes(self.user.username) as userdb:
            userdb.set_word_known(
                simplified=in_note["Simplified"],
                pinyin=in_note["Pinyin"],
                meanings=[in_note["Meaning"]],
                tags=in_note["Tags"],
                review_in=review_in,
            )

        out_note = self._get_word(in_note["Simplified"])
        return out_note

    @staticmethod
    def _in_note():
        with open(os.path.join(settings.BASE_DIR, "ankrobes/test/assets/note.json"), "r") as note_file:
            return json.loads(note_file.read())

    # @staticmethod
    # def _cleaned_note():

    def _get_word(self, lword):
        with Ankrobes(self.user.username) as userdb:
            return userdb.get_word(lword)[0]

    def _clean_note(self, lword):
        with Ankrobes(self.user.username) as userdb:
            userdb.delete_note(lword)

    def _get_test_note(self, clean):
        in_note = self._in_note()
        if clean:
            self._clean_note(in_note["Simplified"])
        return in_note

    def _add_note(self, in_note):
        with Ankrobes(self.user.username) as userdb:
            note_id = userdb.add_ankrobes_note(
                simplified=in_note["Simplified"],
                pinyin=in_note["Pinyin"],
                meanings=[in_note["Meaning"]],
                tags=in_note["Tags"],
                review_in=0,
            )
        return note_id

    ##
    ## Tests for public methods
    ##

    # def _clean_inputs(fields):
    def test_clean_inputs(self):
        """
        Ensure that the required fields are all present for adding a note in the right format
        """
        with open(os.path.join(settings.BASE_DIR, "ankrobes/test/assets/cleaned_note.json"), "r") as note_file:
            clean = json.load(note_file)

        with open(os.path.join(settings.BASE_DIR, "ankrobes/test/assets/uncleaned_note.json"), "r") as note_file:
            unclean = json.load(note_file)

        with Ankrobes(self.user.username) as userdb:
            cleaned = userdb.clean_inputs(unclean)

        self.assertEqual(clean, cleaned)

    # def set_word_known(self, simplified, pinyin, meanings=[], tags=[], review_in=1):
    def test_set_word_known(self):
        in_note = self._get_test_note(clean=True)

        expected_note = in_note.copy()
        expected_note["Is_Known"] = 1

        out_note = self._set_word_known_tester(1, in_note)
        self.assertEqual(expected_note, out_note)

    def test_set_word_known_no_review(self):
        in_note = self._get_test_note(clean=True)

        out_note = self._set_word_known_tester(-1, in_note)
        self.assertEqual(in_note, out_note)

    # def add_ankrobes_note(self, simplified, pinyin, meanings=[], tags=[], review_in=0):
    def test_add_ankrobes_note_ok(self):
        in_note = self._get_test_note(clean=True)

        self._add_note(in_note)

        out_note = self._get_word(in_note["Simplified"])
        self.assertEqual(in_note, out_note)

    def test_add_ankrobes_note_missing_fields(self):
        """
        Ensure that the required fields are all present for adding a note
        """
        in_note = self._get_test_note(clean=True)

        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(Exception):
                userdb.add_ankrobes_note(
                    simplified="",
                    pinyin=in_note["Pinyin"],
                    meanings=[in_note["Meaning"]],
                    tags=in_note["Tags"],
                    review_in=0,
                )

        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(Exception):
                userdb.add_ankrobes_note(
                    simplified=in_note["Simplified"],
                    pinyin="",
                    meanings=[in_note["Meaning"]],
                    tags=in_note["Tags"],
                    review_in=0,
                )

        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(InvalidNoteFields):
                userdb.add_ankrobes_note(
                    simplified=in_note["Simplified"],
                    pinyin=in_note["Pinyin"],
                    meanings=[],
                    tags=in_note["Tags"],
                    review_in=0,
                )

    def test_set_word_known_missing_fields(self):
        """
        Ensure that the required fields are all present when updating a note
        """
        in_note = self._get_test_note(clean=True)
        self._add_note(in_note)
        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(Exception):
                userdb.set_word_known(
                    simplified="",
                    pinyin=in_note["Pinyin"],
                    meanings=[in_note["Meaning"]],
                    tags=in_note["Tags"],
                    review_in=1,
                )

        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(Exception):
                userdb.set_word_known(
                    simplified=in_note["Simplified"],
                    pinyin="",
                    meanings=[in_note["Meaning"]],
                    tags=in_note["Tags"],
                    review_in=1,
                )

        with Ankrobes(self.user.username) as userdb:
            with self.assertRaises(InvalidNoteFields):
                userdb.set_word_known(
                    simplified=in_note["Simplified"],
                    pinyin=in_note["Pinyin"],
                    meanings=[],
                    tags=in_note["Tags"],
                    review_in=1,
                )

    # def test_set_word_known_review_immediately(self):
    #     # FIXME: this should test that passing 0 for review_in resets the due date
    #     # to today. It should probably call the actual Anki scheduler to get the next
    #     # note so, say,
    #     # create_new_note -> check scheduled
    #     # review_new_note -> check nothing scheduled
    #     # set_word_known(review_in=0) -> check scheduled
    #     raise NotImplementedError

    # def close(self):
    def test_close(self):
        """
        Ensure that Ankrobes properly disposes of the db connection on close
        """

        # Test the context manager
        with Ankrobes(self.user.username) as userdb:
            self.assertIsNotNone(userdb.col.db)
        self.assertIsNone(userdb.col.db)

        # Test the close() method
        userdb = Ankrobes(self.user.username)
        self.assertIsNotNone(userdb.col.db)
        userdb.close()
        self.assertIsNone(userdb.col.db)

    # def get_word(self, word, deck_name='transcrobes'):
    def test_get_word(self):
        in_note = self._get_test_note(clean=True)

        # Look for a note that we know isn't there, it should be empty/falsey
        with Ankrobes(self.user.username) as userdb:
            empty_note = userdb.get_word(in_note["Simplified"])
        self.assertFalse(userdb.col.db)

        self.assertFalse(empty_note)

        # Add the note, now we should get it
        self._add_note(in_note)

        with Ankrobes(self.user.username) as userdb:
            out_note = userdb.get_word(in_note["Simplified"])[0]

        self.assertEqual(in_note, out_note)

    # def delete_note(self, lword):
    def test_delete_note(self):
        in_note = self._get_test_note(clean=True)

        # Look for a note that we know isn't there, it should be empty/falsey
        with Ankrobes(self.user.username) as userdb:
            empty_note = userdb.get_word(in_note["Simplified"])

        self.assertFalse(empty_note)

        # Add the note, now we should get it
        self._add_note(in_note)
        with Ankrobes(self.user.username) as userdb:
            out_note = userdb.get_word(in_note["Simplified"])[0]

        self.assertEqual(in_note, out_note)

        # Delete the note
        with Ankrobes(self.user.username) as userdb:
            userdb.delete_note(in_note["Simplified"])

        # Now it should be gone again
        with Ankrobes(self.user.username) as userdb:
            empty_note = userdb.get_word(in_note["Simplified"])

        self.assertFalse(empty_note)

    # # def delete_user(self, username):
    # def test_delete_user(self):
    #     raise NotImplementedError

    # FIXME: unused methods, delete
    # def is_known(self, token):
    # def test_is_known(self):
    #     raise NotImplementedError

    # FIXME: unused methods, delete
    # # def is_known_chars(self, token):
    # def test_is_known_chars(self):
    #     raise NotImplementedError

    ##
    ## Tests for private methods
    ##

    # # returns 0 if not known, the id of the note if you do
    # def _word_known_from_types(self, card_types):
    # # returns 0 if not known, the id of the note if you do
    # def _word_known(self, word, deck_name='transcrobes'):
    # def _search_regex(self, word):
    # def _cards(self, word, deck_name='transcrobes'):
    # def _card_types(self, word, deck_name='transcrobes'):
    # def _add_note(self, data, deck_name='transcrobes', review_in=0):
    # def _update_note(self, note_id, simplified, pinyin, meanings, tags, review_in=-1):
    # def _update_note_known(self, note_id, review_in):


class AnkrobesAddUserCommand(TestCase):
    ##
    ## Plumbing methods
    ##
    # def setUp(self):
    #     raise NotImplementedError

    # def tearDown(self):
    #     raise NotImplementedError

    ##
    ## Tests for public methods
    ##

    def test_add_user(self):
        # def test_add_user(self):
        raise NotImplementedError


class AnkrobesViewTests(TestCase):
    # def setUp(self):
    #     raise NotImplementedError

    # def tearDown(self):
    #     raise NotImplementedError

    ##
    ## Tests for public methods
    ##

    def test_add_note_chromecrobes(self):
        # def test_add_note_chromecrobes(self):
        raise NotImplementedError

    def test_set_word_known(self):
        # def test_set_word_known(self):
        raise NotImplementedError

    def test_set_word(self):
        # def test_set_word(self):
        raise NotImplementedError


class AnkiDataModelTests(TestCase):
    @staticmethod
    def test_generate_schema_sql(schema_name):
        # def generate_schema_sql(schema_name):
        raise NotImplementedError

    @staticmethod
    def test_insert_on_conflict_update(table_name):
        # def insert_on_conflict_update(table_name):
        raise NotImplementedError

    @staticmethod
    def test_insert_on_conflict_nothing(table_name):
        # def insert_on_conflict_nothing(table_name):
        raise NotImplementedError


class PGAnkisyncdTests(TestCase):
    def test_username_from_dbpath(self, _path):
        # def username_from_dbpath(path):
        raise NotImplementedError


class PostgresSqliteAdaptorTests(TestCase):
    @staticmethod
    def test_sqlite_sql_to_postgres(_sql):
        # def sqlite_sql_to_postgres(sql):
        raise NotImplementedError

    def test_fs(self, sql):
        # def fs(self, sql):
        raise NotImplementedError

    def test__conn(self, schema_name=None):
        # def _conn(self, schema_name=None):
        raise NotImplementedError

    def test__create_schema(self, schema_name=None, conn=None):
        # def _create_schema(self, schema_name=None, conn=None):
        raise NotImplementedError

    def test__db_table_exists(self, table_name, conn=None):
        # def _db_table_exists(self, table_name, conn=None):
        raise NotImplementedError


class PostgresCollectionWrapperTests(TestCase):
    def test_open(self):
        # def open(self):
        raise NotImplementedError

    def test__schema_exists(self, schema_name):
        # def _schema_exists(self, schema_name):
        raise NotImplementedError

    def test__get_collection(self, lock=True, log=False):
        # def _get_collection(self, lock=True, log=False):
        raise NotImplementedError

    def test_delete(self):
        # def delete(self):
        raise NotImplementedError


class PostgresCollectionTests(TestCase):
    def test_reopen(self):
        # def reopen(self):
        raise NotImplementedError


class PostgresDBTests(TestCase):
    def test___init__(self, _config, path, username, timeout=1):
        # def __init__(self, _config, path, username, timeout=1):
        raise NotImplementedError


class EfficientConnectionTests(TestCase):
    def test_execute(self, sql, *a, **ka):
        # def execute(self, sql, *a, **ka):
        raise NotImplementedError

    def test_executemany(self, _sql, _li):
        # def executemany(self, sql, l):
        raise NotImplementedError

    def test_executescript(self, sql):
        # def executescript(self, sql):
        raise NotImplementedError


class PostgresPersistenceManagerTests(TestCase):
    @staticmethod
    def test__check_sqlite3_db(db_path):
        # def _check_sqlite3_db(db_path):
        raise NotImplementedError

    def test_upload(self, col, data, session):
        # def upload(self, col, data, session):
        raise NotImplementedError

    def test_download(self, col, session):
        # def download(self, col, session):
        raise NotImplementedError

    def test__create_empty_sqlite3_db(self):
        # def _create_empty_sqlite3_db(self):
        raise NotImplementedError

    def test_create_pg_schema(self, schema_name):
        # def create_pg_schema(self, schema_name):
        raise NotImplementedError

    def test_delete_pg_schema(self, schema_name):
        # def delete_pg_schema(self, schema_name):
        raise NotImplementedError

    def test_execute_sql_script(self, script_name, schema_name=None):
        # def execute_sql_script(self, script_name, schema_name=None):
        raise NotImplementedError

    def test_execute_sql(self, sql, schema_name=None):
        # def execute_sql(self, sql, schema_name=None):
        raise NotImplementedError


class PostgresSessionManagerTests(TestCase):
    def test__conn(self):
        # def _conn(self):
        raise NotImplementedError

    def test_save(self, hkey, session):
        # def save(self, hkey, session):
        raise NotImplementedError


class PostgresUserManagerTests(TestCase):
    def test_auth_db_exists(self):
        # def auth_db_exists(self):
        raise NotImplementedError

    def test__conn(self):
        # def _conn(self):
        raise NotImplementedError


class DjangoUserManagerTests(TestCase):
    def test_authenticate(self, username, password):
        # def authenticate(self, username, password):
        raise NotImplementedError

    def test_add_user(self, username, password, email):
        # def add_user(self, username, password, email):
        raise NotImplementedError

    def test_del_user(self, username, keep_data=False):
        # def del_user(self, username, keep_data=False):
        raise NotImplementedError
