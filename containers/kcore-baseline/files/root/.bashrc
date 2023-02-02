# .bashrc

# Preferred path.
if [ "$UID" == "0" ]; then
  export PATH=~/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
else
  export PATH=~/bin:/usr/local/bin:/usr/bin:/bin
fi

# If not running interactively, stop now.
[ -z "$PS1" ] && return

# ======================================================================
# general global settings

# General settings & options
set -a
umask 027
export PATH=~/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/bin

set -a         # Auto export all variable sets.
umask 027      # rwx r-x ---

export HISTSIZE=2000
export HISTFILESIZE=2000

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
# app specific settings

[[ -f /usr/bin/emacs ]] && EDITOR="/usr/bin/emacs -nw"
PAGER="less"
LESS="-e -i -j4 -M -q -R -S -W"
if [ -x /usr/bin/dircolors ]; then COLOR_OPTION='--color=auto'; else COLOR_OPTION=''; fi


# ======================================================================
# prompt

BLACK='\u001b[30m'
BLUE='\033[01;34m'
CYAN='\u001b[36m'
GREEN='\033[01;32m'
MAGENTA='\u001b[35m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
WHITE='\u001b[37m'
RESET='\033[00m'

function set_prompt() {
  local last=$?
  PS1=""
  if [[ "${last}" != 0 ]]; then PS1+="\[${RED}\][exit ${last}] "; fi
  if [[ -s $HOME/.status ]]; then PS1+="\[${RED}\]{ Status file alert } "; fi
  if [[ -n "$debian_chroot" ]]; then PS1+="\[${YELLOW}\]${debian_chroot}> "; fi
  PS1+="\[${GREEN}\]\u@"
  if [[ -z "${container}" ]]; then PS1+="\h"; else PS1+="\[${YELLOW}\]\h"; fi
  PS1+="\[${RESET}\]:\[${BLUE}\]\w\[${RESET}\]\\$ "
}
PROMPT_COMMAND='set_prompt'

# ======================================================================

# ls
alias ls='ls $COLOR_OPTION'
alias l='ls $COLOR_OPTION -l'
alias ll='ls $COLOR_OPTION -la'

# grep
alias grep='grep $COLOR_OPTION'
alias fgrep='fgrep $COLOR_OPTION'
alias egrep='egrep $COLOR_OPTION'

# viewers and editors
alias e='$EDITOR'
alias E='/usr/bin/emacs -nw'
alias m='less'
alias L='less'
alias Less='less'

# directory control
alias ..='cd ..'
alias md='mkdir'
alias pd='pushd .'
alias po='popd'
alias rd='rmdir'

# general command shortcuts
function S() { screen -D -R $@; AX; }
alias mine="ps aux --forest  | grep $UID"
alias pag='ps auxwww --forest | grep '
alias pam='ps aux --forest | less'
alias R="sudo -i bash"

