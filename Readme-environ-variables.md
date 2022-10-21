
# Control variables

A number of environment variables affect the way the ktools operates:


## Makefile controls

These only affect things when running the "make" command.

- BUILD_SIMPLE: In the pylib/ directory, the default is to build and install
  by building a Python "wheel" .whl file.  This is reasonably portable, but
  requires pip3 and takes quite a bit longer.  Set BUILD_SIMPLE="1" to skip
  the wheel and install the files directly by copying into place.

- ROOT_RO: TODO(defer): {not fully implemented yet}
  If set to "1", then ktools Makefile's assume that your root filesystem is
  read-only, and that anything being installed there requires a temporary
  remounting of the root-fs in "rw" mode.


## Docker controls: building containers

These affect how containers are built by the docker-infrastructure/d-build.sh
script (which is run automatically by make commands run explicitly inside the
docker-containers subdirectory).

- DBUILD_PARAMS: d-build will pass anything set here through to the "docker
  build" command.  Not generally needed.

- DBUILD_REPO: name of the docker repository that d-build will build into.
  default is 'ktools'

- DOCKER_BASE_DIR: If d-build is given a relative directory in-which to find a
  container to build (via the --cd flag), this is the directory the reference
  will be relative to.


## Docker controls: launching containers

These affect how containers are launched by docker-infrastructure/d-run.sh

- KTOOLS_DRUN_LOG: default Docker log type to use for
  docker-infrastructure/d-run.sh if not specified on the command-line or in
  the container's settings file.

- KTOOLS_DRUN_NETWORK: default Docker network to use when launching containers
  from d-run, if not specified via flag or settings file.

- KTOOLS_DRUN_REPO2: fallback Docker repository to use for d-run, if not
  specified via flag or settings file.  Note that the primary repo to try
  "ktools", but d-run will fall back to this if that doesn't work.  So if
  you've got a personal repo, set it's value here.

- KTOOLS_DRUN_TEST_NETWORK: docker Network to use when d-run is launching a
  container in --dev or --dev_test mode, if not specified via flag.


## Home-control

- HC_DATA_DIR: pylib/home-control/hc.py needs a bunch of data files to operate
  (to provide device and scene data, and for plugins to load).  If set, this
  variable provides a default location to search for those files.


## /varz

- KTOOLS_VARZ_PROM: set to "1" for kcore.varz to automatically export all
  varz to Prometheus /metrics.  Requires the prometheus_client library
  to be installed.

