#!/bin/bash
set -e

source scripts/runsetup.sh

TAG=${TRANSCROBES_BUILD_TAG:-$(git describe --tags)}

MAIN_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes:$TAG
buildah bud -t ${MAIN_IMAGE} -f images/main/Dockerfile .
buildah push ${MAIN_IMAGE}

STATIC_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes-static:$TAG
npm run prod
python3 src/manage.py collectstatic --noinput
buildah bud -t ${STATIC_IMAGE} -f images/static/Dockerfile .
buildah push ${STATIC_IMAGE}
