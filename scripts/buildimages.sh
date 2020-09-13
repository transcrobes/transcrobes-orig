#!/bin/bash
set -e

source scripts/runsetup.sh

MAIN_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes:$(git describe --tags)
docker build -f images/main/Dockerfile . -t ${MAIN_IMAGE}
docker push ${MAIN_IMAGE}

STATIC_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes-static:$(git describe --tags)
npm build prod
python src/manage.py collectstatic --noinput
docker build -f images/static/Dockerfile . -t ${STATIC_IMAGE}
docker push ${STATIC_IMAGE}
