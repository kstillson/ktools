
# Control variables

A number of environment variables affect the way the ktools operates:


## Makefile controls

These affect the way the "make" command works.

- BUILD_SIMPLE: In the pylib/ directory, the default is to build and install
  by building a Python "wheel" .whl file.  This is reasonably portable, but
  requires pip3 and takes quite a bit longer.  Set BUILD_SIMPLE="1" to skip
  the wheel and install the files directly by copying into place.

- ROOT_RO: TODO(defer): {not fully implemented yet}
  If set to "1", then ktools Makefile's assume that your root filesystem is
  read-only, and that anything being installed there requires a temporary
  remounting of the root-fs in "rw" mode.

- KTOOLS_KEN: if set, triggers various actions that are specific to the
  original author's systems and configurations; you probably don't want this.


## Docker controls: building containers

These affect how containers are built by the container-infrastructure/d-build.sh
script (which is run automatically by make commands run explicitly inside the
./containers subdirectory).

- BUILD_DOCKER_CONTAINERS: if set to "1", then automatically include the
  ./containers subdirectory from the main directory's targets.

- DBUILD_PARAMS: d-build will pass anything set here through to the "docker
  build" command.  Not generally needed.

- DBUILD_PODMAN_SHARED_APK_CACHE: if set to "1" (the default) and DOCKER_EXEC
  is "podman", then d-build will automatically add a read-write volume for
  /var/cache/apk when using podman to build containers.  This allows for
  shared caching of APKs.  If set to "2", then d-build will take no action
  regarding the apk cache dir.  If neither Dockerfile nor files/prep take any
  particular action, this means APK cache will be populated in the built image
  (i.e. wasting space).  If set to any other value, or if podman isn't in use,
  the d-build will mount a tmpfs in /var/cache/apk, thus minimizing image
  size, but meaning each container needs to redownload all used apk's.

If set to any other value, or if not using podman, then
  d-build will mount a tmpfs in /var/cache/apk, thus making sure images are
  as small as possible (no cached apks)


- DBUILD_PUSH_OPTS: options when pushing a build to a remote repo
  (defaults to "--tls-verify=false")

- DBUILD_PUSH_TO: registry server to push remote repo builds to
  (defaults to "localhost:5000")

- DBUILD_REPO: path prefix for the local docker repository that d-build will
  build into.  default is 'ktools'

- D_SRC_DIR: Directory with container source directories in it.  e.g. if
  d-build is given a relative directory in-which to find a container to build
  (via the --cd flag), this is the directory the reference will be relative to.
  Should generally be set to the full path of the directory contianing this
  file, with "/containers" appended.

- D_SRC_DIR2: If set, is similar to D_SRC_DIR, but provides an alternate
  location that d.sh, d-build.sh, and similar tools will search for container
  sources to build, test, etc.  Intended to be used to point to private
  container collections that exist outside the ktools subtree.  Note that for
  such a secondary collection to work, it needs to contain symlinks (or
  copies, or something similar) in the D_SRC_DIR2 directory to ktools/etc and
  ktools/containers/kcore-baseline.
  

## Docker controls: testing containers

- KTOOLS_DRUN_TEST_PROD: when tests are requested (e.g "d.sh test" or "make
  test"), if KTOOLS_DRUN_TEST_PROD=1, then ./Test-prod is used, otherwise
  ./Test.  Basically, setting this to "1" indicates that the full production
  environment is available on the current host, e.g. all bind-mounted
  directories are present and have their uid's (potentially mapped) and
  permissions set correctly for the test to use.

- KTOOLS_DRUN_TEST_NETWORK: docker Network to use when d-run is launching a
  container in --dev or --dev_test mode, if not specified via flag.


## Docker controls: launching containers

These affect how containers are launched by container-infrastructure/d-run.sh

- DOCKER_EXEC: Defaults to '/usr/bin/docker', but can be changed to alternate
  commands with the same API (e.g. "podman") or a wrapper script.

- DOCKER_VOL_BASE: Defaults to /rw/dv, and gives the default location for
  mounted volume source directories, i.e. $DOCKER_VOL_BASE/{container_name}/...

- KTOOLS_DRUN_LOG: default Docker log type to use for
  container-infrastructure/d-run.sh if not specified on the command-line or in
  the container's settings file.

- KTOOLS_DRUN_NETWORK: default Docker network to use when launching containers
  from d-run, if not specified via flag or settings file.

- KTOOLS_DRUN_REPO: default Docker repo/registry to use.  Default is "ktools"
  which is implicitly "localhost/ktools", i.e. assuming a local repo.  If a
  remote repo is specified, the image will be pulled from there, i.e.  the
  only file in a container dir that is used is settings.yaml, which is used to
  construct the params for the container launch.  Note also that if using
  Docker and the registry is "insecure" (i.e. http only), you need to add it
  to /etc/docker/daemon.json in the "insure-registries" list.

- KTOOLS_DRUN_REPO2: fallback Docker repository to use for d-run, if not
  specified via flag or settings file.  Note that the primary repo to try
  "ktools", but d-run will fall back to this if that doesn't work.  So if
  you've got a personal repo, set it's value here.



## Home-control

- HC_DATA_DIR: pylib/home-control/hc.py needs a bunch of data files to operate
  (to provide device and scene data, and for plugins to load).  If set, this
  variable provides a default location to search for those files.


## tools-for-root/q.sh

- KMHOST: "hostname:port" of the keymaster to work with
- KTOOLS_Q_DD: Where dnsmasq config files are stored
- KTOOLS_Q_EXCLUDE: csv list of hosts to exclude
- KTOOLS_Q_GIT_DIRS: ssv (space separated values) list of git dirs this script manages.
- KTOOLS_Q_KMD_P: Location of encrypted keymaster secrets file
- KTOOLS_Q_LEASES: Location of dnsmasq leases (output/generated) file.
- KTOOLS_Q_LIST_LINUX: ssv list of non-RPi linux hosts
- KTOOLS_Q_LIST_PIS: ssv list of RPi linux hosts
- KTOOLS_Q_PROCQ:  Location of ../services/procmon output file
- KTOOLS_Q_RSNAP_CONF: Location of rsnapshot config input file
- PROCMON: "hostname:port" of the procmon to work with


## /varz

- KTOOLS_VARZ_PROM: set to "1" for kcore.varz to automatically export all
  varz to Prometheus /metrics.  Requires the prometheus_client library
  to be installed.

