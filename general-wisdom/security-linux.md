
# Random Tricks for Improving Linux Security

## Read-only root

Did you know that on almost all modern Linux systems, you can make your root
directory read-only?  It does take a little configuration, but I find the
benefits are worth it.

First, create a separate partition that you'll keep as read+write.  Throughout
the various systems in this repo, you'll see various references to the
directory /rw.  That's my read+write partition.  Take the various directories
where continuous write access is needed (/mnt, /tmp, /var), and move them
under /rw, and then put symlinks from their root-dir positions to their /rw
positions.  (This is most safely done in single user mode, or at least with a
composite bash command; Linux gets unhappy quite quickly if top level things
like /tmp and /var go missing.)  Then you add the options "ro,noatime" to your
root partition entry in /etc/fstab and reboot.

When you want to update the root partition (change things in /etc, update the
software, etc), just run: "mount -o remount,rw /".  And when you're done, run:
"mount -o remount,ro /" to set it back.

If there are particular files you want to change all the time (e.g. things in
/etc), just replace things at the individual files level with symlinks to /rw.

This won't significantly slow down an interactive human hacker who has root
access- they'll just run that remount command.  However, there's an incredible
number of automated attacks that this will just stop dead.  And I really like
the idea that the contents of the root partition are very unlikely to change
without me coming and manually enabling the rw remount.

Btw, you'll find that many of the Makefile throughout this repo check for the
environment variable ROOT_RO, and if they see a "1", then they'll
automatically remount,rw at the start of an install phase, and remount,ro when
they're done.  This minimizes the inconvenience when installing lots of
things.


## Firewalls

Everyone likes firewalls.  I *really* like firewalls.  Specifically, I like my
firewalls to be incredibly tight, especially for hosts that generally just run
automated processes, i.e. have predictable traffic patterns.

I generally start off blocking everything, inbound *and outbound*, and require
a specific whitelist entry for every {source-ip + dest-ip + destination-port}
that needs to communicate.

Obviously this doesn't work for workstations that have humans on them
regularly.  Humans want to roam all over the net.  And for that reason, you
really must consider your (and other human-infested workstations) to be a
significant source of threat to your servers.  Do not set up an outer
perimeter and put both human-occupied and automated-server systems as peers
inside the outer walls.  Protect your servers from your human-occupied
workstations just as you would from the Internet -- consider them hostile --
even (especially) your own server.  I'm not saying don't allow any
connectivity, obviously you need to manage your servers.  But don't allow
unrestricted connectivity.  Choose your open ports deliberately.

Furthermore, don't just have firewalls silently block things they don't allow.
iptables has great features for logging rejected packets, but also adding
rate-limiting to the logs, so they don't overwhelm your logs.

When there's traffic that you don't want to let through but also you don't
need to investigate, add a rule that drops that specific traffic before
logging.

The goal is to work towards having sufficiently comprehensive accept and
silent-deny rules that you basically never get any traffic which is rejected
"by default".  And when you get there, you can actually change your logging
system to raise an alert whenever such new-and-unexpected traffic is seen.
That gives you an incredible line of defense against novel attacks.


# Other Things To Watch Out For

## Relative paths

You've probably noticed that when some scripts want to list files, they run
"ls", whereas others run "/usr/bin/ls".  What's the deal?

There's a whole class of attacks where the baddy can't directly change the
logic of a script, but can affect the environment variables it runs with.  So
the attacker could create /tmp/ls, a script that does something bad, and then
runs the normal /usr/bin/ls command.  And then they trick some system process
to use a $PATH variable that includes /tmp before /usr/bin.  Now scripts that
call plain "ls" are going to run the infected script rather than the real
command, and they won't even notice, because /tmp/ls does in-fact eventually
run the real command and generate the expected output.

So you'll often find that folks with security experience tend to almost always
code full paths.

This is the safer thing to do security-wise, although of-course it also
undermines some of the things $PATH is good for.  For example, if you decide
to move a file from /root/bin to /usr/local/bin, or from /usr/local/bin to
/usr/local/sbin, etc, you suddenly find that you've got to change all the
references from one full path to the new one.

It's a traditional security-vs-flexibility trade-off.

For the most part, you'll find things in this repo use full paths.
This is why.

