
TODO: better doc

TODO: user must manually generate and populate these:
  files/root/.ssh/private.d/known_hosts
  files/root/.ssh/private.d/id_rsa
  files/root/.ssh/private.d/id_rsa.pub

user may want to populate:
  files/root/.ssh/private.d/config


For this container to work, permissions must be added to target
machines to give the rsnap login the ability to bypass normal ACLs.

Instructions are in files/etc/rsnapshot.conf

