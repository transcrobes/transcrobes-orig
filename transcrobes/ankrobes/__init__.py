# -*- coding: utf-8 -*-

import os
import re
import json
import logging

from django.conf import settings
from django.utils.html import strip_tags

import ankrobes.pgankisyncd

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
            entry['Simplified'] = re.sub("(?:<[^>]+>)*", '', entry['Simplified'], flags=re.MULTILINE)
            entry['Pinyin'] = re.sub("(?:<[^>]+>)*", '', entry['Pinyin'], flags=re.MULTILINE)
            entry['Meaning'] = re.sub("(?:<[^>]+>)*", '', entry['Meaning'], flags=re.MULTILINE)
        return entries

    ##
    ## instance methods
    ##

    def __init__(self, username):
        # For the moment just using a new, manual collection to make sure
        # we set the appropriate search_path for postgres to not need the
        # user schema_name in queries

        # FIXME: find a better solution for the tmpdir and something less
        # bad for the *hopefully* unused `collection_init`
        self.config = settings.ANKISYNCD_CONFIG()
        self._username = username

        path = f"fake/{self._username}/collection.anki2"
        db = pgankisyncd.PostgresDB(self.config, path, self._username)
        self.col = pgankisyncd.PostgresCollection(db, True)

    def __enter__(self):
        """Context manager __enter__"""
        return self

    def __exit__(self, type, value, traceback):
        """Context manager __exit__"""
        self.col.close()

    def __del__(self):
        """Close the collection if not already closed."""
        self.col.close()

    def delete_note(self, lword):
        cards = self._cards(lword)
        if cards:  # else nothing to do
            self.col.remCards(list(cards.keys()))

    def delete_user(self, username):
        # FIXME:
        # This can only reasonably (currently) be done via an API call
        # as there may be cruft on the Ankrobes-Server - namely the
        # media. When that is migrated to common storage, this can
        # be implemented
        raise NotImplementedError

    def close(self):
        # Close the DB connection so other threads can lock it for the
        # user in question
        self.col.close()

    def clean_inputs(self, fields):
        simplified = fields['Simplified']
        # TODO: make sure we have only one pinyin format - either 'là' or 'la4', not both!
        pinyin = fields['Pinyin'].strip(' ()')

        # TODO: this should support multiple meanings
        regex = r"(?:<style>.*</style>)"  # While using ODH - they force including css at the start of meanings...
        result = re.sub(regex, '', fields['Meaning'], 0, re.MULTILINE | re.DOTALL)
        # TODO: add my own (Hanping compatible???) tags here after stripping the existing entry stuff
        meanings = [strip_tags(result).strip()]

        tags = ['chromecrobes'] + (fields['Tags'] if 'Tags' in fields else [])

        return { 'simplified': simplified,
                'pinyin': pinyin,
                'meanings': meanings,
                'tags': tags,
                }

    # copied from old
    # FIXME: Unused, delete me!
    # def is_known(self, token):
    #     # TODO: This method should take into account the POS but we'll need to implement that in Anki somehow
    #     # a tag is probably the logical solution
    #     return self.is_known_chars(token)

    # def is_known_chars(self, token):
    #     return self._word_known(token['word'])

    # returns 0 if not known, the id of the note if you do
    def _word_known_from_types(self, card_types):

        known = 0

        # FIXME: this doesn't deal with suspended/filtered new cards...
        # TODO: for the moment we just assume that if you know one definition of a word you "know it"
        for note_id, card_type in card_types.items():
            if not (0 in list(card_type.keys()) and len(list(card_type.keys())) == 1):
                return note_id  # if we don't only have new cards you "know it"

        return known

    # returns 0 if not known, the id of the note if it is
    def _word_known(self, word, deck_name='transcrobes'):
        card_types = self._card_types(word, deck_name)

        return self._word_known_from_types(card_types)

    def get_word(self, word, deck_name='transcrobes'):
        card_types = self._card_types(word, deck_name)
        if card_types: # is in anki
            json_notes = []
            for note_id, card_states in card_types.items():
                note = self.col.getNote(id=note_id)

                is_known = 0 if 0 in list(card_states.keys()) and len(list(card_states.keys())) == 1 else 1

                json_note = {
                    'Simplified': note.fields[0],
                    'Pinyin': note.fields[1],
                    'Meaning': note.fields[2],
                    'Is_Known': is_known,
                    'Tags': note.tags,
                }
                json_notes.append(json_note)

            return json_notes
        else:
            # NOT for here
            return {}

    def _search_regex(self, word):
        # construct a regexp that will match words mixed in with html
        regexp = '^(?:<[^>]+>)*'
        for i in word:
            regexp += "{}(?:<[^>]+>)*".format(i)
        regexp += '$'
        return regexp

    def _cards(self, word, deck_name='transcrobes'):
        logging.debug("Looking for card ids for word '{}'".format(word))

        regexp = self._search_regex(word)

        sql = """
        SELECT c.id as card_id, n.id as note_id, c.type as type
            FROM json_each((SELECT decks FROM col)::json) a
                INNER JOIN cards c on c.did = a.key::bigint
                INNER JOIN notes n on c.nid = n.id
            WHERE json_extract_path_text(a.value, 'name') = %(deck_name)s
                AND substring(n.flds from 0 for position(chr(31) in n.flds)) ~* %(regexp)s
            """

        res = self.col.db.execute(sql, deck_name=deck_name, regexp=regexp)
        j = res.fetchall()
        if not j:
            return {}

        # The system knows it
        card_ids = {}
        for row in j:
            # card_types[row['card_id']] = {row['note_id']: row['type']}
            card_ids[row[0]] = {row[1]: row[2]}

        return card_ids

    def _card_types(self, word, deck_name='transcrobes'):
        logging.debug("Looking for card types for word '{}'".format(word))

        # construct a regexp that will match words mixed in with html
        regexp = self._search_regex(word)

        sql = """
        SELECT count(0) as icount, n.id as note_id, c.type as type
            FROM json_each((SELECT decks FROM col)::json) a
                INNER JOIN cards c on c.did = a.key::bigint
                INNER JOIN notes n on c.nid = n.id
            WHERE json_extract_path_text(a.value, 'name') = %(deck_name)s
                AND substring(n.flds from 0 for position(chr(31) in n.flds)) ~* %(regexp)s
            GROUP BY n.id, c.type;"""
        # print(self.col.db._conn().get_dsn_parameters())
        res = self.col.db.execute(sql, deck_name=deck_name, regexp=regexp)
        j = res.fetchall()
        if not j:
            return {}  # or maybe {0, {0: 0}}  # System doesn't know it at all

        # The system knows it
        card_types = {}
        for row in j:
            # card_types[row['note_id']] = {row['type']: row['icount']}
            card_types[row[1]] = {row[2]: row[0]}

        return card_types

    def _add_note(self, data, deck_name='transcrobes', review_in=0):
        from anki.notes import Note

        model = self.col.models.byName(data['model'])
        self.col.models.setCurrent(model)

        # Creates or reuses deck with name passed using `deck_name`
        did = self.col.decks.id(deck_name)
        deck = self.col.decks.get(did)

        note = self.col.newNote()
        myid = note.id
        note.model()['did'] = did

        for name, value in data['fields'].items():
            note[name] = value

        for tag in data['tags']:
            if tag.strip():
                note.addTag(tag)

        if myid:
            note.id = myid
        self.col.addNote(note)
        self.col.save()

        # We can't use the "proper" client code anymore since the sync code now only really supports clients
        # and we are half-client, half-server with the add_notes
        # required since a83e68412d176b8c91419888a5b6220fe8d5b2e6
        minUsn = self.col._usn

        if review_in > 0:
            self._update_note_known(note.id, review_in)

        return note.id


    # TODO: This should be more intelligent
    def add_ankrobes_note(self, simplified, pinyin, meanings, tags=[], review_in=0):
        if not simplified or not pinyin or not meanings:
            raise InvalidNoteFields('You must supply a value for simplified, pinyin and meanings')

        if not 'ankrobes' in tags:
            tags.append('ankrobes')
        data = {
            'model': 'transcrobes',
            'fields': {
                'Simplified': simplified,
                'Pinyin': pinyin,
                'Meaning': "¤".join(meanings),
            },
            'tags': tags,
        }

        return self._add_note(data, deck_name='transcrobes', review_in=review_in)

    def set_word_known(self, simplified, pinyin, meanings=[], tags=[], review_in=1):
        if not simplified or not pinyin or not meanings:
            raise InvalidNoteFields('You must supply a value for simplified, pinyin and meanings')

        card_types = self._card_types(simplified)
        if not card_types:
            self.add_ankrobes_note(simplified, pinyin, meanings=meanings, tags=tags, review_in=review_in)
        else:
            for note_id in list(card_types.keys()):
                self._update_note(note_id, simplified, pinyin, meanings, tags, review_in)
                if review_in >= 0:  # if review_in not -1, update
                    self._update_note_known(note_id, review_in)

        return {"result": "Ok"}

    def _update_note(self, note_id, simplified, pinyin, meanings, tags, review_in=-1):
        # FIXME: not using review_in yet

        note = self.col.getNote(id=note_id)

        note['Simplified'] = simplified
        note['Pinyin'] = pinyin
        note['Meaning'] = "¤".join(meanings)

        for tag in tags:
            note.addTag(tag)

        note.flush()
        self.col.save()  # FIXME: Find a better way to unlock the db

    def _update_note_known(self, note_id, review_in):
        import datetime
        import time

        note = self.col.getNote(id=note_id)

        # see https://github.com/ankidroid/Anki-Android/wiki/Database-Structure
        # for more details of ids
        # type            integer not null,
        #   -- 0=new, 1=learning, 2=due, 3=filtered
        # queue           integer not null,
        #   -- -3=sched buried, -2=user buried, -1=suspended,
        #   -- 0=new, 1=learning, 2=due (as for type)
        #   -- 3=in learning, next rev in at least a day after the previous review
        # due             integer not null,
        #  -- Due is used differently for different card types:
        #  --   new: note id or random int
        #  --   due: integer day, relative to the collection's creation time
        #  --   learning: integer timestamp
        # odue            integer not null,
        #   -- original due: only used when the card is currently in filtered deck
        # odid            integer not null,
        #   -- original did: only used when the card is currently in filtered deck

        # TODO: we should also be able to add definitions from the UI

        # TODO: decide what to do about:
        # factor
        # ivl
        # filtered cards

        # FIXME: this may be way too dumb to actually work - I am assuming this will work not
        # only for cards that are for reviewing in the future but also new and learning cards
        # and that is just a blind guess! There may well be other fields/things that need to
        # be modified in addition to factor, ivl and filtered cards
        today = int((time.time() - self.col.crt) // 86400)
        due = today + review_in
        for card in note.cards():
            if card.type == 3:
                raise Exception("We don't know what to do with filtered cards yet, come back soon")

            card.type = 2
            card.queue = 2
            card.due = due
            card.flush()

        self.col.save()  # FIXME: Find a better way to unlock the db
