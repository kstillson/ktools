#!/bin/bash

# High level container control and maintenance routines.

# NB: This script hard-codes the assumption that the container name matches
# the dirname containing settings.yaml.  (For the most part), it doesn't
# understand the idea of alternately-named settings files, or that a settings
# file can change the name of a container.

set -e   # Stop on first error...

source /root/bin/blib  # for erun, emit*.  needs full path for when run via logrotate.

cmd="$1"
shift || true
spec="$1"
shift || true
extra_flags="$@"

# Make sure /root/bin is on the path (needed by things like cron and logrotate
# that don't use .bashrc or .profile).
if [[ "$PATH" != "/root/bin"* ]]; then PATH="/root/bin:${PATH}"; fi

# Load settings
eval $(ktools_settings -cn docker_exec d_src_dir d_src_dir2 timeout)
TIMEOUT=${TIMEOUT:-60}

if [[ "$TESTER" == "" ]]; then
    if [[ "$KTOOLS_DRUN_TEST_PROD" == "1" ]]; then
	TESTER="./Test-prod"
    else
	TESTER="./Test"
    fi
fi


# ----------------------------------------
# general support

function cd_sel() { cd $(find_dir $1); }

function dlib_run() {
    func="$1"
    param="$2"
    python3 -c "import kcore.docker_lib as D; print(D.${func}('${param}'))"
}

# stdin a list of pathnames, on per-line.  output is the basename of the dirname for each input.
# e.g. /q/x/y/z -> y
# this is more efficient that calling $(basename $(dirname $i)) for each line in a list.
function dirnames() {
    sed -e 's:/[^/]*$::' -e 's:^.*/::'
}

# Given a container name, dir, or settings path, return the dir (no partial matching).
function find_dir() {
    sel="$1"
    if [[ "$sel" == "" ]]; then sel=$(cat); fi            # Accept sel either from args or stdin (i.e. as filter)

    if [[ -d "$sel" ]]; then echo "$sel"; return; fi      # given the container directory already.
    if [[ -f "$sel" ]]; then dirname $sel; return; fi     # given the settings file (or any other file in the dir)
    if [[ -d "${D_SRC_DIR}/$sel" ]]; then echo "${D_SRC_DIR}/$sel"; return; fi     # given the container name
    if [[ -d "${D_SRC_DIR2}/$sel" ]]; then echo "${D_SRC_DIR2}/$sel"; return; fi   # given the private container name
    emitC red "cannot find directory for selection: $sel"
    return 1
}

function get_autostart_wave() {
    sel="$1"
    dir=$(find_dir $sel)
    if [[ -f ${dir}/autostart ]]; then
	wave="$(cat ${dir}/autostart)"
    else
	wave=$(fgrep "autostart:" ${dir}/settings.yaml 2>/dev/null | sed -e 's/^.*: *//')
    fi
    if [[ "$wave" == *"host="* ]]; then
	required_host=$(echo "$wave" | sed -e s'/^.*host=//' -e 's/,.*$//')
	if [[ "$required_host" != $(hostname) ]]; then
	    emitC yellow "info: skipping $sel autostart; not required host ($required_host)."
	    echo ""
	    return
	fi
    fi
    if [[ -f ${dir}/autostart ]]; then
	wave=$(cat ${dir}/autostart)
	if [[ "$wave" == "" ]]; then
	    emitC yellow "warn: found empty autostart file; assuming wave 5; $dir"
	    wave="5"
	fi
    fi
    echo "$wave"
}

# stdin is a list of inputs to find_dir; output is a list of container names
function get_container_names() {
    while IFS='$\n' read -r line; do
	basename $(find_dir $line )
    done
}

# sort, skipping a single header row
function sort_skip_header() {
    t=$(mktemp)
    cat > $t
    head -n 1 $t && tail -n +2 $t | sort "$@"
    rm $t
}

# re-group output of list-autostart-waves by wave
function waves() {
    current_wave=""
    current_out=""
    while read -r wave line; do
	if [[ "$wave" != "$current_wave" ]]; then
	    if [[ "$current_out" != "" ]]; then echo "$current_out"; fi
	    echo "+ $wave"
	    current_wave="$wave"
	    current_out=""
	fi
	current_out="${current_out}${line} "
    done
    if [[ "$current_out" != "" ]]; then echo "$current_out"; fi
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
    list-up | /bin/egrep "^${srch}" | pick_first
}

function pick_container_from_all() {
    srch="$1"
    list-all | egrep "^${srch}" | pick_first
}

function pick_first() {
    in=$(cat)
    sel=$(echo "${in}" | head -1)
    if [[ "$in" != "$sel" ]]; then emitC cyan "selected [ $(echo "$in" | tr '\n' ' ') ] -> ${sel}"; fi
    echo "$sel"
}

