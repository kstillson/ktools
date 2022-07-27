
# Docker containers

For the reasons outlined under ../general-wisdom, it's my belief that just
about everything should be wrapped in its own micro-service container, and
I've been pretty happy with Docker, so that's what I tend to use.

Most of these directories contain nothing more than the minimal configuration
to build and image and launch its container.  You can think of it as painting
a thin layer of containment on-top of the business logic that's contained
elsewhere.  However, there are a few of them where the critical service
configuration is stored here in the docker-containers tree.

For example, with filewatchdock/, this is a service created by and for this
system, so the source code and configuration are both in
../services/filewatchdock.  In that way, it's possible to run filewatchdock
stand-alone (i.e. outside a container), with everything needed in the
../services/filewatchdock directory.  The container-oriented subdirectory
contains nothing more than some logic to copy over the needed files from
../services, and set up a reasonably-locked-down container chroot for it to
run in.

Conversely, for dnsdock/, this container uses dnsmasq for its server.  That's
an externally obtained binary, so there is no ../services directory.  The
configuration needs to go somewhere, so it goes into
dnsmasq/files/etc/dnsmasq.  Specifically, what's you'll find in
dnsmasq/files/etc/dnsmasq is some template / example files.  Your real
configuration should go into dnsmasq/files/etc/dnsmasq/private.d (a directory
which git ignores, so you don't accidentally try to submit your private
configuration to the repo, and so you don't get to see my private config).
The image building process will override the final configuration with the
contents of the private.d/ directory.


## Current status

** THINGS IN THIS PART OF THE TREE ARE INCOMPLETE **

Specifically, almost all of these containers require bind-mounted directories
to store persisted data and logs.  You'll find lots of references to
"/rw/dv/{container-name}" (that's my main server's writable mount-point [as I
keep my root directory read-only most of the time], and then the "docker
volumes (dv)" subdir).

Most of these containers have some expectations about the subdirectories,
files, ownership, permissions, etc, that they will find in their container's
dv/{container-name} subtree.  Eventually, I'll get Makefile :prep targets
working to populate all those expectations with a working starting point.  But
this is slightly complicated, especially if you've got uid-namespace-mapping
turned on (which you should), then if you're mapping is different from mine,
figuring out the correct ownership uid's for mapped files is a little tricky.

Anyway, until that's all ready-to-go, you'll have to infer the expected
docker-volume contents, and set it up yourself.  Most of the information you
need is in the settings.yaml files, and perhaps a few foreground container
runs (so any error messages about inaccessible files are easy to see) should
get you there.  Or you can just use these Docker configurations as inspiration
for setting up your own.


## Image details: Alpine, kcore-baseline

All my containers are based off Alpine Linux.  Alpine is a brilliant minimal
implementation that provides a mostly complete chroot that takes only a few MB
of space.  It also has a simple packaging engine ("apk") which has equally
simple and elegant ports of the majority of standard services.  There are a
few cases where I need a more recent version of something than Alpine has
pre-packaged (e.g. rclone under rclonedock), and in those cases, the Makefile
downloads a suitable pre-built binary.  But generally apk has what's needed
and installs the packages in the Dockerfile.

Although I've come to trust Alpine, I don't like the idea of my underlying
platform changing unexpectedly.  So rather than having my containers be built
directly on Alpine, I introduce my own "kcore-baseline" image, and build
everything off that.  My baseline depends directly on Alpine, although not on
the auto-generated "latest" tag, instead I pull from a specifically listed
version.  This means I have to remember to check every month or so whether
Alpine's current version has advanced, and if so, evaluate whether I want to
update my baseline's FROM line.  Obviously there's a risk that if a serious
security vulnerability is found in Alpine, there might be a delay before I
notice and update kcore-baseline.  But I only rebuild containers sporadically
anyway, so I've chosen stability over bleeding-edge-security in this case.

As I have my own baseline, I also take the opportunity to tweak it's contents
a little, adding some hardening logic and some common tools that I want
available in every image (e.g. ../../pylib/tools/kmc.py).  See the next
sections for details.


## Image details: files/...

Each command run in a Dockerfile actually creates a new temporary image.  They
aren't hard to clean-up, but if you forget, it ends up wasting space, and
unnecessarily complicating the list of available images.  So I try to minimize
the number of separate commands I have in my Dockerfile's:

1) rather than copying files into place one-by-one, I assemble everything I
want to copy into the image into the files/ subdirectory and copy it all in a
single COPY command

2) rather than using individual Dockerfile RUN commands to finalize the image,
I have a shared files/prep that all images inherit from kcore-baseline, and
create image-specific files/prep-local, which contains all the finalization
commands specific to the details of that container.  Dockerfile's RUN /prep,
which in-turn runs /prep-local.

Worth understanding about #1: the files/... subtree ends up containing a
mixture of fixed files that are specific to the container being built, and
dynamic files that copied in from elsewhere; either from other subdirectories
that are part of this system, or from external sources (i.e. downloading via
curl).  These files are all mixed together into files/..., so they can be
copied into the container in a single go.  The .gitignore files are set to
ignore the dynamically copied-in files, and running "make clean" will delete
the dynamic files, leaving behind only the fixed ones.  So it's best to think
of files/... as a staging area for image contents that comes partially
pre-populated.


