#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

FILE=test.env
if [ -f "$FILE" ]; then
    source $FILE
fi

coverage run --source='src' src/manage.py test tests

coverage report -m --skip-covered --skip-empty --fail-under 66
