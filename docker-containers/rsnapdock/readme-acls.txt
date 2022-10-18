
TODO(doc)

TODO: 1-time initial setup; user must manually generate and populate these:
  files/root/.ssh/private.d/id_rsa
  files/root/.ssh/private.d/id_rsa.pub

user may want to populate (e.g., if using ssh config host aliases)
  files/root/.ssh/private.d/config


For this container to work, permissions must be added to target
machines to give the rsnap login the ability to bypass normal ACLs.

Instructions are in files/etc/rsnapshot.conf

