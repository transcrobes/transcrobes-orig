#!/bin/bash

source set_python_path.sh

python transcrobes/manage.py adduser "$@"
