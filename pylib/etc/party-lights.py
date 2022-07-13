#!/usr/bin/python3

'''Trivial slow color animation sequence for TP-Link smart bulbs.

This code sends color setting commands to 4 TP-Link color changing bulbs I've
got around my living room.  The idea is that the bulbs change between randomly
selected (although always high-saturation) colors at randomly selected
(although generally too-slow-to-see-unless-you-watch-carefully) intervals.

It's a decent example of what you can do with ./tplink.py, and who-knows,
might provide some inspiration for some other fun lightshows...

'''

import argparse, atexit, os, random, signal, subprocess, sys, threading, time
import tplink

LIGHTS = [ 'tp-color-sofa-left', 'tp-color-stairs', 'tp-color-sofa-right', 'tp-color-moon' ]


def bulb_set(target, command):
    resp = tplink.control(target, command)


def set_random_color(target):
    hue = random.randrange(255)
    delay = random.randrange(ARGS.min, ARGS.max)
    cmd0 = 'color'
    if ARGS.dim: cmd0 += '-dim'
    if not ARGS.fast: cmd0 += '-slow'
    if ARGS.debug: print('%s: %s hue %d, then sleep %d' % (target, cmd0, hue, delay))
    bulb_set(target, '%s:%d' % (cmd0, hue))
    time.sleep(delay)


def run_show(target):
    while True:
        set_random_color(target)


def all_off():
    for i in LIGHTS: bulb_set(i, 'bulb-off')


def cgi_wrap(out):
    html_preamble = '<html>\n<head>\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
    html_postamble = '\n</body></html>\n'
    cgi_preamble = 'Content-type: text/html\nContent-Length: %d\n\n' % (len(html_preamble) + len(out) + len(html_postamble))
    print(cgi_preamble + html_preamble + out + html_postamble)


def args():
    ap = argparse.ArgumentParser(description='nagios status summarizer')
    ap.add_argument('--cgi', action='store_true', help='Output suitable for being called as a CGI')
    ap.add_argument('--debug', '-d', action='store_true', help='Print actions as taken')
    ap.add_argument('--dim', '-D', action='store_true', help='Use lower light level')
    ap.add_argument('--fast', '-f', action='store_true', help='Use fast dim rate')
    ap.add_argument('--fg', action='store_true', help='(intended for internal use only) overrides the --on flag')
    ap.add_argument('--min', '-m', type=int, default=10, help='Min seconds between transitions')
    ap.add_argument('--max', '-M', type=int, default=300, help='Max seconds between transitions')
    ap.add_argument('--off', '-0', action='store_true', help='Stop background party mode')
    ap.add_argument('--on', '-1', action='store_true', help='Launch party in background and exit')
    ap.add_argument('--zero', '-z', action='store_true', help='Just turn everything off')
    return ap.parse_args()


def main():
    global ARGS
    ARGS = args()

    # Alternate primary modes
    if ARGS.zero: return all_off()

    if ARGS.off:
        all_off()
        if ARGS.cgi: cgi_wrap('party cancelled.')
        pids = list(map(int, subprocess.check_output(['pgrep', os.path.basename(__file__)]).split()))
        for pid in pids:
            if pid != os.getpid(): os.kill(pid, signal.SIGKILL)
        return

    if ARGS.on and not ARGS.fg:
        args2 = sys.argv
        args2.append('--fg')
        subprocess.Popen(args2)
        if ARGS.cgi: cgi_wrap('party on, dude!')
        return

    # Primary party mode
    atexit.register(all_off)

    random.seed()
    threads = []
    for i in LIGHTS:
        t = threading.Thread(target=run_show, args=(i, ))
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        for t in threads: t.join()

    except KeyboardInterrupt:
        if ARGS.debug: print('bye...')


if __name__ == '__main__':
    main()
