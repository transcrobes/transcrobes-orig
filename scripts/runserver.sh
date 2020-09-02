#!/bin/bash

source scripts/runsetup.sh

gunicorn --timeout $TRANSCROBES_GUNICORN_TIMEOUT --workers=$TRANSCROBES_GUNICORN_WORKERS -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.wsgi
