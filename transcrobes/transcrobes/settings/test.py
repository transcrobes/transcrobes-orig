# -*- coding: utf-8 -*-

from .base import *
import logging
logging.disable(os.getenv('DJANGO_LOG_LEVEL') or logging.INFO)

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
ALLOWED_HOSTS = [os.getenv('TRANSCROBES_PUBLIC_HOST') or '*']

# Enrich app config
ANKROBES_ENDPOINT = 'https://{}/%s'.format(os.getenv('ANKROBES_HOST'))

BING_SUBSCRIPTION_KEY = os.getenv('BING_SUBSCRIPTION_KEY')

CORENLP_URL = "http://{}".format(os.getenv('CORENLP_HOST'))
