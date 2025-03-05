#!/bin/bash

# Ken note-to-self (i.e. this is specific to the author's primary server config)
# For this container to work, the following extended ACLs are needed:

. blib

# keep this in-sync with /files/home/watch/filewatch_config
mapfile targets <<EOF
 /rw/dv/dnsdock/var_log_dnsmasq/dnsmasq.leases
 /rw/dv/eximdock/var/log/exim/mainlog
 /rw/dv/nagdock/var_log_nagios/nagios.log
 /rw/dv/rsnapdock/var_log/rsnapshot.log
 /rw/dv/webdock/var_log_apache2/access.log
 /rw/dv/eximdock/var/spool/exim/input
 /home/ken/share/rcam/homesec1
 /home/ken/share/rcam/homesec2
 /rw/mnt/rsnap/daily.0/a4/var/log/syslog
 /rw/mnt/rsnap/daily.0/home2/encfs-black-backup/mnt/home2/encfs-black-backup/8KDFlw0eY0UZy98mW4ieT5q3/ilYCfI3KAmQTQB99BhQhdNHt/H1kiffd4L60JLSu5uU5RK13E/mga-bX,iZAg5pfspBbT3Remr
 /rw/mnt/rsnap/daily.0/home/home/ken/share/tmp/touch
 /rw/mnt/rsnap/daily.0/home/home/rubuntu/backup/var/log/syslog
 /rw/mnt/rsnap/echo-back/vault-touch
 /rw/log/cron*
 /rw/log/daemon.log
 /rw/log/iptables.log
EOF

cd /rw/mnt/rsnap  # set stop dir for "q parent_dirs"

for t in "${targets[@]}"; do
    case "$t" in *\**) erun setfacl -m g:dwatch:rX $t; continue ;; esac
    t=$(echo $t | tr -d '\n ')
    if [[ ! -e "$t" ]]; then emitc red "no such target: $t"; continue; fi
    erun setfacl -m g:dwatch:rX $t $(/root/bin/q parent-dirs $t | tr '\n' ' ')
done
