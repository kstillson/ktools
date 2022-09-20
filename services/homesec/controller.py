
# see homesec.py for doc

import datetime, threading

import ext, model

import kcore.common as C
import kcore.varz as V


# ---------- API presented to the view

def get_statusz_state():
  arm_state = model.partition_state_resolve_auto('default')
  touches = model.get_touches()
  return '%s/%s/%s' % (arm_state,
                       touches[1].value if len(touches) > 1 else '?',
                       touches[0].value if len(touches) > 0 else '/')


def run_trigger(request_dict, name, trigger_param=None):
  '''returns (status text, tracking dict)'''
  V.bump('triggers')
  V.set('last_trigger', name)

  tracking = dict(request_dict)   # shallow copy; contains things like 'user'
  tracking['trigger'] = name
  tracking['trigger_param'] = trigger_param

  tl = model.lookup_trigger(name)
  tracking['partition'] = tl.partition if tl else 'default'
  tracking['trigger_friendly'] = tl.friendly_name if tl else None
  tracking['zone'] = tl.zone if tl else 'default'

  # Check for too many hits from this trigger
  if squelch(tracking['trigger'], tracking['zone']): return 'squelched', tracking

  tracking['partition_start_state'] = model.partition_state(tracking['partition'])
  tracking['state'] = model.resolve_auto(tracking['partition_start_state'])

  # Look up the action from this trigger.
  tracking['action'], tracking['params'] = lookup_action(tracking['state'], tracking['partition'], tracking['zone'], tracking['trigger'])

  # Prep for statusz change detection
  statusz_before = get_statusz_state()

  C.log(f'processing {tracking}')

  # Perform requested action.
  err = take_action(tracking, tracking['action'], tracking['params'])

  # If statuz has changed, notify external tracking unit(s).
  statusz_after = get_statusz_state()
  if statusz_before != statusz_after:
    C.log('sending statusz update: ' + statusz_after)
    status = ext.read_web('http://hs-mud:8080/update?' + statusz_after)
    if status != 'ok':
      C.log_error('error: unexpected status sending hs-mud update: %s' % status)

  # last action tracking
  if tracking['action'] and tracking['action'].find('touch') < 0 and tracking['zone'] != 'control':
    model.touch(tracking['trigger'])

  V.set('last_action', tracking['action'])
  V.bump(f'action_{tracking["action"]}')
  if err: return err, tracking
  return 'ok', tracking


# ---------- support routines

def lookup_action(state, partition, zone, trigger):
  '''returns (action, params)'''
  action, param = model.lookup_trigger_rule(state, partition, zone, trigger)
  if not action:
    action = 'pass'
    C.log_warning(f'no action found for {tracking}; defaulting to pass')
  V.set('last_action', '%s(%s)' % (action, param))
  return action, param


def set_state(tracking, new_state, skip_actions=False):
  '''Change the current partitions state, and take any implied actions.'''
  C.log('partition %s : state %s -> %s' % (
    tracking['partition'], tracking['state'], new_state))
  if tracking['partition_start_state'] == new_state: return
  leave_actions = model.get_state_rules(tracking['partition'], 'leave', tracking['state'])
  tracking['state'] = new_state
  model.set_partition_state(tracking['partition'], new_state)
  if skip_actions: return
  for i in leave_actions: take_action(tracking, i[0], i[1])
  enter_actions = model.get_state_rules(tracking['partition'], 'enter', new_state)
  for i in enter_actions: take_action(tracking, i[0], i[1])


def schedule_trigger(request_dict, delay, then_trigger, then_trigger_param=None):
  '''Schedule a trigger to run after a time-delay.'''
  C.log(f'delay {delay} then trigger {then_trigger}/{then_trigger_param}')
  t = threading.Timer(int(delay), function=run_trigger, args=(request_dict, then_trigger, then_trigger_param))
  t.daemon = True
  t.start()


def squelch(trigger, zone):
  t = model.lookup_trigger(trigger)
  if not t or not t.squelch_time: return False
  last_run = model.last_trigger_touch(trigger)
  time_since = model.now() - last_run
  if time_since < t.squelch_time:
    C.log(f'squelched trigger {trigger}/{zone} (last used {time_since} seconds ago)')
    return True
  return False


