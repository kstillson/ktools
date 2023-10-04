# dotfiles

A collection of dotfiles with features accumulated over the years;
shared here in hopes they are useful to others.

As noted by the :install target in the Makefile, many of these files contain
details that are specific to the original author, so they are presented here
in hopes that they will provide ideas and inspiration for your own Linux
customization, but are not really intended to be installed as-is.


## Contents

- .bashrc: sets a few system settings (prompt, path, umask, bash history,
  etc), but primarily sets a bunch of aliases and bash functions (where an
  alias wouldn't work, for example the need to process arguments).

- .emacs: sets a number of editing defaults, but primarily loads the "emacs
  extension system" (ees.el, which gets installed into ~/bin), which is a
  rather complicated set of additions and customizations accumulated over
  years of using Emacs as a primary editor.  Most of the EES functionality
  gets assigned to the ^C command prefix.

- .gitconfig: a bunch of command aliases and other minor customizations.
  Note that you'll probably want to change the [user] section, which currently
  defines the original author's values.   TODO: fix this.

- .gitignore: a few basic values that seem general useful for git to ignore.

- .profile: a number of exported variables to set various applicaion defaults,
  and logic for interactive+login shell starts that initialize the Linux
  "screen" command to one of several possible profiles (see below).

- .screenrc: Basically sets some defaults, and populates key bindings and
  registers with commonly used commands and text to insert.  A single bash
  window is opened to get started.

- .screenrc-k1: the "screen" profile selected by default (or timeout) via
  .profile.  Basically the same as .screenrc, but as well as bash in window 0,
  also opens a window 1 with emacs running.  Press F12 to jump to it.

- .screenrc-ke: the screen profile selected by the command letter "e", which
  loads the defaults from .screenrc, but switches to emacs as the initially
  selected window.

