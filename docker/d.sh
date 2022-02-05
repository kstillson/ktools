#!/bin/bash

set -e

cmd="$1"
shift || true
spec="$1"
shift || true
extra_flags="$@"

DLIB_DEFAULT="$(dirname $0)/d_lib.py"

# Overridable from the environment
D_SRC_DIR=${D_SRC_DIR:-/root/docker-dev}
DLIB=${DLIB:-$DLIB_DEFAULT}
TIMEOUT=${TIMEOUT:-60}

# ----------------------------------------

function emit() { echo ">> $@" >&2; }

function pick_container_from_up() {
  srch=$1
  sel=$(list-up | /bin/egrep "^${srch}")
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

function down() {
  name="$1"
  docker stop ${name}
}

function up() {
  sel="$1"
  echo "Starting: $sel ${extra_flags}"
  cd ${D_SRC_DIR}/$sel
  if [[ -x ./Run ]]; then
   echo "launching via legacy Run file"
    ./Run ${extra_flags}
  else
    # This substitution only supports a single param to the right of the "--".
    extra_flags=${extra_flags/-- /--extra-init=}
    /root/bin/d-run ${extra_flags}
  fi
}

function test() {
  name=$1
  shift
  cd ${D_SRC_DIR}/${name}
  if [[ ! -x ./Test ]]; then
      emit "${name}: no test available; default to pass"
      echo "pass"
      return
  fi
  emit "Testing ${name}."
  out="/rw/dv/TMP/${name}/test.out"
  rslt=$(./Test -r -o "${out}" "$@" | tail -1)
  if [[ "$rslt" == "pass" ]]; then
	  emit "test passed    ( $out )."
	  echo "pass"
  else
	  emit "test failed. [ $rslt ]; log: $out"
	  echo "fail"
  fi
}

function upgrade() {
  name=$1
  emit ""
  emit "<> Building container ${name}"
  cd ${D_SRC_DIR}/${name}
  ./Build
  if [[ "$($DLIB latest_equals_live $name)" == "true" ]]; then
      emit "#latest == #live, so nothing more to do."
      return
  fi
  rslt=$(test $name)
  if [[ "$rslt" != "pass" ]]; then
      return 1
  fi
  ./Build --setlive
  if [[ -f ./autostart ]]; then
      emit "restarting $name"
      down $name
      sleep 1
      up $name
  fi
  emit "done with $name"
}

# ----------------------------------------
# internal

function myhelp() {
    awk -- '/case "\$flag/,/esac/{ print } /case "\$cmd/,/esac/{ print }' $0 | sed -e '/[#)]/!d' -e '/(/d' -e '/*)/d' -e 's/).*$//' -e '/##/d'
}

case "$cmd" in

  # Simple container management
  build | b) cd ${D_SRC_DIR}/$(pick_container_from_dev $spec); ./Build ;;
  down | stop | 0) down $(pick_container_from_up $spec) ;;
  restart | 01 | R)
    name=$(pick_container_from_up $spec)
    echo "Shutting down $name"
    down $name
    sleep 1
    echo "Starting up $name"
    up $name
    ;;
  up | start | 1)
    sel=$(pick_container_from_dev $spec)
    up=$(pick_container_from_up $sel)
    if [[ "$up" != "" ]]; then
	echo "error- container already up: $sel"
	exit 1
    fi
    up $sel
    ;;

# container maintenance
  add-su | addsu)
    name=$(pick_container_from_up $spec)
    docker cp ${D_SRC_DIR}/Etc/su ${name}:/bin
    echo "added /bin/su to ${name}"
    ;;
  add-debug | debug)
    name=$(pick_container_from_up $spec)
    docker cp ${D_SRC_DIR}/debugger/debug.tgz ${name}:/
    docker exec -u 0 ${name} tar x -k -o -z -f debug.tgz
    docker exec -u 0 -ti ${name} /bin/bash
    echo "back from container."
    ;;
  clean)
    ## Don't want to use 'docker system prune' because would delete
    ## network 'docker2' which is not always in use, but is useful.
    ##
    ## WARNING: deletes all the "prev" images.  Only run this once
    ## confident we don't need to revert to any of those...
    ##
    docker container prune -f --filter label!=live
    docker image prune -f -a --filter label!=live
    docker volume prune -f --filter label!=live
    docker builder prune -f
    ;;
  dmap|map)
    docker ps --format "{{.ID}} {{.Names}}" > /var/run/dmap
    chmod 644 /var/run/dmap
    ;;
  hup | H | HUP | reload | r)
    docker exec -u 0 $(pick_container_from_up $spec) kill -HUP 1
    ;;
  mini-dlna-refresh | M)
    echo "@@ not ready yet"
    exit -1
    lxc-attach -n plex -- /usr/sbin/service minidlna force-reload
    ;;
  test | t) test $(pick_container_from_dev $spec) ;;
  upgrade | u) upgrade $(pick_container_from_dev $spec) ;;

