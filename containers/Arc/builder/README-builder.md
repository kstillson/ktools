
- podman based container builder

_well blow me down-- containers building containers..._

This is loosely inspired by Google's production "Secure Build Rabbit."

Basically the idea is that you've got a separate process that downloads the
latest committed code and build tools, and perform a completely hands-off
build process.

Google does this as a sort of hermetic build clean-room... The builder will
only build committed/approved code using committed/approved tools, and it
digitally signs the output, thus locking out subsequent changes and
effectively marking it as approved for production.

I originally wrote this because I was starting to use podman features in my
container build processes (e.g. alternate user-ns during builds), and the
version of Ubuntu my real host was running didn't support podman.  So the idea
was to install podman within Alpine and do the builds from there.

It turns out that running podman inside of Docker (or podman inside podman) is
tricky.  First, podman needs a bunch of host level system calls, which
basically come down to needing to launch the builder container in --privileged
mode (see settings.yaml).  It's possible that some complex combination of
other individual privileges could be made to work, but the level of access
within the container would end up equivalent to --privileged, and so
--privileged is simpler and less fragile.

--privileged mode requires --userns=host, and although I played with it for a
while, I could not get rootless podman working inside the builder container.
This means that the builds are run by unmapped system uid 0 and in a
privileged container!  i.e. There is not even a pretence of security
separation between the build environment and root on the real host.

This is most unfortunate.  I don't anticipate using this contianer much; once
I upgrade my base system to one that supports podman, I'll just use rootless
podman on the host to build things.  But I kinda like the hands-off build
concept, so I'll keep this around for potential emergency use, and as a
starting point for something that eventually can run with more acceptable
security settings.

This container pushes its images to a registry running in a separate container
(see ../registry).  See files/etc/env for the settings, files/etc/init for the
internal setup, and files/etc/builder for the building logic.

To build all available containers in parallel mode:
  d-run --extra-init a

change "a" to "A" to build in sequential mode.  Pass no arg to init to enter
interactive mode, where you can then run things like: /etc/builder {container}

