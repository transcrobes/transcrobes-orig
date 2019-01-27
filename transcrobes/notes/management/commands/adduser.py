from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
import getpass

import anki.consts
# MUST be set before importing anki.sync !!!!!!!
# anki.consts.SYNC_BASE = "https://ank.t.melser.org:5223/%s"
anki.consts.SYNC_BASE = settings.ANKROBES_ENDPOINT  # "http://{}/%s".format(sys.argv[1])

from anki.sync import RemoteServer
anki.sync.SYNC_BASE = anki.consts.SYNC_BASE


class Command(BaseCommand):
    help = 'Allows for normal user management'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        # parser.add_argument('password', nargs='+', type=str, help='Password for the new user')
        parser.add_argument('-p', '--password', type=str, help='Password for the new user')
        parser.add_argument('-e', '--email', type=str, help='Email for the new user')

    def handle(self, *args, **options):

        try:
            User.objects.get(username=options['username'])
        except Exception:
            pass  # User shouldn't exist
        else:
            raise CommandError('There is already a user with that username')
        username = options['username']
        password = None
        while password is None:
            password1 = getpass.getpass('Enter the user password: ')
            password2 = getpass.getpass('Password (again): ')
            if password1 != password2:
                self.stderr.write("Error: Your passwords didn't match.")
                # Don't validate passwords that don't match.
                continue
            if password1.strip() == '':
                self.stderr.write("Error: Blank passwords aren't allowed.")
                # Don't validate blank passwords.
                continue

            password = password2

        email = options['email'] if 'email' in options else ''
        try:
            user = User.objects.create_user(username, email, password)
        except:
            raise CommandError('There was an error creating the user, please check the username and try again')

        # Call the hostKey endpoint which will create the user-related database structures
        # This happens automatically when ankrobes is called (via Anki/Ankidroid + pg-ankysyncd)
        # but if a user uses one of the other clients before that, it will cause an error in
        # transcrobes, as transcrobes (now) accesses the database directly rather than going via
        # an ankrobes API
        try:
            server = RemoteServer(None, None)
            key = server.hostKey(username, password)
            server.meta()
        except:
            self.stdout.write("The user was created but there was an error initialising Ankrobes. "
                              "Try connecting with these credentials via Anki or Ankidroid to "
                              "finish initialisation")
        else:
            self.stdout.write(f"Successfully created new user {username}")

