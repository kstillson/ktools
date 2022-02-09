#!/bin/bash
set -e

# q - quick Linux commands and reference.
# (c) Ken Stillson, 2021.  Released under the MIT license.

# Whenever I find I'm running a non-trivial Linux command more than once,
# or need to look up how a Linux utility works, I tend to add a subcommand
# for it to this script.  This both provides a quick and easy way of
# running it next time, and provides a central location where I can find
# such tools.  I used to create .bashrc aliases, but when bashrc gets too
# complex, it becomes dangerous to modify and slows down every shell
# launch.  This is better.
#
# Over time, I started to add things like colorization and other neat bash
# tricks (like some commands adjusting operation depending on whether the
# calling stdin is an interactive terminal or not).  So now I also use this
# as a repository of clever bash tricks.
#
# The built-in help system works by auto-generating its content from the
# source.  To get a list of all commands, use "q help".  Adding a param
# searches for commands with a keyword, e.g. "q h syslog" lists all
# commands that have anything to do with syslog.
#
# Many of the details in here are specific to my home configuration and
# won't be directly useful.  But I'm releasing the script anyway, in hopes
# that the bash-tricks collection and the overall structure/approach might
# be of interest, and can be adapted to your own environment.

# TODO(kstillson): The ECHO, TEST, and VERBOSE options are redundant,
# confusing, and not uniformly implimented.

# flag defaults
ECHO=0           # print commands to stdout instead of executing them
EXCLUDE="blue"   # csv list of hosts to exclude
HOST_SUBST="@"   # replace this substring with hostnames in commands
PARA=1           # run commands for multiple hosts in parallel
TEST=0           # similar to ECHO but label as testing and send to stderr
TIMEOUT=90       # ssh connect timeout
VERBOSE=0        # similar to ECHO but also execute the commands

MY_HOSTNAME=$(hostname)    # always run commands locally on this host.
DD="/root/docker-dev/dnsdock/files/etc/dnsmasq"
GIT_DIRS="/root/arps /root/docker-dev /root/dev/dots-rc /root/dev/homectrl /root/dev/ktools /home/ken/bin /rw/dv/webdock/home/ken/homesec"
LEASES="/rw/dv/dnsdock/var_log_dnsmasq/dnsmasq.leases"
PROCQ="/var/procmon/queue"
RP_FLAGS='--output - --plain --quiet '

# ----------------------------------------
# colorizers

BLUE='\x1b[01;34m'
CYAN='\x1b[36m'
GREEN='\x1b[01;32m'
MAGENTA='\x1b[35m'
RED='\x1b[0;31m'
YELLOW='\x1b[0;33m'
WHITE='\x1b[37m'
RESET='\x1b[00m'

# Print $2+ in color named by $1. insert "-" as $1 to skip ending newline.
function echoC() { if [[ "$1" == "-" ]]; then shift; nl=''; else nl="\n"; fi; color=${1^^}; shift; q="$@"; printf "${!color}${q}${RESET}${nl}"; }
# Print $2+ in color named by $1, but only if stdin is an interactive terminal.
function echoc() { color=${1^^}; shift; if [[ -t 1 ]]; then echoC "$color" "$@"; else printf "$@\n"; fi; }

# Same as above, but send to stderr.
function emit() { echo ">> $@" >&2; }
function emitC() { if [[ "$1" == "-" ]]; then shift; nl=''; else nl="\n"; fi; color=${1^^}; shift; q="$@"; printf "${!color}${q}${RESET}${nl}" 2>&1 ; }
function emitc() { color=${1^^}; shift; if [[ -t 1 ]]; then emitC "$color" "$@"; else printf "$@\n" >&2; fi; }

# ----------------------------------------
# ssh agent

# return success (0) if agent is running and registered with this shell.
function test_ssh_agent() {
  if [[ ! -v SSH_AGENT_PID || ! -v SSH_AUTH_SOCK ]]; then return 1; fi
  if [[ ! -d "/proc/${SSH_AGENT_PID}" ]]; then return 1; fi
  if [[ ! -S "$SSH_AUTH_SOCK" ]]; then return 1; fi
  return 0
}
# run ssh-add if keyring empty (agent should already be running).
function AA() {
  { ssh-add -l >& /dev/null; } || ssh-add -v
}
# attempt to reconnect with existing agent; return 0 if successful.
SSH_AGENT_DAT="${HOME}/.ssh_agent"
function A0() {
  test_ssh_agent && return 0
  [[ -f ${SSH_AGENT_DAT} ]] || return 1
  source ${SSH_AGENT_DAT}
  test_ssh_agent && return 0
  echo "existing agent data stale." 2>&1
  # rm ${SSH_AGENT_DAT}
  return 2
}
# activate ssh agent (attach to old or start new)
function A() {
  if A0; then echo "attached to existing agent" 2>&1; return 0; fi
  /usr/bin/ssh-agent -s -t 4h > ${SSH_AGENT_DAT}
  source ${SSH_AGENT_DAT}
  if ! test_ssh_agent; then echo "ouch; unable to start agent" 2>&1; return -1; fi
  echo "agent started" 2>&1;
  AA
}
# kill all agents for this user.
alias AX='{ pkill -u $USER ssh-agent && echo "ssh-agent stopped"; }; rm -f ${SSH_AGENT_DAT}'