## Image details: hardening

./kcore-baseline/files/prep is mostly a bunch of commands designed to harden
the default Alpine image.  Specifically, it removes a whole lot of stuff-
accounts, groups, directories, binaries, etc.  The goal is to minimize the
"attack surface area" that a hacker would find, should they gain the ability
to execute arbitrary commands inside the container.  Even the "root" account
is removed from /etc/passwd if it's not needed (because all processes are
running as non-root accounts).  It's harder to attack Linux if the whole
concept of root doesn't even exit (truthfully the concept of uid 0 still
exists, unless you're using uid-namespace-mapping, see
[../docker-infrastructure/Readme-uid-mapping.md](uid-mapping) for details),
but regardless, it's harder to hack a system where username "root" can't even
reference the concept of uid 0).

/prep starts out with a section of environment variable definitions which
control what is going to be removed / cleaned-up.  Then /prep sources
/prep-local (if it exists).  Then /prep runs the clean-up code.  The idea is
that /prep-local can override the default environment variables, thus
controlling what particular things will / will-not be hardened for a
particular container.  Of course, /prep-local can also make whatever other
changes it needs to; fixing permissions or whatever.  It just needs to make
sure it tweaks the environment variables to disable any hardening that would
effectively un-do what it has just done.

btw- the list of things I harden is a collection of ideas from a variety of
web sources, plus a bunch of ideas from my own experience.  It's certainly not
bullet-proof, and truthfully much of the removal of the binaries is kinda
pointless, as Alpine is actually a bunch of hard-links to a single busybox
binary that has the capabilities of all the binaries built-in.  i.e. a hacker
could just replace the "deleted" binary with a link back to the busybox.  I
remove the "ln" binary to make this a bit harder, but a clever hacker won't
have too much trouble finding ways around this.  But...  You never know what
constraints a hacker will find themselves working within, so every bit of
additional difficult you add has the possibility of stymying them.  And if
you're just removing functionality that Alpine provides by default but you
really don't need in the container, then there's very little reason not to.
Anyway, if you have additional suggestions of things that could be hardened,
I'd certainly love to hear about them!  <ktools@point0.net>


## Walking through an example:  filewatchdock

As with all my things, start with "make" (which implicitly runs "make all").

All depends on "copy" and "docker-all".  :copy will basically copy over the
files fileswatch.py and filewatch_config.py from ../services/filewatch, strip
off the .py extensions, and put the files into files/home/watch

:docker-all (which comes from ../etc/Makefile-docker) depends on
./build-stamp, which depends on ../kcore-baseline/baseline-stamp.  This is
because filewatchdock/Dockerfile depends on the image
ktools/kcore-baseline:live, which means we not only have to have the
kcore-baseline built, but also tested and promoted from #latest to #live.  So
Makefile-docker has a target to switch to ./kcore-baseline and "make all".

The kcore-baseline:all target is special, in that it will build, :test, and
:install (i.e. promote #latest to #live) all in one go.  Most of the ":all"
targets only do the image building part.  Once the kcore-baseline#live image
is ready, we get our ../kcore-baseline/baseline-stamp.  Then
../etc/Makefile-docker:build-stamp proceeds with a "sudo /root/bin/d-build"
(see ../docker-infrastructure/d-build.sh), which in this case doesn't do much
more than run "docker build .", with some parameters telling it to tag the
output image as "latest".

Okay, we have an image.  Now we want to test it, which is "make test".  :test
defers to ../etc/Makefile-docker:docker-test, which wants ./test-stamp, which
basically just runs "sudo ./Test -r".  What that's going to do is use
kcore.docker_lib to launch an instance of the container with settings for
testing.  That means it'll run #latest rather than #live, runs with an
alternate container name, IP address, and volume mounts -- so as not to
interfere with any running production service.  Then ./Test peppers the
launched instance with a number of positive and negative tests to make sure
the primary service is up and at least basically functional.  Assuming all
that goes okay, ./Test exits with status 0, and we get our ./test-stamp.

The final make step is "make install", which defers to
../etc/Makefile-docker:docker-install, which wants ./install-stamp.  To get
that, we check that we've got a ./build-stamp and a ./test-stamp, and if so,
we call "d-build -s", which basically takes the image tagged with #latest and
tags it with #live.  This means it's "production ready" and we get our
./install-stamp.

To actually launch the container, use "sudo /root/d 1 filewatch" (or "sudo
/root/d 1 f", if "f" is sufficient to uniquely identify the container).  Use
"d 01" rather than "d 1" if the container is already up and needs to be
stopped before it can be re-launched.

btw- a shortcut to the entire above process (all the make sub-steps and the
final "start and/or re-start the container") can be run with either "d-build
-a" when in the docker-containers/filewatchdock directory, or with the even
shorter "d u f" (docker upgrade f*) regardless of your current working dir.
See ../docker-infrastructure for the source to all those tools.

