# -*- coding: utf-8 -*-
import logging
import os
from datetime import timedelta

import djankiserv.unki
from djankiserv.unki.database import PostgresAnkiDataModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str(os.getenv("TRANSCROBES_DEBUG")).lower() == "true"

INSTALLED_APPS = [
    # core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "corsheaders",
    # community
    "registration",
    "anymail",
    "widget_tweaks",
    # "simple_history",
    "rest_framework",
    "django_filters",
    "django_k8s",  # allows for a more elegant init-container to check for migrations and db availability
    "django_prometheus",
    "django_extensions",
    "djankiserv.apps.DjankiservConfig",
    # local
    "enrich.apps.EnrichConfig",
    "ankrobes.apps.AnkrobesConfig",
    "en_zhhans.apps.EnZhhansConfig",
    "zhhans_en.apps.ZhhansEnConfig",
    "enrichers.apps.EnrichersConfig",
    "data.apps.DataConfig",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}
CORS_ALLOW_ALL_ORIGINS = True  # TODO: think about restricting this

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("TRANSCROBES_JWT_ACCESS_TOKEN_LIFETIME_MINS", "10"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("TRANSCROBES_JWT_REFRESH_TOKEN_LIFETIME_DAYS", "1"))),
}

# TODO: fix the csrf thing - is this fixed now???
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
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

WSGI_APPLICATION = "transcrobes.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = "build/static"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LL = "ERROR"

PROMETHEUS_EXPORT_MIGRATIONS = False
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

if os.getenv("DJANGO_LOG_LEVEL"):
    logging.disable(os.getenv("DJANGO_LOG_LEVEL"))

if DEBUG:
    MIDDLEWARE.append("request_logging.middleware.LoggingMiddleware")
    LOGGING["loggers"]["django.request"] = {"handlers": ["console"], "level": "DEBUG", "propagate": False}

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.getenv("TC_POSTGRES_DATABASE", "transcrobes"),
        "USER": os.getenv("TC_POSTGRES_USER", "your_user"),
        "PASSWORD": os.getenv("TC_POSTGRES_PASSWORD", "your_password"),
        "HOST": os.getenv("TC_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("TC_POSTGRES_PORT", "5432"),
    },
    "userdata": {
        "ENGINE": os.getenv("TC_DJANKISERV_USERDB_ENGINE", "django_prometheus.db.backends.postgresql"),
        "NAME": os.getenv("TC_DJANKISERV_USERDB_NAME", "transcrobes"),
        "USER": os.getenv("TC_DJANKISERV_USERDB_USER", "your_user"),
        "PASSWORD": os.getenv("TC_DJANKISERV_USERDB_PASSWORD", "your_password"),
        "HOST": os.getenv("TC_DJANKISERV_USERDB_HOST", "127.0.0.1"),
        "PORT": os.getenv("TC_DJANKISERV_USERDB_PORT", "5432"),
    },
}

djankiserv.unki.AnkiDataModel = PostgresAnkiDataModel
SITE_ID = 1

# WARNING!!! MUST be behind ssl proxy for both security and for both djankiserv and brocrobes to work
ALLOWED_HOSTS = " ".join(os.getenv("TRANSCROBES_SYSTEM_HOSTS", "*").split(",")).split()
ALLOWED_HOSTS += " ".join(os.getenv("TRANSCROBES_NODE_HOSTS", "").split(",")).split()

HA_HOST = os.getenv("TRANSCROBES_HA_HOST")
if HA_HOST:
    ALLOWED_HOSTS.append(HA_HOST)
