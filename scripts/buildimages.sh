#!/bin/bash
set -e

source scripts/runsetup.sh

TAG=${TRANSCROBES_BUILD_TAG:-$(git describe --tags)}

MAIN_IMAGE=${TRANSCROBES_DOCKER_REPO}/transcrobes:$TAG
if [ -z "$TRANSCROBES_SKIP_JS_COMPILE" ]
then
  npm run prod
  npm run mediap
  npm run readiump
else
      echo "\$TRANSCROBES_SKIP_JS_COMPILE is NOT empty, skipped JS compilation"
fi
python3 src/manage.py collectstatic --noinput
buildah bud --layers -t ${MAIN_IMAGE} -f images/main/Dockerfile .
buildah push ${MAIN_IMAGE}
