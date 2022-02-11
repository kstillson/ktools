# Docker

## Motivation

With a little added infrastructure, Docker is an incredible tool.
I convert almost every service into a Docker container.  Why?

  1. Security
  
     + uid-mapping: the entire concept of system uid root ceases to exist
       in the containers.  See [uid mapping](Readme-uid-mapping.md).
     
     + attack surface area reduction: trimming the available tools inside
       the container limits the footholds an attacker can use.
     
     + copy on write: besides the obvious fact that restarting a container
       puts it back to a last-known-good state, the COW change layer is
       neatly organized by Docker into the real file-system.  This means
       it's trivial to monitor for changes to files within a container.
       Filter out any expected changes, and you're left with a clear and
       simple set of the unexpected changes.  This is fantastic both for
       discovering and understanding unexpected changes.  See
       [Readme-uid-mapping.md](Readme-uid-mapping.md) for details.
     
  2. Installation and configuration as code

     + most servers take a fair amount of tweaking to get install and
       config just right.  Far too often these changes get lost in
       countless adjustments to obscure files.  With Docker, when correctly
       used, all those adjustments get captured, either in the Dockerfile
       or things it pulls in, which means they can be tracked in git,
       commented, and tested- just like normal code.
  
  3. Testability

     + Docker makes it really easy to build, launch, and test changes in a
       separate container that doesn't interfere with the production
       instance.  This makes things like automated updates much safer-- if
       you're confident about your tests, you can have scripts
       automatically update, build, test, and deploy many containers and
       only need to get involved should a test fail.

---

## Docker source tricks and techniques

### Image Source Structure

The tools included here make assumptions about the file structure of the
source files for docker images & containers.

All of the source-files used to construct an image (e.g. the `Dockerfile`
and the other files specified below) should be gathered togehter into a
directory.  The name of this directory is used as the name of the built
images and the launched container.

There should also be a single directory, generally referred to as the
D_SRC_DIR, which contains all of these container source directories (or at
least symbolic links to all the source dirs).  There are various commands
that execute on all managed containers (even ones not currently running),
so D_SRC_DIR is needed to enumate the list of all possible containers.

Here are the contents expected for each container source directory:

  - autostart: To include this container in the list of containers that
    should be started automatically upon boot, place an empty file named
    "autostart" in the source dir.

    Note that actually all this does is cause the container name to be
    included in the "list-autostart" command of the `d.sh` script.  To
    actually get containers to auto-start, you'll need something to run the
    command `d start-all` at the appropriate time in boot.

  - Build: This just adds a little bash boilerplate around the command
    `docker build`.  Specifically, it generally permits the build to use a
    less restrictive network, and makes sure the appropriate labels are
    applied to the built image.

  - Dockerfile: This is a standard Dockerfile.

  - .dockerignore: This isn't really required, but its purpose is to make
    sure that infrastructure files, like the ones listed here, don't
    accidentally make their way into the images if you end up using remote
    image uploading.

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
    container.
    - TODO: more doc

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
    `./Build`
    `./Test -r`   ("-r" to run a separate test instance of the container)

    If all tests pass, the script should output "pass" and exit status 0.
    If that happens, you're good to run:  `./Build --setlive` to tag the
    latest image build as "live" (i.e. in production).

    If a test fails, it should output a human-readable explanation of what
    went wrong, and exit with non-0 status.

    [d_lib.py][] provides a whole bunch of useful helper tools to make
    testing easier.  See the provided `Test` files for examples.


### Testing


### Baseline Image


### Security Additions


### d-map


---

## The Tools

A set of tools for docker container updates, monitoring and control.

### "d-run"

docker takes copious instructions about how to launch a container from the
command-line.  This is painful if constructing command-lines by hand, so
don't do that.

"settings.yaml" takes the data needed to construct command-line args up a
level of abstraction.  "d-run" transforms those settings, plus a bit of
data on context, into specific command-line args to launch a container.

For example, settings.yaml lists directories to bind-mount, but can use
different directories or add various additional features depending on
whether you're launching the real production image, or a test image.

See the code for a reference of settings.yaml values and the list of all
the supported d-run command flags.

Some common examples:

`d-run`
start up the production version of the container whose settings.yaml file
is in the current directory, using all defaults.

`d-run -D`
start up the latest build of the image (tagged "latest") in development
mode.  This runs in the foreground, disables logging, uses the alternate
("testing") bind mounts, the development network, etc.

`d-run -D -S`
same as above, but don't launch the standard entry point for the container,
instead drop to an interactive command-line shell inside the container once
its started.


### "d"

"d" is a shell script designed to provide a very terse way of running
docker commands on both single containers and bunches of them.  Some examples:

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

TODO: add self-help logic like q's, and document here.

### "d-cowscan"

As mentioned in the Motivation section above, one of the neat things about
the Docker copy-on-write filesystem is that it's easy to identify
unexpected changes in files inside containers.  d-cowscan automates this.
It will scan all "up" containers, subtract out the specified list of files
that are expected to change, and output any remaining unexpected changes.

If this program outputs anything other than "all ok", you can take it as a
security alert that unexpected files are present.

Optionally, the script can also remove changed files while leaving the
container runnning, although generally restarting the container would be a
safer way to re-establish a known-good state.


### "d_lib.py"

d_lib is a Python library that provides logic to shell-based docker tools
that would be difficult to provide in shell.  As such, it provides some
logic used by the tools above, and also a set of abstractions used by
testing modules; see the [Testing][] section for details.


