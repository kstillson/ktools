#!/bin/bash
DOCKER_EXEC=$(~/bin/ktools_settings -b docker_exec)
exec $DOCKER_EXEC ps --format '{{.ID}} {{.Names}}'
