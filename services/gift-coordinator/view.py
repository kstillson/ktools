
# see gift_coordinator.py for doc

import os
import model
import kcore.common as C
import kcore.html as H
import kcore.webserver as W
import kcore.varz as V


# ---------- global controls

DEBUG = False                   # set by flag
SESSION_COOKIE_NAME = 'gc_sesion_id'
TEMPLATE_DIR = 'templates'

USER_SELECTOR = H.list_to_select_input('user', model.USERS, autofocus=True)


# ---------- general purpose

def done(user_verb, log_msg, success=True):
    C.log(f'{log_msg}: {"ok" if success else "error"}', C.INFO if success else C.ERROR)
    V.bump('log:successes' if success else 'log:failures')
    if not success:
        V.set('last-log-fail', log_msg)
        V.stamp('last-log-fail-stamp')
        out = f'<p>Something went wrong during the {user_verb}.</p>\n'
        out += '<a href=".">Try again</a>\n'
        return W.Response(H.html_page_wrap(out), 500)
    return H.redirect('.', 1.2, f'<p style="color: green"><b>successful {user_verb}</b></p>')


# ---------- cookie handling

'''WARNING- Very little attention paid to security for this as yet...'''

def get_cookie_named(name, request):
    cookie_header = request.headers.get('Cookie')
    if not cookie_header: return None

    for cookie in cookie_header.split('; '):
        n, v = cookie.split('=')
        if n == name: return v
    return None


def get_session_data(request):
    session_id = get_cookie_named(SESSION_COOKIE_NAME, request)
    if not session_id:
        if DEBUG: C.log_debug('no session id from cookie')
        return None
    session_data = model.get_session_data(session_id)
    if DEBUG: C.log_debug(f'session id from cookie: {session_id} retrieved session data {session_data}')
    return session_data


# ---------- template system

def render(template_filename, repl):
    out = C.read_file(os.path.join(TEMPLATE_DIR, template_filename), wrap_exceptions=False)
    for seek0, replace in repl.items():
        seek = '{{ ' + seek0 + ' }}'
        out = out.replace(seek, str(replace))
    return out


# ---------- handlers

def add_view(request):
    session_data = get_session_data(request)
    if not session_data: return W.Response('invalid session', 500)
    repl = { 'USER_INPUT': USER_SELECTOR,
             'TAKEN_INPUT': H.list_to_select_input('taken', model.TAKEN_VALS) }
    repl.update(session_data)
    
    if not request.post_params:
        return render('add.html', repl)

    pp = request.post_params
    gi = model.data.GiftIdea(key=None, recip=pp.get('user'), item=pp.get('item'),
                             taken=pp.get('taken'), notes=pp.get('notes'), url=pp.get('url'),
                             entered_by=session_data['user'], entered_on=model.now(),
                             deleted=0)
    ok = model.add_gift_idea(gi)
    return done('add gift idea', f'add idea by {session_data.get("user")}: {gi}', ok)


def edit_view(request):
    session_data = get_session_data(request)
    if not session_data: return W.Response('invalid session', 500)
    key =request.get_params.get('key')
    gi = model.get_gift_idea(key)
    if not gi: return done('edit', f'edit handler by {session_data.get("user")} with gi not found for key {key}', False)

    if request.get_params.get('del') == '1':
        ok = model.del_gift_idea(key)
        return done('delete', f'delete gi by {session_data.get("user")}; key={key}', ok)

    pp = request.post_params
    if not pp:
        repl = { 'KEY': gi.key,
                 'USER_INPUT': H.list_to_select_input('user', model.USERS, selected=gi.recip),
                 'ITEM': gi.item,
                 'TAKEN_INPUT': H.list_to_select_input('taken', model.TAKEN_VALS, selected=gi.taken),
                 'URL': gi.url,
                 'NOTES': gi.notes }
        return render('edit.html', repl)

    # Copy form data into GiftIdea instance and save it.
    gi.recip = pp.get("user")
    gi.item = pp.get('item')
    gi.taken = pp.get('taken')
    gi.url = pp.get('url')
    gi.notes = pp.get('notes')
    ok = model.edit_gift_idea(gi)
    return done('edit', f'edit save by {session_data.get("user")} for key={key}, gi={gi}', ok)
    
    
def export_view(request):
    return model.data.GIFT_IDEAS.serialize(model.data.GIFT_IDEAS)

    
def healthz_view(request):
    return 'ok'


def login_form_view(request):
    session_id = model.start_session()
    user_selector = H.list_to_select_input('user', model.USERS)
    return W.Response(render('login.html', { 'USER_INPUT': USER_SELECTOR }),
                      extra_headers={'Set-Cookie': f'{SESSION_COOKIE_NAME}={session_id}'})


def login_view(request):
    session_data = get_session_data(request)
    if not session_data: return W.Response('invalid session', 500)
    session_data['user'] = request.post_params.get("user")
    session_data['hide_mine'] = request.post_params.get('hide_mine', None) == 'X'
    session_data['hide_taken'] = request.post_params.get('hide_taken', None) == 'X'
    C.log(f'successful login: {session_data}')
    ok = model.save_session_data(session_data)
    return done('login', f'login session update: {session_data}', ok)


def logout_view(request):
    model.del_session(get_session_data(request))
    return W.Response(H.redirect("."),
                      extra_headers={'Set-Cookie': f'{SESSION_COOKIE_NAME}=; Max-Age=0'})


def root_view(request):
    session_data = get_session_data(request)
    if not session_data or not session_data.get('user'): return login_form_view(request)

    all = request.get_params.get('all') == '1'
    if all: C.log('add data (including deleted) requested by get param')
    
    out = f'<br/>hello {session_data["user"]} &nbsp; &nbsp; [ <a href="./logout">logout</a> ]<p>'

    tab = []
    for gi in model.get_gift_ideas():
        if DEBUG: C.log_debug(f'processing gift idea: {gi}')
        # Filtering.
        if session_data['hide_mine'] and gi.recip == session_data['user']: continue
        if session_data['hide_taken'] and gi.taken == 'taken': continue
        if gi.deleted and not all: continue
        if DEBUG: C.log_debug(f'gift idea survived filtering: {gi}')

        notes = gi.notes
        url = gi.url
        if url:
            if not url.startswith('http'): url = f'https://{gi.url}'
            notes += f'<p>[ <a href="{url}" target="_new">link</a> ]'
        controls = f'<form action="edit?key={gi.key}" method="post"><input type="submit" value="edit"/></form>'
        tab.append([controls, gi.recip, gi.item, gi.taken, gi.entered_by, notes])

    out += H.list_to_table(tab, table_fmt='border="1" cellpadding="5"', 
                           header_list=['controls', 'recipient', 'item', 'taken?', 'entered by', 'notes'],
                           title='Gift ideas')

    out += '<p>[ <a href="./add">Add a gift idea</a> ]'
    return H.html_page_wrap(out, 'Gift Coordinator')
