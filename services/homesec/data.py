import datetime, os, re, sys
from contextlib import contextmanager
from dataclasses import dataclass

import kcore.common as C
import kcore.uncommon as UC


# ---------- helpers

def nice_time(epoch_seconds):
  '''Convert epoch seconds into user-readable date string.'''
  return str(datetime.datetime.fromtimestamp(epoch_seconds))


# ---------- hard-coded data types

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
    friendly_name: str = ''

    def __post_init__(self): self.re = re.compile(self.trigger_regex)


@dataclass
class TriggerRule:
    state: str
    partition: str
    zone: str
    trigger: str
    action: str
    params: str = ''
    

# ---------- hard-coded constants

# ----- load secrets

USER_SECRETS = {}
USER_SECRETS_FILE = 'private.d/user_secrets.py'
if os.path.isfile(USER_SECRETS_FILE):
  m = UC.load_file_as_module('private.d/user_secrets.py', 'user_secrets')
  USER_SECRETS.update(m.USER_SECRETS)
else:
  C.log_error(f'no user logins available; {USER_SECRETS_FILE} not found.')


# ----- simple constants

CONSTANTS = {
  'ALARM_DURATION':        120,         # %Talarm
  'ALARM_TRIGGERED_DELAY': 25,          # %Ttrig
  'ARM_AWAY_DELAY':        60,          # %Tarm
  'PANIC_DURATION':        1200,        # %Tpanic
  'SQUELCH_DURATION':      360,
  'TARDY_SECS':            14 * 60 * 60 * 24,   # 14 days
  'TOUCH_WINDOW_SECS':     20 * 60,     # %Ttouch
}


# What to do upon entering or leaving various states.
STATE_RULES = [
  #     partition  state          transition -> action          params
    StateRule('*', 'alarm',           'enter', 'announce',     '#a, alarm triggered, @alarm1'),
    StateRule('*', 'alarm',           'enter', 'control',      'all, on'),
    StateRule('*', 'alarm',           'enter', 'httpget',      'http://jack:8080/panic'),
    StateRule('*', 'alarm',           'leave', 'announce',     '#i, @alarm5, alarm reset'),
    StateRule('*', 'alarm',           'leave', 'control',      'all, off'),
    StateRule('*', 'alarm-triggered', 'enter', 'announce',     '#i, @chime3, %f alarm triggered. %Ttrig seconds to disarm'),
    StateRule('*', 'arm-auto',        'enter', 'announce',     '#i, @chime6, automatic arming mode by %u %f'),
    StateRule('*', 'arm-away',        'enter', 'announce',     '#i, @chime5, system armed by %u %f'),
    StateRule('*', 'arm-home',        'enter', 'announce',     '#i, @chime7, armed at home mode by %u %f'),
    StateRule('*', 'arming-auto',     'enter', 'announce',     '#i, @chime2, auto arming by %u %f in %Tarm seconds'),
    StateRule('*', 'arming-away',     'enter', 'announce',     '#i, @chime2, arming by %u %f in %Tarm seconds'),
    StateRule('*', 'disarmed',        'enter', 'announce',     '#i, @chime8, system disarmed by %u %f'),
    StateRule('*', 'disarmed',        'enter', 'control',      'sirens, off'),
    StateRule('*', 'panic',           'enter', 'announce',     '#a, @alarm3, panic mode activated by %u %f'),
    StateRule('*', 'panic',           'enter', 'control',      'all, on'),
    StateRule('*', 'panic',           'enter', 'control',      'sirens, on'),
    StateRule('*', 'panic',           'enter', 'httpget',      'http://jack:8080/panic'),
    StateRule('*', 'panic',           'leave', 'control',      'sirens, off'),
    StateRule('*', 'silent-panic',    'enter', 'announce',     '#i, @chime8, system deactivated'),
    StateRule('*', 'silent-panic',    'enter', 'silent-panic', ''),
    StateRule('*', 'test-mode',       'enter', 'announce',     '#i, @chime1, entering test mode by %u %f'),
]

