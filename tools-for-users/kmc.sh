#!/bin/bash
# Keymanager client

# ---------- command line flags

# keymaster usually uses the naming convension "$hostname-$keyname".
# To follow this convention, provide keyname as $1 and do not provide a $2.
# To use a prefix other than "$hostname-", provide it as $2.
# Include any prefix/keyname separator (e.g. "-") at the end of $2.
# To skip using a prefix, provide "" as $2.
# (Note that the prefix comes AFTER the suffix in the command line...  Yeah, yeah, so sue me..  No wait - please don't sue me.)
#
# The retrieved secret is send to stdout.  Any errors go to stderr.
# Exit status: 0 for success, or the curl error status for the most recent try.

KEYNAME="$1"

if [[ $# -gt 1 ]]; then
  PREFIX="$2"
else
  PREFIX="$(/usr/bin/hostname)-"
fi

# ---------- settings (can be overridden by the environment)

CA_CERT_FILE="${CA_CERT_FILE:-km.crt}"   # set to "-" to skip TLS validation

CURL_OPTS="${CURL_OPTS:--sS}"

KMHOST="${KMHOST:-km}"
KMPORT="${KMPORT:-4443}"

RETRY_DELAY=${RETRY_DELAY:-5}     # seconds (delay between retries)
RETRY_LIMIT=${RETRY_LIMIT:-9999}  # set to zero to output "" upon failure.

TIMEOUT=${TIMEOUT:-5}            # seconds (how long to wait for each try)

# ---------- computed settings

URL="https://${KMHOST}:${KMPORT}/${PREFIX}${KEYNAME}"

if [[ "$CA_CERT_FILE" == "-" ]]; then
    TLS_OPT="--insecure"
else
    TLS_OPT="--cacert ${CA_CERT_FILE}"
fi

# ---------- main retry loop

try=0
secret=""
while [[ $try -le $RETRY_LIMIT ]]; do 
    ((try++))
    secret=$(/usr/bin/curl $CURL_OPTS --connect-timeout $TIMEOUT $TLS_OPT $URL)
    curl_status=$?
    if [[ "$secret" != "" ]]; then
	echo "$secret"
	exit 0
    fi
    echo "$(/usr/bin/date): try #${try} failed (status $curl_status); will retry in $RETRY_DELAY" >&2
    sleep $RETRY_DELAY
done

echo "retries exceeded" >&2
exit $curl_status
