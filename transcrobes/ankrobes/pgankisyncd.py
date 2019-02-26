# -*- coding: utf-8 -*-

import os
import re
import sys
import abc
import time
import copy
import pkgutil
import logging
import tempfile
import datetime
from pathlib import Path
from sqlite3 import dbapi2 as sqlite

import psycopg2
import psycopg2.extras

from django.conf import settings

# See https://www.sqlite.org/datatype3.html
# All Anki's numeric column types are `INT`, meaning that their "affinity"
# will always be `INT`. This *appears* to mean that the return values of all functions, like
# `sum(left/1000)...` will be interpreted as `int` by the sql driver, and get an `int` object.
# psycopg2 tries to be intelligent and returns `Decimal`, meaning many things
# that expect `int` (such as serialising `dict`) will fail. Here we tell
# psycopg2 to use `int` and keep compatibility with up-upstream
DEC2INT = psycopg2.extensions.new_type(
        psycopg2.extensions.DECIMAL.values,
        'DEC2INT',
        lambda value, curs: int(value) if value is not None else None)
psycopg2.extensions.register_type(DEC2INT)

from anki.consts import SCHEMA_VERSION
import anki.db as ankidb
from anki.models import ModelManager
from anki.media import MediaManager
from anki.decks import DeckManager
from anki.tags import TagManager
from anki.collection import _Collection
import anki.storage
from anki.utils import intTime, json
from anki.stdmodels import addBasicModel, addClozeModel, addForwardReverse, \
    addForwardOptionalReverse, addBasicTypingModel

# from ankisyncd import config as conf
from ankisyncd.persistence import PersistenceManager
from ankisyncd.sessions import SqliteSessionManager, SimpleSessionManager
from ankisyncd.persistence import PersistenceManager
from ankisyncd.collection import CollectionManager, CollectionWrapper
from ankisyncd.users import SqliteUserManager, SimpleUserManager