# Make sure ssh agent is up and running; start it if needed.
# (This is the method generally called from below; the stuff above is internals...)
function need_ssh_agent() { A0>/dev/null || A; }

# ----------------------------------------
# general purpose

# Expect stdin to match $2, print status decorated by title in $1 and output stdin upon mismatch.
# For example, if you expect a file to be empty:  cat file | expect "file should be empty" ""
function expect() {
    title="$1"
    expect="$2"
    got=$(cat)
    if [[ "$expect" == "$got" ]]; then
        emit "$title - ok"
        return 0
    fi
    emit "$title - error"
    echoC yellow "$title: "
    echo "$got"
}

# Run "$@" respecting TEST and VERBOSE flags, print exit code if not 0.
function runner() {
    # nb: use "$@" rather than copying to local var to preseve args with spaces in them.  "$@" is magic..
    if [[ "$TEST" == 1 ]]; then
        emit "TEST; would run: $@"
        return
    fi
    if [[ "$VERBOSE" == 1 ]]; then
        emit "running: $@"
    fi
    status="0"
    "$@" || status=$?
    if [[ $status != "0" ]]; then emitC red "status $status from $@\n"
    else if [[ "$VERBOSE" == 1 ]]; then emitC green "done (ok): $@\n"; fi
    fi
}

# Wrapper around /usr/local/bin/run_para which assumes --ssh mode unless
# $1 is "LOCAL", in which case it uses --cmd mode.  ssv hosts in $1,
# command to run in $2+.
function run_para() {
    if [[ "$1" == "LOCAL" ]]; then
        type="--cmd"
        shift
    else
        type="--ssh"
        need_ssh_agent
    fi
    hosts="$1"
    shift
    echo "$hosts" | tr ' ' '\n' | without - "$EXCLUDE" | /usr/local/bin/run_para $RP_FLAGS --subst "$HOST_SUBST" --timeout $TIMEOUT  "$type" "$@"
    return $?
}

# Assume a 1 line header and output stdin sorted but preserving the header.
function sort_skip_header() {
    t=$(mktemp)
    cat > $t
    head -n 1 $t && tail -n +2 $t | sort
    rm $t
}

# ----------------------------------------
# general linux maintenance

# Add a new repository (named $1) to the git docker instance.
function git_add_repo() {
    name="$1"
    if [[ ! "$name" == *.git ]]; then name="${name}.git"; fi
    dir="/rw/dv/gitdock/home/ken/git/$name"
    mkdir $dir
    cd $dir
    git init --bare
    chown -R dken.200802 $dir
    chmod -R go+rx,g+w $dir
    emitc green "ready: git:git/${name}"
}

# Check all known git dirs for any local changes; output dirs with changes.
function git_check_all() {
    pushd . >& /dev/null
    for dir in $GIT_DIRS; do
        if [[ ! -d "${dir}/.git" ]]; then emitc red "missing git dir: $dir"; continue; fi
        cd $dir
        git_status=$(git status -s)
        if [[ "$git_status" != "" ]]; then echo "$dir"; fi
    done
    popd >& /dev/null
}

# $1 is a git controlled directory.  Will check-in any local changes, then
# pull updates from all remotes, then push updates to all remotes.
# assumes "need_ssh_agent" was already called.
# TODO: assumes remote branch is named "master"
function git_sync() {
    dir="$1"
    if [[ ! -d "${dir}/.git" ]]; then emitc red "missing git dir: $dir"; return 1; fi
    pushd . >& /dev/null
    cd $dir
    git_status=$(git status -s)
    if [[ "$git_status" == "" ]]; then
        emitc green "no local changes: $dir"
    else
        git commit -v -a
    fi
    git remote | xargs -L1 -I@ echo git pull @ master
    git remote | xargs -L1 git push
    popd >& /dev/null
    echoc green "done: $dir"
}


# Sync all known git dirs.
function git_sync_all() {
    need_ssh_agent
    for dir in $GIT_DIRS; do git_sync $dir; done
    emitc green "all done\n"
}

# Runs a pull in all known local git dirs.
function git_pull_all() {
    need_ssh_agent
    for dir in $GIT_DIRS; do
        if [[ ! -d $dir ]]; then emit "missing dir: $dir"; continue; fi
        cd $dir
        runner git pull
    done
    emitc green "all done\n"
}

