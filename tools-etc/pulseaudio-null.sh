#!/bin/bash
set +e

read -d '' ABOUT <<-EOF
     Add a 'null sink' to pulse audio,
     optionally making it the default (-d),
     optionally also a "combo" that sends to the null and the existing default (-c).

     null sinks are useful for things like adding effects chains (route the
     signal to be processed to the null, and the output of the null to the
     desired destination),

     or to have multiple simultaneous processing streams that don't interfere
     with each other (e.g. recording one stream to a file while not playing it
     back on the main speakers, and while using the main speakers normally).

     NB: the --remove option removes all combo/null sinks (by unloading the
     modules).  That boldly assumes this script is the only such module loader.
EOF


function get_sink_id() {
    search_name="$1"
    found=''
    # note: the pipe causes RHS to run in a subshell, so "return" or "break" wouldn't give
    # a signal to the parent about whether we succeeded for not.  So use a custom return
    # value (123) to signal success to the parent.
    pactl list short sinks | while read id name engine type chan spd stat; do
	if [[ "$search_name" == "$name" ]]; then echo "$id"; exit 123; fi
    done
    if [[ $? == 123 ]]; then return 0; fi
    echo "sink '${search_name}' not found" >&2
    return 1
}

function rm_mod() {
    name="$1"
    pactl list short modules | grep "$name" >/dev/null || return 1
    pactl unload-module "${name}"
    echo "unloaded module $name"
    return 0
}


# ---------- args

set_name="NULL1"
set_default_target="NULL1"
while [[ $# -gt 0 ]]; do
    case $1 in
	-c|*combo) set_combo=1; set_default_target="combo" ;;

	-d|*default) set_default=1 ;;

	-g|--get-id) get_sink_id "$2"; exit $? ;;

	-h|--help) printf "\n$0 [--combo|-c] [--default|-d] [--name|-n name]  OR  {--get-id|-g name}  OR {--list|-l}  OR  {--remove|-r}\n\n${ABOUT}\n\n"; exit 0 ;;

	-l|*list) pactl list short sinks; exit $? ;;

	-n|--name) set_name="$2"; shift ;;

	-r|-x|*rm|*remove)
	    rm_mod module-combine-sink || true
	    rm_mod module-null-sink || echo "null-sink module doesn't appear to have been loaded..."
	    exit $? ;;

	*)  echo "unknown arg: $1"; exit 1 ;;
    esac
    shift
done


# ---------- main

pactl load-module module-null-sink sink_name="$set_name" sink_properties=device.description="$set_name"
echo "added sink $set_name"

if [[ "$set_combo" == "1" ]]; then
    current_out=$(pactl get-default-sink)
    pactl load-module module-combine-sink sink_name=combo slaves="${set_name},${current_out}"
    echo "added sink combo -> ${set_name},${current_out}"
fi

if [[ "$set_default" == "1" ]]; then
    pactl set-default-sink ${set_default_target}
    echo "set default sink: $set_default_target"
fi

exit 0
