
# Control variables

A number of environment variables affect the way the ktools operates:


## Settings controls

- KTOOLS_SETTINGS: contains the pathname of the "global" settings file
  (i.e. settings shared by the entire host).  If not set, defaults to
  ~/.ktools_settings


## Docker controls: building containers

These affect how containers are built by the container-infrastructure/d-build.sh
script (which is run automatically by make commands run explicitly inside the
./containers subdirectory).

- BUILD_DOCKER_CONTAINERS: if set to "1", then automatically include the
  ./containers subdirectory from the main directory's targets.

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


## Docker controls: launching containers

These affect how containers are launched by container-infrastructure/d-run.sh

- KTOOLS_DRUN_DNS: If set, this becomes the default value for the setting
  'dns' for pylib/tools/ktools_settings.py.  This should be the IP address of
  the dns server to use when launching or testing containers.  If not set, the
  default is '', which leaves dns server determination up to the container
  manager.  Either a container-specific or the global settings file will
  override this environment varaiable.

- KTOOLS_DRUN_EXTRA: If set, this becomes the default value for the setting
  'ktools_drun_extra' for pylib/tools/ktools_settings.py.  This is basically a
  list of ";"-separated additional params to pass to the container manager
  during a launch.  Either a container-specific or the global settings file
  will override this environment varaiable.


## Docker controls: testing containers

- KTOOLS_DRUN_TEST_PROD: when tests are requested (e.g "d.sh test" or "make
  test"), if KTOOLS_DRUN_TEST_PROD="1", then the test runs against the production
  container (which is expected to already be up), rather than running against
  a test-mode container (which is launched if necessary).


## tools-for-root/q.sh

These override the internal logic in q.sh for finding these various files and
services.  All are optional (i.e. q.sh uses it's default logic if these are
not specified in the environment).

- KTOOLS_Q_DD: Where dnsmasq config files are stored
- KTOOLS_Q_KMD_P: Location of encrypted keymaster secrets file
- KTOOLS_Q_LEASES: Location of dnsmasq leases (output/generated) file.
- KTOOLS_Q_PROCQ:  Location of ../services/procmon output file
- KTOOLS_Q_RSNAP_CONF: Location of rsnapshot config input file
- PROCMON: "hostname:port" of the procmon to work with


## /varz

- KTOOLS_VARZ_PROM: set to "1" for kcore.varz to automatically export all
  varz to Prometheus /metrics.  Requires the prometheus_client library
  to be installed.


## Makefile controls

These affect the way the "make" command works.

- KTOOLS_KEN: if set, triggers various actions that are specific to the
  original author's systems and configurations; you probably don't want this.
