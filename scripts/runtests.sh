#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

FILE=.env.test
if [ -f "$FILE" ]; then
    source $FILE
fi

pylint --ignore requirements.txt,requirements.ci.txt,transcrobes.egg-info,cmu $APP_PATH/*
pylint tests/*

# pre-commit also has flake8 linter
pre-commit run --all-files --verbose

coverage run --source="${APP_PATH}" $APP_PATH/manage.py test --verbosity=1 tests $1

coverage report -m --skip-covered --skip-empty --fail-under 60
