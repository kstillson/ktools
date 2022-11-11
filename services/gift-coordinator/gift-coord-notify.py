#!/usr/bin/python3

'''Send notifications to people other than the recipient about new gift ideas.

This contains a few hard-coded assuptions for the author's system, you'll want
to make adjustments to the 'constants' section for the specifics of your system.

This script uses the /export handler to grab the list of gifts, i.e. it's
able/intended to be run from a different system from the one housing the
actual server.

'''

import smtplib, os, sys, time
from email.mime.text import MIMEText

import kcore.common as C
import kcore.persister as P


# ---------- constants

EXPORT_URL = 'https://point0.net/xmas/export'

GC_HOME_URL = 'https://point0.net/xmas'

GC_SRC_DIR = '/root/dev/ktools/services/gift-coordinator'

LAST_SENT_STAMP = '/var/local/gift-coord-notify.stamp'

NOTIFY_LIST = {
  'alexlbullock@icloud.com': 'Alex',
  'bullockxj@point0.net': 'Judy',
  'gavin@point0.net': 'Gavin',
  'ken@kenstillson.com': 'Ken',
  'mbs@point0.net': 'Nanny',
  'rts@point0.net': 'Poppy',
  'xander.bullock@gmail.com': 'Xander',
}

SMTP_SERVER = 'eximdock:2525'

TEST = False    # Just print what would be done.

# ----------


if sys.path[0] != GC_SRC_DIR: sys.path.insert(0, GC_SRC_DIR)
import data as D    # gift coordinator data model needed for GiftIdea dataclass.


def now(): return int(time.time())


def gen_message(keys, gift_ideas):
  msg = '''The gift coordinator system has new unclaimed gift(s):\n\n'''
  for key in keys:
    gi = gift_ideas.get(key)
    msg += f'  For: {gi.recip}  --  {gi.item}\n'
  return msg + f'\nVisit the gift coordinator at {GC_HOME_URL}\n\n'


def send_mail(msg_from, to, subject, msg):
  wrapper = MIMEText(msg)
  wrapper['Subject'] = subject
  wrapper['To'] = to
  smtp = smtplib.SMTP(SMTP_SERVER)
  smtp.sendmail(msg_from, [to], wrapper.as_string())
  smtp.quit

# ----------


def main():
  stamp_persister = P.Persister(filename=LAST_SENT_STAMP, default_value='0')
  last_sent = int(stamp_persister.get_data())
  if TEST: print(f'{last_sent=}')

  # Load all gift ideas.
  gift_persister = P.PersisterDictOfDC(filename=None, rhs_type=D.GiftIdea)
  serialized_ideas = C.read_web(EXPORT_URL)
  gift_ideas = gift_persister.deserialize(serialized_ideas)
  if not gift_ideas:
    if TEST: print(f'no gift ideas found in export.  {serialized_ideas=}')
    return 0

  # Filter ideas created before the last time we sent a notification.
  skip = {}
  for key, gi in gift_ideas.items():
    if gi.entered_on < last_sent: skip[key] = 'already_notified'
    elif gi.deleted > 0: skip[key] = 'deleted'
    elif gi.taken != 'available': skip[key] = f'status {gi.taken}'
  for key in skip:
    if TEST: print(f'{key} filtered because {skip[key]}')
    gift_ideas.pop(key)
  if TEST: print(f'{len(gift_ideas)} ideas remain unfiltered.')
  if not gift_ideas: return 0

  # Send notifications, filtering out notifications to the person the gift is for.
  for to in NOTIFY_LIST.keys():
    keys = [k for k in gift_ideas.keys() if gift_ideas[k].recip != NOTIFY_LIST[to]]
    if not keys:
      if TEST: print(f'all ideas filtered for {to=}')
      continue

    msg = gen_message(keys, gift_ideas)
    if TEST:
      print(f'TEST RUN; would mail {to=}: {msg=}')
      continue
    else:
      send_mail('ken@kenstillson.com', to, 'Unclaimed gift idea noficiation', msg)

  #if not TEST:
  with stamp_persister.get_rw(): stamp_persister.set_data(now())

  return 0


if __name__ == '__main__':
  sys.exit(main())
