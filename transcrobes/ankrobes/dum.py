# -*- coding: utf-8 -*-
import os

from ankisyncd.users import SimpleUserManager
from django.contrib import auth

from ankrobes.models import Transcrober
from ankrobes.pgankisyncd import PostgresCollectionWrapper


class DjangoUserManager(SimpleUserManager):
    """Authenticate against an existing Django database."""

    def __init__(self, config):
        self._conf = config
        SimpleUserManager.__init__(self, config["data_root"])

    def authenticate(self, username, password):
        """
        Returns True if this username is allowed to connect with this password.
        False otherwise.
        """
        user = auth.authenticate(username=username, password=password)
        return bool(user)  # None if auth fails

    def add_user(self, username, password, email, from_lang="zh-Hans", to_lang="en"):
        try:
            auth.models.User.objects.get(username=username)
        except auth.models.User.DoesNotExist:
            pass  # User shouldn't exist
        else:
            raise Exception("There is already a user with that username or you have " "entered an invalid username")

        t = Transcrober()
        t.from_lang = from_lang
        t.to_lang = to_lang
        t.user = auth.models.User.objects.create_user(username, email, password)
        t.save()

        col = PostgresCollectionWrapper(self._conf, os.path.join(self.collection_path, username, "collection.anki2"))
        col.open()  # TODO: creates the user schema if it doesn't exist, this should be cleaner

        return t.user

    def del_user(self, username, keep_data=False):

        user = auth.models.User.objects.get(username=username)
        user.delete()

        if not keep_data:
            col = PostgresCollectionWrapper(
                self._conf, os.path.join(self.collection_path, username, "collection.anki2")
            )
            col.delete()  # deletes the user schema, if it exists
            ## FIXME:
            ## This needs to be implemented but can't be until common storage is implemented
            ## so currently any media files for deleted users will be orphaned
            ##
            # shutil.rmtree(self.userdir(username), ignore_errors=True)
