# must be sourced rather than executed; sets various environment variables.

function debug_mode() {
  echo "debug mode..."
  BACKGROUND=""
  LOG="--log-driver=none"
  NAME="dbg-${NAME}"
  XTRA="$XTRA --rm"

  # Allow caller to specify extra/override things to do for debug mode.
  t=$(type -t debug_mode_extra || true)
  if [[ "$t" == "function" ]]; then debug_mode_extra; fi
}

temp=$(getopt -o dnlsSt::T --long debug,network,latest,setlive,set-live,set_live,shell,strace,tag::,test -n "$0" -- "$@")
if [ $? -ne 0 ]; then exit -1; fi
eval set -- $temp

if [[ -z "${REPO}" ]]; then . /root/bin/d-common.sh; fi

while true; do case "$1" in
  -d|--debug) debug_mode; shift ;;
  -n|--network) set_network docker2 192.168.3.99; echo "IP: ${IP}"; shift ;;
  -l|--latest) determine_tag latest; shift ;;
  -s|--setlive|--set-live|--set_live) docker tag ${REPO}:live ${REPO}:prev; docker tag ${REPO}:latest ${REPO}:live; exit 0 ;;
  -S|--shell) determine_tag latest; XTRA="$XTRA --user 0 -ti --entrypoint /bin/bash"; debug_mode; echo "override entrypoint to shell..."; shift ;;
  --strace) XTRA="$XTRA --security-opt seccomp:unconfined "; shift ;;
  -t|--tag) determine_tag "$2"; shift 2 ;;
  -T|--test) debug_mode; determine_tag latest; set_network docker1 192.168.2.99; NAME="test-$NAME"; docker rm ${NAME} >/dev/null 2>&1; shift ;;
  --) shift; break ;;
  *) echo "ouch"; exit 1 ;;
esac; done

