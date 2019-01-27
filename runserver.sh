#!/bin/bash

export PYTHONPATH=$PYTHONPATH:transcrobes:pg-ankisyncd:pg-ankisyncd/asd:pg-ankisyncd/asd/anki-bundled

gunicorn --workers=$TRANSCROBES_GUNICORN_WORKERS -b $TRANSCROBES_LISTEN_ADDRESS:$TRANSCROBES_LISTEN_PORT transcrobes.wsgi