# ------------------------------
# generate lists of containers

function list-all() {
    list-all-settings | dirnames | sort -u
}

function list-all-settings() {
    ls -1 ${D_SRC_DIR}/*/*.yaml ${D_SRC_DIR2}/*/*.yaml 2>/dev/null
}

function list-autostart-waves() {
    for s in $(list-all-settings); do
	dir=$(dirname $s)
	name=$(basename $dir)
        src_dir=$(dirname $dir)
        if [[ "$src_dir" == "$D_SRC_DIR2" ]]; then
	    src="${YELLOW}(src-dir 2)${RESET}"
        else
            src=""
        fi
	wave=$(get_autostart_wave $dir)
	if [[ "$wave" != "" ]]; then printf "$wave \t $name \t $src \n"; fi
    done | sort -n
}

function list-autostart() {
    list-autostart-waves | cut -f2 | tr -d ' '
}

function list-buildable() {
    ls -1 ${D_SRC_DIR}/*/Makefile ${D_SRC_DIR2}/*/Makefile 2>/dev/null | get_container_names
}

function list-up() {
  $DOCKER_EXEC ps --format '{{.Names}}'
}

function list-testable() {
    # old style tests: ls -1 ${D_SRC_DIR}/*/Test ${D_SRC_DIR2}/*/Test 2>/dev/null | get_container_names
    ls -1 ${D_SRC_DIR}/*/test_*.py \
          ${D_SRC_DIR}/*/docker-compose.yaml \
          ${D_SRC_DIR2}/*/test_*.py \
          ${D_SRC_DIR2}/*/docker-compose.yaml \
       2>/dev/null | get_container_names
}

# ------------------------------
# operations complicated enough to need their own support functions

function builder() {
  name="$1"
  cd_sel "$name"
  emit ""
  emitc blue "<> Building container ${name}"
  if [[ -r Build ]]; then
      emitc yellow "deferring to ./Build"
      ./Build
  elif [[ -r Makefile ]]; then
      make clean
      make
  else
      echo "no Makefile, falling back to direct d-build"
      d-build
  fi
}

function down() {
  name="$1"
  if [[ "$name" == "" ]]; then emitc red "no such container"; return 1; fi
  $DOCKER_EXEC stop -t 2 "${name}"
  return $?
}

function up() {
  sel="$1"
  echo -n "Starting: $sel ${extra_flags}    "
  cd_sel "$sel"
  if [[ -x ./Run ]]; then
      emitc cyan "launching via legacy Run file"
      erun ./Run ${extra_flags}
  elif [[ -f ./docker-compose.yaml ]]; then
      ip=$(host ${sel} | cut -f4 -d' ')
      if [[ "$ip" == "" ]]; then echo "unable to get IP"; exit -1; fi
      puid="$(k_auth -e):$sel"
      if [[ "$puid" == "" ]]; then echo "unable to get PUID"; exit -2; fi
      emitc cyan "launching via $DOCKER_EXEC compose to $ip"
      erun IP="$ip" PUID="$puid" $DOCKER_EXEC compose up -d ${extra_flags}
  else
      # This substitution only supports a single param to the right of the "--".
      extra_flags=${extra_flags/-- /--extra_init=}
      emitc cyan "launching via d-run"
      erun d-run ${extra_flags} |& sed -e '/See.*--help/d' -e '/Conflict/s/.*/Already up/'
  fi
}

function test() {
  name=$1
  shift

  outdir="/rw/dv/TEST/OUT"
  out="${outdir}/${name}.out"
  mkdir -p $outdir
  emitc blue "Testing ${name} -> ${out}"
  cd_sel "${name}"

  printf "\n---- $(date): Testing ${name}\n" >> $out

  outdir=$(dirname ${out})
  [[ -d ${outdir} ]] || mkdir -p ${outdir}

  if [[ -x $TESTER ]]; then
      rslt=$($TESTER -r -o "${out}" "$@")
      if [[ "$rslt" == *"pass"* ]]; then
	  emitc green "test passed.    ( $out )"
	  echo "pass"
	  return
      fi
  fi

  if [[ -f docker-compose.yaml ]]; then
      target="test_${name}"
      if [[ "$DOCKER_EXEC" == "docker" ]]; then rm="--rm"; else rm=""; fi
      echo "testing via $DOCKER_EXEC compose: $target"
      erun IP="unused" PUID="unused" $DOCKER_EXEC compose run $rm ${target} || { emitc red "failed"; echo "fail"; exit -1; }
      echo "pass"
      return
  fi


  if [[ -f Makefile ]]; then
      make test &>> ${out} || { emitc red "failed"; echo "fail"; exit -1; }
      echo "pass"
      return
  fi

  emitc red "no testing methods available or all available methods failed."
  echo "fail"
}

