
# (note: this file is only run when shells are started with the login option.
#  that is not the default for gnome-terminal launches.  to make sure this
#  logic is included for gnome-terminal, edit the launch profile, under the
#  'command' tab, and check the box to use a login shell.)

[[ -r ~/.bashrc ]] && . ~/.bashrc
[[ -r ~/.profile.local ]] && . ~/.profile.local

if [[ -n "$PS1" && -x ~/bin/offer-screen && "$@" == "" ]]; then
    ~/bin/offer-screen && exit 0
fi