# For all local PIs with git repos, pull any updates and restart dependent daemons.
function git_update_pis() {
    set +e
    t="/tmp/git-updates.out"
    hosts=$(list_pis | without hs-front,pi1,lightning)
    echo "pulling git updates..."
    echo $hosts | /usr/local/bin/run_para --output $t --plain --timeout $TIMEOUT --ssh "/bin/su pi -c 'cd /home/pi/dev; git pull'"
    if [[ $? != 0 ]]; then cat $t; rm $t; echo ''; emitc red "some failures; not safe to do restarts"; return 1; fi
    echo "restarting services..."
    echo $hosts | /usr/local/bin/run_para --plain --timeout $TIMEOUT --ssh systemctl daemon-reload
    echo $hosts | /usr/local/bin/run_para --output $t --plain --timeout $TIMEOUT --ssh /home/pi/dev/Restart
    if [[ $? != 0 ]]; then cat $t; rm $t; echo ''; emitc red "some restart failures"; return 1; fi
    emitc green "all done\n"
}

function iptables_list_tables() {
    iptables-save | egrep '^\*' | tr -d '*' | sort
}

function iptables_list_chains() {
    iptables-save | awk -F' ' '/^\*/ { tab=substr($1,2) } /^:/ { print tab $1 }' | sort
}

# $1 can either be a chain name or a thing to grep for.
function iptables_query_real() {
    search="$1"
    Search="${1^^}"  # try upper case chian names too..
    params="-n -v --line-numbers "
    tables=$(iptables_list_tables | tr '\n' ' ')
    case $Search in
	PREROUTING | PRE) iptables $params -L PREROUTING -t nat ;;
	POSTROUTING | POST) iptables $params -L POSTROUTING -t nat ;;
	"")
	    for tab in $tables; do
		echoc cyan "\nTABLE: $tab\n"
		iptables $params -L -t $tab
	    done
	    ;;
	*)
	    # See if they specified a table-name, and if so, output that whole table.
	    if [[ "$tables" == *"$search"* ]]; then
		echoc cyan "\nTABLE: $search\n"
		iptables $params -L -t $search
		return
	    fi
	    # Decorate each rule line with table and chain name, then search for anything matching the given substring.
	    for tab in $tables; do
		echoc cyan "\nTABLE: $tab\n"
		iptables $params -L -t $tab | awk -F" " '/^Chain/ { chain=$2 } /^[0-9]/ { print chain ":" $0 }' | fgrep --color=auto -i "$search" || true
	    done
    esac
}

function iptables_query() {
    if [[ -t 1 && "$1" == "" ]] ; then
	iptables_query_real | less --raw-control-chars --quit-if-one-screen
    else
	iptables_query_real "$1"
    fi
}

# Save current iptables rules to disk for auto-restore upon boot.
function iptables_save() {
    # TODO: move to standard location (with autodetect for ro root)
    /bin/mv -f ~/iptables.rules ~/iptables.rules.mbk
    /usr/sbin/iptables-save > ~/iptables.rules
    emitc green "saved"
}

# (in parallel) ping the list of hosts in $@.  Try up to 3 times.
function pinger() {
    set +e
    RP_FLAGS="$RP_FLAGS -q -m 99 "
    problems=$(run_para LOCAL "$@" "set -o pipefail; ping -c3 -W3 -i0 -q ^^@ | grep loss | sed -e 's/^.*received, //'" | fgrep -v " 0%" $t | cut -f1 -d:)
    if [[ "$problems" == "" ]]; then emitc green "all ok\n"; return; fi
    for try in 1 2 3; do
        echo ""
        emit $(printf "problems: [ $(echo $problems | tr '\n' ' ') ]... ${RED} retry #${try}/3... ${RESET}")
        sleep 1
        problems=$(run_para LOCAL "$problems" "ping -c3 -W3 -i0 -q ^^@ | grep loss | sed -e 's/^.*received, //'" | fgrep -v " 0%" $t | cut -f1 -d:)
    if [[ "$problems" == "" ]]; then emit "fixed; $(echoC green 'all ok\n')"; return; fi
    done
    emitc red ":-("
}

# Run the ps command with preferred options, colorization, and docker container-id lookups.
function ps_fixer() {
    t=$(mktemp)
    cat >$t <<EOF
s/^root /${RED}root${RESET} /
s/^droot /${YELLOW}droot${RESET} /
s/^dken /${BLUE}dken${RESET} /
s/defunct/${YELLOW}defunct${RESET}/
EOF
    awk "{print \"s/\" \$1 \"/${CYAN}\" \$2 \"${RESET} \", \$1, \"/\"}" < /var/run/dmap >> $t
    ps aux --forest | egrep -v '\]$' | sed -f $t | less
    rm $t
}

