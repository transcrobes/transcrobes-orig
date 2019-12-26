# -*- coding: utf-8 -*-

import logging
import os

from .base import *  # pylint: disable=W0401,W0614  # noqa:F403,F401

if os.getenv("DJANGO_LOG_LEVEL"):
    logging.disable(os.getenv("DJANGO_LOG_LEVEL"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DATABASE"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

USER_CACHE_TIMEOUT = int(os.getenv("TRANSCROBES_USER_CACHE_TIMEOUT", "5"))

# MUST be behind ssl proxy
# FIXME - remove the 'or'
ALLOWED_HOSTS = " ".join(os.getenv("TRANSCROBES_PUBLIC_HOSTS", "*").split(",")).split()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("TRANSCROBES_SECRET_KEY", "not_a_very_good_secret")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str(os.getenv("TRANSCROBES_DEBUG")).lower() == "true"

ANKROBES_DATA_ROOT = os.getenv("TRANSCROBES_ANKROBES_DATA_ROOT", "/tmp")

# TODO: give the option of doing an import to a configmap mounted file
# and configuring from there. That will likely be useful when we have
# proper drop-in language pairs

LANG_PAIRS = {
    "zh-Hans:en": {
        "enrich": {"classname": "enrichers.zhhans.CoreNLP_ZHHANS_Enricher", "config": {}},
        "parse": {
            "classname": "enrich.parse.HTTPCoreNLPProvider",
            "config": {
                "base_url": f'http://{os.getenv("TRANSCROBES_CORENLP_HOST_ZH")}',
                "params": '{"annotators":"lemma","outputFormat":"json"}',
            },
        },
        "word_lemmatizer": {"classname": "enrich.lemmatize.no_op.NoOpWordLemmatizer", "config": {}},
        "default": {
            "classname": "enrich.translate.bing.BingTranslator",
            "config": {
                "from": "zh-Hans",
                "to": "en",
                "api_host": os.getenv("TRANSCROBES_BING_API_HOST"),
                "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY"),
            },
            "transliterator": {
                "classname": "enrich.transliterate.bing.BingTransliterator",
                "config": {
                    "from": "zh-Hans",
                    "to": "en",
                    "from_script": "Hans",
                    "to_script": "Latn",
                    "api_host": os.getenv("TRANSCROBES_BING_API_HOST"),
                    "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY"),
                },
            },
        },
        "secondary": [
            {
                "classname": "zhhans_en.translate.abc.ZHHANS_EN_ABCDictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_EN_ABC_DICT_PATH"),
                    "inmem": os.getenv("TRANSCROBES_ZH_EN_ABC_DICT_INMEM", "").lower() == "true",
                },
            },
            {
                "classname": "zhhans_en.translate.ccc.ZHHANS_EN_CCCedictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_EN_CEDICT_PATH"),
                    "inmem": os.getenv("TRANSCROBES_ZH_EN_CEDICT_INMEM", "").lower() == "true",
                },
            },
        ],
        "metadata": [
            {
                "classname": "enrichers.zhhans.metadata.hsk.ZH_HSKMetadata",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_HSK_LISTS_PATH"),
                    "inmem": os.getenv("TRANSCROBES_ZH_HSK_LISTS_INMEM", "").lower() == "true",
                },
            },
            {
                "classname": "enrichers.zhhans.metadata.subtlex.ZH_SubtlexMetadata",
                "config": {
                    "path": os.getenv("TRANSCROBES_ZH_SUBTLEX_FREQ_PATH"),
                    "inmem": os.getenv("TRANSCROBES_ZH_SUBTLEX_FREQ_INMEM", "").lower() == "true",
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
                "api_host": os.getenv("TRANSCROBES_BING_API_HOST"),
                "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY"),
            },
        },
    },
    "en:zh-Hans": {
        "enrich": {"classname": "enrichers.en.CoreNLP_EN_Enricher", "config": {}},
        "parse": {
            "classname": "enrich.parse.HTTPCoreNLPProvider",
            "config": {
                "base_url": f'http://{os.getenv("TRANSCROBES_CORENLP_HOST_EN")}',
                "params": '{"annotators":"lemma","outputFormat":"json"}',
            },
        },
        "word_lemmatizer": {
            "classname": "enrichers.en.SpaCy_EN_WordLemmatizer",
            "config": {
                # 'model_name': 'en_core_web_sm',  # TODO: Not currently used
            },
        },
        "default": {
            "classname": "enrich.translate.bing.BingTranslator",
            "config": {
                "from": "en",
                "to": "zh-Hans",
                "api_host": os.getenv("TRANSCROBES_BING_API_HOST"),
                "api_key": os.getenv("TRANSCROBES_BING_SUBSCRIPTION_KEY"),
            },
            "transliterator": {
                "classname": "enrichers.en.transliterate.cmu.CMU_EN_Transliterator",
                "config": {
                    "path": os.getenv("TRANSCROBES_EN_CMU_DICT_PATH"),
                    "inmem": os.getenv("TRANSCROBES_EN_CMU_DICT_INMEM", "").lower() == "true",
                },
            },
        },
        "secondary": [
            {
                "classname": "en_zhhans.translate.abc.EN_ZHHANS_ABCDictTranslator",
                "config": {
                    "path": os.getenv("TRANSCROBES_EN_ZH_ABC_DICT_PATH"),
                    "inmem": os.getenv("TRANSCROBES_EN_ZH_ABC_DICT_INMEM", "").lower() == "true",
                },
            },
        ],
        "metadata": [
            {
                "classname": "enrichers.en.metadata.subtlex.EN_SubtlexMetadata",
                "config": {
                    "path": os.getenv("TRANSCROBES_EN_SUBTLEX_FREQ_PATH"),
                    "inmem": os.getenv("TRANSCROBES_EN_SUBTLEX_FREQ_INMEM", "").lower() == "true",
                },
            },
        ],
        "transliterate": {
            "classname": "enrichers.en.transliterate.cmu.CMU_EN_Transliterator",
            "config": {
                "path": os.getenv("TRANSCROBES_EN_CMU_DICT_PATH"),
                "inmem": os.getenv("TRANSCROBES_EN_CMU_DICT_INMEM", "").lower() == "true",
            },
        },
    },
}

# pilot
LOGIN_URL = "login"
LOGOUT_URL = "logout"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
INTERNAL_IPS = ("127.0.0.1",)
# SESSION_COOKIE_HTTPONLY = False
# SESSION_COOKIE_SAMESITE = None