def subst(tracking, input_string):
  if not input_string: return ''
  out = input_string.replace('%t', tracking.get('trigger') or '?')
  out = out.replace('%a', tracking.get('action') or '?')
  out = out.replace('%f', tracking.get('trigger_friendly') or tracking.get('trigger') or '?')
  out = out.replace('%P', tracking.get('trigger_param') or '')
  out = out.replace('%p', tracking.get('partition') or '?')
  out = out.replace('%s', tracking.get('state') or '?')
  out = out.replace('%u', str(tracking.get('user') or '?'))
  out = out.replace('%z', tracking.get('zone') or '?')
  out = out.replace('%Ttouch', str(model.CONSTANTS['TOUCH_WINDOW_SECS']))
  out = out.replace('%Tarm',   str(model.CONSTANTS['ARM_AWAY_DELAY']))
  out = out.replace('%Ttrig',  str(model.CONSTANTS['ALARM_TRIGGERED_DELAY']))
  out = out.replace('%Talarm', str(model.CONSTANTS['ALARM_DURATION']))
  out = out.replace('%Tpanic', str(model.CONSTANTS['PANIC_DURATION']))
  return out


def take_action(tracking, action, params):
  '''Explicit actions called for by routing table.  Return error msg or None.'''
  params = subst(tracking, params)
  C.log(f'Taking {action=} {params=}')

  if action == 'state':
    if ':' in params:
      tracking['partition'], params = params.split(':', 1)
    if not tracking['partition']: tracking['partition'] = 'default'
    set_state(tracking, params)

  elif action == 'state-delay-trigger':
    new_state, delay, then_trigger = params.split(', ')
    if new_state != '-': set_state(tracking, new_state)
    schedule_trigger(tracking, delay, then_trigger)

  elif action == 'touch-home':
    user = params or tracking['user']
    # If touch-home after alarm triggered, reset the alarm state.
    if tracking['state'] == 'alarm-triggered':
      set_state(tracking, 'arm-auto', True)  # skip transition rules: no need to announce "auto arming mode by ..."
    if model.get_touch_status_for(user) == 'home':
      return ext.announce('%s is already home' % user)
    model.touch(user, 'home')
    # Announce welcome home.
    msg = 'welcome home %s' % user
    if user != 'ken': ext.push_notification(msg, 'info')
    if datetime.datetime.now().hour >= 18:
      ext.control('home', 'go')
    tracking['speak'] = msg
    ext.announce(msg)

  elif action == 'touch-away':
    user = params or tracking['user']
    if model.get_touch_status_for(user) == 'away':
      return ext.announce('%s is already away' % user)
    state_before = model.resolve_auto(tracking['partition_start_state'])
    model.touch(user, 'away')
    state_after = model.resolve_auto(tracking['partition_start_state'])
    if state_before != state_after:
      msg = 'homesec armed'
      tracking['speak'] = msg
      ext.announce(msg)
      if user != 'ken': ext.push_notification(msg, 'info')
      if datetime.datetime.now().hour >= 18:
        ext.control('away', 'go')
    else:
      tracking['speak'] = '%s is away' % user

  elif action == 'touch-away-delay':
    user, delay = params.split(', ')
    if not user or user == 'x': user = tracking['user']
    if model.get_touch_status_for(user) == 'away':
      return ext.announce('%s is already away' % user)
    msg = 'goodbye %s' % user
    if model.touches_with_value('home') == 1:
      msg += ', system will arm in %s seconds' % delay
    ext.announce(msg)
    schedule_trigger(tracking, delay, 'touch-away', user)

  elif action == 'pass':
    pass

  elif action == 'announce':
    ext.announce(params)
    msg = params
    if params.startswith('#a'): level = 'alert'
    elif params.startswith('!!'):
      level = 'alert'
      msg = params[2:]
    elif params.startswith('#i'): level = 'info'
    else: level = 'other'
    if level != 'other':
      ext.push_notification(msg, level)

  elif action == 'control':
    unit, state = params.replace('+', ' ').replace('%20', ' ').split(', ')
    return ext.control(unit, state)

  elif action == 'control2':
    unit, state, delay, unit2, state2 = params.split(', ')
    err = ext.control(unit, state)
    schedule_trigger(tracking, delay, 'control/%s:%s' % (unit2, state2))
    return err

  elif action == 'silent-panic':
    ext.silent_panic()

  elif action == 'httpget':
    C.log('httpget action returned: %s' % ext.read_web(params))

  elif action is None:
    msg = 'No matching action found for event: %s' % tracking
    C.log_warning(msg)
    return msg

  else:
    msg = 'Unknown action: %s' % tracking
    C.log_error(msg)
    return msg