# This class is the source of truth for the Anki data model. It is used
# for various SQL generation purposes, such as creating schemas, query
# rewrites and getting all the tables for sqlite -> pg and pg -> sqlite
# import/export
class AnkiDataModel:

    MODEL_SETUP = """
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_with_oids = false;"""

    CREATE_SCHEMA = 'CREATE SCHEMA {schema_name};'
    VERSION = 11
    COLLECTION_PARENT_DB = 'collection'
    MEDIA_PARENT_DB = 'media'

    # is_pk gives a primary key constraint and an identity sequence, currently
    # only supports single
    MODEL = {
        'notes':
        { 'fields' : [
            { 'name': 'id', 'type': 'bigint', 'is_pk': True },
            { 'name': 'guid', 'type': 'text' },
            { 'name': 'mid', 'type': 'bigint' },
            { 'name': 'mod', 'type': 'bigint' },
            { 'name': 'usn', 'type': 'bigint' },
            { 'name': 'tags', 'type': 'text' },
            { 'name': 'flds', 'type': 'text' },
            { 'name': 'sfld', 'type': 'text' },  # WARNING! This is an `integer` in sqlite but contains text...
            { 'name': 'csum', 'type': 'text' },
            { 'name': 'flags', 'type': 'bigint' },
            { 'name': 'data', 'type': 'text' },
        ], 'indexes': [
            { 'name': 'ix_notes_csum', 'fields': ['csum'] },
            { 'name': 'ix_notes_usn', 'fields': ['usn'] },
        ], 'parent': COLLECTION_PARENT_DB,
        },
        'cards':
        { 'fields' : [
            { 'name': 'id', 'type': 'bigint', 'is_pk': True },
            { 'name': 'nid', 'type': 'bigint' },
            { 'name': 'did', 'type': 'bigint' },
            { 'name': 'ord', 'type': 'bigint' },
            { 'name': 'mod', 'type': 'bigint' },
            { 'name': 'usn', 'type': 'bigint' },
            { 'name': 'type', 'type': 'bigint' },
            { 'name': 'queue', 'type': 'bigint' },
            { 'name': 'due', 'type': 'bigint' },
            { 'name': 'ivl', 'type': 'bigint' },
            { 'name': 'factor', 'type': 'bigint' },
            { 'name': 'reps', 'type': 'bigint' },
            { 'name': 'lapses', 'type': 'bigint' },
            { 'name': '"left"', 'type': 'bigint' },
            { 'name': 'odue', 'type': 'bigint' },
            { 'name': 'odid', 'type': 'bigint' },
            { 'name': 'flags', 'type': 'bigint' },
            { 'name': 'data', 'type': 'text' },
        ], 'indexes': [
            { 'name': 'ix_cards_nid', 'fields': ['nid'] },
            { 'name': 'ix_cards_sched', 'fields': ['did', 'queue', 'due'] },
            { 'name': 'ix_cards_usn', 'fields': ['usn'] },
        ], 'parent': COLLECTION_PARENT_DB,
        },
        'col':
        { 'fields' : [
            { 'name': 'id', 'type': 'bigint', 'is_pk': True },
            { 'name': 'crt', 'type': 'bigint' },
            { 'name': 'mod', 'type': 'bigint' },
            { 'name': 'scm', 'type': 'bigint' },
            { 'name': 'ver', 'type': 'bigint' },
            { 'name': 'dty', 'type': 'bigint' },
            { 'name': 'usn', 'type': 'bigint' },
            { 'name': 'ls', 'type': 'bigint' },
            { 'name': 'conf', 'type': 'text' },
            { 'name': 'models', 'type': 'text' },
            { 'name': 'decks', 'type': 'text' },
            { 'name': 'dconf', 'type': 'text' },
            { 'name': 'tags', 'type': 'text' },
        ], 'indexes': [
        ], 'parent': COLLECTION_PARENT_DB,
        },
        'graves':
        { 'fields' : [
            { 'name': 'usn', 'type': 'bigint' },
            { 'name': 'oid', 'type': 'bigint' },
            { 'name': 'type', 'type': 'bigint' },
        ], 'indexes': [
        ], 'parent': COLLECTION_PARENT_DB,
        },
        'revlog':
        { 'fields' : [
            { 'name': 'id', 'type': 'bigint', 'is_pk': True },
            { 'name': 'cid', 'type': 'bigint' },
            { 'name': 'usn', 'type': 'bigint' },
            { 'name': 'ease', 'type': 'bigint' },
            { 'name': 'ivl', 'type': 'bigint' },
            { 'name': 'lastivl', 'type': 'bigint' },
            { 'name': 'factor', 'type': 'bigint' },
            { 'name': 'time', 'type': 'bigint' },
            { 'name': 'type', 'type': 'bigint' },
        ], 'indexes': [
            { 'name': 'ix_revlog_cid', 'fields': ['cid'] },
            { 'name': 'ix_revlog_usn', 'fields': ['usn'] },
        ], 'parent': COLLECTION_PARENT_DB,
        },
        'media':
        { 'fields' : [
            { 'name': 'fname', 'type': 'text', 'is_pk': True },
            { 'name': 'csum', 'type': 'text', 'nullable': True },
            { 'name': 'mtime', 'type': 'bigint' },
            { 'name': 'dirty', 'type': 'bigint' },
         ], 'indexes': [
            { 'name': 'ix_media_dirty', 'fields': ['dirty'] },
        ], 'parent': MEDIA_PARENT_DB,
        },
        'meta':
        { 'fields' : [
            { 'name': 'dirmod', 'type': 'bigint' },
            { 'name': 'lastusn', 'type': 'bigint' },
         ], 'indexes': [
         ], 'parent': MEDIA_PARENT_DB,
            'initsql': 'insert into {schema_name}.meta values (0, 0);'
        },
    }

    @staticmethod
    def generate_schema_sql(schema_name):
        sql = AnkiDataModel.MODEL_SETUP + AnkiDataModel.CREATE_SCHEMA.format(schema_name=schema_name)

        for table_name, defin in AnkiDataModel.MODEL.items():
            tsql = f"CREATE TABLE {schema_name}.{table_name} (" + \
                ",".join([f"{f['name']} {f['type']} {'' if f.get('nullable') else 'NOT'} NULL" for f in defin['fields']]) + \
                ");"
            identity = [ x['name'] for x in defin['fields'] if 'is_pk' in x and x['type'] == 'bigint' ]
            if identity:
                tsql += f"""
                ALTER TABLE {schema_name}.{table_name}
                    ALTER COLUMN {identity[0]} ADD GENERATED BY DEFAULT AS IDENTITY (
                        SEQUENCE NAME {schema_name}.{table_name}_{identity[0]}_seq
                        START WITH 1
                        INCREMENT BY 1
                        NO MINVALUE
                        NO MAXVALUE
                        CACHE 1
                    );"""

            pk = [ x['name'] for x in defin['fields'] if 'is_pk' in x ]
            if pk:
                tsql += f"""
                ALTER TABLE ONLY {schema_name}.{table_name}
                    ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ({pk[0]});"""

            for i in defin['indexes']:
                tsql += f"CREATE INDEX {i['name']} ON {schema_name}.{table_name} USING btree (" + \
                ",".join([f for f in i['fields']]) + \
                ");"

            if 'initsql' in defin:
                tsql += defin['initsql'].replace('{schema_name}', schema_name)  # dynamic replace rather than fstring

            sql += tsql
        sql += f"SELECT {AnkiDataModel.VERSION};"

        return sql

    @staticmethod
    def insert_on_conflict_update(table_name):

        identity = [ x['name'] for x in AnkiDataModel.MODEL[table_name]['fields'] if 'is_pk' in x ]
        fstr = ', '.join(['%s'] * len(AnkiDataModel.MODEL[table_name]['fields']))
        return f"INSERT INTO {table_name} (" + \
            ",".join([f"{f['name']}" for f in AnkiDataModel.MODEL[table_name]['fields']]) + \
            f") VALUES ({fstr}) " + \
            f"ON CONFLICT ({identity[0]}) DO UPDATE SET " + \
            ",".join([f"{f['name']} = EXCLUDED.{f['name']}" for f in AnkiDataModel.MODEL[table_name]['fields'] if 'is_pk' not in f])


    @staticmethod
    def insert_on_conflict_nothing(table_name):

        identity = [ x['name'] for x in AnkiDataModel.MODEL[table_name]['fields'] if 'is_pk' in x ]
        fstr = ', '.join(['%s'] * len(AnkiDataModel.MODEL[table_name]['fields']))

        return f"INSERT INTO {table_name} (" + \
            ",".join([f"{f['name']}" for f in AnkiDataModel.MODEL[table_name]['fields']]) + \
            f") VALUES ({fstr}) " + \
            f"ON CONFLICT ({identity[0]}) DO NOTHING "


