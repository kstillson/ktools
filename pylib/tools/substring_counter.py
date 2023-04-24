#!/usr/bin/python3
'''Replace lines matching a list of substrings with counts (per substring).

For example:

find /usr -type f -print | substring_counter.py -d: -s'$PATH' -f -r | column -t

Indicates how many files there are in each directory on your path under /usr,
sorted by the number of files per directory (decending).

'''

import sys
import kcore.common as C


def parse_args(argv=sys.argv[1:]):
  ap = C.argparse_epilog()
  ap.add_argument('--delim',    '-d', default=',',         help='character separating different substrings in --strings')
  ap.add_argument('--errout',   '-e', action='store_true', help='output counts to stderr rather than stdout')
  ap.add_argument('--filter',   '-f', action='store_true', help='remove lines not matching one of the substrings')
  ap.add_argument('--revcounts','-r', action='store_true', help='sort output by counts (decreasing) rather in original order')
  ap.add_argument('--strings',  '-s',                      help='list of substrings (separated by --delim) to search for.  Supports file:X to read strings (1 per line) from file X.')
  ap.add_argument('--zeros',    '-z', action='store_true', help='print substrings with zero counts as well')
  return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args()
    strings = C.resolve_special_arg(args, 'strings').strip().replace('\n', args.delim).split(args.delim)
    counts = { k:0 for k in strings }

    # Counting & filtering phase.
    for line in sys.stdin:
        for s in strings:
            if s in line:
                counts[s] += 1
                break
        else:  # special for..else form; runs if the for loop completed without hitting a break.
            if not args.filter: print(line.strip())

    # Output phase.
    outfile = sys.stderr if args.errout else sys.stdout
    ordered_keys = sorted(strings, key=lambda x: -counts[x]) if args.revcounts else strings
    for key in ordered_keys:
        if counts[key] > 0 or args.zeros:
            print(f'{key}: {counts[key]}', file=outfile)


if __name__ == '__main__':
    sys.exit(main())
