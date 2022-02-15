
import sys

LOGFILE_NAME = 'circpysim.log'
LOGFILE = None

# Log messages of this level and lower.
LOG_FILTER = 2

# Show messages of this level and lower.
LOG_SHOW = 1

def log(msg, level=1):
    global LOGFILE
    if level <= LOG_FILTER:
        if not LOGFILE: LOGFILE = open(LOGFILE_NAME, 'a')
        LOGFILE.write('%s\n' % msg)
    if level <= LOG_SHOW:
        sys.stderr.write('>>circpysim log: %s\n' % msg)

