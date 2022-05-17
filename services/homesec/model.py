
import datetime, time

import data

# ---------- copy over simple constants from the data module.

ALARM_DURATION = data.ALARM_DURATION
ALARM_TRIGGERED_DELAY = data.ALARM_TRIGGERED_DELAY
ARM_AWAY_DELAY = data.ARM_AWAY_DELAY
PANIC_DURATION = data.PANIC_DURATION
SQUELCH_DURATION = data.SQUELCH_DURATION
TARDY_SECS = data.TARDY_DAYS
TOUCH_WINDOW_SECS = data.TOUCH_WINDOW_SECS


# ---------- getters

def get_all_touches():
  touches = data.get_touch_data()
  return touches.sort(key=lambda x: x.last_update)


def get_friendly_touches():
  '''touches where the friendly name is different than the trigger name are ones where we expect regularly touches or else the trigger is "tardy".'''
  out = []
  for touch in get_all_touches():
    zone, partition, friendly = lookup_trigger(touch.trigger)
    if not friendly or friendly == touch.trigger: continue
    touch.friendly = friendly
    out.append(touch)
  return out.sort(key=lambda x: x.last_update)


def get_state_rules(partition, transition, state):
  '''returns list of (action, params) pairs.  transition is 'enter' or 'leave'.'''
  answer = []
  for sr in data.STATE_RULES:
    if ((sr.partition == partition or sr.partition == '*') and
        (sr.state == state or sr.state == '*') and
        (sr.transition == transition or sr.transition == '*')):
      answer.append([sr.action, sr.params])
  return answer


def get_touch_status_for(username):
  return last_trigger_touch(username)


def get_touches():
  touches = get_all_touches()
  return [x for x in touches if x.trigger in ['ken', 'dad']]


def last_trigger_touch(trigger):
  '''Returns int epoch seconds.'''
  for touch in get_all_touches():
    if touch.trigger == trigger: return touch.last_update
  return None


def lookup_trigger(trigger_name):
  for t in data.TRIGGER_LOOKUPS:
    if t.re.match(trigger_name): return t
  return None


def lookup_trigger_rule(state, partition, zone, trigger):
  '''return (action, param) for the lowest priority matching rule.'''
  for tr in data.TRIGGER_RULES:
    if ((tr.state == state or tr.state == '*') and
        (tr.partition == partition or tr.partition == '*') and
        (tr.zone == zone or tr.zone == '*') and
        (tr.trigger = trigger or tr.trigger == '*')):
      return tr.action, tr.param
  return None, None


def now(): return int(time.time())


def partition_state(partition):
  for ps in data.get_partition_state_data():
    if ps.partition == partition: return ps.state
  return None


def partition_state_resolve_auto(partition):
  base_state = partition_state(partition)
  resolved_state = resolve_auto(base_state)
  if resolved_state != base_state:
    resolved_state = '%s(auto)' % resolved_state
  return resolved_state


def partition_states():
  answer = []
  for ps in data.get_partition_state_data():
    new_state = resolve_auto(ps.state)
    if new_state != ps.state:
      ps.state = '%s(auto)' % new_state
    answer.append(ps)
  return answer


def resolve_auto(state):
  if state != 'arm-auto': return state
  return 'arm-away' if touches_with_value('home') == 0 else 'arm-home'


# ---------- setters

def set_partition_state(partition, new_state):
  with data.saved_list(data.PARTITION_STATE_FILENAME, data.PartitionState) as pdata:
    for ps in pdata:
      if ps.partition == partition:
        ps.state = new_state
        ps.last_update = now()
        return True
    # Not found, so make a new one.
    pdata.append(data.PartitionState(partition, new_state, now()))
    return False


def touch(name, value=""):
  with data.saved_list(data.TOUCH_DATA_FILENAME, data.TouchData) as tdata:
    for t in tdata:
      if t.trigger == name:
        t.last_update = now()
        t.value = value
        return True
    # Not found, so make a new one.
    tdata.append(data.TouchData(name, now(), value))

  
def touches_with_value(value):
  out = []
  for t in data.get_touch_data():
    if t.value == value: out.append(t)
  return out

