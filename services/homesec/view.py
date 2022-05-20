
import datetime, functools, os
import controller, model
import kcore.common as C
import kcore.html as H
import kcore.webserver as W

DEBUG = False

# ---------- helpers

def authn_required(func):
    @functools.wraps(func)
    def wrapper_authn_required(*args, **kwargs):
        request = kwargs.get('request') or args[0]
        request.user = 'user123'
        return func(*args, **kwargs)
    return wrapper_authn_required


def render(template_filename, repl):
    out = C.read_file(os.path.join('templates', template_filename), wrap_exceptions=False)
    for seek0, replace in repl.items():
        seek = '{{ ' + seek0 + ' }}'
        out = out.replace(seek, str(replace))
    return out


# ---------- handlers

@authn_required
def easy_view(request):
  return render('easy_view.html',
    {'status': model.partition_state_resolve_auto('default')})


def healthz_view(request):
  touches = model.get_friendly_touches()
  tardy = [[t.friendly_name, t.last_update_nice] for t in touches if t.tardy]
  if not tardy: return 'ok'
  return H.html_page_wrap('ERROR<p/>' + H.list_to_table(tardy, title='tardy triggers'))


@authn_required
def root_view(request):
  last = []
  for t in model.get_friendly_touches():
    last.append([t.trigger, t.friendly_name, t.last_update_nice, 'tardy' if t.tardy else ''])
  return render('root.html',
    {'count_home': model.touches_with_value('home'),
     'last_sensors': H.list_to_table(last), })


def static_view(request):
  _, filename = request.path.split('/static/')
  pathname = os.path.join('static', os.path.basename(filename))
  if not os.path.isfile(pathname):
      C.log_warning(f'attempt to read non-existent static file {pathname}')
      return W.Response(404, 'file not found')
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
  return H.html_page_wrap(html, 'homesec partition states', css=['style.css'], other_heads=[])


@authn_required
def statusz_view(request):
  return controller.get_statusz_state()


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
  out = status
  if DEBUG: out += '\n\n' + str(tracking)
  return out