# Run apt update and upgrade on ssv list of hosts in $1
function updater() {
    hosts="$1"
    OUT1="/tmp/all-update.out"
    OUT2="/tmp/all-upgrade.out"
    need_ssh_agent
    echo "$hosts" | /usr/local/bin/run_para --output $OUT1 --timeout 240 --ssh 'apt-get update'
    echo "$hosts" | /usr/local/bin/run_para --output $OUT2 --timeout 999 --ssh 'apt-get -y upgrade'
    emit "output sent to $OUT1 and $OUT2 (consider rm $OUT1 $OUT2 )"
}


# ----------------------------------------
# jack / home network specific

# My rsnapshot config relies on capabilities to provide unlimited read access to an otherwise
# unprivlidged account.  Sometimes upgrades remove those capabilities, so this puts them back.
# I keep the root dir read-only on my primary server, so need to temp-enable writes...
function enable_rsnap() {
    run_para "$(list_rsnap_hosts | without jack)" "/sbin/setcap cap_dac_read_search+ei /usr/bin/rsync"
    mount -o remount,rw /
    /sbin/setcap cap_dac_read_search+ei /usr/bin/rsync
    mount -o remount,ro /
}

# Output the list of DHCP leases which are not known to the local dnsmasq server's DNS list.
function leases_list_orphans() {
    t=$(mktemp)
    fgrep -v '#' $DD/dnsmasq.hosts | cut -f2 | sed -e '/^$/d' -e 's/[0-9\.]* *//' | cut -d' ' -f1 | sort -u > $t
    fgrep -v -f $t $LEASES || emitc green 'all ok\n'
    rm $t
}

# Update the DHCP server's mapping for mac->hostname; generally needed when adding a new host to the network.
# (I manage by DNS entries manually in this way, so new hosts will cause an alert until manually added.
#  Because security.)
function update_dns() {
    s1=$(stat -t $DD/dnsmasq.macs)
    emacs $DD/dnsmasq.macs $DD/dnsmasq.hosts $LEASES
    s2=$(stat -t $DD/dnsmasq.macs)
    if [[ "$s1" == "$s2" ]]; then emit "no change to macs; not updating dnsmasq"; return; fi
    if [[ "$TEST" == 1 ]]; then emit "test mode; not updating dnsmasq"; return; fi
    emit "updating dnsmasq"
    /root/bin/d u dnsdock
    cd /root/docker-dev/dnsdock
    git C
    emit "done"
}

# If a dhcp misconfig or a new host has caused an alarm because of an unknown mac address,
# it can be useful to remove it from the DHCP assignments to clear the alarm.
function update_dns_rmmac() {
    search="$1"
    t=$(mktemp)
    fgrep "$search" $LEASES > $t || true
    lines=$(wc -l $t | cut -d' ' -f1)
    if [[ "$lines" -lt 1 ]]; then emit "no change (search not found); not updating."; return; fi
    if [[ "$lines" -gt 4 ]]; then emit "change too large; do manually."; return; fi
    emit "change spec:"
    cat $t
    cp $LEASES ${LEASES}.mbk
    s1=$(wc -l $LEASES)
    sed -e "/$search/d" $LEASES > $t
    s2=$(wc -l $t)
    if [[ "$s1" == "$s2" ]]; then emit "change failed; not updating."; return; fi
    emit "committing change..."
    /root/bin/d 0 dnsdock
    mv -f $t $LEASES
    chown droot.dgroup $LEASES
    # filewatchdock needs to be able to monitor this file.
    chmod go+r $LEASES
    /root/bin/d 1 dnsdock
    emit "done."
}

