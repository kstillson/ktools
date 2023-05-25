#!/usr/bin/python3

'''Run commands in parallel, showing their real-time output in a dashboard.

By default, the list of commands to run is provided on stdin.
Alternatively, the "--ssh {cmd}" flag allows you to specify a list of hosts
on stdin and run {cmd} on all the hosts simultaneously.

Or, using the "--cmd {@cmd}" flag allows you to provide a list of values in
stdin that will be substituted into provided {@cmd}, replacing the "@"
character with each value.  (This is similar to Gnu "parallel" or "xargs -I@",
but adds the improved real-time dashboard, and tracks the output of each
command separately for cleaner post-run reporting.)

The dashboard continuously prints the most recent output line (from stdout
or stderr) as each command runs.  Use the "--output" flag to save full
output transcripts.

Running commands are identified by "job-id's" both in the dashboard and the
--output.  Id's are computed from the commands contents.  If downstream
systems are parsing the output, the details of id's can be important, so
controls are provided to customize them.

If the last word in each command is a suitable id, use the "--last" flag.
If an ideal id is embedded in a command, use '^^' to prefix the id.
(eg. "^^@" is often useful, see the scp example below).

Otherwise, the job id is forumlated from the commands by removing any
common prefixes and suffixes (and a few other common string patterns).

Some example uses:

Upgrade a bunch of hosts all at the same time:
$ echo 'host1 host2 host3' | run_para --output report.log --ssh 'apt-get -y upgrade'

Get a tidy report on root-disk free space for a bunch of hosts:
$ echo 'host1 host2 host3' | run_para --align --ssh "df -h | egrep ' /$'"

Copy a file to a bunch of remote hosts:
$ echo 'host1 host2 host3' | run_para --cmd 'scp file ^^@:/destdir'

'''

import argparse, os, multiprocessing, subprocess, sys, threading, time


# General constants
CLEAR_TO_EOL = '\033[K'
COLORS = {
  'blue':    '\033[1;34m',
  'green':   '\033[1;32m',
  'magenta': '\033[1;35m',
  'red':     '\033[1;31m',
  'reset':   '\033[1;0m',
  'white':   '\033[1;0m',
  'yellow':  '\033[1;33m',
}

# Global state tracking
ARGS = None       # Command line flags dict (from argparse)
CURRENT_WORK = {} # worker number -> job_id
DONE_JOBS = 0
DONE_WORKERS = 0
HOSTNAME = os.uname()[1]
LOG = {}          # job_id -> [entire output as list]
STATUSES = {}     # job_id -> exit status code (int)
UPDATES = {}      # job_id -> single-line most recent output, colorized


# Wrap msg in color escape codes and return it.
def colorize(color, msg): return f'{COLORS[color]}{msg}{COLORS["reset"]}'

# Move cursur up n rows.
# cursor movement: https://tldp.org/HOWTO/Bash-Prompt-HOWTO/x361.html
def cursor_up(n): print(f'\033[{n}A', file=sys.stderr)

# Save incoming data from stdout/stderr from a tracked process.
def update(job_id, color, text):
  text = text.strip()
  UPDATES[job_id] = colorize(color, text)
  prefix = 'STDERR: ' if color == 'red' else ''
  LOG[job_id].append(prefix + text)


# Thread that listens on a stream object and sends each line to the updater.
def stream_copier(stream, job_id, color):
  for line in stream:
    if not isinstance(line, str): line = line.decode('utf-8')
    update(job_id, color, line)
  stream.close()


