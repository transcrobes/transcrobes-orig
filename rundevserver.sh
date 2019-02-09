#!/bin/bash

source set_python_path.sh

python transcrobes/manage.py runserver --settings transcrobes.settings.container
