# -*- coding: utf-8 -*-
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str(os.getenv("TRANSCROBES_DEBUG")).lower() == "true"
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("TRANSCROBES_SECRET_KEY", "not_a_very_good_secret")

INSTALLED_APPS = [
    # core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # community
    "corsheaders",
    "registration",
    "anymail",
    "widget_tweaks",
    # "simple_history",
    "rest_framework",
    "django_filters",
    "django_k8s",  # allows for a more elegant init-container to check for migrations and db availability
    "django_prometheus",
    "django_extensions",
    # local
    "enrich.apps.EnrichConfig",
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

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

CORS_ALLOW_ALL_ORIGINS = True  # TODO: think about restricting this

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("TRANSCROBES_JWT_ACCESS_TOKEN_LIFETIME_MINS", "10"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("TRANSCROBES_JWT_REFRESH_TOKEN_LIFETIME_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": os.getenv("TRANSCROBES_JWT_REFRESH_TOKEN_LIFETIME_DAYS", "true").lower() == "true",
}

MIDDLEWARE = [
    # "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "django_prometheus.middleware.PrometheusAfterMiddleware",
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

ASGI_APPLICATION = "transcrobes.asgi.application"

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
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

STATIC_URL = "/static/"
STATIC_ROOT = "whitenoise"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

MEDIA_ROOT = os.getenv("TRANSCROBES_MEDIA_ROOT", "/tmp/media/")

## Observability
# Prometheus
PROMETHEUS_EXPORT_MIGRATIONS = False  # https://github.com/korfuri/django-prometheus/issues/34
PROMETHEUS_MULTIPROC_MODE = True  # default is False
PROMETHEUS_MULTIPROC_DIR = "/tmp/transcrobes_prometheus"  # this is required when there are multiple workers

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
        "data": {
            "handlers": ["console"],
            "level": os.getenv("TRANSCROBES_DATA_LOG_LEVEL", "ERROR"),
            "propagate": False,
        },
        "enrich": {
            "handlers": ["console"],
            "level": os.getenv("TRANSCROBES_ENRICH_LOG_LEVEL", "ERROR"),
            "propagate": False,
        },
        "enrichers": {
            "handlers": ["console"],
            "level": os.getenv("TRANSCROBES_ENRICHERS_LOG_LEVEL", "ERROR"),
            "propagate": False,
        },
        "": {"handlers": ["console"], "level": os.getenv("TRANSCROBES_DEFAULT_LOG_LEVEL", "ERROR"), "propagate": False},
    },
}

# if DEBUG:
#     MIDDLEWARE.append("request_logging.middleware.LoggingMiddleware")
#     LOGGING["loggers"]["django.request"] = {"handlers": ["console"], "level": "DEBUG", "propagate": False}

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.getenv("TC_POSTGRES_DATABASE", "transcrobes"),
        "USER": os.getenv("TC_POSTGRES_USER", "your_user"),
        "PASSWORD": os.getenv("TC_POSTGRES_PASSWORD", "your_password"),
        "HOST": os.getenv("TC_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("TC_POSTGRES_PORT", "5432"),
    },
}

SITE_ID = 1

# WARNING!!! MUST be behind ssl proxy for both security and for both djankiserv and brocrobes to work
ALLOWED_HOSTS = " ".join(os.getenv("TRANSCROBES_SYSTEM_HOSTS", "*").split(",")).split()
ALLOWED_HOSTS += " ".join(os.getenv("TRANSCROBES_NODE_HOSTS", "").split(",")).split()

HA_HOST = os.getenv("TRANSCROBES_HA_HOST")
if HA_HOST:
    ALLOWED_HOSTS.append(HA_HOST)
if os.getenv("TRANSCROBES_POD_IP"):
    ALLOWED_HOSTS.append(os.getenv("TRANSCROBES_POD_IP"))

# pilot
LOGIN_URL = "/accounts/login/"
LOGOUT_URL = "/accounts/logout/"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "/accounts/login/"
REGISTRATION_FORM = "transcrobes.forms.RestrictiveRegistrationForm"
INTERNAL_IPS = ("127.0.0.1",)

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

TEST_RUNNER = "tests.CleanupTestRunner"

## Stats & Events
# Kafka
KAFKA_BROKER = os.getenv("TRANSCROBES_KAFKA_BROKER", "localhost:9092")
KAFKA_CONSUMER_TIMEOUT_MS = int(os.getenv("TRANSCROBES_KAFKA_CONSUMER_TIMEOUT_MS", "5000"))
KAFKA_STATS_LOOP_SLEEP_SECS = int(os.getenv("TRANSCROBES_KAFKA_STATS_LOOP_SLEEP_SECS", "10"))
KAFKA_MAX_POLL_RECORDS = int(os.getenv("TRANSCROBES_KAFKA_MAX_POLL_RECORDS", "500"))  # 500 is default