# Remove all docker copy-on-write files that have changed unexpectedly.
function procmon_clear_cow() {
    for f in $(curl -sS jack:8080/healthz | grep COW | sed -e 's/COW: unexpected file: //'); do
        emitC blue "$f"
        docker=${f%%:*}
        relfile=${f#*:}
        echoc yellow "${docker}:${relfile}"
        base=$(d cow $docker)
        fn="${base}/${relfile}"
        rm $fn
    done
    emitc green done
}

# Update the whitelist of known-processes on the primary server.  Test the results
# and if the test passes, restart the monitoring daemon with the new list.
function procmon_update() {
    t=$(mktemp)
    sort -u < $PROCQ > $t
    emacs /home/ken/bin/procmon_wl.csv $t
    /home/ken/bin/procmon -t | tee $t
    last=$(tail -1 $t)
    rm -f $t
    if [[ "$last" != "[]" ]]; then
        echoc yellow "SCAN DOESN'T LOOK CLEAN; NOT RESTARTING PROCMON."
        return
    fi
    echo "updating procmon and clearing queue..."
    runner systemctl restart procmon
    runner bash -c ":>$PROCQ"
}

# Run a series of checks on the status of my home network.
function checks_real() {
    nag | expect "nagios checks" "all ok"
    leases_list_orphans | fgrep -v cudy | expect "dns orphans" ""
    cat $PROCQ | expect "procmon queue" ""
    fgrep -v 'session opened' /rw/log/queue | expect "syslog queue" ""
    $0 dup-check | expect "$0 dup cmds" "all ok"
    /root/bin/d dup-check |& expect "docker dup cmds" "all ok"
    /root/bin/d check-all-up |& expect "docker instances" "all ok"
    /root/bin/d run eximdock bash -c 'exim -bpr | grep "<" | wc -l' |& expect "exim queue empty" "0"
    /usr/bin/stat --format=%s /rw/dv/eximdock/var_log/exim/paniclog |& expect "exim panic log empty" "0"
    /usr/bin/stat --format=%s /rw/dv/eximdock/var_log/exim/rejectlog |& expect "exim reject log empty" "0"
    git_check_all |& expect "git dirs with local changes" ""
}

# Wrapper around checks_real that does formatting and checks for overall status.
function checks() {
    t1=$(mktemp)  # checks_real stdout
    t2=$(mktemp)  # checks_real stderr
    checks_real >$t1 2>$t2
    bad=$(fgrep -v -e "- ok" $t2 | wc -l)   # count of failed checks from stderr
    cat $t1
    echo ""
    cat $t2 | column -s- -t
    rm $t1 $t2
    echo ""
    if [[ "$bad" == "0" ]]; then echoc green "all ok\n"; else printf "failed checks: ${RED}${bad}${RESET}\n"; fi
    echo ""
}

# Download the homesec keyscanner common code from git repo, parse out and tidy the keyboard commands, stripping private ones.
function keypad_commands {
    if [[ "$1" == "" ]]; then
	fmt="column"
    else
	fmt="fgrep $1"
    fi
    git archive --remote gitro:git/homectrl.git master ks_common.py | tar -xOf - | \
        sed -e '/[#:]/!d' -e 's/, GO//' -e 's/common.trigger//' -e 's/common.control//' -e 's@common.read_web(\"http://@(web-@' \
            -e '/touch-home/d' -e '/disarm/d' \
            -e "s/)\',//" -e 's/#/:####/' -e "s/'//g" -e 's/"//g' -e 's/),/)/g' | \
        column -t -s: | $fmt
}

# Run $1 as if it was typed into a keypad.
function run_keypad_command {
    curl -sS -d "cmd=$1" -X POST http://homectrl:1235/ | sed -e 's/<[^>]*>//g'
    echo ""
}

# Add a user to the home security system's Django instance.
function homesec_add_user {
    user="$1"
    passwd="$2"
    if [[ "$user" == "" ]]; then emit "need to provide user"; return 1; fi
    if [[ "$passwd" == "" ]]; then emit "need to provide password"; return 1; fi
    docker exec -i -u 0 webdock bash <<EOF1
cd /home/ken/homesec/scripts/
./manage.py shell <<EOF2
from django.contrib.auth.models import User
user=User.objects.create_user('$user', password='$passwd')
user.save()
EOF2
EOF1
}

# Remove a user from the home security system's Django instance.
function homesec_del_user {
    user="$1"
    if [[ "$user" == "" ]]; then emit "need to provide user"; return 1; fi
    docker exec -i -u 0 webdock bash <<EOF1
cd /home/ken/homesec/scripts/
./manage.py shell <<EOF2
from django.contrib.auth.models import User
User.objects.get(username="$user").delete()
EOF2
EOF1
}

# ----------------------------------------
# host lists

function list_all() {
    ( list_linux | tr ' ' '\n' ; cut -d' ' -f4 $LEASES ) | tr -d ' ' | sort -u | tr '\n' ' '
    echo ''
}

function list_linux() {
    echo -n "a1 blue jack mc2 "
    list_pis
}

function list_pis() {
    echo "homectrl homesec1 homesec2 hs-front lightning pi1 pibr pout trellis1 twinkle"
}

function list_rsnap_hosts() {
    egrep '^backup' /root/docker-dev/rsnapdock/files/etc/rsnapshot.conf | cut -d@ -f2 | cut -d: -f1 | sort -u
}

function list_tps() {
    { { cut -d' ' -f4 $LEASES | /bin/fgrep tp- ; } ; { /bin/fgrep tp- $DD/dnsmasq.hosts | /bin/fgrep -v '#' | cut -f2; } ; } | tr -d ' ' | sort -u | tr '\n' ' '
    echo ''
}

# dynamically figure out which list of hosts is desired.  $1 specifies a
# category.  various categories are hard-coded for the lists above.  "-"
# indicates the list of hosts should come from stdin (space, comma, or
# newline separated).  If "$1" names a file, the contents of the file
# should contain the list of hosts.  A single hostname can also be provided
# in $1.

function list_dynamic() {
    case "$1" in
        all|a) list_all ;;
        linux|l) list_linux ;;
        pis|rpi|p) list_pis ;;
        tps|t) list_tps ;;
        -) cat ;;
        *)  # check for a file (which we assume is a list of hosts)
            if [[ -f "$1" ]]; then cat "$1"; return; fi
            # check if a (csv) list of liternal hosts
            hosts=$(echo "$@" | tr , ' ')
            testhost=$(echo "$hosts" | cut -d" " -f1)
            rslt=$(host "$testhost" 2>&1)
            if [[ "$rslt" == *"address"* ]]; then echo "$hosts"; return; fi
            # dunno what we were given...
            emit "unknown host spec: $@"
            exit 4
            ;;
    esac
}

