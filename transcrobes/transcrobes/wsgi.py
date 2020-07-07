# -*- coding: utf-8 -*-
# noqa
# fmt: off
# pylint: skip-file
# flake8: noqa
# WARNING!!! DO NOT allow any reordering of imports here!!! all orderings are EXACTLY how the MUST BE!!!

"""
WSGI config for transcrobes project.
"""

import os  # isort:skip
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transcrobes.settings.container')
import django  # isort:skip
django.setup()

from django_wsgi.handler import DjangoApplication  # isort:skip
application = DjangoApplication()
