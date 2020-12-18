#!/bin/bash

source scripts/runsetup.sh

FILE=.env.test
if [ -f "$FILE" ]; then
    source $FILE
fi

export PYTHONPATH=$PYTHONPATH:tests

coverage run --source="${APP_PATH}" $APP_PATH/manage.py test --verbosity=1 tests $1

coverage report -m --skip-covered --skip-empty --fail-under 60
