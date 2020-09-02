#!/bin/bash

source scripts/runsetup.sh

python src/manage.py load_data "$@"
