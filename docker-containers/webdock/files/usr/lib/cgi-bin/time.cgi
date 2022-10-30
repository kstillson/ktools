#!/usr/bin/python3

import time

def main():
  out = str(int(time.time()))
  
  print(f"Status: 200 OK\nContent-Type: text/html\nContent-Length: {len(out)}\n")
  print(out, end='')


main()
