#!/bin/bash

# Notify upon task completion
# $1 can be a pid # to wait for, or
#           a pgrep search expression (optional -f for full match), or
#           blank, to notify upon run, e.g.:  ./run-long-op | N

. blib

# ---- defaults

set -a  # communicate to our own background subprocess via already-parsed vars.
BEEP="${BEEP:-0}"            # run "beep" command upon notify
DEST="${DEST:-root}"         # set to "-" to skip email
FULL="${FULL:-}"             # grep require full path match
MAX_MATCH="${MAX_MATCH:-5}"  # about if match more than this many processes in grep
PID="${PID:-}"
SUBJ="${SUBJ:-task notification}"

# ---- cli args

POS=()
while [[ $# -gt 0 ]]; do
    case $1 in
	-b|--beep)  BEEP="1"          ;;
	-d|--dest)  DEST="$2"; shift  ;;
	-f|--full)  FULL="-f"         ;;
	-p|--pid)   PID="$2";  shift  ;;
	-s|--subj)  SUBJ="$2"; shift  ;;
	*)          POS+=("$1")       ;;
    esac
    shift
done

ARG1="${ARG1:-${POS[0]}}"
if [[ -n "$ARG1" && -d "/proc/$ARG1" ]]; then PID=$ARG1; fi

# ---- helpers

function die() { emitc red "$@"; exit -2; }


# ---------- main ----------

# ---- run self in background

if [[ "$DEBUG" == "1" ]]; then emitc cyan "DEBUG: beep=$BEEP dest=$DEST full=$FUL pid=$PID arg1=$ARG1 _bg=$_BG"; fi

if [[ -z "$_BG" ]]; then
    _BG=1 $0 &
    emitc green "ok; notifier pid: $!"
    sleep 0.5; echo ""
    exit 0
fi

# ---- pid waiting

if [[ -n "$PID" ]]; then
    if [[ ! -d "/proc/$PID" ]]; then die "pid $PID not found; cannot wait on it."; fi
    name=$(cat /proc/$PID/cmdline | tr '\0' '@' | cut -d@ -f1)
    title="pid $PID ($name)"
    emitc cyan "waiting for: $title"
    tail --pid $PID -f /dev/null

# ---- pgrep waiting

elif [[ -n "$ARG1" ]]; then
    tfile=$(mktemp)
    trap "rm -f $tfile" EXIT
    pgrep -O 2 -a $FULL "$ARG1" > $tfile || die "no such process found: $ARG1"
    cnt=$(wc -l $tfile | cut -d' ' -f1)
    if [[ "$cnt" -gt "$MAX_MATCH" ]]; then die "too many processes matched ($cnt > $MAX_MATCH)"; fi
    if [[ "$cnt" -gt 1 ]]; then emitc yellow "WARNING- pgrep matched multiple processes"; fi
    title=$(cat $tfile | tr '\n' ';')
    emitc cyan "waiting for: "
    cat $tfile
    pidwait -O 2 $FULL "$ARG1"

# ---- no spec waiting (presumably tacked onto the end of a cmd sequence)

else
    title="(previous process chain)"
fi

# ---- check if stdin piped; if so, use that as msg content

msg1="completed wait for: $title\n"
msg="${msg1}"

# ---- notification(s)

if [[ "$BEEP" == "1" ]]; then beep; fi
if [[ -n "$DEST" && "$DEST" != "-" ]]; then echo -e "$msg" | mail -s "$SUBJ" "$DEST"
else emitc cyan "not sending email"
fi

emitc green "$msg1"

exit 0
