# -*- coding: utf-8 -*-

"""
WSGI config for transcrobes project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transcrobes.prod_settings')
import django
django.setup()

from django.contrib.auth.handlers.modwsgi import check_password
from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()
