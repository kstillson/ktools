
# Linux System Administration: networking

## Manual DNS assignment

I use, and recommend, a somewhat unusual DHCP and DNS
[configuration](../docker-containers/dnsdock/files/etc/dnsmasq): IP addresses
and hostnames are assigned manually in my DHCP server.  Why?


1. Security: An new (unregistered) device is immediately noticed and is
   treated differently.

1. Connectivity: Every device has a human-controlled name.  For example,
   in the "TPLink" module, it is necessary for the server to be able to
   contact each of the smart plugs/switches/bulbs being controlled.

1. Traceability: Every connection can be traced back to a known
   registered device by IP.  For example, in the "keymaster" section,
   connection source IP addresses are very important.


It is worth noting that this arrangement requires a flat network.
Specifically, all wireless access points must run in "bridge mode," where they
simply pass traffic back and forth without performing any NAT or IP masking.
Without this the above benefits are lost and many of the tools that depend on
them won't work.

Note that my ["quick" tool](../tools-for-root/q.sh) has a "dns-update" command
that makes editing my DNS configuration, and testing, updating, and restarting
my DNS server all very quick and easy.  I use that whenever I add a new device
and need to register it's MAC address and give it an IP and hostname.


## Network tags and virtual subnets

If you look at my
[dnsmasq.conf](../docker-containers/dnsdock/files/etc/dnsmasq/dnsmasq.conf),
you'll see my "subnet plan."  Basically, I use the entire 192.168.x.x / 16 for
my local network.  Now, that's far more IP numbers than I need, but I divvy
things up by subnet.  In most networks, subnet is reflective of physical
arrangements (e.g. what floor you're on in a building or such), and is used as
a hint for router rules.  As stated above, my network is "flat", the entire
/16 is treated as one single routing zone (and in-fact, I don't have any
routers, just a few switches and bridges).  I use subnets to represent
categories of access and security zones.

The high level map:

- Subnet 1 (192.168.1.*) is used for statically assigned IPs, i.e. things that
  don't use DHCP, and which are generally physical hosts running Linux.

- Subnets 2-4 are used for various Docker-assigned IPs.  Subnet 2 for
  containers considered "in production," subnet 3 for things being developed
  or tested, and subnet 4 for various experiments.

- Subnet 5 is where known-mac-address units are assigned DHCP addresses, and
  tagged within dnsmasq as on the "green" network.

- Subnet 6 is my 'guest network,' tagged "yellow," and is where I put devices
  belonging to visitors.

- Subnet 9 is my 'red network,' which is where anything that asks for a DHCP
  address but hasn't been specifically assigned an IP gets placed.

Machines are treated different based either on their subnet or their networks
tag color.  Specifically-

- Any machine being assigned an address in the red network is picked up by
  my monitoring systems and raises an immediate alert.

- Machines in the yellow network are given an external DNS server, so they can
  contact things in the outside, but don't be told about any of my internal
  services.  Machines in the red network are given an invalid DNS server.


## Outbound firewall rules & alerts

- Machines in subnets 1 and 2 use carefully crafted OUTBOUND firewall rules.
  The main firewall will not allow external communication except where
  specifically white-listed.  These are all servers, and they should have a
  fixed, small, and infrequently changing list of places they're contacting,
  and any other behavior is suspicious.

  btw, for machine updates, I use a [squid
  proxy](../docker-containers/squickdock).  This not only provides faster
  downloads when multiple machines are upgrading and can pull down the
  identical files from the local network rather than from outside, but also
  means I can easily enough put in rules to allow/expect traffic from my
  various servers to the squid proxy, and then keep track of squid's
  configuration and logs to make sure that only the expected sources are being
  queried.

- More important than blocking unexpected traffic is alerting on it.

  This is basically the same philosophy I use for
  [syslog-ng](monitoring.md#syslog-ng), namely: specifically white-list
  packets that are known-good and expected.  Specifically black-list and
  reject packets you don't want and know are unimportant.  And, most
  importantly- block *and alert* on anything else.

  iptables has a great mechanism for sending packet metadata to syslog
  (including various rate-limits to make sure you don't overwhelm the system),
  and syslog-ng has fantastic filtering capabilities, including the ability to
  pipe log messages to programs for more sophisticated analysis.

  Simple services, especially micro-services where you know nothing else should
  be going on inside their container that might create unexpected traffic, are
  ideal monitoring sources.  You know exactly what network traffic should be
  coming in and going out.  Any other traffic either represents a malfunction
  or a hacker looking around.  Alerting on firewall rule blocks is a fantastic
  way to get early notification of this.

  I have not yet released the more detailed tools I use for creating and
  monitoring my iptables rules; I consider them very sensitive, and it will
  take a while to generate a version with the sensitive pieces sufficiently
  separated out that I'm comfortable releasing it.  But in the mean-time, I
  will point out this tool I've provided:
  [iptables_log_sum](../tools-for-root/iptables_log_sum.py).  This tool takes
  logfiles created by indicate iptables rules that requested a syslog entry,
  and generates an easier to read report with duplicates eliminated.

  The idea is that you can have iptables generate log messages, and then use
  this tool to review them, refine your white-list and black-list rules, until
  you get to the point where you're not regularly seeing reported iptables
  violations.  Then rather than just accumulating those logs, you can start
  to alert on them.


# Linux System Administration: other tools

Take a look at [q](../tools-for-root/q.sh).  This is a set of shell-script
utilities I've built up over the years, most of which are directed towards
administering a small fleet of Linux-and-similar computers.  There's some
handy stuff in there...

