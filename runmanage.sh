#!/bin/bash

export PYTHONPATH=$PYTHONPATH:transcrobes:pg-ankisyncd:pg-ankisyncd/asd:pg-ankisyncd/asd/anki-bundled

python transcrobes/manage.py $@
