
'''Data contents and low-level processing for the homesec system.

see homesec.py for doc.

'''

import datetime, re
from contextlib import contextmanager
from dataclasses import dataclass

import kcore.common as C
import kcore.persister as P
import kcore.uncommon as UC


# ---------- helpers

def nice_time(epoch_seconds=None):
  '''Convert epoch seconds into user-readable date string.'''
  if not epoch_seconds: return str(datetime.datetime.now())
  return str(datetime.datetime.fromtimestamp(epoch_seconds))


# ---------- static data types

@dataclass
class StateRule:
    partition: str
    state: str
    transition: str
    action: str
    params: str = ''


@dataclass
class TriggerLookup:
    trigger_regex: str
    zone: str
    partition: str
    tardy_time: int = None    # raise a /healthz error if trigger is not heard from every tardy_time seconds
    squelch_time: int = None  # num seconds before which a duplicate trigger is ignored
    friendly_name: str = ''   # used when speaking or displaying the trigger name

    def __post_init__(self): self.re = re.compile(self.trigger_regex)


@dataclass
class TriggerRule:
    state: str
    partition: str
    zone: str
    trigger: str
    action: str
    params: str = ''


# ---------- static data contents

# ----- simple constants

CONSTANTS = {
  'ALARM_DURATION':        120,         # %Talarm
  'ALARM_TRIGGERED_DELAY': 25,          # %Ttrig
  'ARM_AWAY_DELAY':        60,          # %Tarm
  'PANIC_DURATION':        1200,        # %Tpanic
  'TOUCH_WINDOW_SECS':     20 * 60,     # %Ttouch
}


# SITE-SPECIFIC: you should override these values by creating private.d/data.py
# and putting your site-specific values in there.  See the call to
# UC.load_file_into_module at the bottom for the code that loads this.

USER_LOGINS = {}


# What to do upon entering or leaving various states.
STATE_RULES = [
  #     partition  state          transition -> action          params
    StateRule('*', 'alarm',           'enter', 'announce',     '#a,alarm triggered,@alarm1'),
    StateRule('*', 'alarm',           'enter', 'control',      'all, on'),
    StateRule('*', 'alarm',           'enter', 'httpget',      'http://jack:8080/panic'),
    StateRule('*', 'alarm',           'leave', 'announce',     '#i,@alarm5,alarm reset'),
    StateRule('*', 'alarm',           'leave', 'control',      'all, off'),
    StateRule('*', 'alarm-triggered', 'enter', 'announce',     '#i,@chime3,%f alarm triggered. %Ttrig seconds to disarm'),
    StateRule('*', 'arm-auto',        'enter', 'announce',     '#i,@chime6,automatic arming mode by %u %f'),
    StateRule('*', 'arm-away',        'enter', 'announce',     '#i,@chime5,system armed by %u %f'),
    StateRule('*', 'arm-home',        'enter', 'announce',     '#i,@chime7,armed at home mode by %u %f'),
    StateRule('*', 'arming-auto',     'enter', 'announce',     '#i,@chime2,auto arming by %u %f in %Tarm seconds'),
    StateRule('*', 'arming-away',     'enter', 'announce',     '#i,@chime2,arming by %u %f in %Tarm seconds'),
    StateRule('*', 'disarmed',        'enter', 'announce',     '#i,@chime8,system disarmed by %u'),
    StateRule('*', 'disarmed',        'enter', 'control',      'sirens, off'),
    StateRule('*', 'panic',           'enter', 'announce',     '#a,@alarm3,panic mode activated by %u %f'),
    StateRule('*', 'panic',           'enter', 'control',      'all, on'),
    StateRule('*', 'panic',           'enter', 'control',      'sirens, on'),
    StateRule('*', 'panic',           'enter', 'httpget',      'http://jack:8080/panic'),
    StateRule('*', 'panic',           'leave', 'control',      'sirens, off'),
    StateRule('*', 'silent-panic',    'enter', 'announce',     '#i,@chime8,system deactivated'),
    StateRule('*', 'silent-panic',    'enter', 'silent-panic', ''),
    StateRule('*', 'test-mode',       'enter', 'announce',     '#i,@chime1,entering test mode by %u %f'),
]

