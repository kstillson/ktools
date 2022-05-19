
import sys
from dataclasses import dataclass

@dataclass
class LastCall:
  method: str
  args: list
  kwargs: dict
  def __post_init__(self):
    print(f'Last call: {self.method}, args={self.args}, kwargs={self.kwargs}', file=sys.stderr)
    
  
LAST = None


def announce(*args, **kwargs):
  global LAST
  LAST = LastCall('announce', args, kwargs)


def control(*args, **kwargs):
  global LAST
  LAST = LastCall('control', args, kwargs)


def send_emails(*args, **kwargs):
  global LAST
  LAST = LastCall('send_emails', args, kwargs)


def send_email(*args, **kwargs):
  global LAST
  LAST = LastCall('send_email', args, kwargs)


def silent_panic(*args, **kwargs):
  global LAST
  LAST = LastCall('silent_panic', args, kwargs)

