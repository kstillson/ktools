
import sys


# ----------------------------------------
# Container helpers

def dict_to_list_of_pairs(d):
    out = []
    for i in sorted(d): out.append([i, d[i]])
    return out


# Actually takes a list of lists and output lines of csv.
# (Designed to take the output of dict_to_list_of_pairs())
def list_to_csv(list_in, field_sep=', ', line_sep='\n'):
    out = ''
    for i in list_in:
        for j in range(len(i)):
            if not isinstance(j, str): i[j] = str(i[j])
        out += field_sep.join(i)
        out += line_sep
    return out


# ----------------------------------------
# I/O

def get_input(prompt=""):
    raw_print(prompt)
    return sys.stdin.readline().strip()

def raw_print(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def stderr(msg):
    sys.stderr.write("%s\n" % msg)


# Returns contents as string or list of strings (as-per list_of_lines), and
# returns None on error.  list_of_lines + strip will strip all lines.
def read_file(filename, list_of_lines=False, strip=False, wrap_exceptions=True):
    if wrap_exceptions:
        try:
            with open(filename) as f: data = f.read()
        except: return None
    else:
        with open(filename) as f: data = f.read()
    if list_of_lines:
        data = data.split('\n')
        if strip: data = [i.strip() for i in data if i != '']
    else:
        if strip: data = data.strip()
    return data

