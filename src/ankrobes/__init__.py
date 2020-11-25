# -*- coding: utf-8 -*-
import logging
import re

from django.conf import settings
from django.utils.html import strip_tags
from djankiserv.unki.collection import Collection

logger = logging.getLogger(__name__)


class InvalidNoteFields(Exception):
    pass


class Ankrobes:
    ##
    ## Static methods
    ##

    @staticmethod
    def sanitise_ankrobes_entry(entries):
        # we don't need the HTML here - we'll put the proper html back in later
        for entry in entries:
            entry["Simplified"] = re.sub("(?:<[^>]+>)*", "", entry["Simplified"], flags=re.MULTILINE)
            entry["Pinyin"] = re.sub("(?:<[^>]+>)*", "", entry["Pinyin"], flags=re.MULTILINE)
            entry["Meaning"] = re.sub("(?:<[^>]+>)*", "", entry["Meaning"], flags=re.MULTILINE)
        return entries

    ##
    ## instance methods
    ##

    def __init__(self, username):
        self._username = username
        self.col = Collection(self._username, settings.DJANKISERV_DATA_ROOT)

    def __enter__(self):
        """Context manager __enter__"""
        return self

    def __exit__(self, _type, value, traceback):
        """Context manager __exit__"""
        self.col.close()

    def __del__(self):
        """Close the collection if not already closed."""
        self.col.close()

    def delete_note(self, lword):
        cards = self._cards(lword)
        if cards:  # else nothing to do
            self.col.rem_cards(list(cards.keys()))

    def close(self):
        # Close the DB connection so other threads can lock it for the
        # user in question
        self.col.close()

    @staticmethod
    def clean_inputs(fields):
        simplified = fields["Simplified"]
        # TODO: make sure we have only one pinyin format - either 'là' or 'la4', not both!
        pinyin = fields["Pinyin"].strip(" ()")

        # TODO: this should support multiple meanings
        regex = r"(?:<style>.*</style>)"  # While using ODH - they force including css at the start of meanings...
        result = re.sub(regex, "", fields["Meaning"], 0, re.MULTILINE | re.DOTALL)
        # TODO: add my own (Hanping compatible???) tags here after stripping the existing entry stuff
        meanings = [strip_tags(result).strip()]

        tags = sorted(list(set(["chromecrobes"] + (fields["Tags"] if "Tags" in fields else []))))

        return {
            "simplified": simplified,
            "pinyin": pinyin,
            "meanings": meanings,
            "tags": tags,
        }

    # returns 0 if not known, the id of the note if you do
    @staticmethod
    def _word_known_from_types(card_types):

        known = 0

        # FIXME: this doesn't deal with suspended/filtered new cards...
        # TODO: for the moment we just assume that if you know one definition of a word you "know it"
        for note_id, card_type in card_types.items():
            if not (0 in list(card_type.keys()) and len(list(card_type.keys())) == 1):
                return note_id  # if we don't only have new cards you "know it"

        return known

    # returns 0 if not known, the id of the note if it is
    def _word_known(self, word, deck_name="transcrobes"):
        card_types = self._card_types(word, deck_name)

        return self._word_known_from_types(card_types)

    def get_word(self, word, deck_name="transcrobes"):
        card_types = self._card_types(word, deck_name)
        if not card_types:  # is not in anki
            # NOT for here
            return {}

        json_notes = []
        for note_id, card_states in card_types.items():
            note = self.col.get_note(note_id=note_id)

            is_known = 0 if 0 in card_states and len(card_states) == 1 else 1

            json_note = {
                "Simplified": note.fields[0],
                "Pinyin": note.fields[1],
                "Meaning": note.fields[2],
                "Is_Known": is_known,
                "Tags": note.tags,
            }
            json_notes.append(json_note)

        return json_notes

    def _cards(self, word, deck_name="transcrobes"):
        logging.debug("Looking for card ids for word '%s'", word)

        sql = f"""
        SELECT card_id, note_id, type from {self._username}.user_vocabulary
            WHERE word = %(word)s
        """
        res = self.col.db.execute(sql, deck_name=deck_name, word=word)
        j = res.fetchall()
        if not j:
            return {}

        # The system knows it
        card_ids = {}
        for row in j:
            # card_types[row['card_id']] = {row['note_id']: row['type']}
            card_ids[row[0]] = {row[1]: row[2]}

        return card_ids

    def _card_types(self, word, deck_name="transcrobes"):
        logging.debug("Looking for card types for word '%s'", word)
        sql = f"""
        SELECT count(0) as icount, note_id, type from {self._username}.user_vocabulary
            WHERE word = %(word)s
            GROUP BY note_id, type
        """

        res = self.col.db.execute(sql, deck_name=deck_name, word=word)
        j = res.fetchall()
        if not j:
            return {}  # or maybe {0, {0: 0}}  # System doesn't know it at all

        # The system knows it
        card_types = {}
        for row in j:
            # card_types[row['note_id']] = {row['type']: row['icount']}
            card_types[row[1]] = {row[2]: row[0]}

        return card_types

    # TODO: This should be more intelligent
    def add_ankrobes_note(self, simplified, pinyin, meanings, tags=[], review_in=0):  # pylint: disable=W0102
        if not simplified or not pinyin or not meanings:
            raise InvalidNoteFields("You must supply a value for simplified, pinyin and meanings")

        if "ankrobes" not in tags:
            tags.append("ankrobes")
        data = {
            "model": "transcrobes",
            "fields": [simplified, pinyin, "¤".join(meanings)],
            # "fields": {"Simplified": simplified, "Pinyin": pinyin, "Meaning": "¤".join(meanings)},
            "tags": tags,
        }

        return self.col.create_note(note_json=data, deck_name="transcrobes", review_in=review_in)

    def set_word_known(self, simplified, pinyin, meanings=[], tags=[], review_in=1):  # pylint: disable=W0102
        if not simplified or not pinyin or not meanings:
            raise InvalidNoteFields("You must supply a value for simplified, pinyin and meanings")

        card_types = self._card_types(simplified)
        if not card_types:
            self.add_ankrobes_note(simplified, pinyin, meanings=meanings, tags=tags, review_in=review_in)
        else:
            for note_id in list(card_types.keys()):
                self._update_note(note_id, simplified, pinyin, meanings, tags, review_in)

        return {"result": "Ok"}

    def _update_note(self, note_id, simplified, pinyin, meanings, tags, review_in=-1):
        # FIXME: not using review_in yet

        note = self.col.get_note(note_id=note_id)

        note["Simplified"] = simplified
        note["Pinyin"] = pinyin
        note["Meaning"] = "¤".join(meanings)

        for tag in tags:
            note.tags.append(tag)

        note.flush()
        self.col.save()  # FIXME: Find a better way to unlock the db

        if review_in >= 0:  # if review_in not -1, update
            self.col.set_note_review_in(note_id, review_in)