def username_from_dbpath(path):
    return os.path.basename(os.path.dirname(path))

class PostgresSqliteAdaptor(metaclass=abc.ABCMeta):
    ADMIN_SCHEMA = 'assadmin'
    INSERT_OR_IGNORE = re.compile('\s*insert or ignore into (\w+) ', re.IGNORECASE)
    INSERT_OR_REPLACE = re.compile('\s*insert or replace into (\w+) ', re.IGNORECASE)

    @abc.abstractmethod
    def _schema_name(self):
        pass

    @abc.abstractmethod
    def _config(self):
        pass

    # Clean sqlite3 syntax to psycopg2
    @staticmethod
    def sqlite_sql_to_postgres(sql):
        # replace all newlines with spaces so regexps work on multiline strings
        # I still haven't worked out how to do multiline searches without using `search()`...
        tmp = " ".join(sql.split())

        logging.debug(f'Converting SQL : {sql}')
        # Complete replacements
        insert_or_ignore = PostgresSqliteAdaptor.INSERT_OR_IGNORE.match(tmp)
        if insert_or_ignore and insert_or_ignore.group(1):  # captures the table name
            logging.debug('Found insert or ignore, generating SQL')
            return AnkiDataModel.insert_on_conflict_nothing(insert_or_ignore.group(1))

        insert_or_replace = PostgresSqliteAdaptor.INSERT_OR_REPLACE.match(tmp)
        if insert_or_replace and insert_or_replace.group(1):  # captures the table name
            logging.debug('Found insert or update, generating SQL')
            return AnkiDataModel.insert_on_conflict_update(insert_or_replace.group(1))

        # Change bits of the query
        tmp = sql.replace('?', '%s')  # use posgres style params

        tmp = re.sub(r"count\(\)", "count(0)", tmp, flags=re.I)  # use proper count syntax
        tmp = re.sub(r" id in \(\)", " id in (0)", tmp, flags=re.I)  # use equivalent syntax - ids can't be 0

        # Add name for subqueries as postgres requires this for select from subquery
        # if ' as subq' has already been added, don't add again
        if re.search(r'select.*from\s*\(.*select.*from.*\)', tmp, re.I | re.S) and ' as subq' not in tmp:
            tmp = tmp + ' as subq '

        # replace instances of the column `left` with postgres-compliant `"left"`
        # there may be more of these but this is conservative and won't ever
        # match a `left join`. At Anki v2.8 there is only one `left join`, which is
        # written as `left outer join` but that may change so here we are defensive
        tmp = re.sub("(?i), left,", ', "left",', tmp)
        tmp = re.sub("(?i) sum\(\s*left\s*/\s*1000\s*\)", ' sum("left"/1000)', tmp)
        tmp = re.sub("(?i)select left from ", 'select "left" from ', tmp)
        tmp = re.sub("(?i)left            integer not null", '"left"            integer not null', tmp)

        logging.debug(f'SQL converted to : {tmp}')
        return tmp

    def fs(self, sql):
        return self.sqlite_sql_to_postgres(sql)

    def _conn(self, schema_name=None):
        if not schema_name:
            schema_name = self._schema_name()
        return psycopg2.connect(connection_factory=EfficientConnection, dbname=self._config()['db_name'],
                                user=self._config()['db_user'], host=self._config()['db_host'],
                                password=self._config()['db_password'],
                                options=f'-c search_path={schema_name}')

    def _create_schema(self, schema_name=None, conn=None):
        schema_name = schema_name or self._schema_name()
        lconn = conn or self._conn()

        with lconn.cursor() as cur:
            dsn_params = lconn.get_dsn_parameters()  # should we use self._config() to get these values?
            logging.info(f"Creating {schema_name} schema on db {dsn_params['dbname']} on host "
                         f"{dsn_params['host']}.")
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            conn.commit()

        if not conn: lconn.close()  # close the connection if we created a new one

    def _db_table_exists(self, table_name, conn=None):
        lconn = conn or self._conn()

        with lconn.cursor() as cursor:
            param = (self._schema_name(), table_name,)
            sql = f"""SELECT 1
                        FROM   information_schema.tables
                        WHERE  table_schema = %s
                        AND    table_name = %s"""

            cursor.execute(sql, param)
            exists = cursor.fetchone()

        if not conn: lconn.close()  # close the connection if we created a new one
        return bool(exists)


