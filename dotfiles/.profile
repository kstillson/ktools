
# (note: this file is only run when shells are started with the login option.
#  that is not the default for gnome-terminal launches.  to make sure this
#  logic is included for gnome-terminal, edit the launch profile, under the
#  'command' tab, and check the box to use a login shell.)

[[ -r ~/.profile.local ]] && . ~/.profile.local


# this is redundant to the logic in .bashrc, but for "sudo -i", only .profile
# is run, and some sudo'd commands rely on the path being set.

if [ "$UID" == "0" ]; then
    PATH=/root/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
else
    PATH=~/bin:/usr/local/bin:/usr/bin:/bin
fi

# ---------- interactive only

# If not running interactively, stop now.
[ -z "$PS1" ] && return

# ---- screen startup logic

echo ""
/usr/bin/screen -ls | grep --color=never '(' || true

# too dangerous to auto-start screen as root; tends to interfere with stuff like sulogin, cloud-provider auto-logins, etc
if [[ "$UID" == "0" ]]; then return; fi

echo ""
read -e -p 'Enter screen session: ' -t 5 got
if [[ $? != 0 ]]; then got='k1'; fi
case "$got" in
    "")          exec /usr/bin/screen -c .screenrc-k1 -d -R k1 ;;
    e|E)         exec /usr/bin/screen -c .screenrc-ke -d -R ke ;;
    n|N|x|X|q|Q) echo "no screen..." ;;
    -*|=*)       xdotool type ${got:1}$'\n'; exec /usr/bin/screen -D -R k0 ;;
    *)           exec /usr/bin/screen -D -R -S "${got}" ;;
esac
