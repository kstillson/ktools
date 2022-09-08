'''HTML generators: A few functions that take in strings and output HTML.'''

# in: html body as string.  out: same, wrapped in html and body headers.
def html_page_wrap(body_contents, title='', css=[],
                   other_heads=['<meta name="viewport" content="width=device-width, initial-scale=1">']):
    out = f'<html>\n <head>\n'
    if title: out += f'  <title>{title}</title>\n'
    for i in css: out += f"  <link href='{i}' rel='stylesheet' type='text/css' media='screen' />"
    for h in other_heads: out += f'  {h}\n'
    out += ' </head>\n <body>\n'
    out += body_contents
    out += ' </body>\n</html>\n'
    return out


def list_to_select_input(name, values, prompts=None, selected=None, id=None, indent='  ', autofocus=False):
    set_id = f'id="{id}"' if id else ''
    out = f'{indent}<select name={name} {set_id}{" autofocus" if autofocus else ""}>\n'
    for cnt, val in enumerate(values):
        prompt = prompts[cnt] if prompts else val
        sel = ' selected' if val == selected or prompt == selected else ''
        out += f'{indent}  <option value="{val}"{sel}>{prompt}</option>\n'
    out += f'{indent}</select>\n'
    return out


# in: a dict or a list of lists. out: html code for a table
def list_to_table(list_in, table_fmt='border=1 cellpadding=2', header_list=[], autoexpand=True, title=None):
    ### if not list_in: return ''
    out = '<p/>' + wrap(title, 'b') + '<br/>\n' if title else ''
    out += '<table %s>\n' % table_fmt
    if header_list: out += table_row(header_list, 'th')
    for i in list_in:
        if isinstance(list_in, dict):
            out += table_row([i, list_in[i]])
        else:
            if autoexpand and not isinstance(i, list): i = [i]
            out += table_row(i)
    out += '</table>\n'
    return out


def dict_to_page(d, title=''):
    out = []
    for i in sorted(d): out.append([i, d[i]])
    return html_page_wrap(list_to_table(out), title)


def redirect(to, delay=0, content=None):
    if not content: content =  f'Please <a href="{to}">click here</a>.'
    return html_page_wrap(
        content,
        other_heads=[f'<meta http-equiv="refresh" content="{delay}; url=\'{to}\'" />'])


# in: any iterable, out: html for a row of data in a table.
def table_row(items, item_type='td'):
    out = ''
    for item in items:
        out += wrap_(item, item_type)
    return wrap(out, 'tr')


# in: two strings, out: html for a table row with those two things.
def two_col_row(a, b):
    return '<tr><td>%s</td><td>%s</td></tr>\n' % (a, b)


# wraps msg in opening and closing html blocks.
# e.g. wrap('hi', 'p') produces:   <p>hi</p>\n
def wrap(msg, code, eol=True): return '<%s>%s</%s>%s' % (code, msg, code, '\n' if eol else '')


# Same as wrap() but skips trailing \n without needing an extra param.
def wrap_(msg, code): return wrap(msg, code, eol=False)
