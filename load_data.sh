#!/bin/bash

source runsetup.sh

python transcrobes/manage.py load_data "$@"
