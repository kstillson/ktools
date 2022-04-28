#!/bin/bash

# Better doc
#
# What Docker network will we use for the build?  This is independent from the
# network the container will run in.  Often containers run in highly constrained
# environments (e.g. no or limited connectivity), but we need connectivity during
# the build to pull image contents.
#export NETWORK=""


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

# Any of the following variables can be overridden from the calling environment,
# or from the file private.d/build-env.
#
# As an example, if you put tight outbound restrictions on the default docker
# network, but containers need to be about to reach out during construction to
# install or update packages, you probably want to create a private.d/build-env
# with something like:   NETWORK="--network docker2"

if [[ -r "private.d/build-env" ]]; then source private.d/build-env; fi


# Determine the version name of the image we are to build.
# By default, in a directory named "x", this will be "ktools/x:latest".
NAME=${NAME:-$(basename $(pwd))}
REPO_BASE=${REPO_BASE:-ktools}
REPO=${REPO:-${REPO_BASE}/${NAME}}
TAG=${TAG:-latest}
#
export VER=${VER:-${REPO}:${TAG}}

# ----------  --setlive mode
# Alternate run mode setlive indicates we just tag #live to #latest and quit.
if [[ "$1" == "--setlive" || "$1" == "-s" ]]; then
    setlive ${REPO}
    exit 0
fi

# Defer to directory local logic, if provided.
if [[ -r ./Build ]]; then
    export CONTINUE="0"  # set to "1" to continue with default logic after returning, if desired.
    echo "Deferring to ./Build."
    . ./Build
    status=$?
    if [[ "$CONTINUE" != "1" ]]; then exit $status; fi
    echo "continuing after ./Build"
fi

# ---------- do the build

docker build $NETWORK -t ${VER} .
status=$?
if [[ "$status" != "0" ]]; then exit $status; fi

# ---------- next steps

# If we're in --test mode, run the tests and then exit.
if [[ "$1" == "--test" || "$1" == "-t" ]]; then
    runtests
    exit $?
fi

# If we're NOT in --auto mode, then we're done.
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

