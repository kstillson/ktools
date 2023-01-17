
# settings.yaml

## Purpose / motivation

Docker is fantastic at taking the complicated list of instructions on how to
build an image and codifying that into the Dockerfile.  However, there's a
separate complicated set of instructions on how to transform an image into a
running container; generally a long list of command-line flags passed to the
"docker run" command.  Docker does not do so good a job of codifying that
information.  This is what d-run.py and settings.yaml are for.

Originally I just had a shell script, ./Run, which had the container-specific
details for how to launch an image.  However, I kept finding that there were
lots of cases where I needed some context-specific adjustments to those
params, and the ./Run scripts started to become cumbersome.

As an example: I often have a "production" version of a container up and
running the #live tagged image, attached to it's proper IP address, and
writing it's logs to a bind-mounted directory.  I make some changes, and now
want to test those changes.  This means launching the #latest image, attaching
it to an alternate IP address, and having it write its logs to an alternate
bind-mounted directory.  If the test fails, I want to make sure none of the
mess it leaves behind either breaks the production version or creates
confusing log messages.

So settings.yaml contains some terse and high-level instructions that d-run
can translate into either production parameters or test-instance parameters.
Adding the "--dev-test" flag for d-run tells it to generate the testing
version.


## Contents - things containers almost always need to specify


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


### bind mount instructions

This is the complicated one, because the way one should change bind-mounts
between production and testing runs is context-specific.  So, the fields in
settings.yaml are designed so you can provide the necessary context.

In each of the cases (below), a list of string pairs is given.  The first is
the location on the host where the real files are going to live.  This can be
a full path, or, if just a relative path is given, it's relative to the Docker
volume directory, which by default is /rw/dv/{container-name}/.  The second
string is the path inside the container where the bind-mount will appear.

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

- mount_persistent_test_copy: now we're getting fancy.  Sometimes your test
  instance really needs to be able to write to persistent storage, you just
  don't want it to write to the same persistent storage as the production
  instance.  So during launch, d-run will make a copy of your docker volume
  dir.  i.e. /rw/dv/{container}/* is copied to /rw/dv/TMP/{container}/*.

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
  except copies all the files too.

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

If set to "1", the container runs in the foreground and logs inherently go to
stdout / stderr, i.e. the normal logging driver setting is ignored.


### log

This controls Docker's --log-driver flag, and basically tells Docker what to
do with any stdout / stderr created by your service.  Options are:

- n / none:  throw it away

- s / syslog:  send it to syslog

- j / json:  send it to a JSON file at the location of Docker's choosing.
  (retrieve it with the "docker log" command)

- or any other param to be set directly as the --log-driver flag value.


### extra_init / debug_extra_init:

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
contains the Dockerfile.  i.e. ../docker-containers/eximdock/Dockerfile will
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

Note that the --subnet flag to d-run can override the 3rd octet (?.?.subnet.?)
of the IP address assigned by either DNS or by the "ip" setting, and the
--subnet flag is set implicitly by other flags, such as --dev or --dev-test.

This is because I use that 3rd octet to differentiate between production and
test instances.  For example, if DNS returns 192.168.2.125 for eximdock, then
using d-run with --dev-test will automatically set --subnet=3, which will
launch the container at IP address 192.168.3.125.  This both makes sure that
test containers stay out-of-the-way of the production ones, and gives me a
really easy way to identify what test container is generating a bunch of junk
traffic based on it's IP address.

btw- I never let Docker assign IP numbers and use it's internal routing to
find containers.  This is because I use iptables to lock-down just about all
of my network communication, and it needs fixed IP addresses to work.


### name

Overrides the name of the conatainer as managed by Docker.  By default this is
set to the name of the directory continaing the settings file.


### network

Sets the Docker network name to use.  Defaults to $KTOOLS_DRUN_NETWORK for
normal runs, or $KTOOLS_DRUN_TEST_NETWORK for test runs.  Those both default
to "bridge" if not set.  Generally this is more of a host-specific thing, so I
tend to use the environment variables to control this, rather than the
settings.