# FIXME: Is this required for ASGI??? No idea!!!
THREAD_SENSITIVE = os.getenv("TRANSCROBES_WSGI_PROCESS", "true").lower() == "true"

# TODO: there appears to be an issue with asyncpg because of pgpool, so until aiopg (which is fine with pgpool2) is
# implemented, or we forget about pgpool, then only kafka can work (and don't forget to create the topics beforehand,
# or first connection fails). Default to memory, which is find for debugging
BROACASTER_MESSAGING_LAYER = os.getenv("TRANSCROBES_BROACASTER_MESSAGING_LAYER", "memory")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,
        "OPTIONS": {"MAX_ENTRIES": 1000000},
    },
    "bing_lookup": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,
        "LOCATION": "bing_lookup",
        "OPTIONS": {"MAX_ENTRIES": 1000000},
    },
    "bing_translate": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,
        "LOCATION": "bing_translate",
        "OPTIONS": {"MAX_ENTRIES": 1000000},
    },
    "bing_transliterate": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,
        "LOCATION": "bing_transliterate",
        "OPTIONS": {"MAX_ENTRIES": 1000000},
    },
}

DEFINITIONS_CACHE_DIR = os.getenv("TRANSCROBES_DEFINITIONS_CACHE_DIR", os.path.join(MEDIA_ROOT, "definitions_json"))
DEFINITIONS_PER_CACHE_FILE = int(os.getenv("TRANSCROBES_DEFINITIONS_PER_CACHE_FILE", "5000"))
HANZI_CACHE_DIR = os.getenv("TRANSCROBES_HANZI_CACHE_DIR", os.path.join(MEDIA_ROOT, "hanzi_json"))
HANZI_PER_CACHE_FILE = int(os.getenv("TRANSCROBES_HANZI_PER_CACHE_FILE", "1000"))
HANZI_WRITER_DATA_URL = os.getenv(
    "TRANSCROBES_HANZI_WRITER_DATA_URL",
    "https://raw.githubusercontent.com/chanind/hanzi-writer-data/master/data/all.json",
)

# User list import max file size in KB
IMPORT_MAX_UPLOAD_SIZE_KB = int(os.getenv("TRANSCROBES_IMPORT_MAX_UPLOAD_SIZE_KB", "5120"))

IMPORT_UPLOAD_SAFETY_MARGIN = 10000

# Django-internal, for uploads, the default is 2.5MB, so if not set put to 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("TRANSCROBES_DATA_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = (
    IMPORT_MAX_UPLOAD_SIZE_KB * 1024
    if IMPORT_MAX_UPLOAD_SIZE_KB * 1024 > DATA_UPLOAD_MAX_MEMORY_SIZE
    else DATA_UPLOAD_MAX_MEMORY_SIZE
) + IMPORT_UPLOAD_SAFETY_MARGIN

# The max size of a a chunk of an input/import file to send to the parser (CoreNLP)
# This needs to be measured against resources, and the larger the chunk, the more memory and time
# each chunk will require to process. Also:
# - the CORENLP_TIMEOUT might need to be increased if this is increased
# - the max number of bytes currently supported by the transcrobes/corenlp-chinese image is
#   100k, the image will need to have -maxCharLength -1 (for unlimited) or -maxCharLength ??? if more is required
# WARNING!!! corenlp should have at least 2GB of mem or large values here can quickly overwhelm it, and it
# will start timing out and having regular OOM
IMPORT_PARSE_CHUNK_SIZE_BYTES = int(os.getenv("TRANSCROBES_IMPORT_PARSE_CHUNK_SIZE_BYTES", "20000"))
IMPORT_DETECT_CHUNK_SIZE_BYTES = int(os.getenv("TRANSCROBES_IMPORT_DETECT_CHUNK_SIZE_BYTES", "5000"))
IMPORT_MAX_CONCURRENT_PARSER_QUERIES = int(os.getenv("TRANSCROBES_IMPORT_MAX_CONCURRENT_PARSER_QUERIES", "10"))

USER_ONBOARDING_SURVEY_IDS = [int(i) for i in os.getenv("TRANSCROBES_USER_ONBOARDING_SURVEY_IDS", "1").split(",")]

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
                "inmem": os.getenv("TRANSCROBES_BING_TRANSLATOR_INMEM", "false").lower() == "true",
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
                    "inmem": os.getenv("TRANSCROBES_BING_TRANSLITERATOR_INMEM", "false").lower() == "true",
                },
            },
        },
        "secondary": [
            {
                "classname": "zhhans_en.translate.abc.ZHHANS_EN_ABCDictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_EN_ABC_DICT_PATH", "/opt/transcrobes/abc_zh_en_dict.txt"),
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
                "inmem": os.getenv("TRANSCROBES_BING_TRANSLITERATOR_INMEM", "false").lower() == "true",
            },
        },
    },
}
