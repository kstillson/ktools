# Docker Infrastructure

## Motivation

With a little added infrastructure, Docker is an incredible tool.
I convert almost every service into a Docker container.  Why?

- Security

  - uid-mapping: the entire concept of system uid 0 ceases to exist
    in the containers.  See [uid mapping](Readme-uid-mapping.md).

  - attack surface area reduction: trimming the available tools inside
    the container limits the footholds an attacker can use.

  - copy on write: besides the obvious fact that restarting a container
    puts it back to a last-known-good state, the COW change layer is
    neatly organized by Docker into the real file-system.  This means
    it's trivial to monitor for changes to files within a container.
    Filter out any expected changes, and you're left with a clear and
    simple set of the unexpected changes.  This is fantastic both for
    discovering and understanding unexpected changes.  See
    [Readme-uid-mapping.md](Readme-uid-mapping.md) for details.

- Installation and configuration as code

  - most servers take a fair amount of tweaking to get install and
    config just right.  Far too often these changes get lost in
    countless adjustments to obscure files.  With Docker, when correctly
    used, all those adjustments get captured, either in the Dockerfile
    or things it pulls in, which means they can be tracked in git,
    commented, and tested- just like normal code.

- Testability

  - Docker makes it really easy to build, launch, and test changes in a
    separate container that doesn't interfere with the production
    instance.  This makes things like automated updates much safer-- if
    you're confident about your tests, you can have scripts
    automatically update, build, test, and deploy many containers and
    only need to get involved should a test fail.

  - This system supports several types of tests:

    - Stand-alone readiness test;  ./Test -r

      This type of test launches a test-mode instance of the container,
      and runs tests against it that have minimal environmental assumptions.
      i.e., ideally this test should run anywhere that the image can be built.

    - Production readiness test;   ./Test-prod -r

      This type of test launches a test-mode instance of the container, and
      runs a series of tests which assume the environment matches that needed
      for real production operations.  i.e., bind mounted directories can have
      all sorts of expected already-available contents and permissions, with
      permissions already adjusted for accessibilty via mapped uid's, etc.

   - In-production test;           ./Test-prod

     This test does not launch the container to be tested, it runs the
     Test-prod script against an already-running real production container.

  - "make test" (and d.sh test ..., which runs "make test") will run a
    production readiness test (./Test-prod -r) if $KTOOLS_DRUN_TEST_PROD=1,
    and otherwise a stand-alone readiness test (./Test -r).


- - -

## Docker source tricks and techniques

### Image Source Structure

The tools included here make assumptions about the file structure of the
source files for docker images & containers.

All of the source-files used to construct an image (e.g. the `Dockerfile`
and the other files specified below) should be gathered together into a
directory.  The name of this directory is used as the name of the built
images and the launched container.

There should also be a single directory, generally referred to as the
D_SRC_DIR, which contains all of these container source directories (or at
least symbolic links to all the source dirs).  There are various commands
that execute on all managed containers (even ones not currently running),
so D_SRC_DIR is needed to enumerate the list of all possible containers.

Here are the contents expected for each container source directory:

- Dockerfile: This is a standard Dockerfile.

- files/: Dockerfile's generally copy various files from their source
  directories into their images.  Traditionally these files are left in
  an unorganized pile in the source dir, and logic in the Dockerfile is
  used to copy each file to its correct location in the image.  Not only
  is this messy, but each separate Dockerfile COPY command creates a new
  image layer, which can become very inefficient and is pointlessly
  complex.

  Hence, files/ is a subdirectory of all the static files to be copied
  into the image, arranged in their subdirectory structure just as they
  should be once in the image.  i.e. think of "files/" as the root
  directory of image, but containing only the individual files you need
  to override from whatever earlier parts of the Dockerfile put there.
  And it's copied in with a single recursive COPY command, so only one
  additional layer for all overridden files.

