
import theading
import model

import kcore.common as C
import kcore.varz as V


# ---------- API presented to the view

def get_statusz_state():
  arm_state = model.partition_state_resolve_auto('default')
  touches = model.get_touches()
  return '%s/%s/%s' % (arm_state, 
                       touches[1].value if len(touches) > 1 else '?',
                       touches[0].value if len(touches) > 0 else '/')


def run_trigger(name, force_zone=None):
  '''returns (status text, tracking dict)'''
  V.bump('triggers')
  V.set('last_trigger', name)

  tracking = {}
  tracking['trigger'] = name
  tracking['force_zone'] = force_zone

  tracking['lookup_zone'], tracking['partition'], tracking['trigger_friendly'] = model.lookup_trigger(name)
  tracking['zone'] = force_zone or tracking['lookup_zone']

  # Check for too many hits from this trigger
  if squelch(tracking['trigger'], tracker['zone']): return 'squelched', tracking

  tracking['partition_start_state'] = model.partition_state(tracking['partition'])
  tracking['state'] = model.resolve_auto(tracking['partition_start_state'])

  # Look up the action from this trigger.
  tracking['action'], tracking['params'] = lookup_action(tracking['state'], tracking['partition'], tracking['zone'], tracking['trigger'])

  # Prep for statusz change detection
  statusz_before = get_statusz_state()

  # Perform requested action.
  err = take_action(tracking)

  # If statuz has changed, notify external tracking unit(s).
  statusz_after = get_statusz_state()
  if statusz_before != statusz_after:
    C.log('sending statusz update: ' + statusz_after)
    status = C.read_web('http://hs-mud:8080/update?' + statusz_after)
    if status != 'ok':
      C.log_error('error: unexpected status sending hs-mud update: %s' % status)

  # last action tracking
  if tracking['action'] and tracking['action'].find('touch') < 0 and tracking['zone'] != 'control': 
    model.touch(tracking['trigger'])

  V.set('last_action', tracking['action'])
  V.bump(f'action_{tracking['action']}')
  return err or 'ok', tracking


# ---------- support routines

def lookup_action(state, partition, zone, trigger):
  '''returns (action, params)'''
  action, param = model.lookup_trigger_rule(state, partition, zone, trigger)
  base.last_action = '%s(%s)' % (action, param)
  return action, param


def set_state(tracking, new_state, skip_actions=False):
  '''Change the current partitions state, and take any implied actions.'''
  C.log('partition %s : state %s -> %s' % (
    tracking['partition'], tracking['state'], new_state))
  if tracking['state'] == new_state: return
  leave_actions = model.get_state_rules(tracking['partition'], '0', tracking['state'])
  tracking['state'] = new_state
  model.set_partition_state(tracking['partition'], new_state)
  if skip_actions: return
  for i in leave_actions: take_action(tracking, i[0], i[1])
  enter_actions = model.get_state_rules(tracking['partition'], '1', new_state)
  for i in enter_actions: take_action(tracking, i[0], i[1])


def schedule_trigger(delay, then_trigger, then_force_zone=None):
  '''Schedule a trigger to run after a time-delay.'''
  C.log(f'delay {delay} then trigger {then_trigger}/{then_force_zone}')
  t = threading.Timer(delay, run_trigger, (then_trigger, then_force_zone)).start()


def squelch(trigger, zone):
  if zone not in ['chime', 'default', 'inside', 'outside']: return False
  last_run = model.last_trigger_touch(trigger)
  time_since = (datetime.datetime.now() - last_run).total_seconds()
  if time_since < model.SQUELCH_DURATION:
    C.log(f'squelched trigger {trigger}/{zone} (last used {time_since} seconds ago)')
    return True
  return False