# Similar to 'egrep -v' except input can be space or newline separated, and
# multiple removal expressions can be given easily.
#
# stdin is a space or newline separated list (indivual items should not
# contain spaces) $@ is list of things to remove.  Each "thing" can be a
# substring, a regular expression, or a comma or space separated list of
# substrings or regular expressions.
#
# stdout will be a space separated list with the requested items removed.
#   (give $1 as "-" if you want newline separated instead.)
# stderr will note the list of removed items (if any).
function without() {
    if [[ "$1" == "-" ]]; then newline=1; shift; else newline=0; fi
    if [[ "$1" == "" ]]; then cat; fi
    t=$(mktemp)
    cat > $t
    exp=$(echo "$@" | tr " " "|" | tr "," "|")
    removed=$(cat $t | tr ' ' '\n' | egrep "$exp" | sort | tr '\n' ' ')
    if [[ "$removed" != "" ]]; then emit "filtered: $removed"; fi
    if [[ "$newline" == "1" ]]; then
        cat $t | tr ' ' '\n' | egrep -v "$exp" | sort
    else
        cat $t | tr ' ' '\n' | egrep -v "$exp" | sort | tr '\n' ' '
        echo ""
    fi
    rm $t
}

# ----------------------------------------
# internal

# Scan my own source code, find the main switch statement, extract and format showing the commands this script supports.
function myhelp_real() {
    awk -- '/case "\$flag/,/esac/{ print } /case "\$cmd/,/esac/{ print }' $0 | egrep '(^ *#)|(^ *--)|(^        [a-z])' | sed -e '/case /d' -e '/esac/d' -e 's/^    //' -e 's/##/~/' -e 's/).*;;//' | column -t -s~
}

# Wrapper around myhelp_real, optionally searching for $@ and auto-paging if on an interactive terminal.
function myhelp() {
    if [[ "$@" != "" ]]; then
        myhelp_real | egrep --color=auto "$@"
    else
        if [ -t 1 ] ; then myhelp_real | less
        else myhelp_real
        fi
    fi
}

