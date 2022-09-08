
'''Data contents and low-level processing for the gift coordinator.

# see gift_coordinator.py for doc
'''

import datetime, os, typing
from contextlib import contextmanager
from dataclasses import dataclass

import kcore.common as C
import kcore.uncommon as UC


# ---------- helpers

def nice_time(epoch_seconds=None):
  '''Convert epoch seconds into user-readable date string.'''
  if not epoch_seconds: return str(datetime.datetime.now())
  return str(datetime.datetime.fromtimestamp(epoch_seconds))


# ---------- static data contents

USERS = [
  'user1',
  'user2',
  'user3',
  'user4',
  'user5',
  'user6',
]

TAKEN_VALS = [ 'available', 'hold', 'taken' ]


# ---------- dynamic data types

@dataclass
class GiftIdea:
  key: str
  recip: str
  item: str
  taken: str
  notes: str
  url: str
  entered_by: str
  entered_on: int
  deleted: int


@dataclass
class CookieData:
  session_id: str
  last_update: int
  data: typing.Dict[str, str]
  

# ---------- generic dynamic data getter

@dataclass
class CachedListData:
  filename: str
  datatype: typing.Any      # actually the class of the datatype
  last_mtime: float = 0.0
  cache: typing.Any = None  # actually a list of type datatype
  def __post_init__(self): self.cache = []


def get_list(cached_list_data):
    if not os.path.isfile(cached_list_data.filename):
        C.log_warning(f'{cached_list_data.filename} not found; starting fresh')
        return []

    # Return memory cached version if persistent store not modified.
    mtime = os.path.getmtime(cached_list_data.filename)
    if cached_list_data.cache and mtime == cached_list_data.last_mtime:
      if False: C.log_debug(f'returning cached {cached_list_data.filename}')
      return cached_list_data.cache

    # Load persistent store and update local cache.
    cached_list_data.cache = list_loader(cached_list_data.filename, cached_list_data.datatype)
    cached_list_data.last_mtime = mtime
    return cached_list_data.cache


def list_loader(filename, dataclass):
    C.log_debug(f'loading list from {filename}')
    data = UC.ListOfDataclasses()
    data.from_string(C.read_file(filename) or '', dataclass)
    if not data: C.log_warning(f'{filename} returned no data; starting blank')
    return data


# ---------- generic dynamic data setter

def list_saver(cached_list_data, new_data):
    C.log_debug(f'saving list to {cached_list_data.filename}')
    if not isinstance(new_data, UC.ListOfDataclasses):
        old_data = new_data
        new_data = UC.ListOfDataclasses()
        new_data.extend(old_data)
    with open(cached_list_data.filename, 'w') as f: f.write(new_data.to_string())
    cached_list_data.last_mtime = os.path.getmtime(cached_list_data.filename)
    cached_list_data.cache = new_data


# setter API
@contextmanager
def saved_list(cached_list_data):
    data = get_list(cached_list_data)
    yield data
    list_saver(cached_list_data, data)


# ---------- getter API: bind generics to specifics

# TODO: add CLI flag for data file locations.

GIFT_IDEAS = CachedListData('data/gift_ideas.data', GiftIdea)
def get_gift_data(): return get_list(GIFT_IDEAS)

COOKIE_DATA = CachedListData('data/session_cookies.data', CookieData)
def get_cookie_data(): return get_list(COOKIE_DATA)


# ---------- private.d overrides

UC.load_file_into_module('private.d/data.py')
