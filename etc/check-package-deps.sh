#!/bin/bash

#- make python3-pytest python3-pytest-timeout python3-psutil
#- if not $BUILD_SIMPLE:   python3-venv  python3-pip
#- if building docker containers:   docker.io

OUT=$(mktemp)

function tester() {
    cmd="$1"
    pkg="$2"
    prompt="$3"
    $cmd >&/dev/null && return 0
    fix="sudo apt-get install -y $pkg"
    echo "$fix" >> $OUT
    printf "$(tput setaf 3)PROBLEM: $(tput sgr0)${prompt} ${pkg}\n"
    return 1
}

# ---------- run tests

prompt="required package appears to be missing: "
tester "python3 --version"              "python3"                 "$prompt"
tester "pytest-3 --version"             "pytest3-pytest"          "$prompt"
tester "python3 -m pytest_timeout"      "python3-pytest-timeout"  "$prompt"
echo "import psutil" | tester "python3" "python3-psutil"          "$prompt"

if [[ "$BUILD_SIMPLE" != "1" ]]; then
    echo ""
    prompt='Python wheel related package missing.  Either install or set $BUILD_SIMPLE=1: '
    echo "import ensurepip" | tester "python3"         "python3-venv" "$prompt"
                              tester "pip3 --version"  "python3-pip"  "$prompt"
fi

echo ""
prompt="Docker is needed if you are going to build/use containers: "
tester "docker --help" "docker.io" "$prompt"

# ---------- summary and follow-up

if [[ ! -s $OUT ]]; then echo "$0: all ok"; exit 0; fi

printf "\nYou probably want to run the following commands:\n\n"
cat $OUT

echo ""
read -p 'Shall I do this for you now (y/n)? ' ok
if [[ "$ok" == "y" ]]; then
    . $OUT
    rm $OUT
    printf "\nok, hopefully that's fixed. try running your previous command again."
    exit 2
fi    

rm $OUT
exit 1
