# -*- coding: utf-8 -*-

import getpass
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand

from ankrobes.dum import DjangoUserManager


class Command(BaseCommand):
    help = "Allows for normal user management"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username for the new user")
        # parser.add_argument('password', nargs='+', type=str, help='Password for the new user')
        parser.add_argument("-p", "--password", type=str, help="Password for the new user")
        parser.add_argument("-e", "--email", type=str, help="Email for the new user")
        parser.add_argument("-f", "--from_lang", type=str, default="zh-Hans", help="L2 - learning language")
        parser.add_argument("-t", "--to_lang", type=str, default="en", help="L1 - native(ish) language")

    def handle(self, *args, **options):

        username = options["username"]
        from_lang = options["from_lang"]
        to_lang = options["to_lang"]
        password = options["password"] if "password" in options else None
        while not password:
            password1 = getpass.getpass("Enter the user password: ")
            password2 = getpass.getpass("Password (again): ")
            if password1 != password2:
                self.stderr.write("Error: Your passwords didn't match.")
                # Don't validate passwords that don't match.
                continue
            if password1.strip() == "":
                self.stderr.write("Error: Blank passwords aren't allowed.")
                # Don't validate blank passwords.
                continue

            password = password2

        email = options["email"] if "email" in options else ""

        # FIXME: remember why I need to use tempfile.TemporaryDirectory
        with tempfile.TemporaryDirectory() as _tmpdir:  # noqa:F841
            try:
                duman = DjangoUserManager(settings.ANKISYNCD_CONFIG())
                duman.add_user(username=username, email=email, password=password, from_lang=from_lang, to_lang=to_lang)
            except Exception:
                self.stdout.write(
                    "There was an error creating the user, make sure you have entered a valid "
                    "username, password and email (if provided)"
                )
                raise
            else:
                self.stdout.write(f"Successfully created new user {username}")
