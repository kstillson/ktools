#!/bin/bash

if [[ "$FULL_TEST" != "1" ]]; then cat <<EOF

Testing kmc.sh

Use the environment variables \$KMHOST and \$KMPORT to tell this test
which server to talk to.

If the server is running at a temporary name or IP that doesn't match its
certificate, set \$KMHOST to the name that TLS expects and \$KMHOST_TEST
to the name or IP you actually want this test to talk to.

This initial test checks only the most basic operation of kmc.sh, and works
with either a production or test-mode server, so long as the server is
already unlocked and the database includes the [test] key.

For a more comprehensive test suite, the test must be able to lock and unlock
the server, which means it must be running the test database.  For this, set
the environment variable DATA=km-test.data.gpg inside the server.

To enable the full test suite, pass FULL_TEST=1 to this script.  
i.e.:
  sudo /root/bin/d-run --cd keymaster --name km_test --extra-docker '-e DATA=km-test.data.gpg'
  export KMHOST_TEST=\$(sudo /root/bin/d ip km_test)
  FULL_TEST=1 ./test_kmc.sh

and to shut down the test server once testing is complete:
  d 0 km_test

---------

EOF
fi

# ---------- helper functions

SUCCESS_FLAG_FILE=$(mktemp)
function failed() {
    echo ">> FAIL: $@" >&2
    echo "--" >&2
    rm -f $SUCCESS_FLAG_FILE
}

function expect() {
    title="$1"
    want="$2"
    got=$(cat)
    if [[ "$got" == *"$want"* ]]; then
        echo "$title ok: saw as expected: '$want'" >&2
	echo "--" >&2
        return 0
    fi
    failed "$title: expected '$want' but saw '$got'"
    return -1
}

function all_done() {
    echo ""
    if [[ -f $SUCCESS_FLAG_FILE ]]; then
	rm $SUCCESS_FLAG_FILE
	echo "pass"
	exit 0
    else
	echo "fail"
	exit 1
    fi
}

function unlock_server() {
    curl -ksS ${CURL_OPTS} -d password=ken123 https://${KMHOST}:${KMPORT}/ | expect "unlock database" "ok"
}


# ---------- default env settings for kmc.sh

CA_CERT_FILE="${CA_CERT_FILE:-km.crt}"

export RETRY_DELAY=1
export RETRY_LIMIT=0
export TIMEOUT=2

export KMHOST=${KMHOST:-km}
export KMPORT=${KMPORT:-4443}

if [[ "$KMHOST_TEST" != "" ]]; then
    export CURL_OPTS="$CURL_OPTS -sS --connect-to ${KMHOST}:${KMPORT}:${KMHOST_TEST}:${KMPORT}"
fi

# ---------- limited test

if [[ "$FULL_TEST" != "1" ]]; then
    ./kmc.sh test "" | expect "basic test" "hithere"
    all_done
fi

# ---------- full test

unlock_server

./kmc.sh test "" | expect "basic test" "hithere"

# Disable TLS verfiication and confirm it still works.
CA_CERT_FILE="-" ./kmc.sh test "" | expect "no tls test" "hithere"

# Test that retries eventually fail correctly (reaching out to a bad host)
out=$(RETRY_DELAY=0 RETRY_LIMIT=3 KMHOST=invalid-host ./kmc.sh test "")
status=$?
if [[ $status != 6 ]]; then failed "invalid host should return status 6, not $status"; fi
if [[ "$out" != "" ]]; then failed "invalid host should not return anything; it returned: $out"; fi
echo "--" >&2

# Test that retries work.  We'll do this by pointing to a cert file that doesn't
# exist initially, but then create that file after a short delay.
echo "testing retry loops; expect a few failures then a success."
tmp=$(mktemp)
{ sleep 3; cp $CA_CERT_FILE $tmp; } &
RETRY_DELAY=2 RETRY_LIMIT=5 CA_CERT_FILE=$tmp ./kmc.sh test "" | expect "retry loop test" "hithere"
rm -f $tmp

# Try retrieving a key we don't have access to, confirm this fails and that it disables the server.
./kmc.sh test2 "" | expect "disallowed key retrieval" "error performing host verification"
./kmc.sh test "" | expect "retrieval when server locked" "not ready"

# ----------

all_done
