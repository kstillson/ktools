
# see homesec.py for doc

import base64, datetime, functools, os, time
import controller, model
import kcore.auth as A
import kcore.common as C
import kcore.html as H
import kcore.webserver as W


# ---------- global controls

BASIC_AUTH_REALM = 'homesec'    # can be overriden by caller/importer
DEBUG = False                   # set by flag
KAUTH_PARAMS = None          	# set by calling init_kauth()
PASSWORD_CHECKER = model.check_user_password   # overrideen by tests
STATIC_DIR = 'static'           # can be overriden by caller/importer
TEMPLATE_DIR = 'templates'      # can be overriden by caller/importer


# ---------- Authentication helpers

def init_kauth(params):
  global KAUTH_PARAMS
  KAUTH_PARAMS = params
  C.log('init_kauth done')
    

def authn_required(func):
  @functools.wraps(func)
  def wrapper_authn_required(*args, **kwargs):
    request = kwargs.get('request') or args[0]

    # ----- Try kcore.auth

    kauth_token = request.get_params.get('a2')
    if kauth_token and KAUTH_PARAMS:
      rslt = A.verify_token(token=kauth_token, command=request.path, client_addr=request.remote_address,
                            db_passwd=KAUTH_PARAMS.db_passwd, db_filename=KAUTH_PARAMS.db_filename)
      if rslt.ok:
        request.user = rslt.username or rslt.registered_hostname
        C.log(f'successful kauth as {request.user}')
        return func(*args, **kwargs)

      C.log_warning(f'unsuccessful kauth request: {rslt}')
      return W.Response('authentication failure', 403)
            
    # ----- Try basic auth

    auth_header = request.headers.get('Authorization')
    if not auth_header:
      C.log(f'No auth header; sending 401. {request.full_path}')
      return W.Response(
        'Please log in', 401, extra_headers={'WWW-Authenticate': f'Basic realm="{BASIC_AUTH_REALM}"'})

    _, encoded = auth_header.split(' ', 1)
    provided_username_b, provided_password_b = base64.b64decode(encoded).split(b':', 1)
    provided_username = provided_username_b.decode()
    provided_password = provided_password_b.decode()

    if not PASSWORD_CHECKER(provided_username, provided_password):
      C.log_warning(f'unsuccessful basic-auth for user {provided_username}')
      time.sleep(2)
      return W.Response('Invalid credentials', 401,
          extra_headers={'WWW-Authenticate': f'Basic realm="{BASIC_AUTH_REALM}"'})

    request.user = provided_username
    C.log(f'successful http-basic authN as {request.user}')
    return func(*args, **kwargs)
  return wrapper_authn_required


# ---------- template system

def render(template_filename, repl):
  out = C.read_file(os.path.join(TEMPLATE_DIR, template_filename), wrap_exceptions=False)
  for seek0, replace in repl.items():
    seek = '{{ ' + seek0 + ' }}'
    out = out.replace(seek, str(replace))
  return out


# ---------- handlers

@authn_required
def easy_view(request):
  return render('easy.html',
    {'status': model.partition_state_resolve_auto('default')})


def healthz_view(request):
  touches = model.get_friendly_touches()
  tardy = [[t.friendly_name, t.last_update_nice] for t in touches if t.tardy]
  if not tardy: return 'ok'
  return H.html_page_wrap('ERROR<p/>' + H.list_to_table(tardy, title='tardy triggers'))


def logout_view(request):
    if request.headers.get('Authorization'):
        return W.Response('Please log in', 401, extra_headers={'WWW-Authenticate': f'Basic realm="{BASIC_AUTH_REALM}"'})
    return H.redirect('/')


@authn_required
def root_view(request):
  last = []
  for t in model.get_friendly_touches():
    last.append([t.friendly_name, t.last_update_nice, 'tardy' if t.tardy else ''])
  return render('root.html',
    {'count_home': model.touches_with_value('home'),
     'last_sensors': H.list_to_table(last) })


def static_view(request):
  if not '/static/' in request.path: return W.Response('invalid /static/ request', 400)
  _, filename = request.path.split('/static/')
  pathname = os.path.join(STATIC_DIR, os.path.basename(filename))
  if not os.path.isfile(pathname):
      C.log_warning(f'attempt to read non-existent static file {pathname}')
      return W.Response('file not found', 404)
  mode = 'r' if filename.endswith('.css') or filename.endswith('.html') else 'rb'
  with open(pathname, mode) as f: return f.read()


@authn_required
def status_view(request):
  html = "<table border='2' cellpadding='5' class='states'>\n"
  parts = model.partition_states()
  for part in parts:
      tmp_class = part.state.replace('(','').replace(')','')
      html += f'''  <tr>
    <td class='partition_{part.partition}' width='50%'>{part.partition}</td>
    <td class='state_{tmp_class}'>{part.state}<br/>
      <font size="-1">{part.last_update_nice}</font>
    </td>
  </tr>
'''
  return H.html_page_wrap(html, 'homesec partition states', css=['static/style.css'], other_heads=[])


@authn_required
def statusz_view(request):
  return controller.get_statusz_state()


@authn_required
def test_view(request):
  return f'hello {request.user}'


@authn_required
def touchz_view(request):
  touches = []
  for t in model.get_touches():
    touches.append([t.trigger, t.value, t.last_update_nice])
  return H.html_page_wrap(H.list_to_table(touches, title='touches'), title='last touches')


@authn_required
def trigger_view(request):
  parts = request.path.split('/')
  _ = parts.pop(0)
  _ = parts.pop(0)
  trigger = parts.pop(0)
  trigger_param = parts.pop(0) if parts else None
  status, tracking = controller.run_trigger(request.__dict__, trigger, trigger_param)
  out = str(status)
  if DEBUG: out += '\n\n' + str(tracking)
  return out


def user_view(request):
  if not request.post_params: return '''
<html><body><form action="" method="POST">\n
username <input name="username"><br/>
password <input name="password"><br/>
<input type="submit">
</form></body></html>'''
  return model.hash_user_password(request.post_params.get('username'),
                                  request.post_params.get('password'))

