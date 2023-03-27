#!/bin/sh
DOCKER_EXEC=$(ktools_settings -b docker_exec)
exec $DOCKER_EXEC ps --format '{{.ID}} {{.Names}}'
