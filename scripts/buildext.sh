#!/bin/bash
set -e

rm -rf build/bc/*

npm run bcp

# FIXME: in kiwi browser and yandex
# this works
# cd "C:\Program Files (x86)\Google\Chrome\Application"
# .\chrome.exe --enable-apps --pack-extension=\\wsl$\ubwin\home\anton\dev\tc\transcrobes\build\bc

# this doesn't
# zip -j -r -FS build/brocrobes.zip build/bc/*