class PostgresCollectionWrapper(PostgresSqliteAdaptor, CollectionWrapper):
    # override CollectionWrapper
    def __init__(self, _config, path, setup_new_collection=None):
        self._conf = settings.ANKISYNCD_CONFIG()
        self.path = os.path.realpath(path)
        self._username = username_from_dbpath(self.path)
        self.setup_new_collection = setup_new_collection
        self._CollectionWrapper__col = None  # Pure nastiness :(

    # override CollectionWrapper
    def open(self):
        """Open the collection, or create it if it doesn't exist."""
        if self._CollectionWrapper__col is None:
            if self._schema_exists(self._username):
                self._CollectionWrapper__col = self._get_collection()
            else:
                self._CollectionWrapper__col = self._CollectionWrapper__create_collection()  # more nastiness :(

    # override PostgresSqliteAdaptor
    def _schema_name(self):
        return self._username

    # override PostgresSqliteAdaptor
    def _config(self):
        return self._conf

    def _schema_exists(self, schema_name):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = %s", (schema_name,))
                res = cur.fetchone()
        return res


    def _get_collection(self, lock=True, log=False):
        # The logic here adapted from anki.storage.Collection()
        # def Collection(path, lock=True, server=False, log=False):

        # INFO! The collection lock opens an update cursor `update col set mod = mod`
        # so that no other client can update. It is nowhere near a proper lock
        # but is probably better than nothing...
        # - The first issue is that the other tables *can* be updated
        # - The second is that ankisyncd doesn't release the collection lock until
        # the thread is killed due to inactivity. This might be intentional, a ticket
        # asking for clarification needs to be created!

        # This is a horrible hack - the upstream-upstream code has ripped out
        # the server logic and we are reduced to fudging in lots of places
        is_server = False

        "Open a new or existing collection. Path must be unicode."
        # TODO: the path is still used in many places, for example, for getting
        # the username. We should eventually try and remove it but that will
        # require total test coverage.
        path = os.path.abspath(self.path)
        assert path.endswith(".anki2")
        username = self._username
        create = not self._schema_exists(username)
        if create:
            # FIXME: this was originally a test for the validity of directory of the collection.anki2 file
            # We need whatever is put to be able to be used as a Postgres schema.
            # The following will likely not be perfect, but will hopely avoid any SQL injection, and
            # creation will fail rather than introduce a vulnerability
            # for c in ("/", ":", "\\"):
            #     assert c not in username
            assert username.isidentifier()

        # connect
        db = PostgresDB(self._conf, path, username)
        # db.setAutocommit(True)
        pm = PostgresPersistenceManager(self._conf)
        if create:
            ver = pm.create_pg_schema(username)
            # create the tables because they already exist
            db.execute(AnkiDataModel.insert_on_conflict_nothing('col'),
                       1,0,0,anki.storage.intTime(1000),
                        anki.storage.SCHEMA_VERSION,0,0,0,'','{}','','','{}')

            anki.storage._addColVars(db, *anki.storage._getColVars(db))
        else:
            ver = anki.storage._upgradeSchema(db)
        # db.setAutocommit(False)
        # add db to col and do any remaining upgrades
        col = PostgresCollection(db, is_server, log)
        if ver < SCHEMA_VERSION:
            anki.storage._upgrade(col, ver)
        elif ver > SCHEMA_VERSION:
            raise Exception("This database requires a newer version of Anki Sync Server.")
        elif create:
            # FIXME: this will fail because we don't set default values
            # use the default Anki values
            # add in reverse order so basic is default
            addClozeModel(col)
            addBasicTypingModel(col)
            addForwardOptionalReverse(col)
            addForwardReverse(col)
            addBasicModel(col)
            col.save()
            if "collection_init" in self._conf:
                col.close()
                package, sqlfile = self._conf["collection_init"].split(',')
                # print('the package is {package}, the sqlfile is {sqlfile}')
                sql = pkgutil.get_data(package, sqlfile).decode("utf-8")

                pm.execute_sql(sql, username)
                col.reopen()

        if lock:
            col.lock()
        return col

    def delete(self):
        if not self._schema_exists(self._username):
            return  # TODO: nothing to do, or maybe raise an Exception?

        pm = PostgresPersistenceManager(self._conf)
        pm.delete_pg_schema(self._username)

