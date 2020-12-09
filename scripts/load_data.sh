#!/bin/bash

source scripts/runsetup.sh

FILE=.env
if [ -f "$FILE" ]; then
    echo "Found .env file, sourcing"
    source $FILE
fi

if [ -f "manage.py" ]; then
    echo "Running manage.py at the root"
    python manage.py load_data $@
else
    echo "Running manage.py in the src directory"
    python src/manage.py load_data $@
fi
