#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

FILE=test.env
if [ -f "$FILE" ]; then
    source $FILE
fi

pylint --ignore requirements.txt,transcrobes.egg-info,cmu src/*
pylint tests/*

# pre-commit also has flake8 linter
pre-commit run --all-files --verbose

coverage run --source='src' src/manage.py test --verbosity=1 tests

coverage report -m --skip-covered --skip-empty --fail-under 66
