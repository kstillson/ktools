
# see gift_coordinator.py for doc

import random, string, time
import data
import kcore.common as C


# ---------- controls

MAX_SESSION_AGE = 4 * 60 * 60    # 4 hours


# ---------- general

def gen_random_string(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def now(): return int(time.time())   # Epoch seconds as int.


# ---------- expose static data

USERS = data.USERS
TAKEN_VALS = data.TAKEN_VALS

# ---------- cookie & session

'''WARNING- Very little attention paid to security for this as yet...'''


def start_session(initial_data={}):
    clear_old_session_data()
    session_data = dict(initial_data)
    new_session_id = gen_random_string(16)
    session_data['SESSION_ID'] = new_session_id
    save_session_data(session_data)
    return new_session_id


def get_session_data(session_id):
    with data.COOKIE_DATA.get_ro() as d:
        existing_session = d.get(session_id)
        if existing_session: return existing_session.data

    # This really shouldn't happen, but let's try to recover by creating a new session.
    C.log_warning(f'Saw incoming session id {session_id} but could not find its data.')
    new_session_data = {'SESSION_ID': session_id}
    save_session_data(new_session_data)
    return new_session_data


def save_session_data(session_data):
    session_id = session_data.get('SESSION_ID')
    if not session_id: return False

    with data.COOKIE_DATA.get_rw() as d:
        existing_session = d.get(session_id)
        if existing_session:
            existing_session.data = session_data
        else:
            d[session_id] = data.CookieData(session_id, now(), session_data)
        return True


def del_session(session_data):
    session_id = session_data.get('SESSION_ID')
    if not session_id: return False
    with data.COOKIE_DATA.get_rw() as d:
        d.pop(session_id, None)
    return True


def update_session_data(session_data, key, new_value):
    session_data[key] = new_value
    save_session_data(session_data)


def clear_old_session_data():
    time_now = now()
    del_keys = []
    for k, v in data.COOKIE_DATA.get_data().items():
        if time_now - v.last_update >= MAX_SESSION_AGE:
            del_keys.append(k)

    with data.COOKIE_DATA.get_rw() as d:
        for i in del_keys: d.pop(i)


# ---------- gift data

def get_gift_ideas(): return data.GIFT_IDEAS.get_data().values()


def get_gift_idea(key): return data.GIFT_IDEAS.get_data().get(key, None)


def edit_gift_idea(gift_idea):
    with data.GIFT_IDEAS.get_rw() as d:
        d[gift_idea.key] = gift_idea
    return True


def add_gift_idea(gift_idea):
    gift_idea.key = gen_random_string(16)
    return edit_gift_idea(gift_idea)


def del_gift_idea(key):
    with data.GIFT_IDEAS.get_rw() as d:
        gi = d.get(key, None)
        if not gi: return False
        gi.deleted = now()
        return True