# command execution
  console | C)
    docker attach $(pick_container_from_up $spec)
    echo "back from container console."
    ;;
  enter | exec-cmd | exec | e0 | e)
    name=$(pick_container_from_up $spec)
    docker exec -u 0 -ti ${name} /bin/bash
    echo "back from container."
    ;;
  run) docker exec -u 0 $(pick_container_from_up $spec) "$@" ;;
  shell) docker run -ti --user root --entrypoint /bin/bash kstillson/$(pick_container_from_dev $spec):latest ;;

# Multiple container management done in parallel
  build-all | ba)                    list-buildable | /usr/local/bin/run_para --align --cmd "$0 build @" --output d-build-all.out --timeout $TIMEOUT ;;
  down-all | stop-all | 0a | 00)     list-up | /usr/local/bin/run_para --align --cmd "$0 down @" --timeout $TIMEOUT ;;
  restart-all | 01a | ra | RA | Ra)  list-up | /usr/local/bin/run_para --align --cmd "$0 restart @" --timeout $TIMEOUT ;; 
  run-in-all | ria)                  list-up | /usr/local/bin/run_para --align --cmd "$0 run @ $spec $@" --output d-run-in-all.out --timeout $TIMEOUT ;;
  test-all | ta)                     list-testable | /usr/local/bin/run_para --align --cmd "$0 test @" --output d-all-test.out --timeout $TIMEOUT ;;
  test-all-prod | tap)               list-testable | /usr/local/bin/run_para --align --cmd "$0 test @ -p" --output d-all-test.out --timeout $TIMEOUT ;;
  up-all | start-all | 1a | 11)      list-autostart | /usr/local/bin/run_para --align --cmd "$0 up @" --timeout $TIMEOUT ;;

# various queries
  check-all-up | cau | ca | qa)
      t=$(mktemp)
      list-up | cut -d' ' -f1 > $t
      missing=$(list-autostart | fgrep -v -f $t || true)
      rm $t
      if [[ "$missing" == "" ]]; then
	  echo "all ok"
      else
	  emit "missing containers: $missing"
      fi
      ;;
  cow-dir | cow)
    name=$(pick_container_from_up $spec)
    $DLIB get_cow_dir "$name"
    ;;
  images | i) docker images ;;
  get-ip | getip | get_ip | ip)
    set -o pipefail
    name="$(pick_container_from_up $spec)"
    if [[ "$name" == "" ]]; then exit -1; fi
    docker inspect "$name" | fgrep '"IPAddr' | tail -1 | cut -d'"' -f4
    ;;
  get-all-ips | ips)
    t=$(mktemp)
    list-buildable > $t
    fgrep -f $t /root/docker-dev/dnsdock/files/etc/dnsmasq/dnsmasq.hosts | sort -k 2 | cut -f1-2
    rm $t
    ;;
  list-up | lu | l | ps | p)
    docker ps --format '{{.Names}}@{{.ID}}@{{.Status}}@{{.Image}}@{{.Command}}@{{.Ports}}' | \
      sed -e 's/0.0.0.0/*/g' -e 's:/tcp::g' | \
      column -s @ -t | cut -c-$COLUMNS | sort
    ;;
  log | logs) docker logs -ft --details $(pick_container_from_dev $spec) ;;
  pid) docker inspect --format '{{.State.Pid}}' $(pick_container_from_up $spec) ;;
  spec | s) docker inspect $(pick_container_from_up $spec) ;;
  veth)
    idx=$(docker exec $(pick_container_from_up $spec) cat /sys/class/net/eth0/iflink)
    /bin/grep -l "$idx" /sys/class/net/veth*/ifindex | /usr/bin/cut -d/ -f5
    ;;

# instance lists
  list-autostart | la) list-autostart ;;
  list-buildable | lb) list-buildable ;;
  list-testable | lt) list-testable ;;

# internal
  help | h) myhelp ;;
  dup-check | check | chk) ( myhelp | fgrep -v '#' | tr '|' '\n' | tr -d ' ' | sort | uniq -c | fgrep -v '  1 ') || echo 'all ok' ;;
  *)
     echo "invalid command: $cmd"
     exit 3
     ;;

esac