function main() {
    # --------------------
    # parse flags

    POSITIONAL=()
    while [[ $# -gt 0 ]]; do
        flag="$1"
        case "$flag" in
    # Note: flags mostly only affect multi-host commands...
            --echo | -e) ECHO=1 ;;                        ## print commands INSTEAD of executing them
            --exclude | -x) EXCLUDE=$2; shift ;;          ## csv list of substring match patterns
            --help    | -h) myhelp ;;
            --nopara  | -n | -1) PARA=0 ;;                ## run sequentually rather than in parallel
            --host-subst | -H) HOST_SUBST="$2"; shift ;;  ## use $1 instead of "@" for host subst char
            --test    | -T) TEST=1 ;;                     ## show what would be done rather than doing it
            --timeout | -t)                               ## ssh timeout in seconds
                TIMEOUT=$2;
                if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then echoc red 'error: -t arg must be numeric.'; exit 1; fi
                shift
                ;;
            --verbose | -v) VERBOSE=1 ;;                  ## print things while doing them
            *) POSITIONAL+=("$1") ;;
        esac
        shift
    done
    set -- "${POSITIONAL[@]}" # restore positional parameters

    # --------------------

    cmd="$1"
    if [[ "$cmd" == "" ]]; then myhelp; exit 0; fi
    shift
    case "$cmd" in
    # general linux maintenance routines for localhost
        df) df -h | egrep -v '/docker|/snap|tmpfs|udev' ;;   ## df with only interesting output
        ed) date -u +%m/%d/%y -d @$(( $1 * 86400 )) ;;       ## epoch day $1 to m/d/y
        es) echo "$1" | sed -e 's/,//g' | xargs -iQ date -d @Q ;;             ## epoch seconds $1 to standard date format
        es-day-now | es-now-day | day) echo $(( $(date -u +%s) / 86400 )) ;;  ## print current epoch day
        es-now | now) date -u +%s ;;                         ## print current epoch seconds
	iptables-list-chains | iptc | ic) iptables_list_chains ;;  ## print list of iptables chains
	iptables-list-tables | iptt | it) iptables_list_tables ;;  ## print list of iptables tables
	iptables-query | iptq | iq) iptables_query $1 ;;     ## print/query iptables ($1 to search)
	iptables-save | ipts | is) iptables_save ;;          ## save current iptables
        journal | j) journalctl -u ${1:-procmon} ;;          ## show systemd journal
        git-check-all | gca | gc) git_check_all ;;           ## list any known git dirs with local changes
        git-sync | git | g) need_ssh_agent; git_sync "${1:-.}" ;;             ## git sync a single directory (defaults to .)
        git-sync-all | git-all | ga) git_sync_all ;;         ## check all git dirs for unsubmitted changes and submit them
        pi-root | pir) host=${1:-rp}; need_ssh_agent; P=$(/usr/local/bin/kmc pi-login); sshpass -p $P scp ~/.ssh/id_rsa.pub pi@${host}:/tmp; sshpass -p $P ssh pi@$host 'sudo bash -c "mkdir -p /root/.ssh; cat /tmp/id_rsa.pub >>/root/.ssh/authorized_keys; rm /tmp/id_rsa.pub" '; echo "done" ;;  ## copy root pubkey to root@ arg1's a_k via pi std login.
        ps) ps_fixer ;;                                      ## colorized and improved ps output
        sort-skip-header | sort | snh) sort_skip_header ;;   ## sort stdin->stdout but skip 1 header row
        systemd-daemon-reload | sdr | sR) systemctl daemon-reload && emit "reloaded";;   ## systemd daemon refresh
        systemd-down | s0) systemctl stop ${1:-procmon} ;;            ## stop a specified service (procmon by default)
        systemd-restart | sr) systemctl restart ${1:-procmon} ;;      ## restart a specified service (procmon by default)
        systemd-status | ss | sq) systemctl status ${1:-procmon} ;;   ## check service status (procmon by default)
        systemd-up | s1) systemctl start ${1:-procmon} ;;             ## start a specified service (procmon by default)
        without | wo) cat | without "$@" ;;                           ## remove args (csv or regexp) from stdin (space, csv, or line separated)
    # list multiple hosts (or multiple other things)
        list-all | la) list_all | without $EXCLUDE ;;                 ## list all known local-network hosts (respecting -x) via dhcp server leases
        list-git-dirs | lg) echo $GIT_DIRS ;;                         ## list all known git dirs (hard-coded list)
        list-linux | ll) list_linux | without $EXCLUDE ;;             ## list all linux machines (hard-coded list)
        list-pis | lp) list_pis | without $EXCLUDE ;;                 ## list all pi's (hard-coded list)
        list-rsnaps | lr) list_rsnap_hosts | without $EXCLUDE ;;      ## list all hosts using rsnapshot (hard-coded list)
        list-tps | ltp | lt) list_tps | without $EXCLUDE ;;           ## list all tplink hosts (via dhcp leases prefix search)
    # general linux maintenance routines - for multiple hosts
        disk-free-all | dfa | linux-free | lf) run_para "$(list_linux)" "df -h | egrep ' /$'" | column -t | sort ;;   ## root disk free for all linux hosts
        ping-pis | pp | p) pinger "$(list_pis)" ;;                    ## ping all pis
        ping-tps | ptp) pinger "$(list_tps)" ;;                       ## ping all tplinks
        reboot-counts-month | rcm) m=$(date +%b); run_para "$(list_pis)" "fgrep -a reboot-tracker /var/log/messages | fgrep $m | wc -l" ;;  ## count of reboots this month on all pi's
        reboot-counts | rc) d=$(date "+%b %d " | sed -e "s/ 0/  /"); echo "$d"; run_para "$(list_pis)" "fgrep -a reboot-tracker /var/log/messages | fgrep '$d' | wc -l" ;;  ## count of reboots today on all pi's
        re-wifi-pi | rwp) run_para "$(list_pis)" "wpa_cli -i wlan0 reconfigure" ;;             ## reconf wifi ap on pis
        update-all | update_all | ua) updater "$(list_linux | without jack,blue,mc2)" ;;       ## run apt-get upgrade on all linux hosts
        uptime | uta | ut) run_para "$(list_linux)" "uptime" | sed -e 's/: *[0-9:]* /:/' -e 's/:up/@up/' -e 's/,.*//' -e 's/ssh: con.*/@???/' | column -s@ -t | sort ;;  ## uptime for all linux hosts
    # run arbitrary commands on multiple hosts
        listp) run_para LOCAL "$(cat)" "$@" ;;      ## run $@ locally with --host-subst, taking list of substitutions from stdin rather than a fixed host list.  spaces in stdin cause problems (TODO).
        run | run-remote | rr | r) hostspec=$1; shift; run_para "$(list_dynamic $hostspec)" "$@" ;;  ## run cmd $2+ on listed hosts $1
        run-local | rl) hostspec=$1; shift; run_para LOCAL "$(list_dynamic $hostspec)" "$@" ;;       ## eg: q run-local linux scp localfile @:/destdir
        run-pis | rpis | rp) run_para "$(list_pis)" "$@" ;;               ## run command on all pi's
    # jack/homesec specific maintenance routines
        checks | c) checks ;;                                             ## run all (local) status checks
        dhcp-lease-rm | lease-rm | rml | rmmac) update_dns_rmmac "$@" ;;  ## update lease file to remove an undesired dhcp assignment
        dns-update | mac-update | du | mu | mac) update_dns ;;            ## add/change a mac or dhcp assignment
        exim-queue-count | eqc) d run eximdock bash -c 'exim -bpr | grep "<" | wc -l' ;;              ## count current mail queue
        exim-queue-count-frozen | eqcf) d run eximdock bash -c 'exim -bpr | grep frozen | wc -l' ;;   ## count current frozen msgs in queue
        exim-queue-list | eq) d run eximdock exim -bp ;;                  ## list current mail queue
        exim-queue-zap | eqrm) d run eximdock bash -c 'cd /var/spool/exim/input; ls -1 *-D | sed -e s/-D// | xargs exim -Mrm' ;;  ## clear the exim queue
        exim-queue-zap-frozen | eqrmf) d run eximdock bash -c 'exim -bpr | grep frozen | cut -f4 -d" " | xargs exim -Mrm' ;;   ## clear frozen msgs from queue
        exim-queue-run | eqr) d run eximdock exim -qff ;;                 ## unfreeze and retry the queue
        enable-rsnap | enable_rsnap) enable_rsnap ;;                      ## set capabilities for rsnapshot (upgrades can remove the caps)
        git-add-repo | git-add | gar) git_add_repo "$1" ;;                ## add a new repo $1 to gitdock
        git-update-pis | git-pis | git-up) git_update_pis ;;              ## pull git changes and restart services on pis/homesec
        homesec-add-user | hau) homesec_add_user "$1" "$2" ;;             ## add a user $1 to homesec via djangi cgi
        homesec-del-user | hdu) homesec_del_user "$1" ;;                  ## remove user $1 freom homesec via djangi cgi
        lease-orphans | lsmaco | lo | unknown-macs | um) leases_list_orphans ;;   ## list dhcp leases not known to dnsmasq config
        lease-query | lsmacs | lq) egrep --color=auto "$1" $LEASES ;;     ## search for $1 in dhcp leases file
        lease-query-red | lqr | 9) fgrep --color=auto -F ".9." $LEASES || echoc green "ok\n" ;;  ## list red network leases
        keypad | key | k) run_keypad_command "$1" ;;                      ## run command $1 as if typed on homectrl keypad
        keypad-commands | kc) keypad_commands "$1" ;;                     ## list homesec keypad common commands ($1 to search)
        panic-reset | PR) runner /usr/local/bin/panic reset ;;            ## recover from a homesec panic
        procmon-clear-cow | pcc | cc) procmon_clear_cow ;;                ## remove any unexpected docker cow file changes
        procmon-query | pq) curl -sS jack:8080/healthz; echo ''; if [[ -s $PROCQ ]]; then cat $PROCQ; fi ;;   ## check procmon status
        procmon-rescan | pr) curl -sS jack:8080/scan >/dev/null ; curl -sS jack:8080/healthz; echo '' ;;      ## procmon re-scan and show status
        procmon-zap | homesec-reset | hr | pz) runner :>$PROCQ; echo 'procmon queue cleared.' ;;              ## clear procmon queue
        procmon-update | pu) procmon_update ;;                            ## edit procmon whilelist and restart
        syslog-queue-archive | queue-archive | sqa | qa) zcat -f /root/j/logs/queue $(/bin/ls -t /root/j/logs/Arc/que*) | less ;;  ## show full queue history
        syslog-queue-filter-ssh | queue-filter | sqf | qf) runner sed -i -e "/session opened/d" /rw/log/queue ;;  ## remove sshs from log queue
        syslog-queue-zap | queue-zap | qz) runner bash -c ":>/rw/log/queue" ;;             ## wipe the current log queue
        syslog-queue-view | syslog-queue | sqv | q) less /rw/log/queue ;;                  ## view the current log queue
        syslog-queue-view-no-ssh | sqv0 | q0) fgrep -v 'session opened' /rw/log/queue ;;   ## view the current log queue (w/o ssh)
        syslog-queue-view-yesterday-no-ssh | sqv1 | q1) fgrep -v 'session opened' /rw/log/Arc/queue.1 ;;   ## view yesterday's log queue
    # internal
        help | h) myhelp "$@";;                                           ## display this help ($1 to search)
        commands) myhelp | fgrep -v '#' | sed -e 's/\t/ /g' -e 's/^  *//' -e 's/   .*//' | tr '|' '\n' | tr -d ' ' | sort --version-sort  ;;  ## list q commands and flags
        dup-check | check | chk) ( $0 commands | uniq -c | fgrep -v '  1 ' ) || echoc green 'all ok\n' ;;  ## check this script for duplicated cmd strings
        *) emit "invalid command: $cmd"; exit 3 ;;
    esac
}

main "$@"
