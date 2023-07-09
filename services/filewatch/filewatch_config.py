
DAY = 24 * 60 * 60

CAM_AGE = 2 * DAY
RSNAP_LOG_AGE = 2 * DAY                     # Should propogate to rsnapshot within 2 days.
SYS_LOG_AGE = 2 * 60 * 60                   # Normal logs updated within a few hours
SYS_LOG_AGE_SLOW = 24 * 60 * 60


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
# directory, and that directory should be empty.
#
# If checking rule is 'NOT-FOUND:x', then the file passes if "x" is not found in
# it's contents.

CONFIG = {
  # rsnapshot based
  '/root/rsnap/daily.0/a1/var/log/syslog':                       RSNAP_LOG_AGE,
  '/root/rsnap/daily.0/home/home/ken/share/tmp/touch':           RSNAP_LOG_AGE,
  '/root/rsnap/daily.0/home/home/blue-backup/backup/var/log/auth.log': 4 * DAY,
  '/root/rsnap/echo-back/vault-touch':                           32 * DAY,
    
  # syslog based
  '/root/syslog/daemon.log':                     SYS_LOG_AGE,
  '/root/dv/eximdock/var/log/exim/mainlog':      3 * DAY,
    
  ## '/root/dv/mysqldock/var_log_mysql/mysql.log':  SYS_LOG_AGE_SLOW,
  '/root/dv/nagdock/var_log_nagios/nagios.log':  SYS_LOG_AGE,
  '/root/dv/rsnapdock/var_log/rsnapshot.log':    RSNAP_LOG_AGE,
  '/root/dv/webdock/var_log_apache2/access.log': SYS_LOG_AGE,
    
  # cron exceptions
  '/root/syslog/cron-jack2.log':                 2 * DAY,
  '/root/syslog/cron-glowbox1.log':              None,  # Disable globbed file.
    
  # globs
  '/root/syslog/cron*':                          SYS_LOG_AGE,
    
  # specials
  '/root/exim':                                  'DIR-EMPTY',
  '/root/dnsmasq/dnsmasq.leases':                'NOT-FOUND:.9.',
  '/root/rcam/homesec1/{NEWEST}':                CAM_AGE,
  '/root/rcam/homesec2/{NEWEST}':                CAM_AGE,
}
