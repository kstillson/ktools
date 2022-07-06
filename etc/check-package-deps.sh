#!/bin/bash

OUT=$(mktemp)

# ---------- helpers

function tester() {
    cmd="$1"
    pkg="$2"
    prompt="$3"
    $cmd >&/dev/null && return 0
    echo "$pkg" >> $OUT
    printf "$(tput setaf 3)PROBLEM: $(tput sgr0)${prompt} ${pkg}\n"
    return 1
}

function run_default_tests() {
    prompt="required package appears to be missing: "
    tester "python3 --version"              "python3"                 "$prompt"
    tester "pytest-3 --version"             "python3-pytest"          "$prompt"
    tester "python3 -m pytest_timeout"      "python3-pytest-timeout"  "$prompt"
    echo "import psutil" | tester "python3" "python3-psutil"          "$prompt"

    if [[ "$BUILD_SIMPLE" != "1" ]]; then
	echo ""
	prompt='Python wheel related package missing.  Either install or set $BUILD_SIMPLE=1: '
	echo "import ensurepip" | tester "python3"         "python3-venv" "$prompt"
                                  tester "pip3 --version"  "python3-pip"  "$prompt"
    fi
}


# ---------- run tests

if [[ $# -gt 1 ]]; then
    tester "$1" "$2" "$3"

else
    run_default_tests

fi

# ---------- summary and follow-up

if [[ ! -s $OUT ]]; then echo "$0: all ok"; exit 0; fi

cmd="sudo apt-get install $(tr '\n' ' ' < $OUT)"
printf "\nYou probably want to run the following command:\n\n   ${cmd}\n\n"
read -p 'Shall I do this for you now (y/n)? ' ok
if [[ "$ok" == "y" ]]; then
    $cmd
    rm $OUT
    printf "\n\n$(tput setaf 2)OK $(tput sgr0), hopefully deps are good now; let's try continuing...\n\n"
    exit 0
fi    

rm $OUT
exit 1
