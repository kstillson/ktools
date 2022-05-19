
import datetime, functools, os
import controller, model
import kcore.common as C
import kcore.html as H
import kcore.webserver as W

# ---------- helpers

def authn_required(func):
    @functools.wraps(func)
    def wrapper_authn_required(*args, **kwargs):
        if 'request' in kwargs: kwargs['request'].user = 'user123'
        else: return 'ERROR: no request kwargs'
        return func(*args, **kwargs)
    return wrapper_authn_required


def render(template_filename, repl):
    out = C.read_file(os.path.join('templates', template_filename), wrap_exceptions=False)
    for seek0, replace in repl.items():
        seek = '{{ ' + seek + ' }}'
        out = out.replace(seek, replace)
    return out


# ---------- handlers

@authn_required
def easy_view(request):
  return render('easy_view.html',
    {'status': model.partition_state_resolve_auto('default')})


def healthz_view(request):
  touches = model.get_friendly_touches()
  tardy = [[t.friendly_name, t.last_update_nice] for t in tardy_touches if t.tardy]
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
  return C.read_file(os.path.join('static', os.path.basename(filename)),
                     wrap_exceptions=False)
    

@authn_required
def status_view(request):
  html = "<table border='2' cellpadding='5' class='states'>\n"
  parts = model.partition_states()
  for part in parts:
      tmp_class = part.state.replace('(','').replace(')','')
      html += f'''  <tr>
    <td class='partition_{part.name}' width='50%'>{part.name}</td>
    <td class='state_{tmp_class}'>{part.state}<br/>
      <font size="-1">{part.last_update_nice}</font>
    </td>
  </tr>
'''
  return H.html_page_wrap(html, 'homesec partition states')


@authn_required
def statusz_view(request):
  return controller.get_statusz_state()


@authn_required
def touchz_view(request):
  touches = []
  for t in model.get_touches():
    touches.append([t.trigger, t.value, t.last_update_nice])
  return G.html_page_wrap(H.list_to_table(touches, title='touches'), title='last touches')


@authn_required
def trigger_view(request):
  parts = request.path.split('/')
  trigger = parts[1]
  force_zone = parts[2] if len(parts) > 1 else None
  status, tracking = controller.run_trigger(request.__dict__, name, force_zone)
  return f'{status}\n\n{tracking}'
