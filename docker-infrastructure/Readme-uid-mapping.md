# Docker UID mapping

TODO

- subuid += dmap
- subgid += dmap
- /etc/passwd,group += dmap
- /etc/docker/daemon.json += "userns-remap": "dmap"
- restart daemon
