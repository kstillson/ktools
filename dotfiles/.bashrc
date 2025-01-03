# .bashrc

# Preferred path.
if [ "$UID" == "0" ]; then
  PATH=~/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
else
  PATH=~/bin:/usr/local/bin:/usr/bin:/bin
fi

# ** If not running interactively, stop here. **
[ -z "$PS1" ] && return


# ======================================================================
# general use variables

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


# ======================================================================
# common app settings

[[ -f /usr/bin/emacs ]] && export EDITOR="/usr/bin/emacs -nw"
export PAGER="less"

export FZF_DEFAULT_OPTS="\
 --bind 'ctrl-a:first'              --bind 'ctrl-e:last'  \
 --bind 'ctrl-v:page-down'          --bind 'alt-v:page-up'  \
 --bind '?:preview(Cat {})'         --bind 'shift-down:preview-page-down'  \
 --bind 'alt-shift-up:preview-top'  --bind 'alt-shift-down:preview-bottom'  \
 --bind 'ctrl-/:change-preview-window(70%|down,border-top|hidden|)' \
 --cycle   --layout=reverse-list"

export LESS='--chop-long-lines --ignore-case --jump-target=4 --LINE-NUMBERS --LONG-PROMPT --mouse --quit-at-eof --quit-if-one-screen --quiet --RAW-CONTROL-CHARS --save-marks --squeeze-blank-lines --status-column --HILITE-UNREAD'
less --version | fgrep -q 'less 5' && export LESS="$LESS --line-num-width=4 --use-color"

if [ -x /usr/bin/dircolors ]; then export COLOR_OPTION='--color=auto'; else export COLOR_OPTION=''; fi


# ======================================================================
# includes

# Include any global config if provided.
[[ -f /etc/bashrc ]] && . /etc/bashrc

# Include useful functions from b(ash)lib (e.g.: emitc, _, =, HLE, erun)
[[ -f ${HOME}/bin/blib ]] && source ${HOME}/bin/blib


# ======================================================================
# general global settings

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
function set_prompt() {
  local last=$?
  PS1=""
  if [[ "${last}" != 0 ]]; then PS1+="\[${RED}\][exit ${last}] "; fi
  if [[ -n "${prompt_prefix}" ]]; then PS1+="\[${YELLOW}\]${prompt_prefix}"; fi
  if [[ -f "/tmp/olr" ]]; then PS1+="\[${YELLOW}\]{O/}"; fi
  PS1+="\[${GREEN}\]\u@"
  if [[ -z "${container}" ]]; then PS1+="\h"; else PS1+="\[${YELLOW}\]\h"; fi
  if [[ -n "${VIRTUAL_ENV}" ]]; then PS1+="\[${MAGENTA}\]{$(basename ${VIRTUAL_ENV})}"; fi
  PS1+="\[${RESET}\]:\[${BLUE}\]\w\[${RESET}\]\\$ "
}
PROMPT_COMMAND='set_prompt'


# ======================================================================
# aliases and trivial functions

# ls
alias ls='ls $COLOR_OPTION'

if [[ -x /usr/bin/eza ]] || [[ -x /usr/local/bin/eza ]]; then
    alias l="_ eza --long --almost-all --group --smart-group --color=always --color-scale=size --color-scale-mode=gradient --links   --git --extended --group-directories-first --mounts"
    alias ll="l --total-size --sort=size --reverse"
else
    alias l='ls $COLOR_OPTION -l'
    alias ll='ls $COLOR_OPTION -la'
fi

# finding files by name
function FF() {
    srch="$1"  # If empty, do an interactive fuzzy find; else do a simple grep to stdout
    if [[ "$srch" == "" ]]; then find . | fzf | Copy +
    else find . | grep -i "$srch"; fi
}

# simple finding file contents
alias G='grep -i --color=always'
alias grep='grep $COLOR_OPTION'
alias fgrep='fgrep $COLOR_OPTION'
alias egrep='egrep $COLOR_OPTION'

# simple finding file contents
function F() {
    if [[ -f "$1" ]]; then src="$1"; shift
    elif [ -t 0 ]; then echo "usage: F [file] [search spec]" >&2; return 1
    else src="-"; fi
    if [[ "$1" != "" ]]; then cat "$src" | fzf -q "$@" | Copy +
                         else cat "$src" | fzf         | Copy +
    fi
}
function HL() { /bin/grep --color=always -E "^|$1"; }  # highlight $1

# advanced finding file contents
alias Rg='rg --color=always --column --follow --line-number --no-heading --smart-case '
function RG() {
  srch="$1"  # substring to recursively search for; results displayed via fzf for further filtering and selection.
  RG_PREFIX="rg  --no-heading --color=always --smart-case "
  out=$(FZF_DEFAULT_COMMAND="$RG_PREFIX '$srch'" \
    fzf --ansi --query "$srch" \
        -d: --preview 'cat {1}' --bind 'ctrl-/:change-preview-window(right,70%|down,40%,border-horizontal|hidden|right)' | \
      cut -d: -f1)
  echo ${out} | Copy +
}