def subst(tracking, input_string):
  if not input_string: return ''
  out = input_string.replace('%t', tracking['trigger'])
  out = out.replace('%f', tracking['trigger_friendly'])
  out = out.replace('%z', tracking['zone'])
  out = out.replace('%s', tracking['state'])
  out = out.replace('%u', '%s' % tracking['user'])
  out = out.replace('%p', tracking['partition'])
  out = out.replace('%a', tracking['action'])
  out = out.replace('%Ttouch', '%s' % model.TOUCH_WINDOW_SECS)
  out = out.replace('%Tarm', '%s' % model.ARM_AWAY_DELAY)
  out = out.replace('%Ttrig', '%s' % model.ALARM_TRIGGERED_DELAY)
  out = out.replace('%Talarm', '%s' % model.ALARM_DURATION)
  out = out.replace('%Tpanic', '%s' % model.PANIC_DURATION)
  return out


def take_action(tracking):
  '''Explicit actions called for my routing table.  Return error msg or None.'''
  
  action = tracking['action']
  params = subst(request, request['params'])
  C.log(f'Taking action {action}:{params} for {request}')
  
  if action == 'state':
    set_state(request, params)
    
  elif action == 'state-delay-trigger':
    new_state, delay, then_trigger = params.split(', ')
    if new_state != '-': set_state(request, new_state)
    schedule_trigger(delay, then_trigger)
    
  elif action == 'touch-home':
    user = request['user'] if params == 'x' else params
    # If touch-home after alarm triggered, reset the alarm state.
    if request['state'] == 'alarm-triggered':
      set_state(request, 'arm-auto', True)  # skip transition rules: no need to announce "auto arming mode by ..."
    if model.get_touch_status_for(user) == 'home':
      return ext.announce('%s is already home' % user)
    model.touch(user, 'home')
    # Announce welcome home.
    msg = 'welcome home %s' % user
    if user != 'ken': ext.push_notification(msg, 'info')
    if datetime.datetime.now().hour >= 18:
      ext.control('home', 'go')
    request['speak'] = msg
    ext.announce(msg)
    
  elif action == 'touch-away':
    user = request['user'] if params == 'x' else params
    if model.get_touch_status_for(user) == 'away':
      return ext.announce('%s is already away' % user)
    state_before = model.resolve_auto(request['partition_start_state'])
    model.touch(user, 'away')
    state_after = model.resolve_auto(request['partition_start_state'])
    if state_before != state_after:
      msg = 'homesec armed'
      request['speak'] = msg
      ext.announce(msg)
      if user != 'ken': ext.push_notification(msg, 'info')
      if datetime.datetime.now().hour >= 18:
        ext.control('away', 'go')
    else:
      request['speak'] = '%s is away' % user
      
  elif action == 'touch-away-delay':
    user, delay = params.split(', ')
    if user == 'x': user = request['user']
    if model.get_touch_status_for(user) == 'away':
      return ext.announce('%s is already away' % user)
    msg = 'goodbye %s' % user
    if model.touches_with_value('home') == 1:
      msg += ', system will arm in %s seconds' % delay
    ext.announce(msg)
    schedule_trigger(delay, '%s/touch-away' % user, request)
  elif action == 'pass':
    pass

  elif action == 'announce':
    ext.announce(params)
    msg = params
    if (params.startswith('#a')): level = 'alert'
    elif (params.startswith('!!')):
      level = 'alert'
      msg = params[2:]
    elif (params.startswith('#i')): level = 'info'
    else: level = 'other'
    if level != 'other':
      ext.push_notification(msg, level)
      
  elif action == 'control':
    unit, state = params.replace('+', ' ').replace('%20', ' ').split(', ')
    return ext.control(unit, state)

  elif action == 'control2':
    unit, state, delay, unit2, state2 = params.split(', ')
    err = ext.control(unit, state)
    schedule_trigger(delay, '%s, %s/control' % (unit2, state2))
    return err

  elif action == 'silent-panic':
    ext.silent_panic()
    
  elif action == 'httpget':
    C.log('httpget action returned: %s' % C.read_web(params))
    
  else:
    msg = 'Unknown action request: %s' % request
    C.log_error(msg)
    return msg
