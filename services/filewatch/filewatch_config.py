
# CAUTION- the master copy of this file is in the services/filrwatch directory.
# If you change the copy in the containers/filewatch/files/... tree, it will
# be overwritten during the next container build.

DAY = 24 * 60 * 60

CAM_AGE = 2 * DAY
RSNAP_LOG_AGE = 2 * DAY                     # Constantly changing logs should propogate to rsnapshot within 2 days.
SYS_LOG_AGE = 2 * 60 * 60                   # Normal logs updated within a few hours.
SYS_LOG_AGE_SLOW = 1 * DAY
RUBUNTU_LOG_MAX_AGE = 7 * DAY
TBIRD_MAX_AGE = 14 * DAY

# Maps filename globs to checking rules.
#
# The special glob form "/dir/{NEWEST}" can be used to select the most
# recently modified file in a directory.
#
# If checking rule is an integer, it's the max # of seconds old for the file(s)
# modification time.  Common max-ages are calculated above.
#
# If checking rule is None, then that file automatically passes (generally used
# to create exceptions to filename globs).
#
# If checking rule is 'DIR-EMPTY', then the filename should point to an existing
# directory, and that directory should be empty.  Similiar for FILE-EMPTY
#
# If checking rule is 'NOT-FOUND:x', then the file passes if "x" is not found in
# it's contents.

CONFIG = {
    # rsnapshot based
    '/root/rsnap/daily.0/a4/var/log/syslog':                       RSNAP_LOG_AGE,
    '/root/rsnap/daily.0/home/home/ken/share/tmp/touch':           RSNAP_LOG_AGE,
    '/root/rsnap/echo-back/vault-touch':                           32 * DAY,

    # This is .../gocfs-black-backup/backup/var/log/auth.log:
    '/root/rsnap/daily.0/home2/mnt/home2/gocryptfs-black-backup/MWO9lVk0_fy0jyzCFLa2cg/MFI_Qa5e_2qWhLmHKBDdQQ/W7uzaCEYuNjYCmM8tysTpw/55kMJUCPHMkLt5TD6N1ioA': 2 * DAY,
    
    # syslog based
    '/root/syslog/daemon.log':                     SYS_LOG_AGE,
    '/root/dv/eximdock/var/log/exim/mainlog':      3 * DAY,
    
    # auto mail archiver
    '/root/share/gocryptfs/mailarc/jimVlLOKliHlB2EinQbtpw/69fLQXh0yRjE53VKWU5sHw':  8 * DAY,  # tmp/update.done
    '/root/syslog/mailarc.log':                         8 * DAY,
    '/root/var_local/mailarc/ok-dken-dcc-mbox.stamp':   8 * DAY,
    '/root/var_local/mailarc/ok-dken-dken-sent.stamp':  8 * DAY,
    
    # other general services
    '/root/dv/nagdock/var_log_nagios/nagios.log':  SYS_LOG_AGE,
    '/root/dv/rsnapdock/var_log/rsnapshot.log':    RSNAP_LOG_AGE,
    '/root/dv/webdock/var_log_apache2/access.log': SYS_LOG_AGE,

    '/root/rsnap/daily.0/home/home/rubuntu/backup/var/log/syslog': RUBUNTU_LOG_MAX_AGE,
    
    # cron exceptions
    '/root/syslog/cron-black.log':                 3 * DAY,
    '/root/syslog/cron-jack2.log':                 2 * DAY,
    '/root/syslog/cron-jack3.log':                 2 * DAY,
    '/root/syslog/cron-glowbox1.log':              None,  # Disable globbed file.
    
    # globs
    '/root/syslog/cron*':                          SYS_LOG_AGE,

    # specials
    '/root/dnsmasq/dnsmasq.leases':                'NOT-FOUND:.9.',
    '/root/exim':                                  'DIR-EMPTY',
    '/root/share/rcam/homesec1/{NEWEST}':           CAM_AGE,
    '/root/share/rcam/homesec2/{NEWEST}':           CAM_AGE,
    '/root/syslog/iptables.log':                   'FILE-EMPTY',
}
