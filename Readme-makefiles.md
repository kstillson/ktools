
# Makefile's

The project uses GNU Linux Makefile's.  A bit old fashioned, I know.  And the
code is generally in Python or bash, i.e. there is no compilation phase, which
might make "Make" seem like an odd choice.  However, I like the way Makefile's
document dependencies and how pieces are combined, tested, and deployed.

Even when an overall process becomes complicated, well-written Makefile's
remain small and reasonably easy to understand.  And they can be quite clever
at figuring out the minimal amount of work needed to process a small number of
changed files in a large system.


- - -

## Control Variables

There are several environment variables you can set to influence what & how
things are built.


### Top level Makefile variables

- **BUILD_DOCKER_CONTAINERS=1**

Building Docker containers is a bit special- it requires root privileges, a
bunch of (mostly internal) dependencies must be *installed* before images can
be built or tested, and the constructed containers likely won't be useful
(might not even pass their internal tests) until you do some customization to
fit them to your system.  So to avoid confusion, the top level Makefile will
not descend into the containers subdirectory unless this variable is
set to "1".

- **NO_TRACKING**

Set this variable to any non-blank value to disable the system's occasional
"calling home" to let the author know you're using the system.

- **SUBDIRS**=...

Contains a space-separated list of the sub-directories the top level Makefile
will descend into when figuring out what else to do.  You can set this to a
subset of its default value if there's part of the system you want to skip.


### pylib Makefile variables

- **control "simple" == "1"**

By default, pylib/Makefile will build a Python "wheel" (.whl) file (the :all
target), and then install that using PIP (for the :install target).  Wheel
files are kinda cool, they track metadata like dependencies and allow for
platform-dependent builds.  But this system doesn't need any of that, so
really going through a wheel just slows things down unnecessarily.  Set
simple=1 to skip the whole wheel thing, and "make install" things just
by copying them into place.


- - -

## Targets

The following targets are accepted both at the top-level and in the individual subdirs:

- "**make prep**" does some one-time preparatory stuff, like making sure
  various dependencies are installed, and getting information from you for
  populating the self-signed certificates used by the authentication system.
  "make all" depends on "make prep," so you don't really need to know about
  it, but still it's a useful abstraction, so I thought I'd point it out.

- "**make all**" If using SIMPLE mode and not building Docker containers,
  ":all" doesn't do very much exciting.  Mostly it depends on :prep, and
  copies a few files around to make sure they're where they need to be.

   If not using SIMPLE mode, then :all actually builds the Python "wheel"
   file for pylib/, and if BUILD_DOCKER_CONTAINERS=1, then Docker container
   images are actually built.

- "**make test**" runs tests.  For pylib/ these are very simple in-place
  unit tests.  For services/ and containers/, this involves actually
  starting up real servers (generally on random high ports) and peppering
  them with requests to confirm operation.

- "**make install**"- for libraries and services, copies files into their
  appropriate bin/ or ...lib/ directories.  For docker containers, tags the
  ":latest" image as ":live", which will cause it to be used the next time
  the container is restarted.

- "**make update**" basically a handy shorthand for "all" then "test" then
  "install"

- "**make comp**" this target compares the source files to files copied into
  place by :install.  This is handy for checking to see if any changes made
  in the source directory have been installed.

- "**make clean**" as is standard for Makefiles, will remove all the things
  done in :all, and try to put things back to a default state.  Note that
  this does **not** undo the things done in :prep.

- "**make uninstall**" as in standard Makefiles, undoes a :install


- - -

## Caveats

- **-j not advised**: several Makefiles may attempt to interact with you-
     asking if it's okay to do something, or invoking an editor to set
     defaults.  This will become very confusing if you've activated Make's
     parallel build mode with the "-j" flag.

- **unit tests, not installation tests**: traditionally with Make, you build,
  then install, then test the installation.  However, in this system, "make
  test" runs pre-installation unit tests, i.e. tests that run in the
  source-code directories.

  - So, the standard sequence is:  make && make test && make install
  - If you want to make sure the unit tests pass before even trying the
    primary build, the sequence would be:
    make prep && make test && make && make install

- - -

## Build stamps

"make" does comparisons between file modification time-stamps to determine
which operations need to re-done.  if x depends on y, and y depends on z, and
the user says "make x", then make compares all the timestamps, and if x is
later than both y and z, is declares that there is "nothing to do" to make x.

Occasionally a recipe either does not result in updated files (e.g. testing),
or there is a complex network of dependencies that could use simplifying.  In
either case, stamp files can be a good solution.

Stamp files exist only for their modification date-time; they're usually
empty.  The idea is that you have a make target depend on stamp file, and then
have the recipe update that stamp (usually using the Linux "touch"
command) as the last step in its process.

The ../.gitignore file is set to not upload *-stamp files to git, to make
sure that build progress on one machine doesn't confuse another.  This means
this stamp files should start-off missing, meaning that all rules which
depend on a stamp file should run.  As each recipe is run, various stamp files
are updated, which means don't need to be run again the next time you run
make.

But what if you do *want* something to be run again for the next make?  Well,
you can either manually remove stamp files (which is generally safe- at worst
it will only cause some unnecessary work during the next make), or use the
"make clean" target to reset things for you.  That's ideal if you want to
rebuild parts of the tree, but aren't sure which stamp files are for what.
Doing a "make clean" in a particular subdirectory will remove only the stamp
files relevant to that part of the tree.

