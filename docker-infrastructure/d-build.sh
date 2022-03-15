#!/bin/bash

# ---------- helper functions

function setlive() {
    REPO="$1"
    docker tag ${REPO}:live ${REPO}:prev     # backup old live tag
    docker tag ${REPO}:latest ${REPO}:live
    echo "${REPO} :latest set to :live"
}

function runtests() {
    if [[ ! -x ./Test ]]; then
	echo "WARNING- no tests provided.  Assuming pass."
	return 0
    fi
    ./Test -r
    return $?
}

# ---------- main

if [[ "$1" == "--cd" ]]; then
    shift
    newdir="$1"
    shift
    cd /root/docker-dev/$newdir || exit -2
fi


if [[ ! -f Dockerfile ]]; then
    echo "Please run from the directory containing the Dockerfile to build."
    exit -1
fi

# Any of the following variables can be overridden from the calling environment.

# Determine the version name of the image we are to build.
# By default, in a directory named "x", this will be "kstillson/x:latest".
NAME=${NAME:-$(basename $(pwd))}
REPO_BASE=${REPO_BASE:-kstillson}
REPO=${REPO:-${REPO_BASE}/${NAME}}
TAG=${TAG:-latest}
#
export VER=${VER:-${REPO}:${TAG}}

# What Docker network will we use for the build?  This is independent from the
# network the container will run in.  Often containers run in highly constrained
# environments (e.g. no or limited connectivity), but we need connectivity during
# the build to pull image contents.
export NETWORK=${NETWORK:-docker2}

# Defer to directory local logic, if provided.
if [[ -x ./Build ]]; then
    export CONTINUE="0"  # set to "1" to continue with default logic after returning, if desired.
    echo "Deferring to ./Build."
    . ./Build
    status=$?
    if [[ "$CONTINUE" != "1" ]]; then exit $status; fi
fi

# ----------  --setlive mode
# Alternate run mode setlive indicates we just tag #live to #latest and quit.
if [[ "$1" == "--setlive" || "$1" == "-s" ]]; then
    setlive ${REPO}
    exit 0
fi

# ---------- do the build

docker build --network $NETWORK -t ${VER} .
status=$?
if [[ "$status" != "0" ]]; then exit $status; fi

# If we're not in --auto mode, then we're done.

if [[ "$1" != "--auto" && "$1" != "-a" ]]; then exit 0; fi

# ---------- auto mode.  after build, test, and relabel if ok.

runtests
status=$?
if [[ "$status" != "0" ]]; then exit $status; fi

setlive ${REPO}

if [[ ! -f autostart ]]; then
    echo "successfully built and labeled $NAME"
    exit 0
fi

echo "successfully built and labeled ${NAME}; restarting"
/root/bin/d 01 $NAME
exit $?