- settings.yaml: This file provides the instructions to the `d-run` tool
  on how to construct the docker command-line arguments to launch a
  container.  See [Readme-settings.yaml.md](Readme-settings.yaml.md).

- Test: This is an executable file (generally Python), which performs a
  series of functionality tests on a container.

  The general purpose of this is to confirm that some set of changes to
  an image's source haven't broken it.  This means you want to launch a
  separate test version of the container using the changed source, and
  verify that the basic operations of the container are working.

  There's lots of special testing support in settings.yaml.  For example,
  there might be a directory that in production is mounted read+write,
  but when testing, you instead want to make a separate copy (perhaps
  just of the empty directory, or perhaps of the directory and all its
  contents), and mount the copy instead.  This allows the test instance
  to manipulate files in the copy without disturbing the real data, and
  your test can then inspect the copy to see if the correct modifications
  were made.

  The normal command sequence to test changes in a source-dir is:
    `make
     make test
     make install`

  If a test fails, it should output a human-readable explanation of what
  went wrong, and exit with non-0 status.

- - -

## The Tools


### d-build.sh

This is a simple bash wrapper around the various steps of building, testing,
promoting (i.e. adding a #live tag) container images.  Switch into a directory
that follows the various naming conventions outlines in this doc, and "d-build
-a" will run the whole process on auto-pilot.


### d-cowscan.py

As mentioned in the Motivation section above, one of the neat things about
the Docker copy-on-write filesystem is that it's easy to identify
unexpected changes in files inside containers.  d-cowscan automates this.
It will scan all "up" containers, subtract out the specified list of files
that are expected to change, and output any remaining unexpected changes.

If this program outputs anything other than "all ok", you can take it as a
security alert that unexpected files are present.

Optionally, the script can also remove changed files while leaving the
container running, although generally restarting the container would be a
safer way to re-establish a known-good state.


### d-map.py

A bunch of the tools in this system need to map between the container ID's
(which is what you see in the "ps" command) and the container name's, which
are generally the base-name of the directory containing the Dockerfile that
build the image.

This trivial script outputs the mapping for the currently running containers.
It takes no params and is designed to be simple enough that it can safely be
run under sudo by any uid that needs a current mapping (e.g. see
../services/procmon).


### d-run.sh

docker takes copious instructions about how to launch a container from the
command-line.  This is painful if constructing command-lines by hand, so
don't do that.

"settings.yaml" takes the data needed to construct command-line args up a
level of abstraction.  "d-run" transforms those settings, plus a bit of
data on context, into specific command-line args to launch a container.

For example, settings.yaml lists directories to bind-mount, but can use
different directories or add various additional features depending on
whether you're launching the real production image, or a test image.

Some common examples:

- `d-run`
  start up the production version of the container whose settings.yaml file
  is in the current directory, using all defaults.

- `d-run -D`
  start up the latest build of the image (tagged "latest") in development
  mode.  This runs in the foreground, disables logging, uses the alternate
  ("testing") bind mounts, the development network, etc.

- `d-run -D -S`
  same as above, but don't launch the standard entry point for the container,
  instead drop to an interactive command-line shell inside the container once
  its started.

There are a lot of other things this script can do.  Check out the
command-line flags (i.e. `d-run -h`) for a list.  You can use the `--test`
flag to see what the script would do without actually doing it.


### d.sh.

"d" is a shell script designed to provide a very terse way of running docker
commands on both single containers and bunches of them.  It's kinda like
tools-for-root/q.sh, but with Docker specific commands.

Some examples:

`d 1 X`
If you have only 1 container whose directory starts with the letter "X",
this command will start the standard production container for it.  You can
specify as many letters as needed to uniquely select a container to run.

`d e X`
Enter an interactive shell in an already started container X

`d u X`
Upgrade (build and test) a new image for container X.  If the test passes,
mark the new image as "live" (i.e. in production) and restart the
container.

`d ua`
Same as above, but upgrade all containers.
