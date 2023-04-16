#!/bin/bash

# Build a docker image, optionally also testing and pushing it.
# This is a "low level" builder that runs underneath the Makefile.
# i.e., make uses this, not the other way around.

# Really all this script does is call "docker build" with a few extra params,
# but those extra params can be important.

# You need to already be in the directory with the Dockerfile for the
# container you want to build, unless specifying the --cd flag, in which case
# the value of that flag names the container to be built.

# The "--setlive" (aka "-s") flag causes this script to not doing any
# actual building, but instead unconditionally tags the :latest version
# of the comtainer as :live.  It also creates a backup of the previously
# :live container with the tag :prev.

# The presence of a ":" in the --repo (or $DBUILD_REPO) setting will
# push the image image to the specified remote repo; this includes both
# normal building and --setlive operations.


# ---------- control constants

eval $(ktools_settings -cnq d_src_dir d_src_dir2 docker_exec vol_base build_params repo1 repo2)
       
# TODO:
DBUILD_PODMAN_SHARED_APK_CACHE="${DBUILD_PODMAN_SHARED_APK_CACHE:-1}"


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

    # ----- alpine shared cache (only support for podman, because need to bind-mount
    #       volumes during build command, which docker doesn't support.

    if [[ "$DBUILD_PODMAN_SHARED_APK_CACHE" == "1" &&
	      "$DOCKER_EXEC" == *"podman" ]]; then
	echo "adding shared APK cache dir..."
	apk_cache_dir="${VOL_BASE}/apk_cache_dir"
	mkdir -p $apk_cache_dir
	params="-v $apk_cache_dir:/var/cache/apk $params"
    elif [[ "$DBUILD_PODMAN_SHARED_APK_CACHE" != "2" ]]; then
	echo "adding tmpfs for APK cache dir..."
	params="--tmpfs /var/cache/apk $params"
    fi

    # ----- standard docker/podman build

    # NB: using tar-based trick from https://superuser.com/questions/842642/how-to-make-a-symlinked-folder-appear-as-a-normal-folder
    # to translate symlinks to their contents, even if they are outside the "context."  Needed for private.d contents.
    echo ""
    echo "tar -ch . | ${DOCKER_EXEC} build $params -t $target -"
          tar -ch . | ${DOCKER_EXEC} build $params -t $target -
    return $?
}

function run_push() {
    t="$1"
    echo "pushing $t"
    $DOCKER_EXEC push $t
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
    push="$2"
    ${DOCKER_EXEC} tag ${fullname}:live ${fullname}:prev  >&/dev/null   # backup old live tag
    ${DOCKER_EXEC} tag ${fullname}:latest ${fullname}:live
    echo "${fullname} :latest promoted to :live"
    if [[ "$push" == "1" ]]; then run_push "${fullname}:live"; fi
}

function try_dir() {
    d="$1"
    dir="."
    if [[ -f "$dir/Dockerfile" ]]; then cd "$dir"; return; fi
    dir="$D_SRC_DIR/$d"
    if [[ -f "$dir/Dockerfile" ]]; then cd "$dir"; return; fi
    dir="$D_SRC_DIR2/$d"
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

    # ---- default values

    just_live=0
    push=0
    run_tests=0

    build_params="$BUILD_PARAMS"
    cd="."
    name=""
    repo="$REPO1"
    tag="latest"

    # ---- parse flags

    while [[ $# -gt 0 ]]; do
        flag="$1"
        case "$flag" in
            --setlive | -s) just_live=1 ;;                ## run mode: just tag :latest to :live and exit
            --test | -t) run_tests=1 ;;                   ## run mode: build and run tests, then exit

            --build_params | -b) build_params="$1" ;;     ## params for "docker build" (defaults to $BUILD_PARAMS)
            --cd) cd="$2"; shift ;;                       ## location of Dockerfile to build (can be relative to $D_SRC_DIR)
            --name) name="$1"; shift ;;                   ## output image name; defaults to basename of directory
            --repo) repo="$1"; shift ;;                   ## repo to build image into; defaults to $REPO1
            --tag) tag="$1"; shift ;;                     ## tag to set after build.  defaults to ":latest"

            --help | -h) myhelp; exit 0 ;;
            *) echo "unknown flag: $flag (try --help)"; exit -1 ;;
        esac
        shift
    done

    # ---- prep

    try_dir $cd   # Make sure there's a Dockerfile in our working dir.

    if [[ "$name" == "" ]]; then name=$(basename $(pwd)); fi

    if [[ "$repo" == *":"* ]]; then push="1"; fi

    fullname="${repo}/${name}"
    target="${fullname}:${tag}"

    # ---- build

    if [[ $just_live == 1 ]]; then setlive "$fullname" "$push" ; exit $?; fi

    run_build "$target" "$build_params" || exit $?

    if [[ "$push" == "1" ]]; then run_push "$target"; fi

    # ---- test

    if [[ $run_tests == 1 ]]; then
	run_tests || exit $?
	echo "TESTS PASS"
    fi
    exit 0
}

main "$@"