function Newest() {
    find ${1:-.} -type f -exec stat --format '%Y :%y %n' "{}" \; | sort -nr | cut -d: -f2- | head
}

# add a directory to the end of $PATH if it's valid and not in $PATH already.
addpath() {
    if [[ ! -d "$1" ]]; then echo "$1 not a valid dir"; return 1; fi
    if [[ "$PATH:" == *"$1:"* ]]; then echo "$1 is already in the path."; return 2; fi
    PATH="$PATH:${1}"
    if [[ "$2" != "-" ]]; then echo "ok: $PATH"; fi
}

# viewers and editors
function Cat() { if [[ -d "$1" ]]; then ls -l "$1"; else cat "$@"; fi; }
alias e="$EDITOR --geometry 132x40+100-100 &"
alias E='/usr/bin/emacs -nw'
alias m='less'
alias L='less'
alias BC='batcat'
alias T='TAB'
alias TAB='column -t'
alias Launch='xdg-open'   # opens with default viewer
alias Less='less'
alias V='xdg-open'
alias man='LESS="${LESS/--LINE-NUMBERS /}" /usr/bin/man'

# directory control
alias ..='cd ..'
alias ...='cd ../..'
alias ..3='cd ../../..'
alias pd='pushd .'
alias po='popd'
alias rd='rmdir'
function md() { mkdir -p "$1"; cd "$1"; }

# ssh
alias Ssh='s -fMN'

# git
alias g="git"
alias UPDOT='cd ~/dev/ktools/dotfiles && if [[ -O . ]]; then git pull; else echo "cannot git pull; wrong user"; fi && make dots && cd && . .bashrc'

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
function S() { ses=${1:-k1}; shift; screen -D -R ${ses} $@; exit 0; }
alias Sl="screen -ls"

# make
alias M="make -j ${THREADS} "
alias MC="M clean"
alias MI="sudo make install"
alias MT="rm -f test.log; M test"

# ktools container full update
function CU() {
    if [[ "$1" != "" ]]; then K "$1" || return; fi
    name="$(basename $(pwd))"
    printf "\n\n${MAGENTA}<*>${RESET} container update: ${YELLOW}${name}${RESET}\n\n"
    make clean && make && make test && make install && d 01 $name
}

# root-type stuff
alias R="sudo -i bash"
# btrfs
alias Btrfs='findmnt -t btrfs'
# apt
if [[ -x /usr/bin/nala ]]; then APT=nala; else APT=apt; fi
alias    AAR='sudo $APT autoremove'
alias    AI="_ $APT show"
alias    AIN="sudo $APT install"
alias    AR='sudo $APT remove'
function AS() { $APT search "$@" | less; }
function ASA() { { $APT search "$@"; printf "\n<> Flathub\n"; flatpak search "$@"; printf "\n<> appimage\n"; appimage-cli-tool search "$@"; } | less; }
function AQ() { /usr/bin/dpkg -l "$1" | /usr/bin/tail -1 | /bin/egrep --color=always -e '^..'; }
alias    AU='sudo $APT update'
alias    AUP='sudo $APT upgrade'
# process mgmt
alias    KA='sudo /usr/bin/killall '
alias    KU='sudo /usr/bin/killall -u '

# disk level ops
# human-friendly and filtered list of device blkid's
alias Blk='lsblk -AMfe7'
# combine lines with the same device but different mountpoints (e.g. btrfs) into a single line:
alias Df="Dfs | awk '/Mounted on/ { print; next; } { if (\$1 in a) { a[\$1]=sprintf(\"%s, %s\", a[\$1], \$7); } else { a[\$1]=\$0; } } END { for(i in a) print a[i]; }' | Sort"
alias Dedup="/usr/bin/rmlint --types=duplicates --size ${MINSIZE:-50M} --no-hardlinked --no-followlinks --no-crossdev --xattr --algorithm=sha256 --progress --config=progressbar:fancy --with-color --output=summary:dedup.txt --output=sh:dedup.sh --config=sh:handler=${HANDLER:-hardlink,symlink} "
# human-friendly output and strip out generally uninteresting entries:
alias Dfs="df -hT | egrep -v '/docker|/snap|tmpfs|udev|efi'"
# show a nice map of all the current mountpoints
alias Mnts='findmnt --real | grep -v snap'
alias FakeSdScan='sudo f3probe '
alias ddd="dd status=progress"
alias SdSpeedTest='sudo hdparm --direct -t '
alias Space='baobab'
alias SpaceR='sudo baobab'
# info about the mountpoint of the specified dir (or current) dir.
function mnt() { q="${1:-.}"; findmnt --target ${q}; }
# give just the mountpoint dir of the specified (or current) dir.
function Mnt() { q="${1:-.}"; findmnt -n -o SOURCE --target ${q}; }

