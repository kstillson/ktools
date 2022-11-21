#!/bin/bash

# Are we looking for "default" or "docker" dependencies?
dep_set="${1:-default}"

# List of packages that need to be installed.
OUT=$(mktemp)

# Term colorization
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
RESET=$(tput sgr0)

# ---------- dep checking infrastructure

# Use $test_cmd to see if $pkg is installed.  If it's ok, return 0.
# If not, issue $prompt, and append $pkg to the list of things that need
# to be installed (a file named $OUT), and return 1.
#
function tester() {
    test_cmd="$1"
    pkg="$2"
    prompt="$3"
    $test_cmd >&/dev/null
    if [[ $? == 0 ]]; then
	echo "${pkg}: installed ok"
	return 0
    fi
    echo "$pkg" >> $OUT
    printf "${YELLOW}PROBLEM: ${RESET}${prompt} ${pkg}\n"
    return 1
}

# -----

# Check that packages needed for all parts of the system are available.
#
function default_dep_checks() {
    prompt="required package appears to be missing: "
    tester "python3 --version"              "python3"                 "$prompt"
    tester "pytest-3 --version"             "python3-pytest"          "$prompt"
    tester "python3 -m pytest_timeout"      "python3-pytest-timeout"  "$prompt"
    echo "import psutil" | tester "python3" "python3-psutil"          "$prompt"
    if [[ "$KTOOLS_VARZ_PROM" == "1" ]]; then
	echo "import prometheus_client" | tester "python3" "python3-prometheus-client" "$prompt"
    fi

    # If not using $BUILD_SIMPLE, we need extra pieces to build Python wheels.
    if [[ "$BUILD_SIMPLE" != "1" ]]; then
	echo ""
	prompt='Python wheel related package missing.  Either install or set $BUILD_SIMPLE=1: '
	echo "import ensurepip" | tester "python3"         "python3-venv" "$prompt"
                                  tester "pip3 --version"  "python3-pip"  "$prompt"
    fi
}

# Check that packages needed for Docker container building & testing are available.
#
function docker_dep_checks() {
    prompt="package required for Docker appears to be missing: "
    tester "docker --help"      "docker.io"     "$prompt"
    tester "unzip -v"           "unzip"         "$prompt"
}

# -------------------- MAIN

case "$dep_set" in
     default) default_dep_checks ;;
     docker)  docker_dep_checks ;;
     *) echo "unknown dependency set requested: $dep_set"; exit -3 ;;
esac

# -- If $OUT is empty; we're all set.

if [[ ! -s $OUT ]]; then
    rm -f $OUT
    echo "$0: all ok"
    exit 0
fi

# -- Tell the user what needs to be done, and offer to do it for them.

cmd="sudo apt-get update; sudo apt-get install $(tr '\n' ' ' < $OUT)"
printf "\nYou probably want to run the following command:\n\n   ${cmd}\n\n"
read -p 'Shall I do this for you now (y/n)? ' ok
if [[ "$ok" == "y" ]]; then
    bash -c "$cmd"
    rm $OUT
    printf "\n\n${GREEN}OK ${RESET}, hopefully deps are good now; let's try continuing...\n\n"
    exit 0
fi

rm $OUT
exit 1
