#!/bin/bash

# TODO(doc)


# ---------- control constants
# can be overriden from calling environment or flags.

DOCKER_BASE_DIR=${DOCKER_BASE_DIR:-~/docker-dev}
DOCKER_EXEC="${DOCKER_EXEC:-docker}"
DBUILD_PARAMS="${DBUILD_PARAMS:-}"
DBUILD_REPO="${DBUILD_REPO:-ktools}"


# ---------- business logic

function run_build() {
    target="$1"
    params="$2"

    # ----- defer to local ./Build file, if provided

    if [[ -r ./Build ]]; then
        export CONTINUE="0"  # set to "1" to continue with default logic after returning, if desired.
        echo "Deferring to ./Build."
        . ./Build
        status=$?
        if [[ "$CONTINUE" != "1" ]]; then return $status; fi
        echo "continuing after ./Build"
    fi

    # ----- standard docker build
    ${DOCKER_EXEC} build $params -t $target .
    return $?
}

function run_tests() {
    if [[ ! -x ./Test ]]; then
        echo "WARNING- no tests provided.  Assuming pass."
        return 0
    fi
    ./Test -r
    return $?
}

function setlive() {
    fullname="$1"
    ${DOCKER_EXEC} tag ${fullname}:live ${fullname}:prev  >&/dev/null   # backup old live tag
    ${DOCKER_EXEC} tag ${fullname}:latest ${fullname}:live
    echo "${fullname} :latest promoted to :live"
}

function try_dir() {
    dir="$1"
    if [[ -f "$dir/Dockerfile" ]]; then cd "$dir"; return; fi
    dir="$DOCKER_BASE_DIR/$dir"
    if [[ -f "$dir/Dockerfile" ]]; then cd "$dir"; return; fi
    echo "unable to find $1/Dockerfile.  Run from directory with Dockerfile or use --cd flag."
    exit -2
}

# ---------- dynamic help

function myhelp() {
    grep "##" "$0" | sed -e 's/\t/        /' | egrep '(^ *#)|(^ *--)|(^        [a-z])' | sed -e '/case /d' -e '/esac/d' -e 's/^    //' -e 's/##/~/' -e 's/).*;;//' | column -t -s~
}


# ---------- main

function main() {

    # ---------- default values

    auto_mode=0
    just_live=0
    run_tests=0

    build_params="$DBUILD_PARAMS"
    cd="."
    name=""
    repo="$DBUILD_REPO"
    tag="latest"

    # ---------- parse flags

    while [[ $# -gt 0 ]]; do
        flag="$1"
        case "$flag" in
            --auto | -a) auto_mode=1; run_tests=1 ;;      ## run mode: build, test, promote to live (if pass) and restart (if autostart)
            --setlive | -s) just_live=1 ;;                ## run mode: just tag :latest to :live and exit
            --test | -t) run_tests=1 ;;                   ## run mode: build and run tests, then exit

            --build_params | -b) build_params="$1" ;;     ## params for "docker build" (defaults to $DBUILD_PARAMS)
            --cd) cd="$1"; shift ;;                       ## location of Dockerfile to build (can be relative to $DOCKER_BASE_DIR)
            --name) name="$1"; shift ;;                   ## output image name; defaults to basename of directory
            --repo) repo="$1"; shift ;;                   ## repo to build image into; defaults to $DBUILD_REPO
            --tag) tag="$1"; shift ;;                     ## tag to set after build.  defaults to ":latest"

            --help | -h) myhelp; exit 0 ;;
            *) echo "unknown flag: $flag (try --help)"; exit -1 ;;
        esac
        shift
    done

    try_dir $cd   # Make sure there's a Dockerfile in our working dir.

    if [[ "$name" == "" ]]; then name=$(basename $(pwd)); fi

    fullname="${repo}/${name}"
    target="${fullname}:${tag}"

    if [[ $just_live == 1 ]]; then setlive $fullname ; exit $?; fi

    run_build "$target" "$build_params" || exit $?

    if [[ $run_tests == 1 ]]; then
	run_tests || exit $?
	echo "TESTS PASS"
    fi

    # If not in auto mode, we're done.
    if [[ $auto_mode == 0 ]]; then
        echo "successfully built $target"
        exit 0
    fi

    # ----- auto mode

    setlive $fullname

    if [[ -f autostart ]]; then
        /root/bin/d 01 $name || exit $?
    fi
    exit 0
}

main "$@"