if os.getenv("TRANSCROBES_POD_IP"):
    ALLOWED_HOSTS.append(os.getenv("TRANSCROBES_POD_IP"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("TRANSCROBES_SECRET_KEY", "not_a_very_good_secret")

# pilot
LOGIN_URL = "/accounts/login/"
LOGOUT_URL = "/accounts/logout/"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "/accounts/login/"
REGISTRATION_FORM = "transcrobes.forms.RestrictiveRegistrationForm"
INTERNAL_IPS = ("127.0.0.1",)

# if you change this, it must also be changed in the images/static/Dockerfile
STATIC_ROOT = "build/static"

# Email: anymail via mailgun and defaults
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"  # or sendgrid.emailbackend, or...
ANYMAIL = {
    "MAILGUN_API_KEY": os.getenv("TRANSCROBES_MAILGUN_API_KEY"),  # noqa:F405
    "DEBUG_API_REQUESTS": str(os.getenv("TRANSCROBES_DEBUG", "false")).lower() == "true",  # noqa:F405
}

DEFAULT_FROM_EMAIL = os.getenv("TRANSCROBES_DEFAULT_FROM_EMAIL")
SERVER_EMAIL = os.getenv("TRANSCROBES_SERVER_EMAIL")

# registration
ACCOUNT_ACTIVATION_DAYS = int(os.getenv("TRANSCROBES_ACCOUNT_ACTIVATION_DAYS", "1"))  # One day
REGISTRATION_OPEN = str(os.getenv("TRANSCROBES_REGISTRATION_OPEN")).lower() == "true"
REGISTRATION_AUTO_LOGIN = True

## DJANKISERV
# This is required as Django will add a slash and redirect to that by default, and djankiserv doesn't support that
APPEND_SLASH = False

DJANKISERV_SYNC_URLBASE = "sync/"  # this is not actually currently configurable, due to hardcoding in the clients
DJANKISERV_SYNC_MEDIA_URLBASE = "msync/"  # this is not actually configurable, due to hardcoding in the clients
DJANKISERV_API_URLBASE = "dapi/"  # TODO: turn this into an envvar
DJANKISERV_DATA_ROOT = os.getenv("TRANSCROBES_DJANKISERV_DATA_ROOT", "/tmp")

# DEBUG STUFF
DJANKISERV_DEBUG = str(os.getenv("DJANKISERV_DEBUG", os.getenv("TRANSCROBES_DEBUG", "false"))).lower() == "true"

DJANKISERV_GENERATE_TEST_ASSETS = False
DJANKISERV_GENERATE_TEST_ASSETS_DIR = "/tmp/asrv/"
TEST_RUNNER = "tests.CleanupTestRunner"

KAFKA_BROKER = os.getenv("TRANSCROBES_KAFKA_BROKER", "localhost:9092")
KAFKA_CONSUMER_TIMEOUT_MS = int(os.getenv("TRANSCROBES_KAFKA_CONSUMER_TIMEOUT_MS", "5000"))
KAFKA_STATS_LOOP_SLEEP = int(os.getenv("TRANSCROBES_KAFKA_STATS_LOOP_SLEEP", "10"))
KAFKA_MAX_POLL_RECORDS = int(os.getenv("TRANSCROBES_KAFKA_MAX_POLL_RECORDS", "500"))  # 500 is default

# From here the values are sensible and can be kept if desired

# TODO: give the option of doing an import to a configmap mounted file
# and configuring from there. That will likely be useful when we have
# proper drop-in language pairs

LANG_PAIRS = {
    "zh-Hans:en": {
        "enrich": {"classname": "enrichers.zhhans.CoreNLP_ZHHANS_Enricher", "config": {}},
        "parse": {
            "classname": "enrich.parse.HTTPCoreNLPProvider",
            "config": {
                "base_url": f'http://{os.getenv("TRANSCROBES_ZH_CORENLP_HOST", "corenlp-zh")}',
                "params": '{"annotators":"lemma","outputFormat":"json"}',
            },
        },
        "word_lemmatizer": {"classname": "enrich.lemmatize.no_op.NoOpWordLemmatizer", "config": {}},
        "default": {
            "classname": "enrich.translate.bing.BingTranslator",
            "config": {
                "from": "zh-Hans",
                "to": "en",
                "api_host": os.getenv("TRANSCROBES_BING_API_HOST", "api.cognitive.microsofttranslator.com"),
                "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY", "a_super_api_key"),
            },
            "transliterator": {
                "classname": "enrich.transliterate.bing.BingTransliterator",
                "config": {
                    "from": "zh-Hans",
                    "to": "en",
                    "from_script": "Hans",
                    "to_script": "Latn",
                    "api_host": os.getenv("TRANSCROBES_BING_API_HOST", "api.cognitive.microsofttranslator.com"),
                    "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY", "a_super_api_key"),
                },
            },
        },
        "secondary": [
            {
                "classname": "zhhans_en.translate.abc.ZHHANS_EN_ABCDictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_EN_ABC_DICT_PATH", "/opt/transcrobes/zh_en_abc_dict.txt"),
                    "inmem": os.getenv("TRANSCROBES_ZH_EN_ABC_DICT_INMEM", "false").lower() == "true",
                },
            },
            {
                "classname": "zhhans_en.translate.ccc.ZHHANS_EN_CCCedictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_EN_CEDICT_PATH", "/opt/transcrobes/zh_en_cedict.txt"),
                    "inmem": os.getenv("TRANSCROBES_ZH_EN_CEDICT_INMEM", "false").lower() == "true",
                },
            },
        ],
        "metadata": [
            {
                "classname": "enrichers.zhhans.metadata.hsk.ZH_HSKMetadata",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_HSK_LISTS_PATH", "/opt/transcrobes/zh_hsk{}.txt"),
                    "inmem": os.getenv("TRANSCROBES_ZH_HSK_LISTS_INMEM", "false").lower() == "true",
                },
            },
            {
                "classname": "enrichers.zhhans.metadata.subtlex.ZH_SubtlexMetadata",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_SUBTLEX_FREQ_PATH", "/opt/transcrobes/zh_subtlex.utf8.txt"),
                    "inmem": os.getenv("TRANSCROBES_ZH_SUBTLEX_FREQ_INMEM", "false").lower() == "true",
                },
            },
        ],
        "transliterate": {
            "classname": "enrich.transliterate.bing.BingTransliterator",
            "config": {
                "from": "zh-Hans",
                "to": "en",
                "from_script": "Hans",
                "to_script": "Latn",
                "api_host": os.getenv("TRANSCROBES_BING_API_HOST", "api.cognitive.microsofttranslator.com"),
                "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY", "a_super_api_key"),
            },
        },
    },
}
