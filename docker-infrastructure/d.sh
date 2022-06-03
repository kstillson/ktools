#!/bin/bash

# Stop on first error...
set -e

cmd="$1"
shift || true
spec="$1"
shift || true
extra_flags="$@"

# Overridable from the environment
D_SRC_DIR=${D_SRC_DIR:-/root/docker-dev}
TIMEOUT=${TIMEOUT:-60}

# ----------------------------------------
# colorizer

BLUE='\x1b[01;34m'
CYAN='\x1b[36m'
GREEN='\x1b[01;32m'
MAGENTA='\x1b[35m'
RED='\x1b[0;31m'
YELLOW='\x1b[0;33m'
WHITE='\x1b[37m'
RESET='\x1b[00m'

function emit() { echo ">> $@" >&2; }
# stderr $2+ in color named by $1. insert "-" as $1 to skip ending newline.
function emitC() { if [[ "$1" == "-" ]]; then shift; nl=''; else nl="\n"; fi; color=${1^^}; shift; q="$@"; printf "${!color}${q}${RESET}${nl}" 2>&1 ; }
# stderr $2+ in color named by $1, but only if stdin is an interactive terminal.
function emitc() { color=${1^^}; shift; if [[ -t 1 ]]; then emitC "$color" "$@"; else printf "$@\n" >&2; fi; }

# ----------------------------------------
# run function from dlib

function dlib_run() {
    func="$1"
    param="$2"
    python3 -c "import kcore.docker_lib as D; print(D.${func}('${param}'))"
}


# ----------------------------------------
# select specific container to operate on.
# $1 is a prefix substring search spec.  If search matches more than 1, then 1st alphabetical is picked.

function is_up() {
  srch=$1
  sel=$(list-up | /bin/egrep "^${srch}") || true
  if [[ "$sel" == "" ]]; then echo "n"; return; fi
  echo "y"
}

function pick_container_from_up() {
  srch=$1
  sel=$(list-up | /bin/egrep "^${srch}")
  if [[ "$sel" == "" ]]; then echo "ERROR"; echo "no up container matching $srch" >&2; exit -1; fi
  head=$(echo "$sel" | head -1)
  if [[ "$sel" != "$head" ]]; then
    echo "selected { $sel } -> $head" | tr "\n" " " 1>&2
    echo "" 1>&2
    sel="$head"
  fi
  echo $sel
}

function pick_container_from_dev() {
  srch=$1
  cd ${D_SRC_DIR}
  sel=$(ls -1 ${srch}*/settings*.yaml | head -1 | cut -f1 -d/ )
  echo $sel
}

# ------------------------------
# generate lists of containers

function list-autostart() {
  cd ${D_SRC_DIR}
  if [[ -f dnsdock/autostart ]]; then echo dnsdock; fi
  if [[ -f kmdock/autostart ]]; then echo kmdock; fi
  ls -1 */autostart | cut -d/ -f1 | egrep -v 'dnsdock|kmdock'
}

function list-buildable() {
  cd ${D_SRC_DIR}
  ls -1 */Build | cut -d/ -f1
}

function list-up() {
  docker ps --format '{{.Names}}'
}

function list-testable() {
  cd ${D_SRC_DIR}
  ls -1 */Test | cut -d/ -f1
}

# ------------------------------
# operations complicated enough to need their own support functions

function down() {
  name="$1"
  if [[ "$name" == "" ]]; then emitc red "no such container"; return; fi
  docker stop -t 2 "${name}"
}

function up() {
  sel="$1"
  echo -n "Starting: $sel ${extra_flags}    "
  cd ${D_SRC_DIR}/$sel
  if [[ -x ./Run ]]; then
   echo "launching via legacy Run file"
    ./Run ${extra_flags}
  else
    # This substitution only supports a single param to the right of the "--".
    extra_flags=${extra_flags/-- /--extra-init=}
    /root/bin/d-run ${extra_flags} |& sed -e '/See.*--help/d' -e '/Conflict/s/.*/Already up/'
  fi
}

function test() {
  name=$1
  shift
  cd ${D_SRC_DIR}/${name}
  if [[ ! -x ./Test ]]; then
      emitc magenta "${name}: no test available; default to pass"
      echo "pass"
      return
  fi
  emitc blue "Testing ${name}."
  out="/rw/dv/TMP/${name}/test.out"
  rslt=$(./Test -r -o "${out}" "$@")
  if [[ "$rslt" == *"pass"* ]]; then
          emitc green "test passed    ( $out )."
          echo "pass"
  else
          emitc red "test failed. [ $rslt ]; log: $out"
          echo "fail"
  fi
}

