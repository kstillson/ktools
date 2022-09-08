#!/usr/bin/python3

import sys
import dateutil.parser

sys.path.insert(0, '..')
import model as M
import data as D
import kcore.uncommon as UC

UNK_DATE = '1999-12-31'


def drop(line, reason):
    print(f'drop: {reason}: {line}')
    return None


def sep(line):
    items = line.split('|')
    if len(items) < 3: return None # drop(line, 'too few items')
    items.pop()
    items.pop(0)
    return [x.strip() for x in items]


def convert_date(d):
    if str(d).startswith('0'): return 0
    dt = dateutil.parser.parse(d)
    return int(dt.timestamp())


# ---------- main

gi_list = []

with open('private.d/old-mysql-export.txt') as f:
    for line in f:
        items = sep(line)
        if not items: continue
        count = len(items)
        if count == 6:
            _, recip, item, taken, notes, deleted = items
            event = 'Christmas'
            entered_by = '?'
            entered_on = 0
        elif count == 4:
            _, recip, item, taken = items
            event = 'Christmas'
            notes = ''
            deleted = 0
            entered_by = '?'
            entered_on = 0
        elif count == 5:
            _, recip, event, item, taken = items
            notes = ''
            deleted = 0
            entered_by = '?'
            entered_on = 0
        elif count == 9:
            _, recip, event, item, taken, notes, entered_by, entered_on, deleted = items
        elif count == 10:
            _, recip, event, item, taken, notes, unk, entered_by, entered_on, deleted = items
        else:
            drop(items, f'unknown len: {count}')
            continue

        if not deleted or deleted.startswith('0'): deleted = entered_on or UNK_DATE
        
        gi = D.GiftIdea(M.gen_random_string(), recip, item, taken, notes, '', entered_by,
                        convert_date(entered_on), convert_date(deleted))
        gi_list.append(gi)

lodc = UC.ListOfDataclasses()
lodc.extend(gi_list)
print(lodc.to_string())