# Used to set zone / partition / friendly names for particular triggers
# friendly names are used for vocal announcements, but also imply the is expected to be triggered regularly (i.e. can by 'tardy')
TRIGGER_LOOKUPS = [
  #               trigger_regex   ->      zone           partition   friendly_name
    TriggerLookup('back_door',            'default',     None,       'back door'),
    TriggerLookup('front_door',           'chime',       None,       'front door'),
    TriggerLookup('garage$',              'default',     None,       'door to garage'),
    TriggerLookup('motion-cam-homesec1',  'inside',      None,       'camera motion family room'),
    TriggerLookup('motion-cam-homesec2',  'inside',      None,       'camera motion lounge'),
    TriggerLookup('motion_family_room',   'inside',      None,       'motion family room'),
    TriggerLookup('motion_lounge',        'inside',      None,       'motion in lounge'),
    TriggerLookup('panic.*',              'panic',       None,       'panic button'),
    TriggerLookup('safe.*',               'safe',        'safe',     None),
    TriggerLookup('side_door',            'default',     None,       'side door'),
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
    TriggerRule('alarm-triggered', '*'      , '*',             'arm-away-now'    , 'announce'           , 'cannot arm away once alarm triggered'),
    TriggerRule('alarm-triggered', '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once alarm triggered'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-home'        , 'announce'           , 'cannot arm home once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-auto'        , 'announce'           , 'cannot arm auto once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-auto-delay'  , 'announce'           , 'cannot arm auto once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'arm-away-now'    , 'announce'           , 'cannot arm away once alarm activated'),
    TriggerRule('alarm'          , '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once alarm activated'),
    TriggerRule('panic'          , '*'      , '*',             'arm-home'        , 'announce'           , 'cannot arm home once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-auto'        , 'announce'           , 'cannot arm auto once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-auto-delay'  , 'announce'           , 'cannot arm auto once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-away'        , 'announce'           , 'cannot arm away once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'arm-away-now'    , 'announce'           , 'cannot arm away once panic triggered'),
    TriggerRule('panic'          , '*'      , '*',             'test-mode'       , 'announce'           , 'cannot enter test mode once panic triggered'),
  # Triggers that directly set a new state (these come first so its possible to exit test mode)
    TriggerRule('*'              , '*'      , '*',             'disarm'         ,  'state'              , 'disarmed'),
    TriggerRule('*'              , '*'      , '*',             'arm-home'        , 'state'              , 'arm-home'),
    TriggerRule('*'              , '*'      , '*',             'arm-auto'        , 'state'              , 'arm-auto'),
    TriggerRule('*'              , '*'      , '*',             'arm-auto-delay'  , 'state-delay-trigger', 'arming-auto, %Tarm, arm-auto'),
    TriggerRule('*'              , '*'      , '*',             'arm-away'        , 'state-delay-trigger', 'arming-away, %Tarm, arm-away-now'),
    TriggerRule('*'              , '*'      , '*',             'arm-away-now'    , 'state'              , 'arm-away'),
    TriggerRule('*'              , '*'      , '*',             'silent-panic'    , 'state'              , 'silent-panic'),
    TriggerRule('*'              , '*'      , '*',             'test-mode'       , 'state'              , 'test-mode'),
  # When in test mode, just announce triggers rather than otherwise acting on them.
    TriggerRule('test-mode'      , '*'      , '*',             '*'               , 'announce'           , 'test %f in %p'),
  # Triggers that indirectly set/influence arming state
    TriggerRule('*'              , '*'      , '*',             'touch-home'      , 'touch-home'         , '%u'),
    TriggerRule('*'              , '*'      , '*',             'touch-away'      , 'touch-away'         , '%u'),
    TriggerRule('*'              , '*'      , '*',             'touch-away-delay', 'touch-away-delay'   , '%u, %Tarm'),
  # Triggers that are actually external commands.
    TriggerRule('*'              , '*'      , '*',             'ann'             , 'announce'           , '%z'),   # zone used as general param
    TriggerRule('*'              , '*'      , '*',             'status'          , 'announce'           , 'status %s'),
    TriggerRule('*'              , '*'      , '*',             'control'         , 'control'            , '%z'),   # zone used as general param
  # Alarm mechanics based on zone of the trigger.
    TriggerRule('*'              , '*'      , 'panic'        , '*'               , 'state-delay-trigger', 'panic, %Tpanic, panic-timeout'),
    TriggerRule('arm-home'       , '*'      , 'inside'       , '*'               , 'pass'               , 'pass %t/%z (inside arm-home)'),
    TriggerRule('arm-home'       , '*'      , 'alarm'        , '*'               , 'announce'           , 'alarm %t triggered when home'),
    TriggerRule('arm-home'       , '*'      , 'chime'        , '*'               , 'announce'           , '@chime10'),
    TriggerRule('arm-away'       , '*'      , 'outside'      , '*'               , 'pass'               , 'could turn on a light or such..'),
  # Remaining alarm mechanics.
    TriggerRule('arm-home'       , '*'      , '*'            , '*'               , 'announce'           , '#o, @chime4, %f'),
    TriggerRule('arm-away'       , '*'      , '*'            , '*'               , 'state-delay-trigger', 'alarm-triggered, %Ttrig, alarm'),
    TriggerRule('alarm-triggered', '*'      , '*'            , 'alarm'           , 'state-delay-trigger', 'alarm, %Talarm, %alarm-timeout'),
    TriggerRule('alarm'          , '*'      , '*'            , 'alarm-timeout'   , 'state'              , 'arm-auto'),
    TriggerRule('panic'          , '*'      , '*'            , 'panic-timeout'   , 'state'              , 'arm-auto'),
    TriggerRule('disarmed'       , '*'      , '*'            , '*'               , 'pass'               , 'pass %t/%z (disarmed)'),
]


# ---------- dynamic data types

@dataclass
class PartitionState:
    partition: str     # key
    state: str
    last_update: int

    def __post_init__(self): self.last_update_nice = nice_time(self.last_update)

    
@dataclass
class TouchData:
    trigger: str      # key
    last_update: int
    value: str = None

    def __post_init__(self): self.last_update_nice = nice_time(self.last_update)


PARTITION_STATE_FILENAME = 'data/partition_state.data'
TOUCH_DATA_FILENAME = 'data/touch.data'


# ---------- specific dynamic data loaders

def get_partition_state_data():
    return list_loader(PARTITION_STATE_FILENAME, PartitionState)

def get_touch_data():
    return list_loader(TOUCH_DATA_FILENAME, TouchData)


# ---------- generic dynamic data persistance methods

def list_loader(filename, dataclass):
    data = UC.ListOfDataclasses()
    data.from_string(C.read_file(filename) or '', dataclass)
    if not data: print(f'@@ WARNING- {filename} returned no data', file=sys.stderr)
    return data


def list_saver(filename, data):
    if not isinstance(data, UC.ListOfDataclasses):
        old_data = data
        data = UC.ListOfDataclasses()
        data.update(old_data)
    with open(filename, 'w') as f: f.write(data.to_string())
        

@contextmanager
def saved_list(filename, dataclass):
    data = list_loader(filename, dataclass)
    yield data
    list_saver(filename, data)


