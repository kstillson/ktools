# .bashrc

# Preferred path.
if [ "$UID" == "0" ]; then
  PATH=~/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
else
  PATH=~/bin:/usr/local/bin:/usr/bin:/bin
fi

# If not running interactively, stop now.
[ -z "$PS1" ] && return

# ======================================================================
# general global settings

# Include any global config if provided.
[[ -f /etc/bashrc ]] && . /etc/bashrc

umask 027      # rwx r-x ---

declare -x PATH PS1

# Space is cheap; capture lots of bash command history.
HISTSIZE=2000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If this is an xterm set the title to user@host
case "$TERM" in
xterm*|rxvt*)
  echo -ne "\033]0;${USER}@${HOSTNAME}\007"
  ;;
esac


# ======================================================================
# prompt

# this function is run before each command, so it should be as efficient as possible.
# it's main purpose is to set the prompt to include the current working directory,
# and to incidiate in red if the previous command exited with non-zero status.
# it also supports sending a command transcript to syslog if $BASHLOG is set,
# and various alternate colors to highlight certain virtualization environments.
#
function set_prompt() {
  local last=$?
  if [[ -n "$BASHLOG" ]]; then
    /usr/bin/logger -p local1.info -t bash "bash $USER[$$] $SSH_CONNECTION: $(fc -ln -0)"
  fi
  PS1=""
  if [[ "${last}" != 0 ]]; then PS1+="\[${RED}\][exit ${last}] "; fi
  # if [[ -s $HOME/.status ]]; then PS1+="\[${RED}\]{ Status file alert } "; fi
  # if [[ -n "$debian_chroot" ]]; then PS1+="\[${YELLOW}\]${debian_chroot}> "; fi
  PS1+="\[${GREEN}\]\u@"
  if [[ -z "${container}" ]]; then PS1+="\h"; else PS1+="\[${YELLOW}\]\h"; fi
  if [[ -n "${VIRTUAL_ENV}" ]]; then PS1+="\[${MAGENTA}\]{$(basename ${VIRTUAL_ENV})}"; fi
  PS1+="\[${RESET}\]:\[${BLUE}\]\w\[${RESET}\]\\$ "
}
PROMPT_COMMAND='set_prompt'


# ======================================================================
# ssh agent

# Some logic to try to "do the right thing" with ssh agents.  basically:
# "A" will start a local ssh-agent if needed, set apporpriate environment variables,
#     and load default private keys (prompting for passwords when necessary).
# "AX" will clear out and kill the ssh agent and clean-up the environment.

# TODO: This is dangerously complex stuff for .bashrc.  Move to somewhere safer.

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


# ======================================================================
# aliases and trivial functions

# ls
alias ls='ls $COLOR_OPTION'
alias l='ls $COLOR_OPTION -l'
alias ll='ls $COLOR_OPTION -la'

# grep
alias F="find . | grep -i "
alias G='grep -i $COLOR_OPTION'
alias grep='grep $COLOR_OPTION'
alias fgrep='fgrep $COLOR_OPTION'
alias egrep='egrep $COLOR_OPTION'

# add a directory to the end of $PATH if it's valid and not in $PATH already.
addpath() {
    if [[ ! -d "$1" ]]; then echo "$1 not a valid dir"; return 1; fi
    if [[ "$PATH:" == *"$1:"* ]]; then echo "$1 is already in the path."; return 2; fi
    PATH="$PATH:${1}"
    if [[ "$2" != "-" ]]; then echo "ok: $PATH"; fi
}

# viewers and editors
alias e='$EDITOR'
alias E='/usr/bin/emacs -nw'
alias m='less'
alias L='less'
alias T='TAB'
alias TAB='column -t'
alias Less='less'
alias V='gpg -d < '
function _()  { eval "$@" | less; }

# directory control
alias ..='cd ..'
alias ...='cd ../..'
alias ..3='cd ../../..'
alias md='mkdir'
alias pd='pushd .'
alias po='popd'
alias rd='rmdir'

# ssh
alias s='A; ssh'
alias Ssh='ssh -fMN'

# git
alias g="git"
alias UPDOT="cd ~ken/dev/ktools/dotfiles; make dots; cd; . .bashrc"

# base 64 stuff
alias b64e="perl -MMIME::Base64 -0777 -ne 'print encode_base64(\$_)'"
alias b64d="perl -MMIME::Base64 -ne 'print decode_base64(\$_)'"

# Date/time conversions; seconds and days since the Unix epoch
alias ESnow='date -u +%s'
alias EDnow='echo $(( $(date -u +%s) / 86400 ))'
function ED() { date -u +%m/%d/%y -d @$(( $1 * 86400 )); }
function ES() { echo "$1" | sed -e 's/,//g' | xargs -iQ date -d @Q; }
function EM() { date -d @$(( $1 / 1000000 )); }
function ES2ED() { echo $(( $1 / 86400)); }

