#!/usr/bin/python3
'''Nagios command-line tool: status summaries and update requests.

By default, this tool just lists all services and hosts with non-OK current status.
Given --html or --color, the output format is changed to be suitable for CGI script output.

The --retry flag will queue Nagios commands to immediately (within a few seconds) retry
all currently-failing hosts and services.  --retry-all triggers a complete rescan.

--ack will queue Nagios commands to acknowledge all current failures.
'''

import argparse, enum, os, subprocess, time
from collections import namedtuple


class StatusEnum(enum.Enum):
  OK = 0
  WARNING = 1
  CRITICAL = 2
  UNKNOWN = 3
  ACKED = -2
  FILTERED = -3

Status = namedtuple('Status', 'host, service, status_enum, status_dict')

ARGS = None


def eval_state(sect_dict, svc):
    s = int(sect_dict.get('current_state', '3'))
    if s == 2 and sect_dict.get('problem_has_been_acknowledged', '?') == '1':
        s = -2
    if s == 0 and sect_dict.get('has_been_checked', '?') == '0':
        s = 3  # pending...
    if s > 0:
        for f in ARGS.filter:
            if f in svc: s = -3
            if f in sect_dict.get('host_name', '?'): s = -3
    return StatusEnum(s)


def eval_overall_status(by_status):
    if len(by_status[StatusEnum.CRITICAL]) > 0:
        return 'Critical', 'red'
    if len(by_status[StatusEnum.WARNING]) > 0:
        return 'Warning(s)', 'yellow'
    if len(by_status[StatusEnum.UNKNOWN]) > 0:
        return 'Unknown', 'blue'
    if len(by_status[StatusEnum.ACKED]) > 0:
        return 'Acked', 'purple'
    return 'all ok', 'green'


def count_by_status(by_status):
    out = ''
    for status in StatusEnum:
        out += f'{status.name[0]}={len(by_status[status])}  '
    return out


def scan(status_file):
    '''returns a dict from StatusEnum to lists of Status instances with that status.'''
    by_status = {}
    for i in StatusEnum: by_status[i] = []

    # Occasionally we catch nagios mid-run and the status file doesn't exist for a moment.
    # Re-try a few times with short delays and if still can't find it, it an error.
    retries = 0
    while not os.path.isfile(status_file):
      retries += 1
      if retries > 6: raise RuntimeError(f'unable to open Nagios status file {status_file}.')
      time.sleep(0.5)
    
    section = '?'
    with open(status_file) as fil:
        for line in fil.readlines():
            # comment
            if line[0] == '#':
                pass

            # new section
            elif line[0].isalpha():
                section = line.split(' ')[0]
                sect_dict = {}

            # normal data
            elif '=' in line:
                k, v = line[1:].split('=', 1)
                sect_dict[k] = v.strip()

            # end of section
            elif line == '\n':
                if section == 'hoststatus':
                    svc = ''
                elif section == 'servicestatus': 
                    svc = sect_dict.get('service_description', '?')
                else:
                    # Don't know or care how to parse this section...
                    continue
                hostname = sect_dict.get('host_name', '?')
                if ('test' in svc or 'test' in hostname) and not ARGS.include_test:
                    continue
                if ARGS.fail_sim and (ARGS.fail_sim in svc or ARGS.fail_sim in hostname):
                    status_enum = StatusEnum.CRITICAL
                else:
                    status_enum = eval_state(sect_dict, svc)
                status = Status(hostname, svc, status_enum, sect_dict)
                by_status[status_enum].append(status)
    return by_status


def hosts_list(by_status):
    hosts = set()
    for i in by_status:
        for j in by_status[i]:
            hosts.add(j.host)
    return hosts


def get_now():
    return subprocess.check_output(['/bin/date', '+%s']).decode('utf-8').strip()


def gen_force_all_services_for_hosts(hosts_list):
    out = ''
    now = get_now()
    for host in hosts_list:
        out += f'[{now}] SCHEDULE_FORCED_HOST_SVC_CHECKS;{host};{now}\n'
    return out


CGI_HTML_PREAMBLE = 'Content-type: text/html\n\n<html>\n<head>\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
CGI_HTML_POSTAMBLE = '\n</body></html>\n'
def cgi_wrap_html(out): return CGI_HTML_PREAMBLE + out + CGI_HTML_POSTAMBLE

CGI_TEXT_PREAMBLE = 'Content-type: text\n\n'
CGI_TEXT_POSTAMBLE = ''
def cgi_wrap_text(out): return CGI_TEXT_PREAMBLE + out + CGI_TEXT_POSTAMBLE


