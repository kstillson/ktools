#!/usr/bin/python3

'''Wait until an offset before or after sunset.

Requires: python3-ephem

For example, to use cron (which doesn't support dynamically timed events) to
turn on some lights half-an-hour before sunset:

0 16 * * *   nobody     sunsetter -o -30 && turn-on-the-lights

Thanks to mfreeborn and the 'heliocron' project for the inspiration.
(https://github.com/mfreeborn/heliocron). But I've had nothing but frustration
with Rust (eternal problems of deep dependencies being incompatible with other
deep dependencies), so figured I'd generate a minimal re-implementation of
what I need in Python, and which has only one very-easy dependency: ephem.

'''

import argparse, datetime, ephem, sys, time
from datetime import timedelta


def parse_args(argv):
  ap = argparse.ArgumentParser(description='wait until sunset (or an offset in minutes from sunset)')
  ap.add_argument('--lat',           default='38.9072',  help='Latitude for sunset calculation')
  ap.add_argument('--long',          default='-77.0369', help='Longitude for sunset calculation')
  ap.add_argument('--offset',  '-o', default=0, type=int, help='Offset in minutes from sunset for target date; can be negative.')
  ap.add_argument('--print',   '-p', action='store_true', help='Just print sunset time and exit')
  ap.add_argument('--verbose', '-v', action='store_true', help='Print calculations before starting the wait')
  return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])
    
    ob = ephem.Observer()
    ob.lat = args.lat
    ob.long = args.long
    sun = ephem.Sun()
    sun.compute()

    sunset_dt = eval(repr(ephem.localtime(ob.next_setting(sun))))
    
    delta = timedelta(minutes=args.offset)
    target_dt = sunset_dt + delta

    if args.print:
        print(target_dt.strftime("%c"))
        return 0

    now = datetime.datetime.now()
    seconds_to_wait = (target_dt - now).seconds
    mins_to_wait = int(seconds_to_wait / 60)

    if args.verbose:
        nl = '\n'
        print(f'Time now: {now.strftime("%c")}{nl}Sunset:   {sunset_dt.strftime("%c")}{nl}Target:   {target_dt.strftime("%c")}{nl}Time to wait: {mins_to_wait} minutes')

    time.sleep(seconds_to_wait)
    return 0


if __name__ == '__main__':
    sys.exit(main())
