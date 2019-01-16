# -*- coding: utf-8 -*-

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'enrich',
    'notes',
]

# TODO: FIXME: find out why csrf_exempt isn't working on the enrich view and re-enable CSRF!!!!!
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'transcrobes.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'transcrobes.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../static/')
LL = 'ERROR'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'enrich': {
            'handlers': ['console'],
            'level': LL,
            'propagate': False,
        },
        'enrich.translator': {
            'handlers': ['console'],
            'level': LL,
            'propagate': False,
        },
        'enrich.nlp': {
            'handlers': ['console'],
            'level': LL,
            'propagate': False,
        },
        'notes': {
            'handlers': ['console'],
            'level': LL,
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': LL,
            'propagate': False,
        },
    },
}

# The following values MUST be overriden here or in a prod_settings.py file
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'transcrobes',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'your_secret_key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# MUST be behind ssl proxy
ALLOWED_HOSTS = ['api.transcrobes.example.com']

# Enrich app config
ANKROBES_ENDPOINT = 'https://ankrobes.transcrobes.example.com:5223/%s'

BING_SUBSCRIPTION_KEY = 'your_subscription_key'

# From here the values are sensible and can be kept if desired

BING_API_HOST = 'api.cognitive.microsofttranslator.com'

CORENLP_URL = 'http://localhost:9000'
# depparse requires something like 2GB of RAM, tokenize,ssplit,pos together only 1GB
CORENLP_PARSE_PROPERTIES = '{"annotators":"tokenize,ssplit,pos","outputFormat":"json"}'

CCCEDICT_PATH = '/opt/transcrobes/cedict.txt'
ABCEDICT_PATH = '/opt/transcrobes/abcdict.txt'

# see http://www.hskhsk.com/word-lists.html
# data from http://data.hskhsk.com/lists/
# files renamed "HSK Official With Definitions 2012 L?.txt" ->  hsk?.txt
HSKDICT_PATH = '/opt/transcrobes/hsk{}.txt'

# see https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch
# following file adapted from subtlexch131210.zip, basically removed useless cedict translations
# and fixed incorrect pinyin 'ue:' -> 'u:e'
SUBLEX_FREQ_PATH = '/opt/transcrobes/subtlex-ch.utf8.txt'
