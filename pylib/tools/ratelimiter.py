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

import os, sys, time
import kcore.common2 as C
import kcore.uncommon as UC

VERBOSE = False
WAIT_POLLING_INTERVAL = 0.5 # seconds


def build_instance(args):
    if args.init:
        rate, per = args.init.split(',')
        rl = UC.RateLimiter(float(rate), float(per))
        save_state(rl, args.statefile)

    elif args.limit and not os.path.isfile(args.statefile):
        rate, per = args.limit.split(',')
        rl = UC.RateLimiter(float(rate), float(per))
        save_state(rl, args.statefile)

    else:
        rl = UC.RateLimiter()
        with open(args.statefile) as f: s = f.read()
        rl.deserialize(s)

    return rl


def do_check(rl, statefile):
    with UC.FileLock(statefile):
        if VERBOSE: print(f'before: {str(rl)}')
        check = rl.check()
        if VERBOSE: print(f'after: {str(rl)}\nresult: {"ALLOW" if ok else "REJECT"}')
        save_state(rl, statefile)
        return check


def save_state(rl, statefile):
        with open(statefile, 'w') as f: f.write(rl.serialize())


def parse_args(argv):
    ap = C.argparse_epilog(description='stateful ratelimiter')
    ap.add_argument('--init', '-i', default=None, help='initialize state file with rate,per(seconds).  Overwrites any existing state file with new limit and cleared allowance')
    ap.add_argument('--cmd', '-c', default=None, help='if provided, run this command if rate limit allows (or run it after limit allows, if -w is also specified)')
    ap.add_argument('--limit', '-l', default=None, help='same as --init, but leaves an existing state file alone; only does anything if a new state file needs to be created.')
    ap.add_argument('--wait', '-w', action='store_true', help='if the limit is exceeded, rather than returning an error, just wait until back under the limit')
    ap.add_argument('--verbose', '-v', action='store_true', help='print state')
    ap.add_argument('statefile')
    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])

    global VERBOSE
    if args.verbose: VERBOSE = True

    rl = build_instance(args)
    check = do_check(rl, args.statefile)

    while not check and args.wait:
        time.sleep(WAIT_POLLING_INTERVAL)
        check = do_check(rl, args.statefile)

    if args.cmd: return os.system(args.cmd)

    return 0 if check else 1


if __name__ == '__main__':
    sys.exit(main())

