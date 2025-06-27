#!/bin/bash

CONTMGR="${CONTMGR:-podman}"
CONTAINER="$(basename $PWD)"
IMG="${CONTAINER}"
TAG="${TAG:-live}"

echo "Snapping container ${CONTAINER} to ${IMG}:${TAG}"
read -p 'ok? ' ok
if [[ "$ok" != "y" ]]; then echo "aborted."; exit 1; fi

if [[ "$TAG" == "live" ]]; then
    echo "backing up ${IMG}:live to ${IMG}:prev"
    $CONTMGR tag ${IMG}:live ${IMG}:prev
else
    echo "skipping backup to :prev (not updating :live image)"
fi

$CONTMGR commit \
  --change='CMD ["/root/run"]' \
  ${CONTAINER} ${IMG}:${TAG}
