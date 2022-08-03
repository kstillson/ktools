#!/usr/bin/python3
import re

def chop_at(needle, haystack):
    pos = haystack.find(needle)
    if pos < 0: return haystack
    return haystack[0:pos+len(needle)]


print('Content-Type: text/html')
print()

print("<html>\n<table border='1'>\n")
with open('/etc/apache2/conf.d/site-k3n-ssl.conf') as f:
    for line in f:
        if not line.startswith('Redirect'): continue
        _, addr, redir = re.split('[\t ]+', line)
        redir = redir.replace('https://', '')
        redir = redir.replace('http://', '')
        redir = redir.replace('.point0.net', '')
        redir = chop_at('/drive/', redir)
        redir = chop_at('/spreadsheets/', redir)
        print(f'  <tr><td>{addr}</td><td>{redir}</td></tr>\n')
print("</table>\n</html>\n")