function upgrade() {
  name=$1
  builder $name

  rslt=$(test $name | tail -1)
  if [[ "$rslt" != "pass" ]]; then
    emitc red "test failed.  result: $rslt (expected 'pass')"
    return 1
  fi

  emit green "> Marking ${name} live"
  if [[ -r ./Build ]]; then ./Build --setlive
  else d-build -s
  fi

  astart=$(get_autostart_wave $name)
  if [[ "$astart" != "" ]]; then
      emitc blue "restarting $name"
      down $name
      sleep 1
      up $name
  fi
  emitc green "done with $name"
}

# ----------------------------------------
# group ops

function do-in-waves() {
    op="$1"
    set +e
    list-autostart-waves | cut -f1,2 | waves | while read -r line; do
	if [[ "$line" == +* ]]; then
	    emitc green "starting wave: ${line/+ /}"
	else
	    echo $line | tr ' ' '\n' | /usr/local/bin/run_para --align --cmd "$0 $op @" --timeout $TIMEOUT
	fi
    done
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
  build | b) builder $(pick_container_from_all $spec)   ;;  ## Build container $1
  down | stop | 0) down $(pick_container_from_up $spec) ;;  ## Stop container $1
  restart | 01 | R)                                         ## Restart container $1
    name=$(pick_container_from_up $spec)
    echo "Shutting down $name"
    down $name || { emitc magenta "${spec} was not up, so not restarting"; exit -2; }
    sleep 1
    echo "Starting up $name"
    up $name
    ;;
  up | start | 1)                                           ## Launch container $1
    sel=$(pick_container_from_all $spec)
    if [[ "$sel" == "" ]]; then
      echo "error- cannot find container to launch: $spec"
      exit 1
    fi
    if [[ "$(is_up $sel)" == "y" ]]; then
        echo "error- container already up: $sel"
        exit 1
    fi
    up $sel
    ;;

# container maintenance
  add-su | addsu)                                               ## Copy /bin/su into container $1
    name=$(pick_container_from_up $spec)
    $DOCKER_EXEC exec -u 0 ${name} cp /bin/busybox /bin/su
    echo "added /bin/su to ${name}"
    ;;
  add-debug | debug)                                            ## Add debugging tools and enter container $1
    name=$(pick_container_from_up $spec)
    $DOCKER_EXEC cp ${D_SRC_DIR}/debugger/debug.tgz ${name}:/
    $DOCKER_EXEC exec -u 0 ${name} tar x -k -o -z -f debug.tgz
    $DOCKER_EXEC exec -u 0 -ti ${name} /bin/bash
    echo "back from container."
    ;;
  clean)                                                        ## Remove all sorts of unused docker cruft
    ## Don't want to use 'docker system prune' because would delete
    ## network 'docker2' which is not always in use, but is useful.
    ##
    ## WARNING: deletes all the "prev" images.  Only run this once
    ## confident we don't need to revert to any of those...
    ##
    $DOCKER_EXEC container prune -f --filter "label!=live"
    $DOCKER_EXEC image prune -f --filter "label!=live"
    $DOCKER_EXEC volume prune -f --filter "label!=live"
    $DOCKER_EXEC builder prune -f
    ;;
  hup | H | HUP | reload | r)                                    ## Send sigHup to proc 1 in container $1
    $DOCKER_EXEC exec -u 0 $(pick_container_from_up $spec) kill -HUP 1
    ;;
  mini-dlna-refresh | M)                                         ## kds specific; rescan miniDlna library
    $DOCKER_EXEC exec dlnadock /usr/sbin/minidlnad -R
    ;;
  test | t) test $(pick_container_from_all $spec) ;;             ## Run tests for container $1
  upgrade | u) upgrade $(pick_container_from_all $spec) ;;       ## Upgrade (build, test, relabel, restart) $1.

# command execution
  console | C)                                                   ## Enter console for $1
    $DOCKER_EXEC attach $(pick_container_from_up $spec)
    echo "back from container console."
    ;;
  enter | exec-cmd | exec | e0 | e)                              ## Interactive root shell in $1
    name=$(pick_container_from_up $spec)
    $DOCKER_EXEC exec -u 0 -ti ${name} /bin/bash || $DOCKER_EXEC exec -u 0 -ti ${name} /bin/sh
    echo "back from container."
    ;;
  run) $DOCKER_EXEC exec -u 0 $(pick_container_from_up $spec) "$@" ;;  ## Run command $2+ as root in $1
  shell)                                                         ## Start container $1 but shell overriding entrypoint.
      $DOCKER_EXEC run -ti --user root --entrypoint /bin/bash ktools/$(pick_container_from_all $spec):latest ;;

