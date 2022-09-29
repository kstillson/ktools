
# see homesec.py for doc

import datetime, hashlib, os, time

import data


# ---------- getters

CONSTANTS = data.CONSTANTS


def get_all_touches():
  '''Return list of TouchData with last touch times for all triggers.'''
  touches = data.TOUCH_DATA.get_data().values()
  return sorted(touches, key=lambda x: x.last_update)


def get_friendly_touches():
  '''return list of TriggerLookup for all triggers with friendly names'''
  time_now = now()
  out = []
  for touch in get_all_touches():
    tl = lookup_trigger(touch.trigger)
    if not tl or not tl.friendly_name: continue
    touch.friendly_name = tl.friendly_name
    touch.tardy = (time_now - touch.last_update) > tl.tardy_time
    out.append(touch)
  return out


def get_state(partition='default'):
  '''return current partition state (as string) a partition'''
  return partition_state(partition)


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
  '''Return most recent touch 'value' (usually "home" or "away") for a trigger (generally a user).'''
  for touch in get_all_touches():
    if touch.trigger == username: return touch.value
  return None


def get_touches(search=['ken', 'dad']):
  '''Return list of TouchData for specified user list.'''
  touches = get_all_touches()
  return [x for x in touches if x.trigger in search]


def last_trigger_touch(trigger):
  '''Returns int epoch seconds of last touch for given trigger.'''
  for touch in get_all_touches():
    if touch.trigger == trigger: return touch.last_update
  return 0


def lookup_trigger(trigger_name):
  '''Returns first TriggerLookup that matches the given trigger_name.'''
  for t in data.TRIGGER_LOOKUPS:
    if t.re.match(trigger_name): return t
  return None


def lookup_trigger_rule(state, partition, zone, trigger):
  '''return (action, param) for the first-matching rule.'''
  for tr in data.TRIGGER_RULES:
    if ((tr.state == state or tr.state == '*') and
        (tr.partition == partition or tr.partition == '*') and
        (tr.zone == zone or tr.zone == '*') and
        (tr.trigger == trigger or tr.trigger == '*')):
      return tr.action, tr.params
  return None, None


def now(): return int(time.time())   # Epoch seconds as int.


def partition_state(partition):
  p = data.PARTITION_STATE.get_data().get(partition, None)
  return p.state if p else None


def partition_state_resolve_auto(partition):
  '''Return current state (as string) for a partition, but resolves auto to home or away.'''
  base_state = partition_state(partition)
  resolved_state = resolve_auto(base_state)
  if resolved_state != base_state:
    resolved_state = '%s(auto)' % resolved_state
  return resolved_state


def partition_states():
  '''Return a list of PartitionState for all partitions, but with state field resolved if it's arm-auto.'''
  answer = []
  for ps in data.PARTITION_STATE.get_data().values():
    new_state = resolve_auto(ps.state)
    if new_state != ps.state:
      ps.state = '%s(auto)' % new_state
    answer.append(ps)
  return answer


def resolve_auto(state):
  '''Resolve arm-auto to arm-home or arm-away based on how many people are home.'''
  if not 'auto' in state: return state
  twvh = touches_with_value('home')
  return 'arm-away' if twvh == 0 else 'arm-home'


# ---------- getters with authn internal logic

def check_user_password(username, password):
  hashed = hash_user_password(username, password)
  return data.USER_LOGINS.get(username) == hashed


def hash_user_password(username, password):
  salt = os.environ.get('SALT', os.environ.get('PUID', ''))
  plaintext = f'v2a:{username}:{password}:{salt}'.encode('utf-8')
  return hashlib.sha1(plaintext).hexdigest()


# ---------- setters

def set_partition_state(partition, new_state):
  with data.PARTITION_STATE.get_rw() as d:
    target = d.get(partition, None)
    if not target:
      # Not found, so create a new one.
      new_state.last_update = now()
      d[partition] = data.PartitionState(partition, new_state, now())
      return False

    target.state = new_state
    target.last_update = now()
    return True


def touch(trigger_name, value=''):
  '''Update a given trigger_name's last touch time to now.
     'value' is generally only used if the trigger is the name of a user, and
     the user's "at home" state is being updated to "home" or "away".  '''
  time_now = now()
  with data.TOUCH_DATA.get_rw() as d:
    target = d.get(trigger_name, None)
    if not target:
      # Not found, so create a new one.
      d[trigger_name] = data.TouchData(trigger_name, now(), value)
      return False

    target.last_update = time_now
    target.last_update_nice = data.nice_time(time_now)
    if value: target.value = value
    return True

  
def touches_with_value(value):
  '''Return a list of TouchData who's "value" field matches the specified query.
     Used, for example, to return a list of user's who are "home" or "away".  '''
  out = []
  for t in data.TOUCH_DATA.get_data().values():
    if t.value == value: out.append(t)
  return len(out)