FOUR_DAYS =  4 * 60 * 60 * 24  #  4 days in seconds.
TWO_WEEKS = 14 * 60 * 60 * 24  # 14 days in seconds.

# Used to set zone / partition / friendly names for particular triggers
# friendly names are used for vocal announcements, but also imply the is expected to be triggered regularly (i.e. can by 'tardy')
TRIGGER_LOOKUPS = [
  #               trigger_regex   ->      zone           partition   tardy_time,  squelch_time friendly_name
    TriggerLookup('back_door',            'perimeter',   'default',  FOUR_DAYS,   360,         'back door'),
    TriggerLookup('front_door',           'chime',       'default',  TWO_WEEKS,   360,         'front door'),
    TriggerLookup('garage$',              'perimeter',   'default',  FOUR_DAYS,   360,         'door to garage'),
    TriggerLookup('motion_family_room',   'inside',      'default',  FOUR_DAYS,   360,         'motion family room'),
    TriggerLookup('motion_lounge',        'inside',      'default',  FOUR_DAYS,   360,         'motion in lounge'),
    TriggerLookup('motion_outside',       'outside',     'default',  None     ,   360,         'motion outdoors'),
    TriggerLookup('panic.*',              'panic',       'default',  None,        None,        'panic button'),
    TriggerLookup('safe.*',               'safe',        'safe',     None,        None,        None),
    TriggerLookup('side_door',            'perimeter',   'default',  TWO_WEEKS,   360,         'side door'),
]

