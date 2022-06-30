# Docker UID mapping

TODO(doc)

- subuid += dmap
- subgid += dmap
- /etc/passwd,group += dmap
- /etc/docker/daemon.json += "userns-remap": "dmap"
- restart daemon