function upgrade() {
  name=$1
  emit ""
  emitc blue "<> Building container ${name}"
  cd ${D_SRC_DIR}/${name}
  if [[ -r Makefile ]]; then
      make
  else
      ./Build
  fi
  if [[ "$(dlib_run latest_equals_live $name)" == "true" ]]; then
      emitc yellow "#latest == #live, so nothing more to do."
      return
  fi
  rslt=$(test $name)
  if [[ "$rslt" != "pass" ]]; then
      emitc yellow "result: $rslt (expected 'pass')"
      return 1
  fi
  if [[ -r Makefile ]]; then
      d-build -s
  else
      ./Build --setlive
  fi
  if [[ -f ./autostart ]]; then
      emitc blue "restarting $name"
      down $name
      sleep 1
      up $name
  fi
  emitc green "done with $name"
}

# ----------------------------------------
# internal

# Scan my own source code, find the main switch statement, extract and format showing the commands this script supports.
function myhelp_real() {
    awk -- '/case "\$cmd/,/esac/{ print }' $0 | egrep '(^#)|(^..[a-z])' | sed -e '/case /d' -e '/esac/d' -e '/*)/d' -e 's/##/~/' -e 's/).*;;//' | column -t -s~
}

# Wrapper around myhelp_real, optionally searching for $1 and auto-paging if on an interactive terminal.
function myhelp() {
    if [[ "$1" != "" ]]; then
        myhelp_real | egrep --color=auto "$1"
    else
        if [ -t 1 ] ; then myhelp_real | less
        else myhelp_real
        fi
    fi
}

# ------------------------------
# main:

case "$cmd" in

# Simple container management
  build | b) cd ${D_SRC_DIR}/$(pick_container_from_dev $spec); d-build ;;  ## Build container, name=$1
  down | stop | 0) down $(pick_container_from_up $spec) ;;                 ## Stop container $1
  restart | 01 | R)           ## Restart container $1
    name=$(pick_container_from_up $spec)
    echo "Shutting down $name"
    down $name
    sleep 1
    echo "Starting up $name"
    up $name
    ;;
  up | start | 1)             ## Launch container $1
    sel=$(pick_container_from_dev $spec)
    if [[ "$sel" == "" ]]; then
      echo "error- cannot find container to launch: $sel"
      exit 1
    fi
    if [[ "$(is_up $sel)" == "y" ]]; then
        echo "error- container already up: $sel"
        exit 1
    fi
    up $sel
    ;;

# container maintenance
  add-su | addsu)             ## Copy /bin/su into container $1
    name=$(pick_container_from_up $spec)
    docker cp ${D_SRC_DIR}/Etc/su ${name}:/bin
    echo "added /bin/su to ${name}"
    ;;
  add-debug | debug)          ## Add debugging tools and enter container $1
    name=$(pick_container_from_up $spec)
    docker cp ${D_SRC_DIR}/debugger/debug.tgz ${name}:/
    docker exec -u 0 ${name} tar x -k -o -z -f debug.tgz
    docker exec -u 0 -ti ${name} /bin/bash
    echo "back from container."
    ;;
  clean)                        ## Remove all sorts of unused docker cruft
    ## Don't want to use 'docker system prune' because would delete
    ## network 'docker2' which is not always in use, but is useful.
    ##
    ## WARNING: deletes all the "prev" images.  Only run this once
    ## confident we don't need to revert to any of those...
    ##
    docker container prune -f --filter "label!=live"
    docker image prune -f --filter "label!=live"
    docker volume prune -f --filter "label!=live"
    docker builder prune -f
    ;;
  hup | H | HUP | reload | r)   ## Send sigHup to proc 1 in container $1
    docker exec -u 0 $(pick_container_from_up $spec) kill -HUP 1
    ;;
  mini-dlna-refresh | M)        ## kds specific; rescan miniDlna library
    docker exec dlnadock /usr/sbin/minidlnad -R
    ;;
  test | t) test $(pick_container_from_dev $spec) ;;  ## Run tests for container $1
  upgrade | u) upgrade $(pick_container_from_dev $spec) ;;  ## Upgrade (build, test, relabel, restart) $1.

# command execution
  console | C)                  ## Enter console for $1
    docker attach $(pick_container_from_up $spec)
    echo "back from container console."
    ;;
  enter | exec-cmd | exec | e0 | e)   ## Interactive root shell in $1
    name=$(pick_container_from_up $spec)
    docker exec -u 0 -ti ${name} /bin/bash
    echo "back from container."
    ;;
  run) docker exec -u 0 $(pick_container_from_up $spec) "$@" ;;  ## Run command $2+ as root in $1
  shell) docker run -ti --user root --entrypoint /bin/bash ktools/$(pick_container_from_dev $spec):latest ;;  ## Start container $1 but shell overriding entrypoint.