class PostgresMediaManager(MediaManager):

    # override MediaManager
    def connect(self):
        if self.col.server:
            return
        path = self.dir()+".db2"
        create = not os.path.exists(path)
        os.chdir(self._dir)
        self.db = self.col.db  # we can just reuse the existing connection as the tables are in the user schema
        # if create:
        #     self._initDB()
        # self.maybeUpgrade()

    # override MediaManager
    def _initDB(self):
        # Not needed, we do this at user-creation time
        pass

    # override MediaManager
    def maybeUpgrade(self):
        # FIXME: this is weird
        """
        The upstream code contains SQL from 2014 that appears to contain references to a table that
        is never created. It is wrapped in a try/except so won't actually raise an error for
        the user so I'm going to assume it is just cruft that was never cleaned
        """
        pass

    # override MediaManager
    def close(self):
        if self.col.server:
            return

        # We don't close the DB connection as we are using the parents connection
        # self.db.close()
        self.db = None
        # change cwd back to old location
        if self._oldcwd:
            try:
                os.chdir(self._oldcwd)
            except:
                # may have been deleted
                pass

    # override MediaManager
    def _deleteDB(self):
        self.db.execute("truncate table media")
        self.db.execute("update meta set lastUsn=0,dirMod=0")
        self.db.commit()

        self.close()
        self.connect()

    def forceResync(self):
        self._deleteDB()  # because we have no file to delete, this is the same


class PostgresCollection(_Collection):

    # override _Collection
    def __init__(self, db, server=False, log=False):
        self._debugLog = log
        self.db = db
        self.path = db._path
        self._openLog()
        self.log(self.path, anki.version)
        self.server = server
        self._lastSave = time.time()
        self.clearUndo()
        self.media = PostgresMediaManager(self, server)
        self.models = ModelManager(self)
        self.decks = DeckManager(self)
        self.tags = TagManager(self)
        self.load()
        if not self.crt:
            d = datetime.datetime.today()
            d -= datetime.timedelta(hours=4)
            d = datetime.datetime(d.year, d.month, d.day)
            d += datetime.timedelta(hours=4)
            self.crt = int(time.mktime(d.timetuple()))
        self._loadScheduler()
        if not self.conf.get("newBury", False):
            self.conf['newBury'] = True
            self.setMod()

    # override _Collection
    def reopen(self):
        "Reconnect to DB (after changing threads, etc)."

        if not self.db:
            self.db = PostgresDB(settings.ANKISYNCD_CONFIG(), self.path, username_from_dbpath(self.path))
            self.media.connect()
            self._openLog()


