#!/bin/bash
set -e

source scripts/runsetup.sh

TAG=${TRANSCROBES_BUILD_TAG:-$(git describe --tags)}

MAIN_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes:$TAG
docker build -f images/main/Dockerfile . -t ${MAIN_IMAGE}
docker push ${MAIN_IMAGE}

STATIC_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes-static:$TAG
npm run prod
python3 src/manage.py collectstatic --noinput
docker build -f images/static/Dockerfile . -t ${STATIC_IMAGE}
docker push ${STATIC_IMAGE}
