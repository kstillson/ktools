
# Containers and Micro-services Everywhere

## Background

There are a lot of non-security reasons why it's a good idea to wrap just
about everything into separate Docker containers...

- Configuration and setup of your containers' run environment become
  source-code that's trivial to back up and version control.

- The details of your host's configuration starts to become largely
  irrelevant, containers can be re-started on any host that supports Docker,
  including lots of different cloud-services.  It becomes so much easier
  to transplant or scale services when you don't need to worry about
  setting up the environment outside the container, and the environment
  inside is taken care of by the Dockerfile.

- You can (with just a little care) start up independent instances of services
  that don't interfere with each other.  This allows very clean separation of
  production, development, and testing instances, and trivial horizontal
  scaling.

But for me, but main reason I want to wrap things into containers is security.


## Security Advantages

### Attack surface area reduction

Attackers usually start by gaining some little foothold in a service, and from
there, wiggle around, making use of whatever permissions they have in their
foothold, generally grabbing on to other pieces of infrastructure to widen
their access or move laterally to other more vulnerable areas.

So obviously you want your services to run with as diminished permissions as
possible, as a hacker's foothold will likely start-off with whatever
permissions your service is using.  But a container with a hardened base image
removes the other critical piece for hackers- the copious Linux infrastructure
that's sitting around waiting to be exploited.

My base-image is based off Alpine Linux, which is a fantastic starting point.
It's very small, and quite minimal.  Alpine provides a basic small set of
Linux command-line tools- many of which we can safely remove, at least once
our in-container software is installed.  And it provides a Linux environment
that requires exactly *zero* processes to make its internals go.  The only
processes in the container are the one you put there to provide your service,
and of course any other helper processes that it launches.

And once your various service files and their dependencies are installed, you
can happily wipe out every binary they don't require, and trim down the
internal configuration to almost nothing, even removing the "root" username
from /etc/passwd, if you're not using it.

This is seriously stripping down the attack surface area an attacker will have
to work with down to its absolute minimum.

For the details of the scripts I use to set up my containers and strip down
their contents, see [Readme-containers](../containers/README-containers.md).

Most of the magic is [here](../containers/kcore-baseline/files/prep).


### Uid namespace mapping

This is a feature of Docker that isn't turned on automatically, but which you
should absolutely turn on.  What it does is create an offset between user-id's
inside and outside the container.  A common offset is 200,000.  So, for
example, what looks like root (uid 0) inside the container, is actually
executing in the real kernel as uid 200000; a completely unprivileged user.
The very concept of real uid 0 does not exist inside the container.  There is
no way to become it, there is no way to even reference it, as uid -200000 is
nonsense.

Obviously this doesn't work is the root user in your container needs to do
things with real host root privs, but if that's the case, you're probably
doing something more fundamentally wrong.

There are some complications to turning uid mapping.  First is that if you
bind-mount directories, you've got to make sure the real uids outside the
container match the mapped uid's inside the container.  So, for example, if
you're mapping in the real directory /rw/dv/apache/var_log as a place for the
Apache web server user to store it's logs, and inside-the-container apache has
the uid of 33, then var_log needs to be writable by uid 200033, and the chain
/rw/dv/apache needs to be readable by that uid.  This can look kinda confusing
from the outside, although it can be helpful if you create /etc/passwd entries
for the mapped uid's.  For example, I create an entry:
  droot:x:200000:200000:docker root map,,,:/tmp:/usr/sbin/nologin

so that contained "root" processes show up as "droot" rather than "root" or
rather than showing up as numerical usernames because there's no passwd entry.

Anyway, once you activate uid-mapping, a hacker can go to all the trouble they
care to to "hack root" from their foothold inside your service, and they'll
still find themselves with a completely unprivileged account.

See [Readme-uid-mapping.md](../container-infrastructure/Readme-uid-mapping.md)
for more information on activating this feature.


### Intrusion Detection via COW

But by far my favorite security feature of Docker is it's copy-on-write
filesystem.  When you launch a container, it's image is read-only.  It is not
possible to change the image's real contents from inside the container.  Of
course that would break most software, so a copy-on-write layer is put on-top
of the read-only image.  Basically, whenever a file is changed, the modified
contents gets stored in a changes-only directory, somewhere deep in the Docker
infrastructure directories.  The file-system contents that are visible from
inside the container is the read-only image, but with individual files
overridden from the COW directory, if they exist.

The well-known feature of this is that if you restart a container, the COW
directory is cleared out, which means that the container starts from the fresh
read-only image.  If something nasty has happened in a container, just restart
it, and you're back to a known-good state.

But only slightly less well-known, is that you can find the COW directory and
access it directly.  In other words, taking an inventory of the files in the
COW directory shows you list of every single thing that has changed from the
read-only baseline.

It is very easy to come up with a list of files that are 'expected to change,'
and then monitor for the presence of anything in the COW directory that isn't
on that list.  It is very difficult to hack into a system without changing any
files.  Especially if you have settings to do things like log every command
bash command into a .bash_history file.  Which I do.

Relevant tools:

[d cow-dir](../container-infrastructure/d.sh) will output the COW directory
for a container.

[d-cowscan](../container-infrastructure/d-cowscan.py) contains the process for
scanning all up containers for files not on an IGNORE_LIST.

[procmon](../services/procmon) wraps that into a security scanning service
that regularly sweeps the system and raises a sticky alert (i.e. the alert is
maintained even if the change that triggered it is undone), if any unexpected
changes are seen.


## Security Concerns

- group/docker: to do anything with Docker, you need to be in the "docker"
  account group.  Once you're in group/docker, your command over the Docker
  daemon (which runs as root) is basically unlimited, and there are numerous
  known ways to trick the daemon into running arbitrary commands.  In other
  words, anyone in group/docker is effectively user/root.  This isn't
  immediately obvious.  You need to be really careful about adding users
  to group/docker.  In-fact, I generally recommend you don't.  Command
  Docker as root, using sudo as necessary.

- docker daemon: I suppose it's necessary that they structured it the way they
  did- just about everything you ask Docker to do for you requires real root
  privs to make happen.  But the consequence is that the Docker daemon is a
  very large and very complex program that does a lot of things, and accepts a
  lot of very complex and subtle commands.  It makes me nervous.  I suppose
  historically it hasn't actually had more really bad security problems than
  any other security-critical piece of Linux FOSS...  But in my experience,
  it's better to have lots of tiny little pieces of functionality each of
  which just do one thing, and do that one thing well - rather than having
  these gigantic do-it-all services.

  But anyway, you can tell by the fact that I use Docker extensively, that
  I've decided the concrete advantages outweigh the potential concerns.