def generate_html(by_status, the_list, counts_by_status):
    out, color = eval_overall_status(by_status)
    out += '<br/>\n'
    out += counts_by_status
    out += '\n<p><div style="width:100px;height:100px;background-color:%s"></div>\n<p>\n' % color
    for i in the_list:
        out += f'host:{i.host} service:{i.service} status:{i.status_enum.name}<br/>\n'
    return cgi_wrap_html(out)


def generate_color(by_status):
    _, color = eval_overall_status(by_status)
    return cgi_wrap_text(color)


def gen_ack_for_one_item(host, service):
    now = get_now()
    if not service:
      return f'[{now}] ACKNOWLEDGE_HOST_PROBLEM;{host};2;1;0;Admin;via nag cmd\n'
    else:
      return f'[{now}] ACKNOWLEDGE_SVC_PROBLEM;{host};{service};1;1;1;Admin;via nag cmd\n'


def gen_force_for_one_item(host, service):
    now = get_now()
    if not service:
      return f'[{now}] SCHEDULE_FORCED_HOST_CHECK;{host};{now}\n'
    else:
      return f'[{now}] SCHEDULE_FORCED_SVC_CHECK;{host};{service};{now}\n'


def run_list(the_list, ack=False):   # If !ack, then do retry.
    out = ''
    for i in the_list:
        if ack:
            out += gen_ack_for_one_item(i.host, i.service)
        else:
            out += gen_force_for_one_item(i.host, i.service)
    write_to_cmdfile(out)
    return f'wrote {len(the_list)} {"ack" if ack else "retry"} command(s).'


def write_to_cmdfile(out):
    if ARGS.test:
        print(f'TEST (would queue):\n{out}--\n')
        return
    with open(ARGS.cmd_file, 'w') as f:
        f.write(out)


def parse_args():
    ap = argparse.ArgumentParser(description='nagios status summarizer')
    ap.add_argument('--ack', '-A',      action='store_true', help='Ack all non-ok services.')
    ap.add_argument('--all', '-a',      action='store_true', help='Include all, not just currently not-ok (in either output report or retry commands)')
    ap.add_argument('--cmd_file', '-o', default='/rw/dv/nagdock/var_nagios/rw/nagios.cmd', help='Location of nagios command input pipe')
    ap.add_argument('--fail_sim', '-F', default=None, help='Simulate failure in matching host/services')
    ap.add_argument('--filter', '-f',   nargs='+', default=[], help='exclude from failures anything with names matching these substrings')
    ap.add_argument('--color',          action='store_true', help='Output just the color of the overall status block (suitable for a cgi-bin call)')
    ap.add_argument('--html',           action='store_true', help='Output html format (suitable for a cgi-bin call)')
    ap.add_argument('--include_test', '-T', action='store_true', help='Do not filter services contianing the word "test"')
    ap.add_argument('--just', '-j',     default=None, help='process only service(s) matching this string')
    ap.add_argument('--retry_all', '-R', action='store_true', help='Equivalent to --retry --all')
    ap.add_argument('--retry', '-r',    action='store_true', help='Queue all non-ok services for a retry')
    ap.add_argument('--status_file', '-i', default='/rw/dv/nagdock/var_nagios/status.dat', help='Location of nagios status file')
    ap.add_argument('--summary', '-s',  action='store_true', help='Just print a two-line overall summary')
    ap.add_argument('--test', '-t',     action='store_true', help='Output command updates to stdout, rather than to cmd_file')
    args = ap.parse_args()
    if args.retry_all:
        args.retry = True
        args.all = True
    return args


def main():
    global ARGS
    ARGS = parse_args()

    by_status = scan(ARGS.status_file)
    counts_by_status = count_by_status(by_status)

    if ARGS.summary:
        print(eval_overall_status(by_status)[0])
        print(counts_by_status)
        return

    # Create the list of things to display/process (all items if
    # --all used, otherwise all things not in status ok).
    the_list = []   # List of Status instances

    if ARGS.just:
        for i in by_status.values():
            for j in i:
                if j.service == ARGS.just: the_list.append(j)
    else:
        for status in StatusEnum:
            if status == StatusEnum.OK and not ARGS.all: continue
            the_list.extend(by_status[status])

    if ARGS.ack:
        out = run_list(the_list, ack=True)
        print(cgi_wrap_html(out) if ARGS.html else out)
        return

    if ARGS.retry:
        out = run_list(the_list, ack=False)
        print(cgi_wrap_html(out) if ARGS.html else out)
        return

    if ARGS.html:
        print(generate_html(by_status, the_list, counts_by_status))
        return

    if ARGS.color:
        print(generate_color(by_status))
        return
      
    # Default action is just to print status of each service.
    any_output = False
    for i in the_list:
        print('%-9s %-25s %s' % (i.status_enum.name, i.host, i.service))
        any_output = True
    if not any_output: print('all ok')


if __name__ == '__main__':
    main()
