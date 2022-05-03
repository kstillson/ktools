
TODO

# DNS and DHCP

### DHCP and DNS controls

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

ktools uses a somewhat unusual DHCP and DNS configuration: IP addresses and
hostnames are assigned manually in the DHCP server.  Why?

  1. Security: An new (unregistered) device is immediately noticed and is
  treated differently.
  
  2. Connectivity: Every device has a human-controlled name.  For example,
  in the "tplink" module, it is necessary for the server to be able to
  contact each of the smart plugs/switches/bulbs being controlled.
  
  3. Traceability: Every connection can be traced back to a known
  registered device by IP.  For example, in the "keynmaster" section,
  connection source IP addresses are very important.

It is worth noting that this arrangement requires a flat network.
Specifically, all wireless access points must run in "bridge mode," where
they simply pass traffic back and forth without performing any NAT or IP
masking.  Without this the above benefits are lost and many of the tools
below won't work.

See also the "system-maint" module below, for tools that make DNS assignment and management easy.
