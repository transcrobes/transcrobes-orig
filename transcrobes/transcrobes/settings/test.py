# -*- coding: utf-8 -*-

from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tc_db',
        'USER': 'tc_user',
        'PASSWORD': 'tc_pass',
        'HOST': 'db',
        'PORT': '5432',
    }
}
