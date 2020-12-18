#!/bin/bash

source scripts/runsetup.sh

FILE=.env
if [ -f "$FILE" ]; then
    echo "Found .env file, sourcing"
    source $FILE
fi

export PYTHONPATH=$PYTHONPATH:tests

pip install -r requirements.ci.txt &&
    scripts/runmanage.sh migrate &&
    scripts/load_data.sh --all &&
    scripts/runmanage.sh loaddata $APP_PATH/tests/fixtures/* &&
    scripts/rundevserver.sh
    python ./manage.py runserver 0.0.0.0:8002
