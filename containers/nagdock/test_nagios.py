#!/usr/bin/python3

import pytest, re, time, warnings
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

CMD_FILE = '/rw/dv/TMP/nagdock/_rw_dv_nagdock_var_nagios/rw/nagios.cmd'
LOG_FILE = '/rw/dv/TMP/nagdock/_rw_dv_nagdock_var_log_nagios/nagios.log'
STATUS_FILE = '/rw/dv/TMP/nagdock/_rw_dv_nagdock_var_nagios/status.dat'
MAX_UPDATE_DELAY = 20


def send_cmd(cmd, alt=True):
  now = str(int(time.time()))
  msg = '[%s] %s\n' % (now, cmd.replace('$NOW', now))
  D.emit(f'sending: {msg.strip()}')
  with open(CMD_FILE, 'a') as f: f.write(msg)
  time.sleep(1)


def parse_nagios(nagfile):
  conf = []
  with open(nagfile) as f: source = f.read()
  for line in source.splitlines():
      line = line.strip()
      matchID = re.match(r"(?:\s*define)?\s*(\w+)\s+{", line)
      matchAttr = re.match(r"\s*(\w+)(?:=|\s+)(.*)", line)
      matchEndID = re.match(r"\s*}", line)
      if len(line) == 0 or line[0] == '#':
          pass
      elif matchID:
          identifier = matchID.group(1)
          cur = [identifier, {}]
      elif matchAttr:
          attribute = matchAttr.group(1)
          value = matchAttr.group(2).strip()
          cur[1][attribute] = value
      elif matchEndID and cur:
          conf.append(cur)
          del cur
  return conf


def find_test(conf):
  for i in conf:
    if i[1].get('service_description') == 'test-service':
      return i


def status_expect(field, expected_status, conf=None):
  if not conf: conf = parse_nagios(STATUS_FILE)
  status = find_test(conf)
  assert status, 'unable to find test-service data'
  val = status[1].get(field)
  assert val == expected_status


# ---------- tests
      
def test_nagios(container_to_test):
    if D.check_env_for_prod_mode():
        warnings.warn('this test does not work in production mode; it requires the test-mode-only server and config')
        return

    # Check incoming assumptions
    conf = parse_nagios(STATUS_FILE)
    status_expect('active_checks_enabled', '0', conf)
    status_expect('has_been_checked', '0', conf)

    # Enable checking
    send_cmd('ENABLE_SVC_CHECK;host;test-service')
    send_cmd('SCHEDULE_FORCED_SVC_CHECK;host;test-service;$NOW')
    D.file_expect_within(MAX_UPDATE_DELAY, 'EXTERNAL COMMAND: ENABLE_SVC_CHECK;host;test-service', LOG_FILE)

    # check initial state of test server show its working
    D.file_expect('INITIAL HOST STATE: host;UP;HARD;', LOG_FILE)
    D.file_expect('INITIAL SERVICE STATE: host;test-service;OK;', LOG_FILE)

    # now disable health on the test service and make sure Nagios notices.
    D.web_expect('bad', server='localhost', path='/?v=bad', port=1234+container_to_test.port_shift)
    send_cmd('SCHEDULE_FORCED_SVC_CHECK;host;test-service;$NOW')
    D.file_expect_within(MAX_UPDATE_DELAY, 'SERVICE ALERT: host;test-service;CRITICAL;', LOG_FILE)

    # check the status file now shows the current state
    time.sleep(4)  # wait more than the status file update internval.
    conf = parse_nagios(STATUS_FILE)
    status_expect('active_checks_enabled', '1', conf)
    status_expect('has_been_checked', '1', conf)
    status_expect('current_state', '2', conf)


if __name__ == "__main__":
  main()
