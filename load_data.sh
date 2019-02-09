#!/bin/bash

source set_python_path.sh

python transcrobes/manage.py load_data "$@"
