
# (note: this file is only run when shells are started with the login option.
#  that is not the default for gnome-terminal launches.  to make sure this
#  logic is included for gnome-terminal, edit the launch profile, under the
#  'command' tab, and check the box to use a login shell.)

[[ -r ~/.bashrc ]] && . ~/.bashrc
[[ -r ~/.profile.local ]] && . ~/.profile.local


# ---- exported internal use varz

export BLACK='\u001b[30m'
export BLUE='\033[01;34m'
export CYAN='\033[01;36m'
export GREEN='\033[01;32m'
export MAGENTA='\033[01;35m'
export RED='\033[0;31m'
export YELLOW='\033[0;33m'
export WHITE='\033[01;37m'
export RESET='\033[00m'

export THREADS=$(grep -c ^processor /proc/cpuinfo)


# ---- export app settings

[[ -f /usr/bin/emacs ]] && export EDITOR="/usr/bin/emacs -nw"
export PAGER="less"

export FZF_DEFAULT_OPTS='--bind "ctrl-v:page-down" --bind "alt-v:page-up" --cycle --reverse'

export LESS='--chop-long-lines --ignore-case --jump-target=4 --LINE-NUMBERS --LONG-PROMPT --quit-at-eof --quiet --RAW-CONTROL-CHARS --squeeze-blank-lines --HILITE-UNREAD'
less --version | fgrep -q 'less 5' && export LESS="$LESS --line-num-width=4 --use-color"

if [ -x /usr/bin/dircolors ]; then export COLOR_OPTION='--color=auto'; else export COLOR_OPTION=''; fi


# ---- screen startup logic

# If not running interactively, stop now.
[ -z "$PS1" ] && return

echo ""
/usr/bin/screen -ls | grep --color=never '('

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
