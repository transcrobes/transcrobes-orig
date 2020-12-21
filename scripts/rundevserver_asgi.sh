#!/bin/bash

source scripts/runsetup.sh

FILE=.env.export
if [ -f "$FILE" ]; then
    echo "Found .env file, sourcing"
    source $FILE
fi

export TRANSCROBES_ZH_EN_CEDICT_INMEM=False
export TRANSCROBES_ZH_EN_ABC_DICT_INMEM=False
export TRANSCROBES_ZH_SUBTLEX_FREQ_INMEM=False
export TRANSCROBES_ZH_HSK_LISTS_INMEM=False
export TRANSCROBES_BING_TRANSLITERATOR_INMEM=False
export TRANSCROBES_BING_TRANSLATOR_INMEM=False

export TRANSCROBES_WSGI_PROCESS=False
# poetry run uvicorn transcrobes.asgi:application --port 8003 --debug

gunicorn --timeout $TRANSCROBES_GUNICORN_TIMEOUT --workers=$TRANSCROBES_GUNICORN_WORKERS \
    -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.asgi:application -k uvicorn.workers.UvicornWorker
