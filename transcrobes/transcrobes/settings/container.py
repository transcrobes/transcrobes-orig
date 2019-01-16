# -*- coding: utf-8 -*-

import logging

from .base import *


if os.getenv('DJANGO_LOG_LEVEL'):
    logging.disable(os.getenv('DJANGO_LOG_LEVEL'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DATABASE'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT', 5432),
    }
}

# MUST be behind ssl proxy
# FIXME - remove the 'or'
ALLOWED_HOSTS = ' '.join(os.getenv('TRANSCROBES_PUBLIC_HOSTS').split(',')).split() or ['*']

# Enrich app config
ANKROBES_ENDPOINT = 'http://{}/%s'.format(os.getenv('TRANSCROBES_ANKROBES_HOST'))

BING_SUBSCRIPTION_KEY = os.getenv('TRANSCROBES_BING_SUBSCRIPTION_KEY')

CORENLP_URL = "http://{}".format(os.getenv('TRANSCROBES_CORENLP_HOST'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('TRANSCROBES_SECRET_KEY') or 'not_a_very_good_secret'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('TRANSCROBES_DEBUG') or False

CCCEDICT_PATH = os.getenv('TRANSCROBES_CCCEDICT_PATH') or '/opt/transcrobes/cedict.txt'
ABCEDICT_PATH = os.getenv('TRANSCROBES_ABCEDICT_PATH') or '/opt/transcrobes/abcdict.txt'

# see http://www.hskhsk.com/word-lists.html
# data from http://data.hskhsk.com/lists/
# files renamed "HSK Official With Definitions 2012 L?.txt" ->  hsk?.txt
HSKDICT_PATH = os.getenv('TRANSCROBES_HSKDICT_PATH') or '/opt/transcrobes/hsk{}.txt'

# see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch
# following file adapted from subtlexch131210.zip, basically removed useless cedict translations
# and fixed incorrect pinyin 'ue:' -> 'u:e'
SUBLEX_FREQ_PATH = os.getenv('TRANSCROBES_SUBLEX_FREQ_PATH') or '/opt/transcrobes/subtlex-ch.utf8.txt'
