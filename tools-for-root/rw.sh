#!/bin/bash

# This tool helps admins deal with read-only root and overlay-root file systems.
#
# Run without params to open an interactive subshell in +rw mode, or provide a
# single command to run +rw mode.  If neither read-only-root nor overlay-root
# are in use, this command is a safe no-op (so when running a command on many
# machines, it should generally be safe to prefix it with "rw ").
#
# running "rw --sync" will take any changes already made to an overlay upper
# filesystem (generally a ramdisk), and transfer them to the lower filesystem
# (even if it is read-only), which should persist them.  The upper dir change
# files are left in-place, but are now essentially no-ops.
# NB: search for "exclude_file" below to see what files are not transferred.
#
# the exit status from the subshell should be echoed to the caller of "rw".
#
# some flags can also query whether read-only or overlay-root is in use.


. blib
set -e # stop at first error

# ---------- env (settings that can be overriden from caller's environment)

export DEBUG="${DEBUG:-}"

export LOWERDIR="${LOWERDIR:-/media/root-ro}"
export UPPERDIR="${UPPERDIR:-/media/root-rw/overlay}"
if [[ ! -d "$UPPERDIR" ]]; then UPPERDIR=/media/root-rw/root; fi


# ---------- defaults for globals

MOUNTS=""    # bind-mounts to remove upon exit
OVERLAY=""   # detected an overlay root fs ?
RO_LOWER=""  # lowerdir of overlay is read-only ?
RO_ROOT=""   # root dir is read-only ?
RM_FILES=""  # temp files to remove upon exit


# ---------- helpers

debug()   { if [[ "$DEBUG" == "1" ]]; then emitc cyan "DEBUG: $@"; fi; }
fail()    { emitc red "FATAL $@"; exit 1; }
info()    { emitc blue "INFO: $@"; }
warning() { emitc yellow "WARNING: $@"; }

bind_mount() {
    src="$1"; dest="$2"
    mount -o bind "$src" "$dest" >&/dev/null && debug "bind-mounted $src -> $dest" || fail "Unable to bind-mount $src -> $dest"
    MOUNTS="$MOUNTS $dest"
}

make_ro() {
    mount -o remount,ro "$1" >&/dev/null && debug "back to read-only: $1" || warning "Unable to set $1 to read-only mode."
}

make_rw() {
    mount -o remount,rw "$1" >&/dev/null && debug "made writable: $1" || fail "Unable to set $1 to read-write mode."
}

subshell() {
    if [[ "$@" == "" ]]; then
	info "entering +rw shell"
	bash -i
    else
	debug "entering +rw shell with cmnd: $@"
	echo "$@" | bash -i
    fi
}

clean_exit() {
    debug "exit cleanup (bind-mounts: ${MOUNTS})"
    if [[ -n "$MOUNTS" ]];   then umount $MOUNTS || warning "Unable to unmount $d"; fi
    if [[ -n "$RM_FILES" ]]; then rm -rf $RM_FILES || warning "Unable to remove $f"; fi
    if [[ -n "$RO_ROOT" ]];  then make_ro /; fi
    if [[ -n "$RO_LOWER" ]]; then make_ro $LOWERDIR; fi
}

# ---------- main

trap clean_exit EXIT HUP INT QUIT TERM

grep  -q ' / overlay'         /proc/mounts && OVERLAY=1
egrep -q ' / .*[ ,]ro,'       /proc/mounts && RO_ROOT=1
egrep -q " ${LOWERDIR} .*ro," /proc/mounts && RO_LOWER=1


# ---- simple query modes

if [[ "$1" == *"query" ]]; then echo "overlay: ${OVERLAY:-0}  root_ro: ${RO_ROOT:-0}  lower_ro: ${RO_LOWER:-0}"; exit 0

elif [[ "$1" == "is_overlay" ]]; then echo "${OVERLAY:-0}"; exit 0

elif [[ "$1" == "is_root_ro" ]]; then echo "${RO_ROOT:-0}"; exit 0

elif [[ "$1" == "is_lower_ro" ]]; then echo "${RO_LOWER:-0}"; exit 0


# ---- sync mode

elif [[ "$0" == *"rw-sync" || "$1" == *"sync" ]]; then
    dirs="${2:-*}"
    info "mode: sync overlay ${UPPERDIR}/$dirs -> ${LOWERDIR}/"
    if [[ -z "$OVERLAY" ]]; then fail "cannot run sync on non-overlay system"; fi

    if [[ -n "$RO_LOWER" ]]; then make_rw $LOWERDIR; fi

    exclude_file=$(mktemp)
    cat >$exclude_file <<EOF
*fstab
*cache*
*clock*
*lock*
media/
resolv.conf
*swap*
systemd-private*/
*timer*
tmp/
var/lib/NetworkManager/internal-*
var/lib/NetworkManager/timestamps
var/log/
var/tmp/
EOF
    RM_FILES="$exclude_file $RM_FILES"

    info "updating changed files"
    cd $UPPERDIR
    erun rsync -auvP --relative --min-size=1 --exclude-from $exclude_file $dirs $LOWERDIR

    info "removing deleted files"
    find $dirs -type c -print | sed -e 's:^./::' -e "s:^:${LOWERDIR}/:" -e '/fstab/d' | tee /dev/stderr | xargs -I@ rm -rf "@"


# ---- simple read-only root mode

elif [[ -n "$RO_ROOT" ]]; then
    debug "mode: read-only root"
    make_rw /
    subshell


# ---- overlay mode

elif [[ -n "$OVERLAY" ]]; then
    debug "mode: overlay"

    # make sure we have a valid $UPPERDIR
    if [[ ! -d "$UPPERDIR" ]]; then fail 'cannot find upperdir (try setting $UPPERDIR)'; fi

    # setup bind-mounts to support chroot
    for d in dev proc run sys /etc/resolv.conf; do bind_mount "/$d" "$LOWERDIR/$d"; done

    # make current upperdir visible inside the chroot
    dest=${LOWERDIR}/media/overlay-rw
    mkdir -p $dest
    bind_mount $LOWERDIR $dest

    # make lowerdir +rw, if needed.
    if [[ -n "$RO_LOWER" ]]; then make_rw $LOWERDIR; fi

    if [[ "$@" == "" ]]; then
	info "entering non-overlay chroot"
	chroot $LOWERDIR /bin/bash -i
    else
	debug "entering non-overlay chroot: $@"
	echo "$@" | chroot ${LOWERDIR} /bin/bash
    fi


# ---- no-op mode

else
    info "Neither overlay nor read-only root; $0 is a no-op."
    subshell

fi

status=$?
if [[ "$status" == "0" ]]; then info "$0 completed; exit status: $status"   # info so user knows they're out of the subshell.
else warning "$0 completed; exit status: $status"
fi
exit $status
