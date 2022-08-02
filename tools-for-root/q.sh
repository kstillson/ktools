#!/bin/bash
set -e

# q - quick Linux commands and reference.
# (c) Ken Stillson <ktools@point0.net>, 2021.  Released under the MIT license.

# Whenever I find I'm running a non-trivial Linux command a bunch, or need to
# look up how a Linux utility works, I tend to add a subcommand for it to this
# script.  This both provides a quick and easy way of running it next time,
# and provides a central location where I can find such tools.  I used to
# create .bashrc aliases, but when bashrc gets too complex, it becomes
# dangerous to modify and slows down every shell launch.  This is better.
#
# Over time, I started to add things like colorization and other neat bash
# tricks (like some commands adjusting operation depending on whether the
# calling stdin is an interactive terminal or not).  So now I also use this
# as a repository of clever bash tricks.
#
# The built-in help system works by auto-generating its content from the
# source code.  To get a list of all commands, use "q help".  Adding a param
# searches for commands with a keyword, e.g. "q h syslog" lists all commands
# that have anything to do with syslog.
#
# Some of the details in here are specific to my home configuration and
# won't be directly useful.  But I'm releasing the script anyway, in hopes
# that the bash-tricks collection and the overall structure/approach might
# be of interest, and can be adapted to your own environment.


# ---------- flag defaults

DEBUG=0          # don't delete tempfiles
EXCLUDE="blue"   # csv list of hosts to exclude
HOST_SUBST="@"   # replace this substring with hostnames in some commands
PARA=1           # run commands for multiple hosts in parallel
TEST=0           # for commands that would make changes, print them rather than running them
TIMEOUT=90       # default ssh connect timeout
VERBOSE=0        # print commands as they are run

# ---------- control constants

MY_HOSTNAME=$(hostname)    # always run commands locally on this host.
# default flags to run_para command (see ../pylib_tools):
RP_FLAGS_BASE="--plain --quiet --subst $HOST_SUBST --timeout $TIMEOUT "
RP_FLAGS="${RP_FLAGS_BASE} --output - "


# ---------- hard-coded control constants
# (almost certainly wrong for anyone else but the author...)

if [[ "$MY_HOSTNAME" == "jack" ]]; then KMHOST="keymaster:4444"; else KMHOST="jack:4444"; fi
KM="https://${KMHOST}"

DD="/root/docker-dev/dnsdock/files/etc/dnsmasq/private.d"   # Where dnsmasq config files are stored.
GIT_DIRS="/root/arps /root/docker-dev /root/dev/dots-rc /root/dev/homectrl /root/dev/ktools"  # List of git dirs this script manages.
KMD_P="$HOME/dev/ktools/private.d/km.data.pcrypt"  # Location of encrypted keymaster secrets file
LIST_LINUX="a1 blue jack mc2 "  # list of non-RPi linux hosts
LIST_PIS="hs-mud hs-family hs-lounge hs-front lightning pi1 pibr pout trellis1 twinkle"  # list of RPi linux hosts
LEASES="/rw/dv/dnsdock/var_log_dnsmasq/dnsmasq.leases"  # Location of dnsmasq leases (output/generated) file.
PROCQ="/var/procmon/queue"  # Location of ../services/procmon output file
RSNAP_CONF="/root/docker-dev/rsnapdock/files/etc/rsnapshot.conf"  # Location of rsnapshot config input file

# ---------- colorizers

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

# ---------- ssh agent

# TODO: can this be simplified?  externalized?

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
# general purpose helpers

# Return (i.e. output) a tempfile name with $1 embedded (for easier debugging)
function gettemp() {
    name="${1:-temp}"
    mktemp /tmp/q-${name}-XXXX
}

function rmtemp() {
    filename="$1"
    if [[ $DEBUG == 1 ]]; then emitc yellow "DEBUG: leaving tempfile in place: $filename"; return; fi
    rm $filename
}

# If stdin is empty, do nothing.  Otherwise, append title and stdin contents to $out.
function append_if() {
    out="$1"
    title="$2"
    #
    tmp=$(gettemp appendif)
    cat > $tmp
    if [[ -s $tmp ]]; then
        echo "" >> $out
        echo "${title}:" >> $out
        cat $tmp >> $out
    fi
    rmtemp $tmp
    return 0
}

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


# Run "$@" respecting TEST and VERBOSE flags, print exit status if not 0.
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
    bash -c "$@" || status=$?
    if [[ $status != "0" ]]; then emitC red "status $status from $@\n"
    else if [[ "$VERBOSE" == 1 ]]; then emitC green "done (ok): $@\n"; fi
    fi
}