# networky stuff
# watch tcp flows (improved tcpdump)..  Follow with filters, e.g.:  -i docker1 port 8080
alias TCP='tcpflow -acg -X /dev/null'
# condensed list of IPs
function Ips() {
  cols="1,2"; filter='^(lo|veth)'
  while [[ $# -gt 0 ]]; do case "${1//-/}" in
      6) cols="${cols},3" ;;
      a*) filter='qqq' ;;
      e*|m*) cols="${cols},4" ;;
      h*) echo 'Ips [-6] [-all] [-macs]'; return 1 ;;
    esac; shift
  done
  /usr/sbin/ifconfig | awk '/^[a-z]/{sub(":",""); d=$1} /inet6/{i6=$2} /inet /{i4=$2} /ether/{e=$2} /^$/{print d,i4,i6,e; d=i4=i6=e=""}' | \
      egrep -v "$filter" | cut -d" " -f $cols | sort | column -t
}
function Ip() { Ips | grep "$1" | awk '{print $2}'; }

# process inspectors
alias mine="ps aux --forest  | grep '$USER '"
alias pag='ps auxwww --forest | grep '
alias pam='ps aux --forest | less'
alias pidc='ps h -o user --sort user --ppid 2 --deselect  | uniq -c | sort -rn'
alias pidC='pidc | egrep -v -f ~/bin/pidc.expect'

# x-win helpers
alias Clk="xclock -d -twelve -brief &"
alias LOCK="xscreensaver-command -lock"
alias XF='/usr/bin/xhost +si:localuser:nobody'
alias XR='/usr/bin/xhost +si:localuser:root'
alias clock='xclock -digital -twelve -brief -fg white -bg black -face "arial black-20:bold" &'
alias x="/home/ken/bin/x-start"
function copy() {
    if [[ "$1" == "+" ]]; then printer='echo -n "copied to clipboard: " >&2; tee -a /dev/stderr'; shift; else printer='cat'; fi
    if [[ "$1" == "" ]]; then src="cat -"; else src="echo $@"; fi
    if [[ ! -x "/usr/bin/xclip" ]]; then bash -c "$src"; return; fi
    bash -c "$src | { $printer; } | /usr/bin/xclip -selection clipboard -rmlastnl -in"
}
function Copy() { if [[ "$1" == "+" ]]; then clear; shift; fi; copy + "$@"; }

# other general command shortcuts
function Curl() { curl -sS $(echo "$@" | perl -p -e 's/([^A-Za-z0-9\:\/])/sprintf("%%%02X", ord($1))/seg' | sed -e 's/%0A//'); }
alias Sort="( sed -u 1q; sort )"
alias broken_links='find -L . -type l'
alias c2n='tr "," "\n"'
alias rlcp='cp --reflink=always '
alias s2n='tr " " "\n"'
alias Z="xz -T0 -v "
function Gpg() { sed -e "s/\r//g" "$@" | gpg -d; }

# parallel execs
alias RP='run_para --align --cmd'
alias listp='run_para --dry_run --cmd'   # $1 is command to run (needs to be quoted)
function listP() { while IFS= read -r line; do echo "${@//@/${line}}"; done; }  # perform "@" expansion from stdin to stdout (not auto-run)

# ---- fancy directory selectors

# switch through directories via prefix matching.  for example, if you have
# directory ./dev/this/and/that   then  C d t a t   would switch to that lower level dir.
# If multiple dirs match the provided pattern, all matches are listed, and you can
# pick which you want.  Use "~" as the first arg to start at home-dir (otherwise is
# relative to current directory).
#
function C() {
    srch=''
    if [[ $# == 1 ]]; then srch="${1//?/&*/}"
    else for i in "$@"; do srch="${srch}${i}*/"; done; fi
    readarray -t out < <(ls -1d $srch 2>/dev/null)
    if [[ ${#out[@]} == 0 ]]; then readarray -t out < <(ls -1d ~/$srch 2>/dev/null); fi
    if [[ ${#out[@]} == 0 ]]; then readarray -t out < <(ls -1d  /$srch 2>/dev/null); fi
    case ${#out[@]} in
	0) echo "not found  ($srch)" ;;
	1) cd "${out[0]}" ;;
	*) COLUMNS=20; select i in ${out[@]}; do cd "$i"; break; done ;;
    esac
}

# interactively select dir to switch to via fuzzy matching
# if $1 is a directory, use that as a starting point (/,~ ok)
# remaining params are an initial search expression (regex ok),
# unless $1 looks like a flag, in which case they're just passed to fzf.
#
function Cd() {
    if [[ -d "$1" ]]; then cd "$1"; shift; fi
    if [[ "$1" != "" && "$1" != "-"* ]]; then q='-q'; else q=''; fi
    cd $(find . -type d 2>/dev/null | fzf --select-1 $q "$@")
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