class PostgresDB(PostgresSqliteAdaptor, ankidb.DB):
    # override PostgresSqliteAdaptor
    def _schema_name(self):
        return self._username

    # override PostgresSqliteAdaptor
    def _config(self):
        return self._conf

    # override
    def __init__(self, _config, path, username, timeout=1):
        self._conf = settings.ANKISYNCD_CONFIG()
        self._username = username
        self._db = self._conn()

        # FIXME: do we get invalid utf-8?
        # self._db.text_factory = self._textFactory
        self._path = path
        self.echo = os.environ.get("DBECHO")
        self.mod = False

    # override
    def setAutocommit(self, autocommit):
        # self._db.autocommit = autocommit
        # FIXME: behaviour is different between sqlite and psycopg2
        pass

# Because Anki is "efficient" :-(
# https://docs.python.org/3/library/sqlite3.html#using-sqlite3-efficiently
# std connection with sqlite3's execute/executemany/executescript extensions for psycopg2
# and some adaption so they can accept sql strings meant for sqlite3 (eg, replacing '?' with '%s', ignoring pragma)
class EfficientConnection(psycopg2.extensions.connection):
    def execute(self, sql, *a, **ka):
        # This is a nonstandard shortcut that creates a cursor object by calling the cursor() method,
        # calls the cursor’s execute() method with the parameters given, and returns the cursor.
        cur = self.cursor()
        # TODO: Can we just ignore all of these?
        if "pragma " in sql:
            cur.execute("select 'ok'")
            return cur
        # print(self.get_dsn_parameters())
        if ka:
            # execute("...where id = :id", id=5)
            cur.execute(PostgresSqliteAdaptor.sqlite_sql_to_postgres(sql), ka)
        else:
            # execute("...where id = ?", 5)
            cur.execute(PostgresSqliteAdaptor.sqlite_sql_to_postgres(sql), *a)
        return cur

    def executemany(self, sql, l):
        # This is a nonstandard shortcut that creates a cursor object by calling the cursor() method,
        # calls the cursor’s executemany() method with the parameters given, and returns the cursor.
        cur = self.cursor()

        cur.executemany(PostgresSqliteAdaptor.sqlite_sql_to_postgres(sql), l)
        return cur

    def executescript(self, sql):
        # This is a nonstandard shortcut that creates a cursor object by calling the cursor() method,
        # calls the cursor’s execute() method with the given sql_script, and returns the cursor.
        cur = self.cursor()
        cur.execute(PostgresSqliteAdaptor.sqlite_sql_to_postgres(sql))
        return cur


