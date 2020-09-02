# -*- coding: utf-8 -*-
import json
import pkgutil

from django.contrib.auth.models import User
from django.test import TestCase

from ankrobes import Ankrobes, InvalidNoteFields  # pylint: disable=E0611  # because pylint is dumb

# FIXME: there are some @staticmethods in the TestCase classes. This is likely just a copy/paste error and should be
# fixed


class AnkrobesTests(TestCase):
    databases = "__all__"
    USERNAME = "a_username"
    EMAIL = "a_email@transcrob.es"
    PASSWORD = "top_secret"

    ##
    ## Plumbing methods
    ##
    def setUp(self):
        # super().setUp()
        self.user = User.objects.create_user(
            username=AnkrobesTests.USERNAME, email=AnkrobesTests.EMAIL, password=AnkrobesTests.PASSWORD
        )

    def tearDown(self):
        # super().tearDown()
        self.user.delete()

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
        return json.loads(pkgutil.get_data("assets.ankrobes", "note.json").decode("utf-8"))

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

    def test_clean_inputs(self):
        # def clean_inputs(fields):
        """
        Ensure that the required fields are all present for adding a note in the right format
        """
        clean = json.loads(pkgutil.get_data("assets.ankrobes", "cleaned_note.json").decode("utf-8"))
        unclean = json.loads(pkgutil.get_data("assets.ankrobes", "uncleaned_note.json").decode("utf-8"))

        with Ankrobes(self.user.username) as userdb:
            cleaned = userdb.clean_inputs(unclean)

        self.assertEqual(clean, cleaned)

    def test_set_word_known(self):
        # def set_word_known(self, simplified, pinyin, meanings=[], tags=[], review_in=1):
        in_note = self._get_test_note(clean=True)

        expected_note = in_note.copy()
        expected_note["Is_Known"] = 1

        out_note = self._set_word_known_tester(1, in_note)
        self.assertEqual(expected_note, out_note)

    def test_set_word_known_no_review(self):
        in_note = self._get_test_note(clean=True)

        out_note = self._set_word_known_tester(-1, in_note)
        self.assertEqual(in_note, out_note)

    def test_add_ankrobes_note_ok(self):
        # def add_ankrobes_note(self, simplified, pinyin, meanings=[], tags=[], review_in=0):
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

    def test_get_word(self):
        # def get_word(self, word, deck_name='transcrobes'):
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

    def test_delete_note(self):
        # def delete_note(self, lword):
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

    def test_sanitise_ankrobes_entry(self):
        # def sanitise_ankrobes_entry(entries):

        ## original hanping-sourced entry
        # html in L2 only
        words = [
            {
                "Simplified": '<span class="cmn_tone4">看</span><span class="cmn_tone4">见</span>',
                "Pinyin": "kan4 jian4",
                "Meaning": "to see • to catch sight of",
                "Is_Known": 1,
                "Tags": ["ccfb", "hj14", "hsk1", "lesson29", "st23"],
            }
        ]
        cleaned_words = [
            {
                "Simplified": "看见",
                "Pinyin": "kan4 jian4",
                "Meaning": "to see • to catch sight of",
                "Is_Known": 1,
                "Tags": ["ccfb", "hj14", "hsk1", "lesson29", "st23"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), cleaned_words)

        # html in L2 and L1
        words = [
            {
                "Simplified": '<span class="cmn_tone3">母</span><span class="cmn_tone1">亲</span>',
                "Pinyin": "mu3 qin1",
                "Meaning": "mother • also pr.  (mǔ qin) • CL: <span class=chinese_word>個|个|ge4</span>",
                "Is_Known": 1,
                "Tags": ["ccfb", "hsk4", "lesson7", "st9"],
            }
        ]
        cleaned_words = [
            {
                "Simplified": "母亲",
                "Pinyin": "mu3 qin1",
                "Meaning": "mother • also pr.  (mǔ qin) • CL: 個|个|ge4",
                "Is_Known": 1,
                "Tags": ["ccfb", "hsk4", "lesson7", "st9"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), cleaned_words)

        ## cccedict-sourced entry
        words = [
            {"Simplified": "榴莲", "Pinyin": "liu2 lian2", "Meaning": "durian (fruit)", "Is_Known": 1, "Tags": ["class"]}
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

        ## abcdict-sourced entry
        words = [
            {
                "Simplified": "交通",
                "Pinyin": "jiāotōng",
                "Meaning": "(n.). traffic; communications; transportation, liaison (v.). be connected/linked, cross (of streets/etc.) (attr.). unobstructed",  # noqa: E501  # pylint: disable=C0301
                "Is_Known": 1,
                "Tags": ["ankrobes", "chromecrobes"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

        words = [
            {
                "Simplified": "眼",
                "Pinyin": "yǎn",
                "Meaning": "(NOUN). eyes, glance, sight, yan (ADJ). ocular, eyed, ophthalmic (1 char)",
                "Is_Known": 1,
                "Tags": ["ankrobes", "chromecrobes"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

        # 摄影 - manually entered
        words = [
            {
                "Simplified": "摄影",
                "Pinyin": "she4 ying3",
                "Meaning": "photography; to take a picture (bis4)",
                "Is_Known": 1,
                "Tags": ["hj25"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

        # 出租汽车 - manually entered '(4 chars)'
        words = [
            {
                "Simplified": "出租汽车",
                "Pinyin": "chu1 zu1 qi4 che1",
                "Meaning": "taxi (4 chars)",
                "Is_Known": 1,
                "Tags": ["st15"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

        # ...另一个... - manually entered expression
        words = [
            {
                "Simplified": "...另一个...",
                "Pinyin": "ling4 yi2 ge4 ",
                "Meaning": "...and the other is...",
                "Is_Known": 1,
                "Tags": ["class"],
            }
        ]
        self.assertEqual(Ankrobes.sanitise_ankrobes_entry(words), words)

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


# class AnkrobesViewTests(TestCase):
#     ##
#     ## Tests for public methods
#     ##
#
#     def test_add_note_chromecrobes(self):
#         # def test_add_note_chromecrobes(self):
#         # raise NotImplementedError
#         pass
#
#     def test_set_word_known(self):
#         # def test_set_word_known(self):
#         # raise NotImplementedError
#         pass
#
#     def test_set_word(self):
#         # def test_set_word(self):
#         # raise NotImplementedError
#         pass