# Multiple container management done in parallel
  build-all | ba)                    list-buildable | /usr/local/bin/run_para --align --cmd "$0 build @" --output d-build-all.out --timeout $TIMEOUT ;;  ## Build all buildable containers.
  down-all | stop-all | 0a | 00)     list-up | /usr/local/bin/run_para --align --cmd "$0 down @" --timeout $TIMEOUT ;;        ## Down all up containers
  restart-all | 01a | ra | RA | Ra)  list-up | /usr/local/bin/run_para --align --cmd "$0 restart @" --timeout $TIMEOUT ;;     ## Restart all up containers
  run-in-all | ria)                  list-up | /usr/local/bin/run_para --align --cmd "$0 run @ $spec $@" --output d-run-in-all.out --timeout $TIMEOUT ;; ## Run $1+ in root shell in all up containers
  test-all | ta)                     list-testable | /usr/local/bin/run_para --align --cmd "$0 test @" --output d-all-test.out --timeout $TIMEOUT ;;     ## Test all testable containers (#latest)
  test-all-prod | tap)               list-testable | /usr/local/bin/run_para --align --cmd "$0 test @ -p" --output d-all-test.out --timeout $TIMEOUT ;;  ## Test all testable production containers
  up-all | start-all | 1a | 11)      set +e; for i in $(list-autostart); do up "$i"; done ;;                                  ## Launch all autostart containers
  upgrade-all | ua)                  list-buildable | /usr/local/bin/run_para --align --cmd "$0 upgrade @" --output d-upgrade-all.out --timeout $TIMEOUT ;;  ## upgrade all containers
# various queries
  check-all-up | cau | ca | qa)       ## Check that all autostart containers are up.
      t=$(mktemp)
      list-up | cut -d' ' -f1 > $t
      missing=$(list-autostart | fgrep -v -f $t || true)
      rm $t
      if [[ "$missing" == "" ]]; then
          echo "all ok"
      else
          emitc red "missing containers: $missing"
      fi
      ;;
  cow-dir | cow)                       ## Print the copy-on-write layer dir location for $1
    name=$(pick_container_from_up $spec)
    dlib_run get_cow_dir "$name"
    ;;
  images | i) docker images ;;         ## List docker images
  is-up | iu) is_up $spec ;;           ## Is container up (y/n)
  get-ip | getip | get_ip | ip)        ## Print the IP address for $1
    set -o pipefail
    name="$(pick_container_from_up $spec)"
    if [[ "$name" == "" ]]; then exit -1; fi
    docker inspect "$name" | fgrep '"IPAddr' | tail -1 | cut -d'"' -f4
    ;;
  get-all-ips | ips)                   ## Print IPs for all up containers.
    t=$(mktemp)
    list-buildable > $t
    fgrep -f $t /root/docker-dev/dnsdock/files/etc/dnsmasq/dnsmasq.hosts | sort -k 2 | cut -f1-2
    rm $t
    ;;
  list-up | lu | ls | l | ps | p)      ## List all up containers
    docker ps --format '{{.Names}}@{{.ID}}@{{.Status}}@{{.Image}}@{{.Command}}@{{.Ports}}' | \
      sed -e 's/0.0.0.0/*/g' -e 's:/tcp::g' | \
      column -s @ -t | cut -c-${COLUMNS:-200} | sort -k6
    ;;
  log | logs) docker logs -ft --details $(pick_container_from_dev $spec) ;;  ## Print logs for $1
  pid) docker inspect --format '{{.State.Pid}}' $(pick_container_from_up $spec) ;;  ## Print main PID for $1
  spec | s) docker inspect $(pick_container_from_up $spec) ;;    ## Print docker details for $1
  veth)                                ## Print virtual eth name for $1
    idx=$(docker exec $(pick_container_from_up $spec) cat /sys/class/net/eth0/iflink)
    /bin/grep -l "$idx" /sys/class/net/veth*/ifindex | /usr/bin/cut -d/ -f5
    ;;

# instance lists
  list-autostart | la) list-autostart ;;   ## List auto-startable containers
  list-buildable | lb) list-buildable ;;   ## List buildable containers
  list-testable | lt) list-testable ;;     ## List containers with tests

# internal
  help | h) myhelp "$spec" ;;              ## display this help
  dup-check | check | chk) ( myhelp | fgrep -v '#' | tr '|' '\n' | tr -d ' ' | sort | uniq -c | fgrep -v '  1 ') || echo 'all ok' ;;  ## Check if any command-shortcuts are duplicated.
  *)
     echo "invalid command: $cmd"
     exit 3
     ;;

esac