class PostgresPersistenceManager(PostgresSqliteAdaptor, PersistenceManager):
    # TODO, maybe make this from config or an envvar
    pg_select_cursor_size = 10000  # this has no effect on memory and less than 1k significantly increases the time
    pg_insert_cursor_size = 10000  # this has no effect on memory and less than 1k significantly increases the time

    # override PostgresSqliteAdaptor
    def _schema_name(self):
        return self._username

    # override PostgresSqliteAdaptor
    def _config(self):
        return self._conf

    def __init__(self, _config):
        PersistenceManager.__init__(self)
        self._conf = settings.ANKISYNCD_CONFIG()
        self._username = None  # How should we manage this?

    @staticmethod
    def _check_sqlite3_db(db_path):
        try:
            with anki.db.DB(db_path) as test_db:
                if test_db.scalar("pragma integrity_check") != "ok":
                    raise HTTPBadRequest("Integrity check failed for uploaded "
                                         "collection database file.")
        except sqlite.Error as e:
            raise HTTPBadRequest("Uploaded collection database file is "
                                 "corrupt.")

    def upload(self, col, data, session):
        # from sqlite to postgres
        self._username = session.name

        # write data to a tempfile
        with tempfile.NamedTemporaryFile(suffix='.anki2', delete=False) as f:
            temp_db_path = f.name
            f.write(data)

        # Verify integrity of the received database file before replacing our
        # existing db.
        self._check_sqlite3_db(temp_db_path)

        # create new schema in pg db that we'll fill with the new data
        timestamp = str(time.time()).replace('.', '_')
        tmp_schema_name = f"{self._username}_{timestamp}"
        self.create_pg_schema(tmp_schema_name)

        # close the coll to remove the db lock
        col.close()

        # should maybe create a global transaction here?
        # same issue as https://github.com/tsudoko/anki-sync-server/issues/6
        with self._conn() as pg_conn, sqlite.connect(temp_db_path) as sqlite_conn:
            pg_conn.autocommit = False
            with pg_conn.cursor() as to_pg_cursor:
                for table, props in AnkiDataModel.MODEL.items():
                    if props['parent'] != AnkiDataModel.COLLECTION_PARENT_DB: continue

                    start_sqlite_cursor = sqlite_conn.cursor()
                    start_sqlite_cursor.execute(f"SELECT * FROM {table}")
                    while True:
                        current_data = start_sqlite_cursor.fetchmany(self.pg_insert_cursor_size)
                        if not current_data:
                            break
                        psycopg2.extras.execute_values (
                            to_pg_cursor, f"INSERT INTO {tmp_schema_name}.{table} VALUES %s", current_data
                        )
                    start_sqlite_cursor.close()

                # rename the existing schema, rename the new schema to the username, delete the old schema
                to_pg_cursor.execute(f"ALTER SCHEMA {self._username} RENAME TO {tmp_schema_name}_old")
                to_pg_cursor.execute(f"ALTER SCHEMA {tmp_schema_name} RENAME TO {self._username}")
                to_pg_cursor.execute(f"DROP SCHEMA {tmp_schema_name}_old CASCADE")
                pg_conn.commit()

            os.remove(temp_db_path)

        # reopen the collection to get another lock
        col.reopen()
        col.load()

        return "OK"

    def download(self, col, session):

        self._username = session.name
        col.close()

        # try:

        download_db = self._create_empty_sqlite3_db()
        # should maybe create a global transaction here?
        # same issue as https://github.com/tsudoko/anki-sync-server/issues/6
        with sqlite.connect(download_db) as sqlite_conn, self._conn() as pg_conn:
            for table, props in AnkiDataModel.MODEL.items():
                if props['parent'] != AnkiDataModel.COLLECTION_PARENT_DB: continue

                with pg_conn.cursor() as from_pg_cursor:
                    to_sqlite_cursor = sqlite_conn.cursor()  # can't use `with` with an sqlite3 cursor
                    from_pg_cursor.execute(f"SELECT * FROM {self._username}.{table}")
                    while True:
                        current_data = from_pg_cursor.fetchmany(self.pg_select_cursor_size)
                        if not current_data:
                            break
                        cols = ','.join(['?'] * len(current_data[0]))
                        # TODO: executemany has terrible performance but whatever
                        to_sqlite_cursor.executemany(f"INSERT INTO {table} VALUES ({cols})",
                                                     current_data)

                    to_sqlite_cursor.close()

        self._check_sqlite3_db(download_db)
        data = open(download_db, 'rb').read()
        os.remove(download_db)

        # finally:
        col.reopen()
        col.load()

        return data


    # using anki's own methods for empty db creation
    def _create_empty_sqlite3_db(self):
        # we need to get a tmp filename where the file doesn't exist, or we can't use anki.storage.Collection
        # to create it
        tmp = tempfile.mktemp(suffix='.anki2')
        anki.storage.Collection(tmp).close()  # will create and close cleanly
        # clean up the rows added in up-upstream db initialisation and leave only the schema
        with sqlite.connect(tmp) as conn:
            cur = conn.cursor()  # can't use `with` with an sqlite3 cursor
            cur.execute("DELETE FROM col")
            cur.close()

        return tmp

    def create_pg_schema(self, schema_name):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(AnkiDataModel.generate_schema_sql(schema_name))
                res = cur.fetchone()
                return res[0]

    def delete_pg_schema(self, schema_name):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP SCHEMA {schema_name} CASCADE')

    # FIXME: there shouldn't be any sql scripts, it should all be done via classes, like
    # in up-upstream
    def execute_sql_script(self, script_name, schema_name=None):
        # This is pure postgres sql, so no need for adapting. The sql has the placeholder {schema_name}
        # that gets replaced with schema_name
        sql = Path(script_name).read_text()

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.replace('{schema_name}', schema_name) if schema_name else sql)
                res = cur.fetchone()
                conn.commit()
                return res[0]

    def execute_sql(self, sql, schema_name=None):
        with self._conn() as conn:
            with conn.cursor() as cur:
                repl = sql.replace('{schema_name}', schema_name)
                cur.execute(repl if schema_name else sql)
                res = cur.fetchone()
                conn.commit()
                return res[0]


