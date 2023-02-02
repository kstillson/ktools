#!/bin/sh
DOCKER_EXEC=${DOCKER_EXEC:-/usr/bin/docker}
exec $DOCKER_EXEC ps --format '{{.ID}} {{.Names}}'
