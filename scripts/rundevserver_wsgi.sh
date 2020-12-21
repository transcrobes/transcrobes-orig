#!/bin/bash

source scripts/runsetup.sh

FILE=.env.export
if [ -f "$FILE" ]; then
    echo "Found .env file, sourcing"
    source $FILE
fi
export TRANSCROBES_WSGI_PROCESS=True
poetry run python src/manage.py runserver 0.0.0.0:8002
