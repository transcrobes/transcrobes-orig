#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

echo "Running pylint on src/*"
pylint --ignore requirements.txt,requirements.ci.txt,transcrobes.egg-info,cmu src/*
echo "Running pylint on tests/*"
pylint tests/*