# Wrapper around /usr/local/bin/run_para which repects EXCLUDE, RP_FLAGS and
# TEST.  This method assumes --ssh mode unless $1 is "LOCAL", in which case it
# uses --cmd mode.  ssv hosts in $1, command to run in $2+.
function RUN_PARA() {
    if [[ "$1" == "LOCAL" ]]; then
        type="--cmd"
        shift
    else
        type="--ssh"
        need_ssh_agent
    fi
    hosts="$1"
    shift
    cmd="/usr/local/bin/run_para $RP_FLAGS $type"
    if [[ "$TEST" == 1 ]]; then
        emit "TEST; would run: $cmd '$@'"
        return
    fi
    echo "$hosts" | tr ' ' '\n' | without - "$EXCLUDE" | $cmd "$@"
    return $?
}


# Assume a 1 line header and output stdin sorted but preserving the header.
function sort_skip_header() {
    t=$(gettemp sortskipheader)
    cat > $t
    head -n 1 $t && tail -n +2 $t | sort "$@"
    rmtemp $t
}


# ----------------------------------------
# general linux maintenance

# Add a new repository (named $1) to the git docker instance.
function git_add_repo() {
    name="$1"
    if [[ ! "$name" == *.git ]]; then name="${name}.git"; fi
    dir="/rw/dv/gitdock/home/ken/git/$name"
    runner "mkdir $dir"
    runner "cd $dir"
    runner "git init --bare"
    runner "chown -R dken.200802 $dir"
    runner "chmod -R go+rx,g+w $dir"
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
        runner "git commit -v -a"
    fi
    runner "git remote | xargs -L1 -I@ echo git pull @ master"
    runner "git remote | xargs -L1 git push"
    popd >& /dev/null
    echoc green "done: $dir"
}


# Sync all known git dirs.
function git_sync_all() {
    need_ssh_agent
    for dir in $GIT_DIRS; do git_sync $dir; done
    emitc green "all done\n"
}

# copy root pubkey to root@ arg1's a_k via pi std login.
function pi_root() {
    host=${1:-rp}
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
    need_ssh_agent
    P=$(/usr/local/bin/kmc pi-login)
    sshpass -p $P scp ~/.ssh/id_rsa.pub pi@${host}:/tmp
    sshpass -p $P ssh pi@$host 'sudo bash -c "mkdir -p /root/.ssh
    cat /tmp/id_rsa.pub >>/root/.ssh/authorized_keys
    rm /tmp/id_rsa.pub" '
    echo "done"
}

# Runs a pull in all known local git dirs.
function git_pull_all() {
    need_ssh_agent
    for dir in $GIT_DIRS; do
        if [[ ! -d $dir ]]; then emit "missing dir: $dir"; continue; fi
        runner "cd $dir"
        runner "git pull"
    done
    emitc green "all done\n"
}

# For all local PIs with git repos, pull any updates and restart dependent daemons.
function git_update_pis() {
    set +e
    t=$(gettemp git-updates.out)
    RP_FLAGS="${RP_FLAGS_BASE} --output $t"
    hosts=$(list_pis | without hs-front,pi1,lightning)
    echo "pulling git updates..."
    RUN_PARA "$hosts" "/bin/su pi -c 'cd /home/pi/dev; git pull'"
    if [[ $? != 0 ]]; then cat $t; rmtemp $t; echo ''; emitc red "some failures; not safe to do restarts"; return 1; fi
    echo "restarting services..."
    RUN_PARA "$hosts" "systemctl daemon-reload"
    RUN_PARA "$hosts" "/home/pi/dev/Restart"
    if [[ $? != 0 ]]; then cat $t; rmtemp $t; echo ''; emitc red "some restart failures"; return 1; fi
    emitc green "all done\n"
}

function iptables_list_tables() {
    # iptables-save only writes to stdout, not persistent; no need to wrap in runner().
    iptables-save | egrep '^\*' | tr -d '*' | sort
}

