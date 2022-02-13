
# ----------------------------------------
# html generators


def html_page_wrap(body_contents, title=None):
    out = '<html>\n<head>\n  <title>%s</title>\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n' % title
    out += body_contents
    out += '</body>\n</html>\n'
    return out


def list_to_table(list_in, table_fmt='border=1 cellpadding=2', header_list=[], autoexpand=True):
    if not list_in: return ''
    out = '<table %s>\n' % table_fmt
    if header_list: out += table_row(header_list, 'th')
    for i in list_in:
        if isinstance(list_in, dict):
            out += table_row([i, list_in[i]])
        else:
            if autoexpand and not isinstance(i, list): i = [i]
            out += table_row(i)
    out += '</table>\n'
    return out


def table_row(items, item_type='td'):
    out = ''
    for item in items:
        out += wrap_(item, item_type)
    return wrap(out, 'tr')


def two_col_row(a, b):
    return '<tr><td>%s</td><td>%s</td></tr>\n' % (a, b)


def wrap(msg, code, eol=True): return '<%s>%s</%s>%s' % (code, msg, code, '\n' if eol else '')


def wrap_(msg, code): return wrap(msg, code, eol=False)

