
# settings.yaml

## Purpose / motivation

Docker is fantastic at taking the complicated list of instructions on how to
build an image and codifying that into the Dockerfile.  However, there's a
separate complicated set of instructions on how to transform an image into a
running container; generally a long list of command-line flags passed to the
"docker run" command.  Docker does not do so good a job of codifying that
information.  This is what d-run.py and settings.yaml are for.

d-run.py translates the terse and high-level settings.yaml file into a
specific set of flags for "docker run".


## The control override structure

The system below may seem like a rather complicated scheme, but each feature
serves a useful purpose.  For example, there are some controls whose correct
values are really determined by the configuration of the host- for example,
which logging method I want to use.  For these I generally don't specify a
value in settings.yaml, and instead use a host-level environment variable to
"override" the control with the host-specific value.

In other cases, for example, the virtual network to use, picking the correct
network is a combination of per-host configuration and the context of whether
we're running in normal mode or --test-mode.  In this case, again I usually
wouldn't specify anything in settings.yaml, which will fall-back to the
control's default.  However, if you check the control's default (either in the
"network" section below or in d-run.py:CONTROLS), you'll see that the
mode-dependent defaults reference two different environment variables, making
it easy to specify host-level defaults that depend on the run mode.

Anyway, the idea is that by carefully selecting the placement of a control
(flags, environmental overrides, settings, environmental defaults, etc), it
should be unusual for you to have to do things like duplicate a host-level
control in many container-specific settings files, or frequently use
command-flag overrides for container-specific settings.

The goal is that in the typical case, only a few container-specific settings
need to be specified in the settings file.

The "d-run --test" flag is provided for a "dry-run," i.e. testing what a d-run
command would do without doing it.  If you want to see where in the heirarchy
of overrides each control is getting its value, use "d-run --debug".


### Highest level override: command-line flags

Most individual controls can be overriden by a command-line flag passed to
d-run.py.  Use "d-run -h" for a list, or see d-run.py:COMMANDS, specifically
the Ctrl.override_flag field, for the name of the flag and which control it
overrides.

For example, to demand a container be started without network virtualization
(i.e. directly on the host's network), use "d-run --network host".  However,
usually you wouldn't do this; you'd allow the non-override logic (below) to
figure out the correct network to use.


### Next level override: environment variables

Most controls also support taking their value from an environment variable.
See Ctrl.override_env for the name of the variable.  For example, if a
particular host always grabs its images from a particular repositoy, and you
don't want to have to specify it in each settings file, you could:
export KTOOLS_DRUN_REPO=reponame


### Individual container settings

Usually there are a few controls that are specific to the way a particular
container works, for example, which bind-mounts to establish.  These are best
stored in the settings file in the container's source direcotry (i.e. peer to
the Dockerfile).

Usually there's just a single settings file per container, named
settings.yaml.  However, it's possible for containers to offer several
alternative modes, encoded in separate settings files.
Use "d-run --settings {filename}" to select which one to use.

The typical settings are documented below.  The table d-run.py:CONTROLS,
specifically Ctrl.setting_name actually specified the name of the yaml field
for each control.

If running in --test-mode, d-run.py will check for a setting with the name
prefix "test_", and if found, will use that instead.  Same for --dev-mode.
So for example, settings.yaml file could specify:
  ip: 1.2.3.4
  test_ip: -     # see below for the meaning of the special values "-" and "0"
  dev_ip: 0


### Defaults

For settings that are not specified by any of the above methods, default
values come from the CONTROLS table in d-run.py.

If d-run.py is running in --test-mode, then the Ctrl.test_mode_default field
is used.  If running in --dev-mode, it starts with the --test-mode default,
but changes any instances of the string "test" to "dev".  If running in normal
mode (i.e. neither --test-mode nor --dev-mode), the value in
Ctrl.normal_mode_default is used.

If the default value selected above starts with a $, then it's interpreted as
an environment variable name, and that value of that variable is used.  If the
environment variable is not set, the setting falls-back to 'None.'  If the
default value contains the special token '@basedir', then that token is
replaced with the name of the directory containing the settings file (which
generally sets the name and hostname of the container).

As an example, the control 'network' defaults to $KTOOLS_DRUN_NETWORK in
normal mode, but $KTOOLS_DRUN_TEST_NETWORK in --test-mode.

In this way, the correct normal-mode and test-mode default network for a
particular host can be set in the environment.  Individual containers which
consistently need to override this default do so in their settings.yaml file,
and you (the human) can override everything using flags on the occasions where
it's needed.


## Contents - things containers usually need to specify


### autostart

This is an arbitary string used more by d.sh than d-run.py.  When launching,
containers are grouped into "waves" with the same string, and then started in
those groupings; sorted numerically.  String should not contain any spaces,
but can contain something like "4,host=x", which would include the container
in wave 4, but only on the host matching "x".


### port

This setting contains a list of port number pairs.  The first number in the
pair is the number in the real host that needs to listen for requests, and the
2nd is the port number inside the container that the service is listening to.

Ports specified for forwarding in this way use the Docker user-space proxy to
forward traffic.  This is simple and generally works fine, but-- be aware that
this mode will cause the source IP address seen by the contained service to
always appear to be the docker gateway IP.  i.e., the real source address is
hidden by the proxy.  There are some cases where this is really not
acceptable.  For example, the keymaster service and some of webdock's CGI
scripts use source IP as part of their access control mechanisms.

In those cases, no "ports" section is specified in settings.yaml; the port
used inside the container is listed in the EXPOSE field of the Dockerfile, and
iptables DNAT forwarding is used to actually move the traffic from the host to
the container.

