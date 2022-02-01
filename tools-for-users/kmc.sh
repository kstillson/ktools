#!/bin/bash
# Keymanager client

# $1 is the "scope", essentially the name of the key we're trying to retrieve.
# By default, key's are named "$hostname-$scope".  Provide no $2 to follow this
# convention.  If you use a different prefix, pass it as $2.  If you don't want
# a prefix at all, pass "" as $2.
SCOPE="$1"

# Ken specific defaults, feel free to override from environment.
KMHOST="${KMHOST:-kmdock}"
KMPORT="${KMPORT:-4443}"

if [[ $# -gt 1 ]]; then
  CONTEXT="$2"
else
  CONTEXT="$(hostname)-"
fi

/usr/bin/wget -O - --no-check-certificate -q https://${KMHOST}:${KMPORT}/${CONTEXT}${SCOPE}
