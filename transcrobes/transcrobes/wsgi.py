# -*- coding: utf-8 -*-

"""
WSGI config for transcrobes project.
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transcrobes.settings.container')
import django
django.setup()

from django_wsgi.handler import DjangoApplication
application = DjangoApplication()
