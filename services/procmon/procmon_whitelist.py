from procmon_wl_type import WL

#      Container    user           child? rqrd?  regex
WHITELIST = [
    WL('/',         '*',           False, False, '/lib/systemd/systemd --(system|user)'),
    WL('/',         '*',           False, False, '\(sd-pam\)'),
    WL('/',         'blue-backup', False, False, 'rsync '),
    WL('/',         'blue-backup', False, False, 'sshd: blue-backup'),
    WL('/',         'ken',         False, False, '(/bin/sh -c *)?/usr/local/bin/hc tree'),
    WL('/',         'ken',         False, False, '/usr/sbin/sendmail'),
    WL('/',         'messagebus',  False, True,  '/usr/bin/dbus-daemon --system --address=systemd: --nofork --nopidfile --systemd-activation'),
    WL('/',         'nobody',      False, False, '(/bin/bash -c *)?/bin/ping -c1 -q -w4 hs-front'),
    WL('/',         'nobody',      False, False, '/usr/bin/python3 /usr/local/procmon/procmon'),
    WL('/',         'nobody',      False, True,  '/usr/local/bin/dhcp-helper -e eth1 -s 192.168.2.2'),
    WL('/',         'ntp',         False, False, '/usr/sbin/ntpd -p /var/run/ntpd.pid'),
    WL('/',         'root',        False, False, '(/bin/bash -c *)?.RETRY -- .HC'),
    WL('/',         'root',        False, False, '(/bin/bash -c *)?{ .SSR -o'),
    WL('/',         'root',        False, False, '.*chmod 644 /var/run/dmap'),
    WL('/',         'root',        False, False, '/bin/(ba)?sh -c test -x /usr/sbin/anacron'),
    WL('/',         'root',        False, False, '/bin/(ba)?sh( -c)? */root/bin/d-run --cd rclonedock --fg --settings'),
    WL('/',         'root',        False, False, '/bin/login'),
    WL('/',         'root',        False, False, '/bin/systemd-tty-ask-password-agent'),
    WL('/',         'root',        False, False, '/sbin/agetty .*noclear tty1 linux'),
    WL('/',         'root',        False, False, '/sbin/fstrim --fstab'),
    WL('/',         'root',        False, False, '/sbin/init'),
    WL('/',         'root',        False, False, '/usr/bin/containerd'),
    WL('/',         'root',        False, False, '/usr/bin/docker run --name rclonedock'),
    WL('/',         'root',        False, False, '/usr/bin/docker-proxy -proto'),
    WL('/',         'root',        False, False, '/usr/bin/dockerd -H'),
    WL('/',         'root',        False, False, '/usr/bin/python3 /root/bin/d-run --cd rclonedock --fg --settings'),
    WL('/',         'root',        False, False, '/usr/bin/python3 /usr/local/bin/sunsetter.py'),
    WL('/',         'root',        False, False, '/usr/bin/retry -d [0-9]* -t [0-9]* -- /usr/local/bin/hc'),
    WL('/',         'root',        False, False, '/usr/lib/openssh/sftp-server'),
    WL('/',         'root',        False, False, '/usr/sbin/CRON -f'),
    WL('/',         'root',        False, False, '/usr/sbin/sendmail -i -FCronDaemon'),
    WL('/',         'root',        False, False, 'containerd-shim'),
    WL('/',         'root',        False, False, 'ddclient'),
    WL('/',         'root',        False, False, 'docker ps --format'),
    WL('/',         'root',        False, False, 'docker-containerd --config /var/run/docker/containerd/containerd.toml'),
    WL('/',         'root',        False, False, 'sleep'),
    WL('/',         'root',        False, False, 'sshd: root@notty'),
    WL('/',         'root',        False, True,  '/lib/systemd/systemd-journald'),
    WL('/',         'root',        False, True,  '/lib/systemd/systemd-logind'),
    WL('/',         'root',        False, True,  '/lib/systemd/systemd-udevd'),
    WL('/',         'root',        False, True,  '/sbin/dhclient'),
    WL('/',         'root',        False, True,  '/usr/bin/python3? /usr/bin/fail2ban-server'),
    WL('/',         'root',        False, True,  '/usr/lib/accountsservice/accounts-daemon'),
    WL('/',         'root',        False, True,  '/usr/lib/policykit-1/polkitd --no-debug'),
    WL('/',         'root',        False, True,  '/usr/sbin/acpid'),
    WL('/',         'root',        False, True,  '/usr/sbin/atd -f'),
    WL('/',         'root',        False, True,  '/usr/sbin/cron -f'),
    WL('/',         'root',        False, True,  '/usr/sbin/irqbalance'),
    WL('/',         'root',        False, True,  '/usr/sbin/rngd -r /dev/hwrng'),
    WL('/',         'root',        False, True,  '/usr/sbin/rsyslogd -n'),
    WL('/',         'root',        False, True,  '/usr/sbin/smartd -n'),
    WL('/',         'root',        False, True,  'sshd: /usr/sbin/sshd -D'),
    WL('/',         'root',        True,  False, '(/bin/sh -c *)?run-parts --report /etc/cron'),
    WL('/',         'root',        True,  False, '/bin/(ba)?sh( -c)? */root/bin/d 01 nagdock'),
    WL('/',         'root',        True,  False, '/bin/(ba)?sh( -c)? */root/bin/ssh-agent-wrap /root/lets-encrypt-getssl/getssl'),
    WL('/',         'root',        True,  False, '/bin/(ba)?sh( -c)? */usr/local/bin/update-ddns'),
    WL('/',         'root',        True,  False, '/bin/sh -c */root/bin/rsnap-diff'),
    WL('/',         'root',        True,  False, '/bin/sh -c */root/bin/run-rsnapshot'),
    WL('/',         'root',        True,  False, '/usr/sbin/logrotate /etc/logrotate.conf'),
    WL('/',         'root',        True,  False, 'bash -c chown droot.dwatch /rw/dv/blender/work/'),
    WL('/',         'root',        True,  False, 'sshd: (blue-backup|rsnap)'),
    WL('/',         'uuidd',       False, False, '/usr/sbin/uuidd'),
    WL('blender',   'droot',       False, False, '/bin/bash /etc/init '),
    WL('blender',   'droot',       False, False, 'blender -b'),
    WL('dlnadock',  '200100',      False, False, '/usr/sbin/minidlnad'),
    WL('dlnadock',  'root',        False, False, '/bin/bash /etc/init'),
    WL('dlnadock',  'root',        False, False, '/usr/bin/encfs'),
    WL('dlnadock',  'root',        False, False, 'sleep'),
    WL('dnsdock',   '200350',      False, True,  '/usr/sbin/dnsmasq --conf-file=/etc/dnsmasq/dnsmasq.conf'),
    WL('eximdock',  '200100',      False, True,  '/usr/sbin/exim'),
    WL('filewatchdock', '200900',  False, True,  '/usr/bin/python3 /home/watch/filewatch'),
    WL('fsdock',    'dken',        False, False, '/usr/lib/ssh/sftp-server'),
    WL('fsdock',    'dken',        False, False, 'sshd: ken@notty'),
    WL('fsdock',    'droot',       False, False, '/usr/sbin/rsyslogd'),
    WL('fsdock',    'droot',       False, False, 'sshd: /usr/sbin/sshd -D'),
    WL('fsdock',    'droot',       False, False, 'sshd: ken \[priv\]'),
    WL('gitdock',   '*',           False, False, 'sshd: [a-z]* ?\[net\]'),
    WL('gitdock',   'droot',       False, False, 'sshd: [a-z0-9-]* \[priv\]'),
    WL('gitdock',   'droot',       False, False, 'sshd: \[accepted\]'),
    WL('gitdock',   'droot',       False, True,  '(sshd: )?/usr/sbin/sshd -D -e'),
    WL('home-control', '200801',   False, False, '/usr/bin/python3 /home/hc/home_control_service.py'),
    WL('homesecdock', '200802',    False, False, '/usr/bin/python3 /home/hs/homesec.py'),
    WL('keymaster', '200800',      False, False, '/usr/bin/python3 /home/km/km.py'),
    WL('lsyncdock', 'droot',       True,  True,  '/usr/bin/lsyncd -nodaemon /etc/lsyncd/lsyncd.conf.lua'),
    WL('mysqldock', '200999',      False, True,  'mysqld'),
    WL('nagdock',   '200360',      True,  True,  '/usr/sbin/nagios'),
    WL('privdock',  '200100',      False, True,  '/usr/sbin/httpd'),
    WL('rclonedock','droot',       False, False, '/bin/bash /etc/init'),
    WL('rclonedock','droot',       False, False, '/usr/bin/encfs --extpass /usr/local/bin/kmc encfs-default /root/gdrive /root/gdrive-efs'),
    WL('rclonedock','droot',       False, False, '/usr/bin/script --append --flush --return --command /etc/init'),
    WL('rclonedock','droot',       False, False, 'fgrep -v non'),
    WL('rclonedock','droot',       False, False, 'rclone (sync|copy)'),
    WL('rclonedock','root',        False, False, '/bin/bash /etc/init'),
    WL('rclonedock','root',        False, False, 'fgrep -v non'),
    WL('rclonedock','root',        False, False, 'rclone (sync|copy)'),
    WL('rpsdock',   'droot',       False, False, '(/usr/bin/python2 )?/root/.rps/rps'),
    WL('rpsdock',   'droot',       False, True,  '/bin/sh /etc/init'),
    WL('rpsdock',   'droot',       False, True,  '/tmp/tmp'),
    WL('rpsdock',   'droot',       False, True,  'sleep'),
    WL('rpsdock',   'droot',       True,  False, '/bin/bash -c gpg'),
    WL('rsnapdock', 'root',        True,  False, '/bin/bash /etc/init'),
    WL('rsnapdock', 'root',        True,  False, '/usr/bin/perl -w /usr/bin/rsnapshot'),
    WL('sambadock', 'dken',        True,  False, '/usr/sbin/smbd'),
    WL('squiddock', '200031',      False, False, '\(logfile-daemon'),
    WL('squiddock', '200031',      False, False, '\(squid-'),
    WL('squiddock', '200031',      False, False, '\(unlinkd'),
    WL('squiddock', '200031',      False, True,  '/usr/sbin/squid'),
    WL('sshdock',   '*',           False, False, 'sshd: [a-z0-9]* ?\[net\]'),
    WL('sshdock',   '200022',      True,  False, 'sshd: '),
    WL('sshdock',   '201002',      False, False, 'sshd: tunnel-glowbox1'),
    WL('sshdock',   '201004',      False, False, 'sshd: tunnel-gong2'),
    WL('sshdock',   '202000',      False, False, 'rsync'),
    WL('sshdock',   '202002',      False, False, 'rsync --server'),
    WL('sshdock',   '202002',      False, False, 'sshd: homesec1'),
    WL('sshdock',   '202003',      False, False, 'rsync --server'),
    WL('sshdock',   '202003',      False, False, 'sshd: homesec2'),
    WL('sshdock',   '202004',      False, False, 'rsync --server'),
    WL('sshdock',   '202004',      False, False, 'sshd: hs-front'),
    WL('sshdock',   'droot',       False, False, 'sshd: [A-Za-z0-9-]* \[priv\]'),
    WL('sshdock',   'droot',       False, False, 'sshd: \[accepted\]'),
    WL('sshdock',   'droot',       False, True,  '(sshd: )?/usr/sbin/sshd -D'),
    WL('sshdock',   'droot',       False, True,  '/usr/sbin/rsyslogd'),
    WL('syslogdock', 'dsyslog',    False, False, '/usr/sbin/ssmtp'),
    WL('syslogdock', 'dsyslog',    False, True,  '/bin/bash /usr/local/sbin/log-mailer'),
    WL('syslogdock', 'dsyslog',    False, True,  '/usr/bin/python. /usr/bin/supervisord -n -c /etc/supervisord.conf'),
    WL('syslogdock', 'dsyslog',    False, True,  '/usr/sbin/syslog-ng'),
    WL('webdock',   '200033',      False, False, '(/usr/bin/python3 )?/usr/lib/cgi-bin/kcmd.cgi'),
    WL('webdock',   '200033',      False, False, '(/usr/bin/python3 )?/usr/local/bin/party-lights'),
    WL('webdock',   '200033',      False, False, '/usr/lib/nagios/cgi-bin/status.cgi'),
    WL('webdock',   '200033',      False, True,  '/usr/sbin/httpd'),
]
#   WL('kmdock',    '200800',      False, True,  '/usr/bin/python /home/km/km.py'),
#   WL('/',         'root',        False, False, '/usr/sbin/thermald --no-daemon --dbus-enable'),
#   WL('/',         'root',        False, False, 'setup-resolver'),

#      Container    user           child? rqrd?  regex
GREYLIST = [
    WL('/',         'root',        False, False,  '/usr/bin/ssh-agent'),
    WL('/',         'root',        True,  False,  'SCREEN -D -R'),
    WL('/',         'root',        False, False,  'sshd: root \[priv\]'),
    WL('/',         'root',        True,  False,  'sshd: root@pts/.'),
    WL('git',       'root',        False, False,  'sshd: ken'),
    WL('ssh',       'root',        False, False,  'sshd: ken'),
    WL('web',       'www-data',    False, False,  'sh'),
]
