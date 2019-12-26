#!/bin/bash

source runsetup.sh

python transcrobes/manage.py runserver --settings transcrobes.settings.container 0.0.0.0:8000
