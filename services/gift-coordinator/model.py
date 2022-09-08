
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
    for cookie_data in data.get_cookie_data():
        if cookie_data.session_id == session_id: return cookie_data.data
    # This really shouldn't happen, but let's try to recover by creating a new session.
    C.log_warning(f'Saw incoming session id {session_id} but could not find its data.')
    return { 'SESSION_ID': session_id }


def save_session_data(session_data):
    session_id = session_data.get('SESSION_ID')
    if not session_id: return False
    with data.saved_list(data.COOKIE_DATA) as cd_list:
        for cd in cd_list:
            if cd.session_id == session_id:
                cd.last_update = now()
                cd.data = session_data
                return True
        # Got to the end, so need to append this new session.
        new_cd = data.CookieData(session_id, now(), session_data)
        cd_list.append(new_cd)


def del_session(session_data):
    session_id = session_data.get('SESSION_ID')
    if not session_id: return False
    with data.saved_list(data.COOKIE_DATA) as cd_list:
        for cnt, cd in enumerate(cd_list):
            if cd.session_id == session_id:
                cd_list.pop(cnt)
                return True
    return False


def update_session_data(session_data, key, new_value):
    session_data[key] = new_value
    save_session_data(session_data)
        

def clear_old_session_data():
    time_now = now()
    with data.saved_list(data.COOKIE_DATA) as cd_list:
        cd_list[:] = [x for x in cd_list if time_now - x.last_update < MAX_SESSION_AGE]


# ---------- gift data

def get_gift_ideas(): return data.get_gift_data()


def get_gift_idea(key):
    for gi in get_gift_ideas():
        if gi.key == key: return gi
    return None


def edit_gift_idea(gift_idea):
    with data.saved_list(data.GIFT_IDEAS) as gi_list:
        for cnt, gi in enumerate(gi_list):
            if gi.key == gift_idea.key:
                gi_list[cnt] = gift_idea
                return True
    return False


def add_gift_idea(gift_idea):
    gift_idea.key = gen_random_string(16)
    with data.saved_list(data.GIFT_IDEAS) as gi_list:
        gi_list.append(gift_idea)
    return True


def del_gift_idea(key):
    with data.saved_list(data.GIFT_IDEAS) as gi_list:
        for gi in gi_list:
            if gi.key == key:
                gi.deleted = now()
                return True
    return False
