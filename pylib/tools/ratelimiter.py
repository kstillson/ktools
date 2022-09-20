#!/usr/bin/python3

'''Run, don't run, or pause a command so as to obey rate limits.

First, decide on the desired limit and initialize the state file:
 ratelimiter -i 1,10 statefile.rl    # allow 1 invocations per 10 seconds.

Then there are several ways to invoke the actual limit:

Exit from a shell script if over limit:
  ratelimiter statefile.rl || { echo 'ratelimited'; exit 1; }
  { take rate-limited action }

Wait until the limit let's the next command through:
  ratelimiter -w statefile.rl
  { take rate-limited action }

Skip a particular command if limit exceeded (but resume rest of script):
 ratelimiter statefile.rl && { take rate-limited action; }
   or, alternatively:
 ratelimiter -z -c "{ rate limited command }" statefile.rl
   (note: when using -c, the exit status of the run command is lost.)

Note that script needs r+w access to statefile.rl and statefile.rl.lock
So either give it write access to the directory or pre-create the lock
file with r+w access.  The lock file remains.
'''

import fcntl, os, pickle, sys, time
import kcore.uncommon as UC


# Class for ensuring that all file operations are atomic, treat
# initialization like a standard call to 'open' that happens to be atomic.
# This file opener *must* be used in a "with" block.
class AtomicOpen:
    def __init__(self, path, *args, **kwargs):
        self.file = open(path, *args, **kwargs)
        fcntl.lockf(self.file, fcntl.LOCK_EX)

    # Return the opened file object (knowing a lock has been obtained).
    def __enter__(self, *args, **kwargs): return self.file

    # Unlock the file and close the file object.
    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        self.file.flush()
        os.fsync(self.file.fileno())
        fcntl.lockf(self.file, fcntl.LOCK_UN)
        self.file.close()
        if (exc_type != None): return False
        else:                  return True


class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()

    def __str__(self):
        return 'rate:%f  per:%f  allowance:%f  last_check:%f' % (self.rate, self.per, self.allowance, self.last_check)

    def check(self):
        current = time.time();
        time_passed = current - self.last_check;
        self.last_check = current;
        self.allowance += time_passed * (self.rate / self.per);
        if self.allowance > self.rate:
            self.allowance = self.rate  # throttle
        if self.allowance < 1.0:
            return False
        else:
            self.allowance -= 1.0
            return True
        

def do_check(args):
    lockfile = '%s.lock' % args.statefile
    with AtomicOpen(lockfile, 'w') as lock:
        with open(args.statefile, 'rb') as f:
            rl = pickle.load(f)
        if args.verbose: print('before: %s' % rl)
        ok = rl.check()
        if args.verbose: print('after: %s\nresult: %s' % (rl, 'ALLOW' if ok else 'REJECT'))
        with AtomicOpen(args.statefile, 'wb') as f2:
            pickle.dump(rl, f2)
    return ok


def parse_args(argv):
    ap = UC.argparse_epilog(description='stateful ratelimiter')
    ap.add_argument('--init', '-i', default=None, help='initialize state file with rate,per(seconds)')
    ap.add_argument('--cmd', '-c', default=None, help='if provided, run this command if rate limit allows (or run it after delay if -w used)')
    ap.add_argument('--wait', '-w', type=float, default=0.0, help='if limit exceeded, rather than error exit, wait this many seconds (in a loop) and try again')
    ap.add_argument('--verbose', '-v', action='store_true', help='print state')
    ap.add_argument('--zap', '-z', action='store_true', help='if true, exit without error (and without running -c) if ratelimit hit')
    ap.add_argument('statefile')
    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])
    
    if args.init:
        rate, per = args.init.split(',')
        rl = RateLimiter(float(rate), float(per))
        with AtomicOpen(args.statefile, 'wb') as f:
            pickle.dump(rl, f)
        print('initialized to max %s per %s seconds.' % (rate, per))
        return 0

    while True:
        ok = do_check(args)
        if ok: 
            if args.cmd: os.system(args.cmd)
            return 0
        # Not ok.
        if not args.wait: 
            return 0 if args.zap else 1
        time.sleep(args.wait)
        # Continue looping...


if __name__ == '__main__':
    sys.exit(main())

