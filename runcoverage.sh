#!/bin/bash

source runsetup.sh

DJANGO_SETTINGS_MODULE=transcrobes.settings.test coverage run --source='transcrobes' transcrobes/manage.py test accounts lang enrich data ankrobes.tests.AnkrobesTests

coverage report -m --skip-covered --skip-empty --fail-under 51