It's usual for the Makefile author to write dependency rules specifying what
other files (source, configuration, etc) the stamp file depends on.  This
attempts to ensure that the presence of a stamp file won't cause build steps to
be skipped because a stamp file exists when real dependencies have changed.

So, if you're going to enumerate stamp file dependencies, what's the point in
the stamp file?  Why not just have the target that would depend on the stamp
file directly depend on the stamp file's dependencies?  Well, truthfully it's
more aesthetic than functional.  It allows complex make rules to be broken
into multiple simpler pieces, and provides a convenient point of reference for
user's to query the last time a build operation was done, or to easily select
parts of the build tree to force a redo on (by removing stamp files) or to
inhibit rebuilding (by manually updating a stamp file).


- - -

## test.log

Note: stamp files are *usually* empty.  But throughout this system, tests
routinely save their output into files (named test.log), and these are
effectively used as stamp files to indicate when testing was last run.

Makefile dependencies on source files are provided, so this scheme is smart
enough to realize you need to re-test if source changes.  However, if tests
fail for some *environmental* reason, you fix that and then try to re-run the
tests, make will say "make: Nothing to be done for 'test'.  This is because
the test.log stamp file does not depend on the environment, and thus doesn't
"see" the fix you made.  Either "make clean" or manually remove test.log and
then "make test" to re-run the tests.


- - -

# Some hints on reading Makefiles

There's a great general Makefile reference at [makefiletutorial.com](https://makefiletutorial.com/)

But here's some rules-of-thumb to help make your way though the Makefile's of
this system.  The general form of a Makefile entry looks like this:

```
target: dep1 dep2
   recipe
```

"dep" stands for "dependency".  In the simplest case, "target", "dep1" and
"dep2" are filenames, and the recipe is a shell command for creating the file
"target" using "dep1" and "dep2" as inputs.

However, "target", "dep1" and "dep2" can be abstractions rather than
filenames.  Make doesn't know that they're abstractions, it just sees them as
files that are missing, which means that their recipes need to be run.  An
example:


```
greetings: file1 step1
    cat file1 file2

file1:
    echo -n "hello " > file1

step1: file2

file2:
    echo "world" > $@
```

If you run "make greetings", make checks for a file named "greetings".  There
isn't one, so it's going to need to run the recipe, but first, it must satisfy
the dependencies "file1" and "step1".  So make implicitly runs "make file1".
There is no file1, and the rule has no further dependencies, so it just runs
the echo command and creates a file1.  Good- we've fulfilled the first
dependency.  Make moves on to "make step1".  Again there is no file "step1",
but we do have a rule for it.  There is no recipe for step1, but we're told it
depends on file2.  So make will run "make file2" and if that works out, we'll
just sort-of assume that step1 is successfully completed, and return to the
original logic for "greetings".  The file2 recipe uses a cute shortcut: "$@"
means for "the name of my current target", so the recipe for file2 just writes
the word "world" into the "file2".  All of our dependencies are fulfilled, so
the "greetings" recipe prints "hello world".

If we ran "make greetings" again, we'd see that it says "hello world" again
(i.e. the recipe for greetings is run), but file1 and file2 are not
re-created.  This is because the targets "greetings" and "step1" need to be
run again: no files with those names exist, but their dependencies (file1 and
file2) do already exist, and because they have no further dependencies, their
existing contents must be good enough.  Step1 is "run," but because it has no
recipe, there's actually nothing to do.  So finally "greetings" is run, which
outputs the greeting.

If you wanted "make greetings" to only run once, you would create build-stamp
files for the "greetings" and "step1" targets.  It would then be important to
also create a "clean" target that removes those stamp files (and ideally file1
and file2 also, as those are artifacts of the make process).

> Adding the "--debug=b" flag to a make command gives a pretty good summary of
> what it's doing and not-doing, and why.

## Other useful tidbits

- Each line in a recipe is run in a new shell, so normally multi-line shell
  commands, like if-then-else, have to be mushed into a single line to work.
  Similarly, if you set a shell environment variable in a recipe, you've got
  to use it on that same line, because it won't exist in the next line of the
  recipe.

- Make has it's own internal variables, and it gives preference to those over
  shell variables.  So if you see $(X) in a recipe, that does not mean "run
  the command X and substitute its output here" as it would in traditional
  shell-code, instead it just means "insert the contents of Make variable X
  here."  To use a shell environment variable rather than a Make variable, one
  uses $$X.  To run a command and substitute its output into the recipe
  (i.e. what the "$(X)" syntax would normally do in shell), one uses "$(shell
  command-to-run)"

- The Make variable assignment operator "?=" means that it's assigning a
  value, but only if the variable does not already have a value either within
  Make or within the environment.  So if you see "X ?= Y" in a Makefile, it
  means the author is either expecting X to be set earlier in the file (or in
  a file that included this one), or that they are inviting you to override
  the default for X from the environment.

- If a line in a recipe is prefixed with "@", that just means Make should not
  echo it when it runs it.  This is useful for like commands that print things
  (to avoid double-printing), or commands within conditionals (where you don't
  want the user to be confused that the conditional command ran when it
  didn't, just because Make is echoing the command inside the conditional
  clause).
