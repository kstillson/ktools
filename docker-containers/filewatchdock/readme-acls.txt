
# Ken note-to-self (i.e. this is specific to the author's primary server config)
# For this container to work, the following extended ACLs are needed:

setfacl -m g:dwatch:rX \
  /rw/mnt/rsnap \
  /rw/mnt/rsnap/daily.0 \
  /rw/mnt/rsnap/daily.0/home \
  /rw/mnt/rsnap/daily.0/home/home \
  /rw/mnt/rsnap/daily.0/home/home/ken \
  /rw/mnt/rsnap/daily.0/home/home/ken/share \
  /rw/mnt/rsnap/daily.0/home/home/ken/share/tmp \
  /rw/mnt/rsnap/daily.0/home/home/ken/share/tmp/touch \
  /rw/mnt/rsnap/daily.0/home/home/blue-backup/backup/var/log/auth.log \
  /rw/mnt/rsnap/daily.0/rw/rw/v \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web/rootfs \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web/rootfs/var \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web/rootfs/var/log \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web/rootfs/var/log/nagios3 \
  /rw/mnt/rsnap/daily.0/rw/rw/v/web/rootfs/var/log/nagios3/nagios.log \
  /rw/mnt/rsnap/daily.0/pi1 \
  /rw/mnt/rsnap/daily.0/pi1/var \
  /rw/mnt/rsnap/daily.0/pi1/var/log \
  /rw/mnt/rsnap/daily.0/pi1/var/log/x10-watcher \
  /rw/mnt/rsnap/daily.0/pi1/var/log/x10-watcher/x10-watcher.log \
  /rw/mnt/rsnap/daily.0/a1 \
  /rw/mnt/rsnap/daily.0/a1/var \
  /rw/mnt/rsnap/daily.0/a1/var/log \
  /rw/mnt/rsnap/daily.0/a1/var/log/syslog 

