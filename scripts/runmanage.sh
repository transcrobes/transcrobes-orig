#!/bin/bash

source scripts/runsetup.sh

FILE=.env
if [ -f "$FILE" ]; then
    echo "Found .env file, sourcing"
    source $FILE
fi

python src/manage.py $@
