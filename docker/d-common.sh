# must be sourced rather than executed; sets various environment variables.

# --------------------

function dmap_update() {
    docker ps --format "{{.ID}} {{.Names}}" > /var/run/dmap
    chmod 644 /var/run/dmap
}

function pre_run() {
    docker rm ${NAME} >/dev/null 2>&1
}

function set_network() {
  if [[ -n "$1" ]]; then 
    NETWORK="--network $1"
  else
    NETWORK="--network docker1"
  fi
  if [[ -n "$2" ]]; then IP="$2"; echo "IP={$IP} (${NET})"; fi
  if [[ -n "$IP" ]]; then
    NETWORK="$NETWORK --ip=${IP}"
  fi
}

function determine_tag() {
  if [[ -n "$1" ]]; then
    TAG="$1"
  else
    if [[ -z "${TAG}" ]]; then
        if [[ $0 == *Run ]]; then TAG="live"; else TAG="latest"; fi
    fi
  fi
  VER="${REPO}:${TAG}"
  echo "Version ${VER}"
  REMOTE_VER="kstillson/repo0:${NAME}-${TAG}"
}    

# --------------------
# export vars

##DIR="$( cd "$( dirname "${0}" )" >/dev/null 2>&1 && pwd )"
DIR=$(pwd)
if [[ ! -v NAME ]]; then NAME=$(basename ${DIR}); fi
REPO="kstillson/${NAME}"
determine_tag

if [[ -z "${IP}" ]]; then
    IP=$(getent hosts ${NAME} | cut -f1 -d" ")
fi
set_network

VOLS=/rw/dv/${NAME}

SYSLOG_IP=$(getent hosts syslogdock | cut -f1 -d" ")
if [[ -z "${LOG}" ]]; then
    LOG="--log-driver=syslog --log-opt mode=non-blocking --log-opt max-buffer-size=4m --log-opt syslog-address=udp://${SYSLOG_IP}:1514 --log-opt syslog-facility=local3 --log-opt tag=${NAME}"
fi

BACKGROUND="-d"
XTRA=""

# --------------------------------------------------
# main

if [[ $0 == *Run ]]; then
  echo "running ${NAME}..."
  pre_run
  ( sleep 3; dmap_update ) &
fi

if [[ $0 == *common ]]; then
  dmap_update
  echo "updated dmap"
fi
