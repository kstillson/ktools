
# NEWS

## ktools v1.0.0  2022-07-26

Packaging up the initial release.

Everything builds and all tests pass (including the docker containers),
at least on my server.

**Known Issues**

The Makefile for the containers/... does not currently know how to
construct the docker volume directories that the containers need for
bind-mounting.  This means that these containers can be built, but testing
will fail on any servers that don't have these directories all pre-populated
with all their permissions and ownerships carefully arranged (which is
complicated when uid namespace mapping is enabled in Docker).  For details,
see the "current status" section in
[README-containers.md](containers/README-containers.md)

For this reason, the top-level Makefile does not automatically descend into the
./containers subdirectory unless $BUILD_DOCKER_CONTAINERS=1.

