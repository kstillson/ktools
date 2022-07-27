#!/usr/bin/python

'''Trivial CGI wrapper for speak.py

This CGI is referenced by ../services/homesec/ext.py:announce(), which makes a
web GET request that ends up here.  It's done this way (rather than having
speak.py directly built-in to homesec), because in the original author's
setup, the server connected to the speakers (referred to in ext.py as "pi1")
is different from the server that runs the homesec instance.

TODO: update to python3 and generally tidy & improve.

'''

import os, re, subprocess, sys, urllib
from multiprocessing import Process

print "Content-Type: text/html\n\n"

data = os.environ.get('PATH_INFO', '').replace('/', '')
if not data:
  data = urllib.unquote(os.environ.get('QUERY_STRING', ''))
  if '=' in data:
    _, data = data.split('=', 1)
if not data:
  print "no data provided."
  sys.exit(0)

data = re.sub('[^\w,#@_]', ' ', data)

print "<p>speak: %s</p>" % data
os.system('./speak "%s" > /dev/null 2>&1 &' % data)
print "<p>ok</p>"

