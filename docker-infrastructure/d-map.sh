#!/bin/sh
exec /usr/bin/docker ps --format '{{.ID}} {{.Names}}'
