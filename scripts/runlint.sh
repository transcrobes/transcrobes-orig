#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

pylint --ignore requirements.txt,transcrobes.egg-info,cmu src/*
pylint tests/*
