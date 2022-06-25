#!/usr/bin/python3

import cgi, requests, sys

def err(msg='invalid request', code=400):
  print(f'Status: {code} {msg}\n\n')
  sys.exit(0)
  

def main():
  form = cgi.FieldStorage()
  if 'k' not in form: err("no data provided.")
  k = form['k'].value
  
  r = requests.post('http://hs-lounge:1235/', data={'cmd': k}, timeout=5)
  if r.status_code != 200: err(r.reason, r.status_code)    
    
  print("Status: 200 OK\nContent-Type: text/html\n\n")
  print(r.text)


main()