# Multiple container management done in parallel
  build-all | ba)                                                ## Build all buildable containers.
      $0 build kcore-baseline; list-buildable | /usr/local/bin/run_para --align --cmd "$0 build @" --output d-build-all.out --timeout $TIMEOUT ;;
  down-all | stop-all | 0a | 00)                                 ## Down all up containers
      list-up | /usr/local/bin/run_para --align --cmd "$0 down @" --timeout $TIMEOUT ;;
  restart-all | 01a | ra | RA | Ra)                              ## Restart all up containers
      $0 down-all ; $0 up-all ;;
  run-in-all | ria)                                              ## Run $1+ in root shell in all up containers
      list-up | /usr/local/bin/run_para --align --cmd "$0 run @ $spec $@" --output d-run-in-all.out --timeout $TIMEOUT ;;
  test-all | ta)                                                 ## Test all testable containers (#latest)
      list-testable | /usr/local/bin/run_para --align --cmd "$0 test @" --output d-all-test.out --timeout $TIMEOUT ;;
  up-all | start-all | 1a | 11) do-in-waves up ;;                ## Launch all autostart containers
  upgrade-all | ua) do-in-waves upgrade ;;                       ## upgrade all containers
# various queries
  autostart-wave | aw | al | ai)                                 ## Print autostart wave for container
      get_autostart_wave $(pick_container_from_all $spec) ;;
  check-all-up | cau | ca | qa)                                  ## Check that all autostart containers are up.
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
  cow-dir | cow)                                                 ## Print the copy-on-write layer dir location for $1
    name=$(pick_container_from_up $spec)
    dlib_run get_cow_dir "$name"
    ;;
  images | i) $DOCKER_EXEC images | sort_skip_header ;;          ## List docker images
  is-up | iu) is_up $spec ;;                                     ## Is container up (y/n)
  get-ip | getip | get_ip | ip)                                  ## Print the IP address for $1
    set -o pipefail
    name="$(pick_container_from_up $spec)"
    if [[ "$name" == "" ]]; then exit -1; fi
    $DOCKER_EXEC inspect "$name" | fgrep '"IPAddr' | tail -1 | cut -d'"' -f4
    ;;
  get-all-ips | ips)                                             ## Print IPs for all up containers.
    for name in $($DOCKER_EXEC ps --format "{{.Names}}"); do
	echo -n "${name}   "
	$DOCKER_EXEC inspect "$name" | fgrep '"IPAddr' | tail -1 | cut -d'"' -f4
    done | column -t | sort
    ;;
  log | logs)                                                    ## Print logs for $1
      $DOCKER_EXEC logs -ft --details $(pick_container_from_all $spec) ;;
  pid)                                                           ## Print main PID for $1
      $DOCKER_EXEC inspect --format '{{.State.Pid}}' $(pick_container_from_up $spec) ;;
  spec | s) $DOCKER_EXEC inspect $(pick_container_from_up $spec) ;;    ## Print docker details for $1
  veth)                                                          ## Print virtual eth name for $1
    idx=$($DOCKER_EXEC exec $(pick_container_from_up $spec) cat /sys/class/net/eth0/iflink)
    /bin/grep -l "$idx" /sys/class/net/veth*/ifindex | /usr/bin/cut -d/ -f5
    ;;

# instance lists
  list-all-settings | las) list-all-settings ;;                  ## List all known settings files
  list-all | lA) list-all ;;                                     ## List all known container names
  list-autostart | la) list-autostart ;;                         ## List auto-startable containers in start-up order
  list-autostart-waves | law) list-autostart-waves ;;            ## List auto-startable containers prefixed by their startup wave
  list-buildable | lb) list-buildable ;;                         ## List buildable containers
  list-testable | lt) list-testable ;;                           ## List containers with tests
  list-up | lu | ls | l | ps | p)                                ## List all up containers
    $DOCKER_EXEC ps --format '{{.Names}}@{{.ID}}@{{.Status}}@{{.Image}}@{{.Command}}@{{.Ports}}' | \
      sed -e 's/0.0.0.0/*/g' -e 's:/tcp::g' | \
      column -s @ -t | cut -c-${COLUMNS:-200} | sort
    ;;
  list-up-names | lun)                                           ## List all up containers (just the names)
    $DOCKER_EXEC ps --format '{{.Names}}' ;;

# internal
  help | h) myhelp "$spec" ;;                                    ## display this help
  dup-check | check | chk) ( myhelp | fgrep -v '#' | tr '|' '\n' | tr -d ' ' | sort | uniq -c | fgrep -v '  1 ') || echo 'all ok' ;;  ## Check if any command-shortcuts are duplicated.
  *)
     echo "invalid command: $cmd"
     exit 3
     ;;

esac
