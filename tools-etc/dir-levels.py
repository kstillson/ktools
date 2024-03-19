#!/usr/bin/python3

'''run a command on each directory level of a path'''

import os, sys
import kcore.common as C


def parse_args(argv):
    ap = C.argparse_epilog(description='otp generator')
    ap.add_argument('--cwd', '-c',       action='store_true',  help='stop at current working directory')
    ap.add_argument('--errors_ok', '-e', action='store_true',  help='do not stop if any errors occur')
    ap.add_argument('--levels', '-l',    default=0, type=int,  help='stop after this many levels')
    ap.add_argument('--logfile',         default='-',          help='logfile for output messages')
    ap.add_argument('--stop', '-s',      default='',           help='stop at this dir')
    ap.add_argument('--verbose', '-v',   action='store_true',  help='print info as running')
    ap.add_argument('start', nargs='?',  default='.',          help='substring of autokey to search for')
    ap.add_argument('cmd',   nargs='*',  default=['echo','@'], help='command to run, use "@" as substution char for current dir')
    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])
    C.init_log('dirlevels', os.path.realpath(args.logfile),
               filter_level_stdout=C.INFO if args.verbose else C.ERROR)

    start = os.path.realpath(args.start)
    if not os.path.isdir(start):
        start = os.path.dirname(start)
        C.log(f'changed non-directory starting point ({args.start}) to parent dir: {start}')

    cwd = start
    count = 0
    stop2 = os.getcwd() if args.cwd else None
    
    while True:
        os.chdir(cwd)

        cmd = [i.replace('@', cwd) for i in args.cmd]
        C.log(f'{cwd}: {cmd}')

        count += 1
        out = C.popen(cmd, passthrough=True)
        if not out.ok: C.log_error(f'{C.c("ERROR:", "red")} [cwd={cwd}] command failed: {cmd}')

        # Evaluate possible stopping conditions
        if not out.ok and not args.errors_ok: return False
        if args.levels > 0 and count >= args.levels: return C.log(f'Stopping at {args.levels} levels.')
        if cwd == args.stop: return C.log(f'Stopping at {args.levels} levels.')
        if cwd == stop2: return C.log('Stopping at original cwd {stop2}.')
        if cwd == '/': return C.log('Stopping at root dir.')

        cwd = os.path.dirname(cwd)
        
    
if __name__ == '__main__': sys.exit(0 if main() else -1)
