# -*- coding: utf-8 -*-

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "enrich",
    "ankrobes",
    "en_zhhans",
    "zhhans_en",
    "enrichers",
    "accounts.apps.AccountsConfig",  # new
    "data.apps.DataConfig",
]


INSTALLED_APPS += ["bootstrapform", "survey"]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}
CORS_ORIGIN_ALLOW_ALL = True  # TODO: think about restricting this

# TODO: fix the csrf thing - is this fixed now???
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "transcrobes.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# In order for anki-sync-server to be served this must be the
# django_wsgi.handler NOT the normal handler
# Warning, this is ignored/unused when running via gunicorn, so
# it must be specified directly in the gunicorn wsgi.py file
WSGI_APPLICATION = "django_wsgi.handler.APPLICATION"
# WSGI_APPLICATION = 'transcrobes.wsgi.application'


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

USER_CACHE_TIMEOUT = 5  # seconds

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../static/")
LL = "ERROR"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "loggers": {
        "django": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
        "enrich": {"handlers": ["console"], "level": LL, "propagate": False},
        "enrich.translator": {"handlers": ["console"], "level": LL, "propagate": False},
        "enrich.nlp": {"handlers": ["console"], "level": LL, "propagate": False},
        "notes": {"handlers": ["console"], "level": LL, "propagate": False},
        "": {"handlers": ["console"], "level": LL, "propagate": False},
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "transcrobes",
        "USER": "your_user",
        "PASSWORD": "your_password",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "your_secret_key"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# MUST be behind ssl proxy
ALLOWED_HOSTS = ["api.transcrobes.example.com"]

ANKROBES_DATA_ROOT = "/tmp"

# From here the values are sensible and can be kept if desired


def ANKISYNCD_CONFIG():
    # PGANKISYNCD_CONFIG
    from django.db import connection  # pylint: disable=C0415

    global ANKROBES_DATA_ROOT  # pylint: disable=W0603
    return {
        "data_root": ANKROBES_DATA_ROOT,
        "base_url": "/sync/",
        "base_media_url": "/msync/",
        "full_sync_manager": "ankrobes.pgankisyncd.PostgresFullSyncManager",
        "session_manager": "ankrobes.pgankisyncd.PostgresSessionManager",
        "user_manager": "ankrobes.dum.DjangoUserManager",
        "collection_wrapper": "ankrobes.pgankisyncd.PostgresCollectionWrapper",
        "collection_init": "ankrobes.resources.sql,ankrobes.sql",
        "db_host": connection.settings_dict["HOST"],
        "db_port": connection.settings_dict["PORT"],
        "db_name": connection.settings_dict["NAME"],
        "db_user": connection.settings_dict["USER"],
        "db_password": connection.settings_dict["PASSWORD"],
    }


LANG_PAIRS = {
    "zh-Hans:en": {
        "enrich": {"classname": "enrichers.zhhans.CoreNLP_ZHHANS_Enricher", "config": {}},
        "parse": {
            "classname": "enrich.parse.HTTPCoreNLPProvider",
            "config": {"base_url": "http://localhost:9000", "params": '{"annotators":"lemma","outputFormat":"json"}'},
        },
        "word_lemmatizer": {"classname": "enrich.lemmatize.no_op.NoOpWordLemmatizer", "config": {}},
        "default": {
            "classname": "enrich.translate.bing.BingTranslator",
            "config": {
                "from": "zh-Hans",
                "to": "en",
                "api_host": "api.cognitive.microsofttranslator.com",
                "api_key": "a_super_api_key",
            },
            "transliterator": {
                "classname": "enrich.transliterate.bing.BingTransliterator",
                "config": {
                    "from": "zh-Hans",
                    "to": "en",
                    "from_script": "Hans",
                    "to_script": "Latn",
                    "api_host": "api.cognitive.microsofttranslator.com",
                    "api_key": "a_super_api_key",
                },
            },
        },
        "secondary": [
            {
                "classname": "zhhans_en.translate.ccc.ZHHANS_EN_CCCedictTranslator",
                "config": {"path": "/opt/transcrobes/cedict.txt", "inmem": True},
            },
            {
                "classname": "zhhans_en.translate.abc.ZHHANS_EN_ABCDictTranslator",
                "config": {"path": "/opt/transcrobes/abc_zh_en_dict.txt", "inmem": True},
            },
        ],
        "metadata": [
            {
                "classname": "enrichers.zhhans.metadata.hsk.ZH_HSKMetadata",
                "config": {"path": "/opt/transcrobes/hsk{}.txt", "inmem": True},
            },
            {
                "classname": "enrichers.zhhans.metadata.subtlex.ZH_SubtlexMetadata",
                "config": {"path": "/opt/transcrobes/subtlex-ch.utf8.txt", "inmem": True},
            },
        ],
        "transliterate": {
            "classname": "enrich.transliterate.bing.BingTransliterator",
            "config": {
                "from": "zh-Hans",
                "to": "en",
                "from_script": "Hans",
                "to_script": "Latn",
                "api_host": "api.cognitive.microsofttranslator.com",
                "api_key": "a_super_api_key",
            },
        },
    },
    "en:zh-Hans": {
        "enrich": {"classname": "enrichers.en.CoreNLP_EN_Enricher", "config": {}},
        "parse": {
            "classname": "enrich.parse.HTTPCoreNLPProvider",
            "config": {"base_url": "http://localhost:9001", "params": '{"annotators":"lemma","outputFormat":"json"}'},
        },
        "word_lemmatizer": {
            "classname": "enrichers.en.SpaCy_EN_WordLemmatizer",
            "config": {
                # 'model_name': 'en_core_web_sm',  # Not currently used
            },
        },
        "default": {
            "classname": "enrich.translate.bing.BingTranslator",
            "config": {
                "from": "en",
                "to": "zh-Hans",
                "api_host": "api.cognitive.microsofttranslator.com",
                "api_key": "a_super_api_key",
            },
            "transliterator": {
                "classname": "enrichers.en.transliterate.cmu.CMU_EN_Transliterator",
                "config": {"path": "/opt/transcrobes/cmudict-0.7b.txt", "inmem": True},
            },
        },
        "secondary": [
            {
                "classname": "en_zhhans.translate.abc.EN_ZHHANS_ABCDictTranslator",
                "config": {"path": "/opt/transcrobes/abc_en_zh_dict.txt", "inmem": True},
            },
        ],
        "metadata": [
            {
                "classname": "enrichers.en.metadata.subtlex.EN_SubtlexMetadata",
                "config": {"path": "/opt/transcrobes/subtlex-en-us.utf8.txt", "inmem": True},
            },
        ],
        "transliterate": {
            "classname": "enrichers.en.transliterate.cmu.CMU_EN_Transliterator",
            "config": {"path": "/opt/transcrobes/cmudict-0.7b.txt", "inmem": True},
        },
    },
}