# Routing table for actions to take upon receiving a trigger, based on current state and trigger (and it's zone and/or partition)
# Only the first matching action is taken!
TRIGGER_RULES = [
  #              state             partition  zone            trigger ->          action                params
  # Don't allow escaping a triggered alarm or panic by setting any new mode except 'disarm'
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-home'        , 'announce'           , 'cannot arm home once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-auto'        , 'announce'           , 'cannot arm auto once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-auto-delay'  , 'announce'           , 'cannot arm auto once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once alarm triggered'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-home'        , 'announce'           , 'cannot arm home once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-auto'        , 'announce'           , 'cannot arm auto once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-auto-delay'  , 'announce'           , 'cannot arm auto once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-away-delay'  , 'announce'           , 'cannot arm away once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once alarm activated'),
    TriggerRule('panic'          , '*'      , '*',             'arm-home'        , 'announce'           , 'cannot arm home once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-auto'        , 'announce'           , 'cannot arm auto once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-auto-delay'  , 'announce'           , 'cannot arm auto once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-away-delay'  , 'announce'           , 'cannot arm away once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once panic triggered'),

  # Triggers that directly set a new state (these come first so its possible to exit test mode)
    TriggerRule('*'              , '*'      , '*',             'disarm'         ,  'state'              , '%P:disarmed'),
    TriggerRule('*'              , '*'      , '*',             'arm-home'        , 'state'              , '%P:arm-home'),
    TriggerRule('*'              , '*'      , '*',             'arm-auto'        , 'state'              , '%P:arm-auto'),
    TriggerRule('*'              , '*'      , '*',             'arm-auto-delay'  , 'state-delay-trigger', '%P:arming-auto, %Tarm, arm-auto'),
    TriggerRule('*'              , '*'      , '*',             'arm-away'        , 'state'              , '%P:arm-away'),
    TriggerRule('*'              , '*'      , '*',             'arm-away-delay'  , 'state-delay-trigger', '%P:arming-away, %Tarm, arm-away'),
    TriggerRule('*'              , '*'      , '*',             'silent-panic'    , 'state'              , 'silent-panic'),
    TriggerRule('*'              , '*'      , '*',             'test-mode'       , 'state'              , 'test-mode'),

  # When in test mode, just announce triggers rather than otherwise acting on them.
    TriggerRule('test-mode'      , '*'      , '*',             '*'               , 'announce'           , 'test %f in %p'),

  # Triggers that indirectly set/influence arming state
    TriggerRule('*'              , '*'      , '*',             'touch-home'      , 'touch-home'         , '%P'),
    TriggerRule('*'              , '*'      , '*',             'touch-away'      , 'touch-away'         , '%P'),
    TriggerRule('*'              , '*'      , '*',             'touch-away-delay', 'touch-away-delay'   , '%P, %Tarm'),

  # Triggers that are actually external commands.
    TriggerRule('*'              , '*'      , '*',             'ann'             , 'announce'           , '%P'),
    TriggerRule('*'              , '*'      , '*',             'status'          , 'announce'           , 'status %s'),
    TriggerRule('*'              , '*'      , '*',             'control'         , 'control'            , '%P'),

  # Alarm mechanics based on zone of the trigger.
    TriggerRule('*'              , '*'      , 'panic'        , '*'               , 'state-delay-trigger', 'panic, %Tpanic, panic-timeout'),
    TriggerRule('arm-home'       , '*'      , 'inside'       , '*'               , 'pass'               , 'pass %t/%z (inside arm-home)'),
    TriggerRule('arm-home'       , '*'      , 'chime'        , '*'               , 'announce'           , '@chime10'),
    TriggerRule('arm-away'       , '*'      , 'outside'      , '*'               , 'pass'               , 'could turn on a light or such..'),

  # Transitioning into an alarm state.
    TriggerRule('arm-away'       , '*'      , '*'            , '*'               , 'state-delay-trigger', 'alarm-triggered, %Ttrig, alarm'),
    TriggerRule('alarm-triggered', '*'      , '*'            , 'alarm'           , 'state-delay-trigger', 'alarm, %Talarm, alarm-timeout'),

  # Transitioning out of an alarm state.
    TriggerRule('alarm'          , '*'      , '*'            , 'alarm-timeout'   , 'state'              , 'arm-auto'),
    TriggerRule('panic'          , '*'      , '*'            , 'panic-timeout'   , 'state'              , 'arm-auto'),

  # Straggler events that can be ignored for various reasons.
    TriggerRule('disarmed'       , '*'      , '*'            , '*'               , 'pass'               , 'pass %t/%z (disarmed)'),
    TriggerRule('*'              , '*'      , '*'            , 'alarm'           , 'pass'               , 'delayed alarm trigger arrived in state %s (ignored)'),
    TriggerRule('alarm-triggered', '*'      , '*'            , '*'               , 'pass'               , 'non-control trigger arrived when already in triggered state (ignored)'),
    TriggerRule('alarm'          , '*'      , '*'            , '*'               , 'pass'               , 'non-control trigger arrived when already in alarm state (ignored)'),
    TriggerRule('panic'          , '*'      , '*'            , '*'               , 'pass'               , 'non-control trigger arrived when already in panic state (ignored)'),

  # If we're in arm-home mode, just announce the trigger's friendly name..
    TriggerRule('arm-home'       , '*'      , '*'            , '*'               , 'announce'           , '#o,@chime4,%f'),
]


# ---------- dynamic data types

@dataclass
class PartitionState:
    partition: str     # key
    state: str
    last_update: int

    def __post_init__(self): self.last_update_nice = nice_time(self.last_update)

    
PARTITION_STATE = P.DictOfDataclasses('data/partition_state.data', PartitionState)


@dataclass
class TouchData:
    trigger: str      # key
    last_update: int
    value: str = None

    def __post_init__(self): self.last_update_nice = nice_time(self.last_update)

    
TOUCH_DATA = P.DictOfDataclasses('data/touch.data', TouchData)


# ---------- private.d overrides

UC.load_file_into_module('private.d/data.py')
