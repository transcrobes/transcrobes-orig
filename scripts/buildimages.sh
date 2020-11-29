#!/bin/bash
set -e

source scripts/runsetup.sh

TAG=${TRANSCROBES_BUILD_TAG:-$(git describe --tags)}

MAIN_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes:$TAG
buildah bud --squash -t ${MAIN_IMAGE} -f images/main/Dockerfile .
buildah push -D ${MAIN_IMAGE}

STATIC_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes-static:$TAG
npm run prod
python3 src/manage.py collectstatic --noinput
buildah bud --squash -t ${STATIC_IMAGE} -f images/static/Dockerfile .
buildah push -D ${STATIC_IMAGE}
