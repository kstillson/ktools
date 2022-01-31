#!/usr/bin/python3

'''iptables syslog summarizer

This script takes a list of logfiles with iptables drop reports and
provides a count of the unique 5-tuples for each logged rule type.

This is useful for evaluating which packets are the "worst offeners"
(i.e. many instances) and which ones are really odd (perhaps needing
security attention).
'''

import argparse, os, sys


class Logline(object):
    def __init__(self):
        self.tracked_fields = ['type', 'PROTO', 'IN', 'OUT', 'SRC', 'DST', 'DPT']
        self.fields = {}

    def is_valid(self): return 'type' in self.fields

    @staticmethod
    def factory_from_text(line, high_port):
        item = Logline()
        item.fields = {}
        for i in line.split(' '):
            if 'log-' in i: item.fields['type'] = i
            elif '=' in i:
                k, v = i.split('=')
                if k in item.tracked_fields: item.fields[k] = v
        if high_port:
            if int(item.fields.get('DPT', 0)) > high_port: item.fields['DPT'] = 'high'
        return item if item.is_valid() else None

    def __str__(self):
        empty = 'xx'
        return '%20s %5s   %10s -> %10s   %-16.16s -> %-16.16s \t=> %s' % (
            self.fields.get('type', empty), self.fields.get('PROTO', empty), self.fields.get('IN', empty),  self.fields.get('OUT', empty),
            self.fields.get('SRC', empty),  self.fields.get('DST', empty),   self.fields.get('DPT', empty))


class Counter(object):
    def __init__(self): self.counter = {}

    def add(self, key):
        if not key in self.counter: self.counter[key] = 0
        self.counter[key] += 1


def opener(source_name):
    if source_name == '-': return sys.stdin
    elif os.path.isfile(source_name): return open(source_name)
    return None


def skip_until_token(f, token):
    if not token: return
    for line in f:
        if token in line: return


def parse_args(argv_list):
    ap = argparse.ArgumentParser(description='iptables log scanner')
    ap.add_argument('--high-port', '-p', default=20000, type=int,
                    help='Collapse all ports higher than this.  0 to disable.')
    ap.add_argument('--input', '-i', nargs='+', help='Input files to scan, or - for stdin',
                    default=['/var/log/iptables.log', '/root/j/logs/iptables.log'])
    ap.add_argument('--start', '-s', help='Ignore log entries in each file before this string')
    return ap.parse_args()


def generate_counter(inputs_list, start_token=None, high_port=0):
    counter = Counter()
    for source_name in inputs_list:
        source = opener(source_name)
        if not source: continue
        skip_until_token(source, start_token)
        for line in source:
            logitem = Logline.factory_from_text(line, high_port)
            if not logitem:
                print(f'skipping invalid input line: {line}')
            else:
                counter.add(str(logitem))
    return counter


def main(args):
    counter = generate_counter(args.input, args.start, args.high_port)
    prev_key_prefix = None
    for key in sorted(counter.counter):
        count = counter.counter[key]
        prefix = key[:20]
        if prev_key_prefix and prefix != prev_key_prefix: print('')
        prev_key_prefix = prefix
        print(f'{count:8}   {key}')
    

if __name__ == '__main__':
    sys.exit(main(parse_args(sys.argv[1:])))

