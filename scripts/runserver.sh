#!/bin/bash

source scripts/runsetup.sh

FILE=.env.export
if [ -f "$FILE" ]; then
    echo "Found $FILE file, sourcing"
    source $FILE
fi

if [ "$TRANSCROBES_WSGI_PROCESS" == "false" ]; then
  echo "Envvar TRANSCROBES_WSGI_PROCESS == $TRANSCROBES_WSGI_PROCESS running ASGI"
  gunicorn --timeout $TRANSCROBES_GUNICORN_TIMEOUT --workers=$TRANSCROBES_GUNICORN_WORKERS \
    -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.asgi:application -k uvicorn.workers.UvicornWorker
else
  echo $TRANSCROBES_LISTEN_PORT
  echo "Envvar TRANSCROBES_WSGI_PROCESS == $TRANSCROBES_WSGI_PROCESS running WSGI"
  gunicorn --timeout $TRANSCROBES_GUNICORN_TIMEOUT --workers=$TRANSCROBES_GUNICORN_WORKERS \
    -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.wsgi
fi
