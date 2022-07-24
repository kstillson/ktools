
# home-control service and lot of example configuration

home_control_service.py provides a reasonably trivial web-service wrapper for
../../pylib/home-control/hc.py.

The web-server's default hander will output "root.html".  The user-controls
contents of this are specialized to the original author's particular home
setup, but hopefully the Javascript framework will provide a good
building-block for you to construct a control panel for your own details.

The javascript send() function calls back to the web-server's "/control"
handler, which then takes actions to control lighting, etc.

Also included are example hcdata_devices.py and hcdata_scenes.py files, which
match-up to the control in root.html, i.e. again they are specialized to the
original author's setup and should be taken as examples.  But there's lots of
comments about how they work, and as this is an actual configuration for a
non-trivial installation, hopefully it shows off a bunch of the options.

The hcdata_test_device.py is provided because all the files in this directory
will be copied into the Docker container for
../../docker-containers/home-control, and the pseudo device created by this
file is used by that container's acceptance unit-test.

