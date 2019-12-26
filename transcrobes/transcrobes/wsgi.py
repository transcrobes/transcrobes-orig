# -*- coding: utf-8 -*-

"""
WSGI config for transcrobes project.
"""

import os

import django
from django_wsgi.handler import DjangoApplication

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "transcrobes.settings.container")

django.setup()


application = DjangoApplication()
