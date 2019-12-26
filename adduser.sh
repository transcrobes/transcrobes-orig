#!/bin/bash

source runsetup.sh

python transcrobes/manage.py adduser "$@"
