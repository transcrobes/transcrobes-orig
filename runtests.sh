#!/bin/bash

source runsetup.sh

pylint transcrobes/*

# pre-commit also has flake8 linter
pre-commit run --all-files --verbose

python transcrobes/manage.py test --settings transcrobes.settings.test --verbosity=1 accounts lang enrich data ankrobes.tests.AnkrobesTests
