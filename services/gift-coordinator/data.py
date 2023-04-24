
'''Data contents and low-level processing for the gift coordinator.

# TODO: add CLI flag for data file locations.

# see gift_coordinator.py for doc
'''

import datetime, typing
from dataclasses import dataclass

import kcore.persister as P
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


# ---------- dynamic data

@dataclass
class GiftIdea:
  key: str    # primary key
  recip: str
  item: str
  taken: str = 'available'
  notes: str = ''
  url: str = ''
  entered_by: str = '?'
  entered_on: int = 0
  deleted: int = 0
  taken_by: str = '?'
  taken_on: int = 0


GIFT_IDEAS = P.DictOfDataclasses('data/gift_ideas.data', GiftIdea)


@dataclass
class CookieData:
  session_id: str  # primary key
  last_update: int
  data: typing.Dict[str, str]

COOKIE_DATA = P.DictOfDataclasses('data/session_cookies.data', CookieData)


# ---------- private.d overrides

UC.load_file_into_module('private.d/data.py')