# To avoid the Diamond of Death, make sure PostgresSqliteAdaptor comes first :-)
class PostgresSessionManager(PostgresSqliteAdaptor, SqliteSessionManager):
    """Stores sessions in a Postgres database to prevent the user from being logged out
    everytime the SyncApp is restarted."""
    TABLENAME = 'session'

    # override PostgresSqliteAdaptor
    def _schema_name(self):
        return self.ADMIN_SCHEMA

    # override PostgresSqliteAdaptor
    def _config(self):
        return self._conf

    def __init__(self, config):
        SimpleSessionManager.__init__(self)
        self._conf = settings.ANKISYNCD_CONFIG()

    # multiple inheritance joys! This overrides PostgresSqliteAdaptor._conn() which overrides
    # SqliteSessionManager._conn() :-)
    def _conn(self):
        conn = PostgresSqliteAdaptor._conn(self)
        with conn.cursor() as cursor:
            exists = self._db_table_exists(self.TABLENAME, conn)
            if not exists:
                self._create_schema(conn=conn)
                # FIXME: how is tablename defined???
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.TABLENAME} (hkey VARCHAR PRIMARY KEY,"
                               "skey VARCHAR, username VARCHAR, path VARCHAR)")
                conn.commit()
        return conn

    # sqlite3 added support for postgres-compatible upsert (see below) in version 3.24 but
    # that is far too new, and postgres doesn't support `insert into or replace`, so
    # we need to override here
    # FIXME: A system to override the SQL directly (see AnkiDataModel) was created
    # This should be reproduced for session and auth
    def save(self, hkey, session):
        SimpleSessionManager.save(self, hkey, session)

        with self._conn() as conn:
            with conn.cursor() as cursor:

                cursor.execute(self.fs("""INSERT INTO session (hkey, skey, username, path) VALUES (?, ?, ?, ?)
                                            ON CONFLICT (hkey)
                                            DO UPDATE SET
                                            (skey, username, path)
                                                = (EXCLUDED.skey, EXCLUDED.username, EXCLUDED.path)
                                       """),
                    (hkey, session.skey, session.name, session.path))

            conn.commit()


# To avoid the Diamond of Death, make sure PostgresSqliteAdaptor comes first :-)
class PostgresUserManager(PostgresSqliteAdaptor, SqliteUserManager):
    TABLENAME = 'auth'

    def __init__(self, config):
        self._conf = settings.ANKISYNCD_CONFIG()
        SimpleUserManager.__init__(self, self._conf["data_root"])
        self.auth_db_path = ''  # this is used in a log message in SqliteUserManager...

    # override PostgresSqliteAdaptor
    def _config(self):
        return self._conf

    # override PostgresSqliteAdaptor
    def _schema_name(self):
        return self.ADMIN_SCHEMA

    # override SqliteUserManager
    def auth_db_exists(self):
        return bool(self._db_table_exists(self.TABLENAME))

    # override SqliteUserManager
    def create_auth_db(self, conn=None):
        # this is done automatically in the connection
        pass

    # multiple inheritance joys! This overrides PostgresSqliteAdaptor._conn() which overrides
    # SqliteUserManager._conn() :-)
    def _conn(self):
        conn = PostgresSqliteAdaptor._conn(self)
        with conn.cursor() as cursor:
            exists = self._db_table_exists(self.TABLENAME, conn)
            if not exists:
                self._create_schema(conn=conn)
                cursor.execute(self.fs(f"CREATE TABLE IF NOT EXISTS {self.TABLENAME} "
                          f"(username VARCHAR PRIMARY KEY, hash VARCHAR)"))
                conn.commit()
        return conn

