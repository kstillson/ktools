'''A few simple common helper methods.

Works for both Python 2 & 3.  Separated out from common.py because
Circuit Python doesn't include the "logging" module, and these
methods should be available to both Cpython and Circuit Python.
'''

import sys


# ----------------------------------------
# Container helpers

def dict_to_list_of_pairs(d):
    out = []
    for i in sorted(d): out.append([i, d[i]])
    return out


def list_to_csv(list_in, field_sep=', ', line_sep='\n'):
    '''Takes a list of lists and outputs lines of csv.
       Works well with the output from dict_to_list_of_pairs().'''
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


def read_file(filename, list_of_lines=False, strip=False, wrap_exceptions=True):
    '''Returns contents as a string or list of strings (as-per "list_of_lines")
       Returns None on error.  list_of_lines + strip will strip all lines.'''
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

