
# Makefile's

The project uses GNU Linux Makefile's.  A bit old fashioned, I know.  And the
code is generally in Python or bash, i.e. there is no compilation phase, which might
make "Make" seem like an odd choice.  However, I like the way Makefile's
document dependencies and how pieces are combined, tested, and deployed.

Even when an overall process becomes complicated, well-written Makefile's
remain small and reasonably easy to understand.  And they can be quite clever at figuring out the minimal amount of work needed to process a small number of changed files in a large system.


- - -

## Control Variables

There are several environment variables you can set to influence what & how things are built.


### Top level Makefile variables


- **BUILD_DOCKER_CONTAINERS=1**
Building Docker containers is a bit special- it requires root privileges, a bunch of (mostly internal) dependencies must be *installed* before images can be built or tested, and the constructed containers likely won't be useful (might not even pass their internal tests) until you do some customization to fit them to your system.  So to avoid confusion, the top level Makefile will not descend into the docker-containers subdirectory unless this variable is set to "1".

- **NO_TRACKING**
Set this variable to any non-blank value to disable the system's occasional "calling home" to let
the author know you're using the system.

- **SUBDIRS**=...
Contains a space-separated list of the sub-directories the top level Makefile will descend into when figuring out what else to do.  You can set this to a subset of its default value if there's part of the system you want to skip.


### pylib Makefile variables

- **BUILD_SIMPLE=1**
By default, pylib/Makefile will build a Python "wheel" (.whl) file (the :all target), and then install that using PIP (for the :install target).  Wheel files are kinda cool, they track metadata like dependencies and allow for platform-dependent builds.  But this system doesn't need any of that, so really going through a wheel just slows things down unnecessarily.  Set BUILD_SIMPLE=1 to skip the whole wheel thing, and "make install" things just by copying them into place.


- - -

## Targets

The following targets are accepted both at the top-level and in the individual subdirs:

  * "**make prep**" does some one-time preparatory
    stuff, like making sure various dependencies are installed, and getting
    information from you for populating the self-signed certificates used by
    the authentication system.  "make all" depends on "make prep," so you don't really
    need to know about it, but still it's a useful abstraction, so I thought I'd point it out.

  * "**make all**" If using BUILD_SIMPLE and not building Docker containers, ":all" doesn't do very much exciting.  Mostly it depends on :prep, and copies a few files around to make sure they're where they need to be.  

     If not using BUILD_SIMPLE, then :all actually builds the Python "wheel" file for pylib/,
     and if BUILD_DOCKER_CONTAINERS=1, then Docker container images are actually built.
  
  * "**make test**" runs tests.  For pylib/ these are very simple in-place unit tests.  For services/ and docker-containers/, this involves actually starting up real servers (generally on random high ports) and peppering them with requests to confirm operation.
  
  * "**make install**"- for libraries and services, copies files into their
    appropriate bin/ or ...lib/ directories.  For docker containers, tags
    the ":latest" image as ":live", which will cause it to be used
    the next time the container is restarted.

  * "**make update**" basically a handy shorthand for "all" then "test" then "install"

  * "**make comp**" this target compares the source files to files copied into place by :install.  This is handy for checking to see if any changes made in the source directory have been installed.

  * "**make clean**" as is standard for Makefiles, will remove all the things done in :all, and try to put things back to a default state.  Note that this does **not** undo the things done in :prep.
 
  * "**make uninstall**" as in standard Makefiles, undoes a :install 


- - -

## Caveats

- **-j not advised**:  several Makefiles may attempt to interact with you- asking if it's okay to do something, or invoking an editor to set defaults.  This will become very confusing if you've activated Make's parallel build mode with the "-j" flag.
 
- **unit tests, not installation tests**: traditionally with Make, you build, then install, then test the installation.  However, in this system, "make test" runs pre-installation unit tests, i.e. tests that run in the source-code directories.
    - So, the standard sequence is:  make && make test && make install
    - If you want to make sure the unit tests pass before even trying the primary build, the sequence would be:  make prep && make test && make && make install


- - -

## Build stamps


"make" does comparisons between file modification time-stamps to determine
which operations need to re-done.  if x depends on y, and y depends on z, and
the user says "make x", then make compares all the timestamps, and if x is
later than both y and z, is declares that there is "nothing to do" to make x.

Occasionally a recipe either does not result in updated files (e.g. testing), or there is a complex network of dependencies that could use simplifying.  In either case, stamp files can be a good solution.

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
routinely save their output into files (named test.log), and these are effectively
used as stamp files to indicate when testing was last run.

Makefile dependencies on source files are provided, so this scheme is smart enough to
realize you need to re-test if source changes.  However, if tests fail for
some *environmental* reason, you fix that and then try to re-run the tests,
make will say "make: Nothing to be done for 'test'.  This is because the
test.log stamp file does not depend on the environment, and thus doesn't
"see" the fix you made.  Either "make clean" or manually remove test.log
and then "make test" to re-run the tests.


- - - 

# Some hints on reading Makefiles

There's a great general Makefile reference at [makefiletutorial.com](https://makefiletutorial.com/)

But here's some general rules-of-thumb to help make your way though the Makefile's of this system:

TODO(doc)