# screen
function S() { ses=${1:-k1}; shift; screen -D -R ${ses} $@; AX; exit 0; }
alias Sl="screen -ls"

# make
alias M="make -j ${THREADS} "
alias MC="M clean"
alias MI="sudo make install"
alias MT="rm -f test.log; M test"

# root-type stuff
alias R="sudo -i bash"
# btrfs
alias Btrfs='findmnt -t btrfs'
# apt
function AI() { _ apt-cache show "$@"; }
function AIN() { sudo apt-get install "$@"; }
alias    AR='sudo apt remove'
function AS() { { apt-cache search "$@"; printf "\n<> Snaps\n"; snap search "$@"; } | less; }
alias    AU='sudo apt update'
alias    AUP='sudo apt upgrade'
alias    KA='sudo /usr/bin/killall '
alias    KU='sudo /usr/bin/killall -u '

# disk level ops
alias Blk='lsblk -e7 -mf'
alias Df="Dfs | awk '/Mounted on/ { print; next; } { if (\$1 in a) { a[\$1]=sprintf(\"%s, %s\", a[\$1], \$7); } else { a[\$1]=\$0; } } END { for(i in a) print a[i]; }' | Sort"
alias Dfs="df -hT | egrep -v '/docker|/snap|tmpfs|udev|efi'"
alias Mnts='findmnt --real | grep -v snap'
alias ddd="dd status=progress"
alias Space='baobab'
alias SpaceR='sudo baobab'
function mnt() { q="${1:-.}"; findmnt --target ${q}; }
function Mnt() { q="${1:-.}"; findmnt -n -o SOURCE --target ${q}; }

# other general command shortcuts
alias Clk="xclock -d -twelve -brief &"
alias LOCK="xscreensaver-command -lock"
alias Sort="( sed -u 1q; sort )"
alias XF='/usr/bin/xhost +si:localuser:nobody'
alias XR='/usr/bin/xhost +si:localuser:root'
alias c2n='tr "," "\n"'
alias clock='xclock -digital -twelve -brief -fg white -bg black -face "arial black-20:bold" &'
alias copy='xclip -selection clipboard -in '
alias mine="ps aux --forest  | grep '$USER '"
alias pag='ps auxwww --forest | grep '
alias pam='ps aux --forest | less'
alias rlcp='cp --reflink=always '
alias s2n='tr " " "\n"'
alias x="exec startx"

alias RP='run_para --align --cmd'
alias listp='run_para --dry_run --cmd'   # $1 is command to run (needs to be quoted)
function listP() { while IFS= read -r line; do echo "${@//@/${line}}"; done; }

# ---- fancy directory selectors

# switch through directories via prefix matching.  for example, if you have
# directory ./dev/this/and/that   then  C d t a t   would switch to that lower level dir.
# If multiple dirs match the provided pattern, all matches are listed, and you can
# pick which you want.  Use "~" as the first arg to start at home-dir (otherwise is
# relative to current directory).
#
function C() {
    srch=''
    for i in "$@"; do srch="${srch}${i}*/"; done
    if [[ "$PWD" != "$HOME" ]]; then srch2="$HOME/$srch"; else srch2=""; fi
    readarray -t out < <(ls -1d $srch $srch2 2>/dev/null)
    case ${#out[@]} in
	0) echo "not found  ($srch)" ;;
	1) cd "${out[0]}" ;;
	*) select i in ${out[@]}; do cd "$i"; break; done ;;
    esac
}

# hop directly to ktools subdirectories by hard-coded key-letter, or to ktools
# container directory by prefix match.
#
function K() {
    cd ~/dev/ktools
    sel="$1"; sel2="$2"
    case "$sel" in
	 '') ;;
         C) cd containers ;;
	 D) cd dotfiles ;;
         I) cd container-infrastructure ;;
	 K) cd pylib/kcore ;;
	 P) cd pylib ;;
	 Q) cd private.d ;;
	 S) cd services ;;
	 T) cd pylib/tools ;;
	 -|\.) ;;  # pass to "C", below
	 *) t=$(ls -1d containers/${sel}* | head -1 2>/dev/null); if [[ -d "$t" ]]; then cd "$t"; else sel2="$sel"; fi ;;
    esac
    if [[ "$sel2" != "" ]]; then C "$@"; fi
}


# ======================================================================
# local bashrc (do this last so it can locally override anything above)
#
if [ -f ~/.bashrc.local ]; then . ~/.bashrc.local; fi