# Launch specified command and attach stream_copier threads to stdout and stderr.
def runner(job_id, cmd, send_stdin=None):
  if ARGS.unbuffer: cmd = '/usr/bin/unbuffer ' + cmd
  p = subprocess.Popen(cmd, shell=True, executable='/bin/bash', bufsize=0,
                       stdin=subprocess.PIPE if send_stdin else None,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  status = p.poll()
  t1 = threading.Thread(target=stream_copier, args=(p.stdout, job_id, 'white'))
  t2 = threading.Thread(target=stream_copier, args=(p.stderr, job_id, 'red'))
  t1.start()
  t2.start()
  if send_stdin:
    p.stdin.write(send_stdin.encode())
    p.stdin.close()
    update(job_id, 'yellow', f'sent: {send_stdin}')
  try:
    status = p.wait(ARGS.timeout)
  except subprocess.TimeoutExpired:
    STATUSES[job_id] = -3  # timeout
    return update(job_id, 'blue', 'TIMEOUT')
  update(job_id, 'green' if status == 0 else 'red', f'exit: {status}  {UPDATES[job_id]}')
  STATUSES[job_id] = status
  t1.join()
  t2.join()


# Wrapper around runner() that takes a queue of assignments, and safely tracks counting upon completion.
# assignment_queue is a list of form [(job_id, cmd, stdin)]
def run_wrapper(worker_number, assignment_queue):
  global CURRENT_WORK, DONE_JOBS, DONE_WORKERS
  for job_id, cmd, stdin in assignment_queue:
    CURRENT_WORK[worker_number] = job_id
    runner(job_id, cmd, stdin)
    with threading.Lock(): DONE_JOBS += 1
  with threading.Lock(): DONE_WORKERS += 1


def common_prefix_and_suffix(input_list):
  if len(input_list) == 1: return []
  common_prefix = os.path.commonprefix(input_list)
  # If that last char in common_prefix is not a space, see if we can rewind to the previous space.
  if common_prefix and common_prefix[-1] != ' ':
    try:
      last_space = common_prefix.rindex(' ')
      common_prefix = common_prefix[0:(last_space + 1)]
    except ValueError: pass
  # Now find common suffix by reversing all strings and finding a common prefix.
  temp = []
  for i in input_list: temp.append(i[::-1])
  common_suffix = os.path.commonprefix(temp)[::-1]
  return [common_prefix, common_suffix]


def gen_id_real(cmd, rm_substrings):
  # If instructed, just use the final word in the cmd as the id.
  if ARGS.last:
    try:
      last_space = cmd.rindex(' ')
      return cmd[(last_space + 1):]
    except ValueError: pass
  # Check for the ^^ hint (indicates the next word is the id).
  pos = cmd.find('^^')
  if pos >= 0:
    end_pos = cmd.find(' ', pos)
    if end_pos < 0: end_pos = len(cmd) + 1
    return cmd[pos + 2:end_pos]
  # Otherwise remove common prefix/suffix's, and use what's left.
  for i in rm_substrings: cmd = cmd.replace(i, '')
  cmd = cmd[:30].strip()
  if not cmd: cmd = 'job'
  return cmd


# Wrapper around gen_id_real that handles duplicate outputs.
def gen_id(cmd, job_ids, rm_substrings):
  new_id = gen_id_real(cmd, rm_substrings)
  if not new_id in job_ids: return new_id
  x = 2
  while x < 100:
    id = f'{new_id}.{x}'
    if not id in job_ids: return id
    x += 1
  raise ValueError('too many identical commands')


def include_in_log(line):
  if not ARGS.plain: return True
  if 'Launch:' in line: return False
  if 'exit:' in line: return False
  return True


def process_stdin(main_stdin):
  sep = ARGS.sep
  if sep == 'auto':
    if len(main_stdin) == 1:
      if ',' in main_stdin[0]: sep = ','
      elif ' ' in main_stdin[0]: sep = ' '
      else: sep = None
    else: sep = None
  if sep:
    tmp = []
    for i in main_stdin: tmp.extend(i.split(sep))
    main_stdin = tmp
  main_stdin = list(map(str.strip, main_stdin))
  main_stdin = [i for i in main_stdin if i]  # Remove any empty elements.
  return main_stdin


# Convert the list from stdin into a list of commands-to-run,
# by taking into account --ssh, --cmd, --subst, and --timeout.
def generate_commands(main_stdin):
  commands = []
  if ARGS.cmd or ARGS.dry_run:
    for line in main_stdin:
      if ARGS.extension_rm:
        line = os.path.splitext(line)[0]
      commands.append(ARGS.cmd.replace(ARGS.subst, line))
  elif ARGS.ssh:
    for host in main_stdin:
      if host == HOSTNAME and ARGS.localhost:
        commands.append(ARGS.ssh.replace(ARGS.subst, host))
      else:
        cmd = f'ssh {host} '
        if ARGS.timeout: cmd += f'-o ConnectTimeout={ARGS.timeout} '
        cmd += '"' + ARGS.ssh.replace(ARGS.subst, host) + '"'
        commands.append(cmd)
  else:
    commands = main_stdin
  return commands


def get_term_width():
  try:
    with open('/dev/tty') as tty:
      rows_b, columns_b = subprocess.check_output(['stty', 'size'], stdin=tty).split()
      return int(columns_b)
  except OSError:   # non-interactive connection; let's guess.
    return 99


def generate_output(job_ids):
  if ARGS.align: ARGS.plain = True
  if ARGS.output == '@':
    for i, job_id in enumerate(job_ids):
      with open(f'out-{i}.log', 'w') as f:
        if not ARGS.plain: print(f'job id: {job_id}', file=f)
        for line in LOG[job_id]:
          if include_in_log(line): print(line, file=f)
    if not ARGS.quiet: print('\noutput transcripts saved to: out-*.log', file=sys.stderr)
  elif ARGS.align:
    if not ARGS.output: ARGS.output = '-'
    stdout = None if ARGS.output == '-' else open(ARGS.output, 'w')
    p = subprocess.Popen(['/usr/bin/column', '-t', '-s^'], stdin=subprocess.PIPE, stdout=stdout)
    out = ''
    for job_id in job_ids:
      for line in LOG[job_id]:
        if include_in_log(line): out += f'{job_id}^{line}\n'
    p.communicate(out.encode('utf-8'))
    if stdout:
      stdout.close()
      if not ARGS.quiet: print(f'\noutput transcript saved to: {ARGS.output}', file=sys.stderr)
  elif ARGS.output:
    outfile = '/dev/stdout' if ARGS.output == '-' else ARGS.output
    with open(outfile, 'w') as f:
      for job_id in job_ids:
        if not ARGS.plain: print(colorize('yellow', f'\n{job_id}:\n'), file=f)
        for line in LOG[job_id]:
          if ARGS.plain:
            out = f'{job_id}: {line}'
          else:
            out = line if not 'STDERR' in line else colorize('red', 'STDERR: ') + line[9:]
          if include_in_log(line): print(out, file=f)
    if ARGS.output != '-' and not ARGS.quiet: print(f'\noutput transcript saved to: {ARGS.output}', file=sys.stderr)


# Scan my own source code and return the leading file comment as a string.
def get_file_comment():
  out = ''
  started = False
  with open(__file__) as f:
    for line in f:
      if started:
        if line.startswith("'''"): return out
        out += line
      elif line.startswith("'''"):
        out += line[3:]
        started = True
  # If we get to here, something went wrong, return nothing.
  return ''

def parse_args(argv):
  parser = argparse.ArgumentParser(description='run commands (from stdin) in parallel', epilog=get_file_comment(), formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--align', '-a', action='store_true', help='In addition to --plain, align the outupt into a nice table')
  parser.add_argument('--cmd', '-c', default=None, help='Rather the reading complete commands from stdin, create commands to run from this param value, substituting each line in stdin for the "@" char specified in this command.')
  parser.add_argument('--cycle_time', '-C', type=float, default=0.2, help='time between updates')
  parser.add_argument('--debug', '-d', action='store_true', help='print debugging internals during run')
  parser.add_argument('--extension_rm', '-e', action='store_true', help='strip the filename extension from each input instance during substitution (--cmd mode only)')
  parser.add_argument('--last', action='store_true', help='when converting commands to job_ids, just take the last word in the command')
  parser.add_argument('--dry_run', '-n', action='store_true', help='(list-processor) modifies --cmd: just output the substituted command list, rather than running them.')
  parser.add_argument('--localhost', '-L', action='store_false', help='DONT detect localhost (which would normally run commands directly rather than via ssh) in list of hosts for --ssh.')
  parser.add_argument('--max_para', '-m', type=int, default=multiprocessing.cpu_count(), help='max number of things to do concurrently')
  parser.add_argument('--output', '-o', default=None, help='name of file to send full output log to (blank to disable, "-" for stdout, "@" to create separate logfile for each)')
  parser.add_argument('--plain', '-p', action='store_true', help='in log output, just include simple stdout, nothing else.')
  parser.add_argument('--quiet', '-q', action='store_true', help='dont print things like overall status')
  parser.add_argument('--sep', default='auto', help='Use this character to separate values from stdin (rather than newline) (e.g. space or comma).  If "auto", attempt autodetect separator if stdin is a single line')
  parser.add_argument('--ssh', default=None, help='Rather than reading complete commands from stdin, stdin is a list of hostnames and the command specified in this flag value will be run on each of them (in parallel)')
  parser.add_argument('--stdin_file', '-s', default=None, help='filename of contents to send to each job stdin')
  parser.add_argument('--strip', '-S', action='store_false', default=True, help='(dont) strip common prefix and suffix in commands when forming job names?')
  parser.add_argument('--subst', default='@', help='Use this substring (rather then "@") for substitution in the --cmd and --ssh flags.')
  parser.add_argument('--timeout', '-t', type=int, default=None, help='remote command timeout in seconds')
  parser.add_argument('--unbuffer', '-u', action='store_true', help='wrap commands in /usr/bin/unbuffer to force continuous outputs (unbuffer is often provided by the "expect" package)')
  return parser.parse_args(argv)


def main(argv=[], stdin_list=[]):
  args = parse_args(argv or sys.argv[1:])
  if not stdin_list: stdin_list = sys.stdin.readlines()

  global ARGS, DONE_JOBS, DONE_WORKERS, UPDATES
  ARGS = args
  if ARGS.debug: print(f'DEBUG: commandline={sys.argv}', file=sys.stderr)

  # Stdin scan, clean-up, and convert to list.
  main_stdin = process_stdin(stdin_list)
  if ARGS.debug: print(f'DEBUG: main_stdin={main_stdin}', file=sys.stderr)

  # Generate list of commands to run.
  commands = generate_commands(main_stdin)
  if ARGS.debug: print(f'DEBUG: commands={commands}', file=sys.stderr)

  if ARGS.dry_run:
    print('\n'.join(commands))
    return 0

  # Calculate the substrings to remove from commands when generating job id's.
  common_bits = common_prefix_and_suffix(commands) if ARGS.strip else []
  # These aren't always found as a prefix/suffix in all commands because of the
  # ARGS.localhost change (above), so include these as substrings to trim, even
  # if not a prefix/suffix for *all* the commands.
  common_bits.extend(['ssh ', f'-o ConnectTimeout={ARGS.timeout}', 'bash -c'])
  if ARGS.debug: print(f'DEBUG: common bits={common_bits}', file=sys.stderr)

  # Get text to send to all tasks's stdin.
  stdin = None
  if ARGS.stdin_file:
    with open(ARGS.stdin_file) as f:
      stdin = f.read()
  if ARGS.debug and stdin and len(stdin<100): print(f'DEBUG: stdin={stdin}', file=sys.stderr)

  # Get our terminal's width (for update max length).
  columns = get_term_width()
  if ARGS.debug: print(f'DEBUG: columns={columns}', file=sys.stderr)

  # Generate job-ids for each task and assign to workers.
  job_ids = []
  num_jobs = len(commands)
  num_workers = min(num_jobs, ARGS.max_para)
  assignment_queues = [ [] for _ in range(num_workers) ]
  for i, cmd in enumerate(commands):
    worker = i % num_workers
    job_id = gen_id(cmd, job_ids, common_bits)
    cmd = cmd.replace('^^', '')  # Strip job-id hint if provided, now that its used.
    assignment = (job_id, cmd, stdin)
    assignment_queues[worker].append(assignment)
    # Update per-job-id tracking.
    job_ids.append(job_id)
    STATUSES[job_id] = -1
    LOG[job_id] = [f'Launch: {cmd}']
    UPDATES[job_id] = 'waiting...'
  if ARGS.debug: print(f'DEBUG: #jobs={num_jobs}, #workers={num_workers}, assignments={assignment_queues}', file=sys.stderr)

  # Create and start the workers.
  print('Running...', file=sys.stderr)
  threads = []
  for worker_number, assignment in enumerate(assignment_queues):
    t = threading.Thread(target=run_wrapper, args=(worker_number, assignment))
    threads.append(t)
    t.daemon = True
    print('worker init...', file=sys.stderr)
    t.start()

  # Update cycle
  job_ids = sorted(job_ids)
  status = -4  # unknown
  try:
    while DONE_WORKERS < num_workers:
      time.sleep(ARGS.cycle_time)
      cursor_up(num_workers + 2)
      print(f'Running {num_workers - DONE_WORKERS} workers on remaining {num_jobs - DONE_JOBS} tasks       ', file=sys.stderr)
      for worker_number in range(num_workers):
        job_id = CURRENT_WORK[worker_number]
        max_len = columns - (len(job_id) + 4)
        print(f'{CLEAR_TO_EOL}{job_id}: {UPDATES[job_id][:max_len]}', file=sys.stderr)
    # All workers done; compute combined status.
    for t in threads: t.join()
    status = 0   # all ok
    for job_id in job_ids:
      if STATUSES[job_id] > 0: status = -1  # failure(s)
      if STATUSES[job_id] == -1 and status == 0: status = -4  # unknown
      if STATUSES[job_id] == -3 and status == 0: status = -3  # timeout(s)
  except KeyboardInterrupt:
    print('aborting...', file=sys.stderr)
    status = -2  # aborted
  if ARGS.debug: print(f'DEBUG: combined exit status={status}', file=sys.stderr)

  # Generate output transcript logs, if requested.
  print('', file=sys.stderr)
  generate_output(job_ids)

  # Overall status summary
  if not ARGS.quiet:
    overall = colorize('green', 'ok') if status == 0 else colorize('red','failures') if status == -1 else colorize('magenta', 'aborted') if status == -2 else colorize('blue', 'timeouts') if status == -3 else status
    print(f'\noverall status: {overall}\n', file=sys.stderr)
  return status


if __name__ == '__main__':
  sys.exit(main())
