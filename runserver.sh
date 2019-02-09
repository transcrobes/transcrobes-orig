#!/bin/bash

source set_python_path.sh

gunicorn --timeout $TRANSCROBES_GUNICORN_TIMEOUT --workers=$TRANSCROBES_GUNICORN_WORKERS -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.wsgi