Note that when running in --test-mode or --dev-mode, the host-side port
numbers will be shifted (up) by the number in d-run.py's --port-offset flag
(10000 by default).  This allows you to run test or development instances in
parallel to production instances, and still support container port-binding,
but without interfering with the production ports.

Note that a cleaner solution would be for your testing/development work to not
bind ports at all, and to interact with the container under test/dev directly
using it's alternate IP number.  However, this sometimes won't work.  For
example, if using rootless podman as the container manager, and a network of
type 'bridge', it does not appear to be possible for the host to directly
contact their container's open ports- you have to use host-mapped port
forwarding.


### bind mount instructions

This is the complicated one, because the way one should change bind-mounts
between normal and --test-mode / --dev-mode is inherently container-specific.
So, the fields in settings.yaml are designed so you can provide the necessary
context.

In each of the cases (below), a list of string pairs is given.  The first is
the location on the host where the real files/directories are going to live.
This can be a full path, or, if just a relative path is given, it's relative
to the Docker volume directory (set by the control 'vol_base', which defaults
to /rw/dv/{container-name}).  The second string is the path inside the
container where the bind-mount will appear.

- mount_ro: this is an easy one.  Because it's read-only, the same path is
  used for both production and testing containers; they can't interfere with
  each other.

- mount_persistent: THIS OPTION IS VERY DANGEROUS- USE IT WITH CARE.  This
  tells d-run to mount the same directory, read+write, for both production and
  test instances.  If you're not careful with the way your service operates,
  the test might change something that interferes with the production
  instance.

- mount_persistent_test_ro: A safer version of the above- the specified
  directory is mounted read+write for production instances, but read-only for
  test instances.

- mount_persistent_test_copy: now we're getting fancy (i.e. useful).
  Sometimes your test instance really needs to be able to write to persistent
  storage, you just don't want it to write to the same persistent storage as
  the production instance.  So during launch, d-run.py will make a copy of
  your docker volume dir.  i.e. /rw/dv/{container}/* is copied to
  /rw/dv/TMP/{container}/*.

  This makes those files available for the test to read / write / play-with,
  but safely out of the way of the real production files.  Note that if the files
  in this directory are really big, you'll need a lot of space for both copies.

  This option only copies files in the top-level volume directory.  See below
  for other options.

- mount_persistent_test_copy_tree: this is like mount_persistent_test_copy,
  but (a) copies the entire recursive directory tree, and (b) copies only the
  directory structure, no files are included.  This is useful when you've got
  a whole tangle of logfiles created in different directories, and the service
  expects to be able to write to the directories, but doesn't actually care
  about individual file contents upon startup.  Exim is like that.

- mount_persistent_test_copy_files: just like mount_persistent_test_copy_tree,
  but copies all the files too.

- mount_logs: ok, now for some simplifications...  Use this when specifying a
  directory to bind-mount that is just going to contain output logs.  Basically
  it just does a "mount_persistent" for production, and for test runs, creates
  just this single directory in the alternate (TMP/...) volume space.

- mount_test_only: just as it says, is ignored for production runs, and
  mounted read+write for test runs.


## Contents - occasionally useful options

### env

A list of name=value pairs to be added to the container's runtime envirnonment.


### foreground

If set to "1", the container runs in the foreground.  This means anything
generated by stdout/stderr from within the container comes out on the screen
(in addition to be stored wherever the "log" control instructs).


### log

This controls Docker's --log-driver flag, and basically tells Docker what to
do with any stdout / stderr created by your service.  Options are:

- n / none:  throw it away

- s / syslog:  send it to syslog

- j / journal:  send it to the systemd journaling system.

- J / json:  send it to a JSON file at the location of Docker's choosing.
  (retrieve it with the "docker log" command)

- or any other param to be set directly as the --log-driver flag value.


### extra_init:

Parameters that will be passed to the service's command-line inside the
container (which serves as the "init" for the mini-linux system in there,
hence the name).  This is mainly so you can do things like tell the service
that it's operating in its test mode.


### extra_docker

In-case you need some other Docker flag that isn't covered by the more
abstract settings available, you can just provide raw Docker flags here.


## Contents - things containers usually don't need to specify


### hostname

Overrides the name of the host inside the container.  By default this is set
to match the container name, which by default is set to match the base
directory name of the directory containing the settings file.


### image

I almost always use a container name that is set to the name of the image that
created it, and where that is set to the base-name of the directory that
contains the Dockerfile.  i.e. ../containers/eximdock/Dockerfile will
create an image called eximdock, and a container named eximdock.

But if you don't want to follow this convention, you can use this setting to
do something different.


### ip

I like to control all my IP assignments in one place- my DNS server.
Therefore, once d-run has figured out the container name, it's default is to
run a DNS query for that name, and assign the returned address to the
container.

But if you'd prefer to manage your container IP addresses in their
settings.yaml files, this is the field for you.

btw- I never let Docker assign IP numbers for non-testing / non-debugging.
This is because I use iptables to lock-down just about all of my network
communication, and that needs fixed IP addresses to work.


### name

Overrides the name of the conatainer as managed by Docker.  By default this is
set to the name of the directory continaing the settings file.


### network

Sets the Docker network name to use.  Defaults to $KTOOLS_DRUN_NETWORK for
normal runs, or $KTOOLS_DRUN_TEST_NETWORK for test runs.  Those both default
to "bridge" if not set.  Generally this is more of a host-specific thing, so I
tend to use the "override" environment variables to control this, rather than
the container-specific settings file.