function iptables_list_chains() {
    # iptables-save only writes to stdout, not persistent; no need to wrap in runner().
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

# Wraps iptables_query_real to provide paging if on a terminal.
function iptables_query() {
    if [[ -t 1 && "$1" == "" ]] ; then
        iptables_query_real | less --raw-control-chars --quit-if-one-screen
    else
        iptables_query_real "$1"
    fi
}

# Save current iptables rules to disk for auto-restore upon boot.
  # TODO: move to standard location (with autodetect for ro root)
  # TODO: check if fail2ban is running, and if so, turn it off before saving and then back on again afterwards.
function iptables_save() {
    runner "/bin/mv -f ~/iptables.rules ~/iptables.rules.mbk"
    runner "/usr/sbin/iptables-save > ~/iptables.rules"
    emitc green "saved"
}

# (in parallel) ping the list of hosts in $@.  Try up to 3 times.
function pinger() {
    set +e
    RP_FLAGS="${RP_FLAGS_BASE} -q -m 99 -o -"
    problems=$(RUN_PARA LOCAL "$@" "set -o pipefail; ping -c3 -W3 -i0.5 -q ^^@ | grep loss | sed -e 's/^.*received, //'" | fgrep -v " 0%" $t | cut -f1 -d:)
    if [[ "$problems" == "" ]]; then emitc green "all ok\n"; return; fi
    for try in 1 2 3; do
        echo ""
        emit $(printf "problems: [ $(echo $problems | tr '\n' ' ') ]... ${RED} retry #${try}/3... ${RESET}")
        sleep 1
        problems=$(RUN_PARA LOCAL "$problems" "ping -c3 -W3 -i0.5 -q ^^@ | grep loss | sed -e 's/^.*received, //'" | fgrep -v " 0%" $t | cut -f1 -d:)
    if [[ "$problems" == "" ]]; then emit "fixed; $(echoC green 'all ok\n')"; return; fi
    done
    emitc red ":-("
}

# Run the ps command with preferred options, colorization, and docker container-id lookups.
function ps_fixer() {
    dmap=$(gettemp dmap)
    /usr/bin/sudo /root/bin/d-map > $dmap
    t=$(gettemp psfixer)
    cat >$t <<EOF
s/^root /${RED}root${RESET} /
s/^droot /${YELLOW}droot${RESET} /
s/^dken /${BLUE}dken${RESET} /
s/defunct/${YELLOW}defunct${RESET}/
EOF
    awk "{print \"s/\" \$1 \"/${CYAN}\" \$2 \"${RESET} \", \$1, \"/\"}" < $dmap >> $t
    ps aux --forest | egrep -v '\]$' | sed -f $t | less
    rmtemp $dmap
    rmtemp $t
}

# Run apt update and upgrade on ssv list of hosts in $1
function updater() {
    hosts="$1"
    OUT1="all-update.out"
    OUT2="all-upgrade.out"
    need_ssh_agent
    RP_FLAGS="--output $OUT1 --timeout 240"
    RUN_PARA "$hosts" "apt-get update"
    RP_FLAGS="--output $OUT2 --timeout 999"
    RUN_PARA "$hosts" "apt-get upgrade --yes"
    emit "output sent to $OUT1 and $OUT2 (consider rm $OUT1 $OUT2 )"
}


# ----------------------------------------
# jack / original author's network specific

# My rsnapshot config relies on capabilities to provide unlimited read access to an otherwise
# unprivlidged account.  Sometimes upgrades remove those capabilities, so this puts them back.
# I keep the root dir read-only on my primary server, so need to temp-enable writes...
function enable_rsnap() {
    RUN_PARA "$(list_rsnap_hosts | without jack)" "/sbin/setcap cap_dac_read_search+ei /usr/bin/rsync"
    runner "mount -o remount,rw /"
    runner "/sbin/setcap cap_dac_read_search+ei /usr/bin/rsync"
    runner "mount -o remount,ro /"
}

# Output the list of DHCP leases which are not known to the local dnsmasq server's DNS list.
function leases_list_orphans() {
    allowed_hosts=$(gettemp allowed_hosts)
    fgrep -v '#' $DD/dnsmasq.hosts | cut -f2 | sed -e '/^$/d' -e 's/[0-9\.]* *//' | cut -d' ' -f1 | sort -u > $allowed_hosts
    yellow_hosts=$(gettemp yellow_hosts)
    fgrep 'set:yellow' $DD/dnsmasq.macs | cut -d, -f3 | tr -d ' ' > $yellow_hosts
    fgrep -v -f $yellow_hosts $LEASES | fgrep -v -f $allowed_hosts || emitc green 'all ok\n'
    rmtemp $yellow_hosts
    rmtemp $allowed_hosts
}

# Run a series of dns configuration and status checks.
function dns_check() {
    out=$(gettemp dns-check-out)

    # Search for duplicates in individual config files.
    egrep '^[0-9a-f]' $DD/dnsmasq.macs | cut -d, -f1 | sort | uniq -c | fgrep -v '  1 ' | append_if $out "duplicate MAC assignments"
    egrep '^[0-9]' $DD/dnsmasq.hosts | tr '\t' ' ' | cut -d' ' -f1 | fgrep -v '192.168.1.2' | sort | uniq -c | fgrep -v '  1 ' | append_if $out "duplicate IP assignments"
    hostnames=$(gettemp sorted-hostnames)
    egrep '^[0-9]' $DD/dnsmasq.hosts | tr '\t' ' ' | cut -d' ' -f2- | tr -s ' ' '\n' | sort > $hostnames
    cat $hostnames | uniq -c | fgrep -v '  1 ' | append_if $out "duplicate hostname assignments"

    # Search for autostart docker containers without assigned addresses.
    hostnames_re=$(gettemp hostnames_re)
    cat $hostnames | sed -e 's/^/^/' -e 's/$/$/' > $hostnames_re
    d la | egrep -v -f $hostnames_re | append_if $out "containers without assigned IP addresses"

    # Search for green network MAC addresses without an assigned IP (will cause dhcp to fail because of dnsmasq 'static' config).
    fgrep 'set:green' $DD/dnsmasq.macs | cut -d, -f3 | tr -d ' ' | egrep -v -f $hostnames_re | append_if $out "green MACs without assigned addresses"
    rmtemp $hostnames
    rmtemp $hostnames_re

    # Search for contradictions between config files and what's actually seen in the leases.
    allowed_mac_to_names=$(gettemp allowed-mac-to-names)
    egrep '^[0-9a-f]' $DD/dnsmasq.macs | cut -d, -f1,3 | tr -d ',' > $allowed_mac_to_names
    cut -d' ' -f2,4 $LEASES | fgrep -v '*' | fgrep -v -f $allowed_mac_to_names | append_if $out "MACs with incorrect hostname assigned"
    rmtemp $allowed_mac_to_names
    #
    allowed_ip_to_hostname=$(gettemp allowed-ip-to-hostnames)
    egrep '^[0-9]' $DD/dnsmasq.hosts | tr -s '\t' ' ' | cut -d' ' -f1,2 > $allowed_ip_to_hostname
    # (note: we filter out .6. (yellow network) addrs because they're dynamically assigned and thus have no 'correct' address).
    cut -d' ' -f3,4 $LEASES | fgrep -v '.6.' | fgrep -v '*' | fgrep -v -f $allowed_ip_to_hostname | append_if $out "MACs with incorrect IP assigned"
    rmtemp $allowed_ip_to_hostname

    # Summarize findings.
    if [[ -s $out ]]; then emitc red problems; cat "$out"; else echoc green 'all ok'; fi
    rmtemp $out
}

# Check for defined hosts not in dhcp leases list (machines could just be off).
function dns_missing() {
    leased_names=$(gettemp leased_names)
    cut -d' ' -f4 $LEASES | fgrep -v '*' > $leased_names
    fgrep 'set:green' $DD/dnsmasq.macs | cut -d, -f3 | tr -d ' ' | fgrep -v -f $leased_names | sort
    rmtemp $leased_names
}

# Update the DHCP server's mapping for mac->hostname; generally needed when adding a new host to the network.
# (I manage by DNS entries manually in this way, so new hosts will cause an alert until manually added.
#  Because security.)
function dns_update() {
    s1=$(stat -t $DD/dnsmasq.macs)
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
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
function dns_update_rmmac() {
    search="$1"
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
    t=$(gettemp leases-search)
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
        runner "/bin/rm $fn"
    done
    emitc green done
}

# Update the whitelist of known-processes on the primary server.  Test the results
# and if the test passes, restart the monitoring daemon with the new list.
function procmon_update() {
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
    t=$(gettemp procmon-queue-sorted)
    sort -u < $PROCQ > $t
    cd /root/dev/ktools/services/procmon
    emacs procmon_whitelist.py $t
    ./procmon.py -t -w procmon_whitelist.py | tee $t
    last=$(tail -1 $t)
    rm -f $t
    if [[ "$last" != "all ok" ]]; then
        echoc yellow "SCAN DOESN'T LOOK CLEAN; NOT RESTARTING PROCMON."
        return
    fi
    echo "updating procmon and clearing queue..."
    runner "make install"
    runner ":>$PROCQ"
    runner "systemctl restart procmon"
    echoc green "procmon restarted; ready for git commit in /root/dev/ktools/services/procmon"
}

# push an update of the pylib wheel distribute to select RPI's
function push_wheel() {
    DESTS="$@"
    if [[ "$DESTS" == "" ]]; then DESTS="ap2 hs-mud hs-family hs-lounge pi1 pibr pout trellis1"; fi
    SRC="/root/dev/ktools/pylib/dist/kcore_pylib-*-py3-none-any.whl"
    SRC_BASE=$(basename "$SRC")
    echoc cyan "copy phase"
    RUN_PARA LOCAL "$DESTS" "scp $SRC @:/tmp" || true
    echoc cyan "install phase"
    RUN_PARA "$DESTS" "umask 022; pip3 install --system --upgrade /tmp/$SRC_BASE; rm /tmp/$SRC_BASE"
}


# Run a series of checks on the status of my home network.
function checks_real() {
    nag | expect "nagios checks" "all ok"
    leases_list_orphans |& expect "dns orphans" "all ok"
    cat $PROCQ | expect "procmon queue" ""
    fgrep -v 'session opened' /rw/log/queue | expect "syslog queue" ""
    $0 dup-check | expect "$(basename $0) dup cmds" "all ok"
    dns_check | expect "dns config check" "all ok"
    /root/bin/d dup-check |& expect "docker dup cmds" "all ok"
    /root/bin/d check-all-up |& expect "docker instances" "all ok"
    /root/bin/d run eximdock bash -c 'exim -bpr | grep "<" | wc -l' |& expect "exim queue empty" "0"
    /usr/bin/stat --format=%s /rw/dv/eximdock/var_log/exim/paniclog |& expect "exim panic log empty" "0"
    /usr/bin/stat --format=%s /rw/dv/eximdock/var_log/exim/rejectlog |& expect "exim reject log empty" "0"
    cat /root/dev/ktools/private.d/*.data 2>/dev/null | wc -l | expect "no unencrpted ktools secrets" "0"
    git_check_all |& expect "git dirs with local changes" ""
}

# Wrapper around checks_real that does formatting and checks for overall status.
function checks() {
    t1=$(gettemp checks-stdout)
    t2=$(gettemp checks-stderr)
    checks_real >$t1 2>$t2
    bad=$(fgrep -v -e "- ok" $t2 | wc -l)   # count of failed checks from stderr
    cat $t1
    echo ""
    cat $t2 | column -s- -t
    rmtemp $t1
    rmtemp $t2
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

# Scan the keymaster logs.  List all errors and a summary of successes.
function keymaster_logs() {
    tmp=$(gettemp km-logs)
    zcat -f /rw/dv/keymaster/var_log_km/km.log* | \
        fgrep ': ' | fgrep -v 'GET: ' | fgrep -v 'POST: ' | \
        cut -d: -f6- | sed -e 's/:16[0-9]*/:T/g' -e 's/delta [0-9]*/delta D/' | \
        sort | uniq -c | sort -rn | \
        less --quit-if-one-screen
}

# Enter the keymaster password to get the service ready.
function keymaster_reload() {
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
    stat=$(curl -ksS ${KM}/healthz)
    if [[ "$stat" == "ok" ]]; then emitc blue "already ok"; return 0; fi
    read -s -p "km password: " passwd
    echo ""
    stat=$(curl -ksS -d "password=$passwd" "${KM}/load" | html2text)
    if [[ "$stat" != "ok" ]]; then emitc red "$stat"; return 1; fi
    emitc green ok
}

function keymaster_status() {
    curl -ksS "${KM}/healthz"
    echo ""
}

# Decrypt, edit, and re-encrypt the KM database, then rebuild and restart KM.
# TODO: gpg_s -> pcrypt
function keymaster_update() {
    if [[ "$TEST" == 1 ]]; then emitC red "not supported in test mode."; exit -1; fi
    read -s -p "km password: " passwd
    tmp=$(gettemp kmd)
    gpg_s -p'$passwd' -i "$KMD_P" -o "$tmp"
    s1=$(stat -t $tmp)
    emacs $tmp
    s2=$(stat -t $tmp)
    if [[ "$s1" == "$s2" ]]; then emitc yellow "no changes; abandoning."; rm $tmp; return; fi
    read -p "ok to proceed? " ok
    if [[ "$ok" != "y" ]]; then emitc yellow "aborted."; rm $tmp; return; fi
    mv -f $KMD_P ${KMD_P}.prev
    pcrypt -p'$passwd' -i "$tmp" -o "$KMD_P"
    rm $tmp
    emitc green "re-encryption done; attempting to rebuild kmdock"
    d u keymaster   # allow -e to abort if this fails.
    emitc blue "waiting for km to stabalize..."
    sleep 2
    echo "$passwd" | keymaster_reload
    emitc green "keymaster update done."
}

# Disable the keymaster.
function keymaster_zap() {
    stat=$(curl -ksS ${KM}/healthz)
    if [[ "$stat" == *"not ready"* ]]; then emitc blue "already zapped"; return 0; fi
    runner "curl -ksS ${KM}/qqq >/dev/null"
    stat=$(curl -ksS ${KM}/healthz)
    if [[ "$stat" == *"not ready"* ]]; then emitc orange "zapped"; return 0; fi
    emitc red "zap failed: $stat"
}

# Run $1 as if it was typed into a homesec keypad.
function run_keypad_command {
    runner "curl -sS -d 'cmd=$1' -X POST http://hs-mud:1235/ | sed -e 's/<[^>]*>//g'"
    echo ""
}


# ----------------------------------------
# host lists

function list_all() {
    ( list_linux | tr ' ' '\n' ; cut -d' ' -f4 $LEASES ) | tr -d ' ' | sort -u | tr '\n' ' '
    echo ''
}

function list_linux() {
    echo -n "$LIST_LINUX"
    list_pis
}

function list_pis() {
    echo $LIST_PIS
}

function list_rsnap_hosts() {
    egrep '^backup' $RSNAP_CONF | cut -d@ -f2 | cut -d: -f1 | sort -u
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
    t=$(gettemp without-stdin)
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
    rmtemp $t
}

# ----------------------------------------
# internal

# Scan my own source code, find the main switch statement, extract and format showing the commands this script supports.
function myhelp_real() {
    awk -- '/case "\$flag/,/esac/{ print } /case "\$cmd/,/esac/{ print }' $0 | \
        sed -e 's/\t/        /' | \
        egrep '(^ *#)|(^ *--)|(^        [a-z])' | \
        sed -e '/case /d' -e '/esac/d' -e 's/^    //' -e 's/##/~/' -e 's/).*;;//' | \
        column -t -s~
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

    # ---------- parse flags

    POSITIONAL=()
    while [[ $# -gt 0 ]]; do
        flag="$1"
        case "$flag" in
    # Note: flags mostly only affect multi-host commands...
            --debug | -d) DEBUG=1 ;;                      ## leave temp files in place
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

    # ---------- main switch

    cmd="$1"
    if [[ "$cmd" == "" ]]; then myhelp; exit 0; fi
    shift
    case "$cmd" in
        # general linux maintenance routines for localhost
        binds | bm | lbm) findmnt | grep  "\[" ;;                  ## list bind mounts
        df) df -h | egrep -v '/docker|/snap|tmpfs|udev' ;;         ## df with only interesting output
        epoch-day | ed | ED)                                       ## epoch day $1 to m/d/y
            date -u +%m/%d/%y -d @$(( $1 * 86400 )) ;;
        epoch-seconds | es | ES)                                   ## epoch seconds $1 to standard date format
            echo "$1" | sed -e 's/,//g' | xargs -iQ date -d @Q ;;
        es-day-now | es-now-day | EDnow | day)                     ## print current epoch day
            echo $(( $(date -u +%s) / 86400 )) ;;
        es-now | ESnow | now) date -u +%s ;;                       ## print current epoch seconds
        iptables-list-chains | iptc | ic) iptables_list_chains ;;  ## print list of iptables chains
        iptables-list-tables | iptt | it) iptables_list_tables ;;  ## print list of iptables tables
        iptables-query | iptq | iq) iptables_query $1 ;;           ## print/query iptables ($1 to search)
        iptables-save | ipts | is) iptables_save ;;                ## save current iptables
        journal | j) journalctl -u ${1:-procmon} ;;                ## show systemd journal
        git-check-all | gca | gc) git_check_all ;;                 ## list any known git dirs with local changes
        git-sync | git | g) need_ssh_agent; git_sync "${1:-.}" ;;  ## git sync a single directory (defaults to .)
        git-sync-all | git-all | ga) git_sync_all ;;               ## check all git dirs for unsubmitted changes and submit them
        pi-root | pir) pi_root ${1:-rp} ;;                         ## copy root pubkey to root@ arg1's a_k via pi std login.
        ports | listening | l)                                     ## list listening TCP ports
            ss -tupln | tail -n +2 | awk '{$3=$4=$6=""; print; }' | sed -e 's/users:((//' -e 's/))//' -e 's/,/ /g' -e 's/"//g' | column -t | sort -n ;;
        ps) ps_fixer ;;                                            ## colorized and improved ps output
        sort-skip-header | sort | snh) sort_skip_header ;;         ## sort stdin->stdout but skip 1 header row
        systemd-daemon-reload | sdr | sR)                                    ## systemd daemon refresh
            runner "systemctl daemon-reload && emit 'reloaded'" ;;
        systemd-down | s0) runner "systemctl stop ${1:-procmon}" ;;          ## stop a specified service (procmon by default)
        systemd-restart | sr) runner "systemctl restart ${1:-procmon}" ;;    ## restart a specified service (procmon by default)
        systemd-status | ss | sq) runner "systemctl status ${1:-procmon}" ;; ## check service status (procmon by default)
        systemd-up | s1) runner "systemctl start ${1:-procmon}" ;;           ## start a specified service (procmon by default)
        without | wo) cat | without "$@" ;;                        ## remove args (csv or regexp) from stdin (space, csv, or line separated)
    # general linux maintenance routines - for multiple hosts
        disk-free-all | dfa | linux-free | lf)                     ## root disk free for all linux hosts
            RUN_PARA "$(list_linux)" "df -h | egrep ' /$'" | column -t | sort ;;
        ping-pis | p) pinger "$(list_pis)" ;;                      ## ping all pis
        ping-pis-continuous | ppc | pp)                            ## ping all pi's continuously until stopped
            RP_FLAGS="--quiet"; RUN_PARA LOCAL "$(list_pis)" "ping @" ;;
        ping-tps | ptp) pinger "$(list_tps)" ;;                    ## ping all tplinks
        reboot-counts-month | rcm)                                 ## count of reboots this month on all pi's
            m=$(date +%b); RUN_PARA "$(list_pis)" "fgrep -a reboot-tracker /var/log/messages | fgrep $m | wc -l" ;;
        reboot-counts | rc)                                        ## count of reboots today on all pi's
            d=$(date "+%b %d " | sed -e "s/ 0/  /"); echo "$d"; RUN_PARA "$(list_pis)" "fgrep -a reboot-tracker /var/log/messages | fgrep '$d' | wc -l" ;;
        re-wifi-pi | rwp)                                          ## reconf wifi ap on pis
            RUN_PARA "$(list_pis)" "wpa_cli -i wlan0 reconfigure" ;;
        update-all | update_all | ua)                              ## run apt-get upgrade on all linux hosts
            updater "$(list_linux | without jack,blue,mc2)" ;;
        uptime | uta | ut)                                         ## uptime for all linux hosts list multiple hosts (or multiple other things)
            RUN_PARA "$(list_linux)" "uptime" | sed -e 's/: *[0-9:]* /:/' -e 's/:up/@up/' -e 's/,.*//' -e 's/ssh: con.*/@???/' | column -s@ -t | sort ;;
        list-all | la) list_all | without $EXCLUDE ;;              ## list all known local-network hosts (respecting -x) via dhcp server leases
        list-git-dirs | lg) echo $GIT_DIRS ;;                      ## list all known git dirs (hard-coded list)
        list-linux | ll) list_linux | without $EXCLUDE ;;          ## list all linux machines (hard-coded list)
        list-pis | lp) list_pis | without $EXCLUDE ;;              ## list all pi's (hard-coded list)
        list-rsnaps | lr) list_rsnap_hosts | without $EXCLUDE ;;   ## list all hosts using rsnapshot (hard-coded list)
        list-tps | ltp | lt) list_tps | without $EXCLUDE ;;        ## list all tplink hosts (via dhcp leases prefix search)
    # run arbitrary commands on multiple hosts
        listp)                                                     ## run $@ locally with --host-subst, taking list of substitutions from stdin rather than a fixed host list.  spaces in stdin cause problems; TODO
            RUN_PARA LOCAL "$(cat)" "$@" ;;
        run | run-remote | rr | r)                                 ## run cmd $2+ on listed hosts $1
            hostspec=$1; shift; RUN_PARA "$(list_dynamic $hostspec)" "$@" ;;
        run-local | rl)                                            ## eg: q run-local linux scp localfile @:/destdir
            hostspec=$1; shift; RUN_PARA LOCAL "$(list_dynamic $hostspec)" "$@" ;;
        run-pis | rpis | rp)                                       ## run command on all pi's
            RUN_PARA "$(list_pis)" "$@" ;;
    # jack/homesec specific maintenance routines
        checks | c) checks ;;                                             ## run all (local) status checks
        dhcp-lease-rm | lease-rm | rml | rmmac) dns_update_rmmac "$@" ;;  ## update lease file to remove an undesired dhcp assignment
        dns-check | dhcp-check | dc) dns_check ;;                         ## check dnsmasq config for dups/missing/etc.
        dns-missing | dhcp-missing | who-is-off | dm) dns_missing ;;      ## any assigned green network hostnames missing from the leases?
        dns-update | mac-update | du | mu | mac) dns_update ;;            ## add/change a mac or dhcp assignment
        exim-queue-count | eqc)                                           ## count current mail queue
            d run eximdock bash -c 'exim -bpr | grep "<" | wc -l' ;;
        exim-queue-count-frozen | eqcf)                                   ## count current frozen msgs in queue
            d run eximdock bash -c 'exim -bpr | grep frozen | wc -l' ;;
        exim-queue-list | eq) d run eximdock exim -bp ;;                  ## list current mail queue
        exim-queue-zap | eqrm)                                            ## clear the exim queue
            runner "d run eximdock bash -c 'cd /var/spool/exim/input; ls -1 *-D | sed -e s/-D// | xargs exim -Mrm'" ;;
        exim-queue-zap-frozen | eqrmf)                                    ## clear frozen msgs from queue
            runner "d run eximdock bash -c 'exim -bpr | grep frozen | cut -f4 -d' ' | xargs exim -Mrm'" ;;
        exim-queue-run | eqr) runner "d run eximdock exim -qff" ;;        ## unfreeze and retry the queue
        enable-rsnap | enable_rsnap) enable_rsnap ;;                      ## set capabilities for rsnapshot (upgrades can remove the caps)
        git-add-repo | git-add | gar) git_add_repo "$1" ;;                ## add a new repo $1 to gitdock
        git-update-pis | git-pis | git-up) git_update_pis ;;              ## pull git changes and restart services on pis/homesec
        lease-orphans | lsmaco | lo | unknown-macs | um) leases_list_orphans ;;   ## list dhcp leases not known to dnsmasq config
        lease-query | lsmacs | lq) egrep --color=auto "$1" $LEASES ;;     ## search for $1 in dhcp leases file
        lease-query-red | lqr | 9) fgrep --color=auto -F ".9." $LEASES || echoc green "ok\n" ;;  ## list red network leases
        keypad | key | k) run_keypad_command "$1" ;;                      ## run command $1 as if typed on homectrl keypad
        keypad-commands | kc) keypad_commands "$1" ;;                     ## list homesec keypad common commands ($1 to search)
        keymaster-reload | kmr) keymaster_reload ;;                       ## load/reload keymaster state (requires password)
        keymaster-logs | kml | kmq) keymaster_logs ;;                     ## analyze km logs
        keymaster-status | kms) keymaster_status ;;                       ## edit keymaster encrypted data and restart
        keymaster-update | kmu) keymaster_update ;;                       ## edit keymaster encrypted data and restart
        keymaster-zap | kmz) keymaster_zap ;;                             ## clear keymaster state (and raise alerts)
        panic-reset | PR)                                                 ## recover from a homesec panic
            keymaster_reload; /usr/local/bin/panic reset ;;
        procmon-clear-cow | pcc | cc) procmon_clear_cow ;;                ## remove any unexpected docker cow file changes
        procmon-query | pq)                                               ## check procmon status
            curl -sS jack:8080/healthz; echo ''; if [[ -s $PROCQ ]]; then cat $PROCQ; fi ;;
        procmon-rescan | pr)                                              ## procmon re-scan and show status
            curl -sS jack:8080/scan >/dev/null ; curl -sS jack:8080/healthz; echo '' ;;
        procmon-zap | homesec-reset | hr | pz)                            ## clear procmon queue
            runner ":>$PROCQ; echo 'procmon queue cleared.'" ;;
        procmon-update | pu) procmon_update ;;                            ## edit procmon whilelist and restart
        push-wheel) push_wheel "$@" ;;                                    ## push update of kcore_pylib to select rpi's
        syslog-queue-archive | queue-archive | sqa | qa)                  ## show full queue history
            zcat -f /root/j/logs/queue $(/bin/ls -t /root/j/logs/Arc/que*) | less ;;
        syslog-queue-filter-ssh | queue-filter | sqf | qf)                ## remove sshs from log queue
            runner 'sed -i -e "/session opened/d" /rw/log/queue' ;;
        syslog-queue-zap | queue-zap | qz) bash -c :>/rw/log/queue ;;     ## wipe the current log queue
        syslog-queue-view | syslog-queue | sqv | q) less /rw/log/queue ;; ## view the current log queue
        syslog-queue-view-no-ssh | sqv0 | q0)                             ## view the current log queue (w/o ssh)
            fgrep -v 'session opened' /rw/log/queue ;;
        syslog-queue-view-yesterday-no-ssh | sqv1 | q1)                   ## view yesterday's log queue
            fgrep -v 'session opened' /rw/log/Arc/queue.1 ;;
    # internal
        help | h) myhelp "$@";;                                           ## display this help ($1 to search)
        commands)                                                         ## list q commands and flags
            myhelp | fgrep -v '#' | sed -e 's/\t/ /g' -e 's/^  *//' -e 's/   .*//' | tr '|' '\n' | tr -d ' ' | sort --version-sort  ;;
        dup-check | check | chk)                                          ## check this script for duplicated cmd strings
            ( $0 commands | uniq -c | fgrep -v '  1 ' ) || echoc green 'all ok\n' ;;
        *) emit "invalid command: $cmd"; exit 3 ;;
    esac
}

main "$@"
