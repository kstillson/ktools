#!/usr/bin/python3

'''Try several methods to turn text into speech.

This script attempts to use several external and internal mechanisms to convert
text-to-speech (in approximate decending order of speech quality), and then 
plays the result through the multimedia system.

It also caches the converted sound files, so they can be played without
contacting any external services the next time the exact same text is
requested.  There is not cache clean-up process, so it's really intended for a
situation where a finite set of stock phrases are going to be said over and
over.  Otherwise, the cacahe will grow quite large.

You can also intermix requests to play existing sounds with the speech.  For
example, if you have a sound file named 'gong.wav' and you'd like to ring the
gong before saying something:  ./speak "@gong,hello world"  should do it.

NOTE: the external text-to-speech engines now require you register an account
and get an "api key" from them.  At the time of writing, Google has a very
generous offer that you can run many thousands of tts requests per month
before they charge you anything.  Anyway, you'll need to get your own API key.

See also ./speak-cgi.py, which is a CGI wrapper around this script.


Note that almost all these functions return shell status codes (i.e. 0 means success).
'''

import argparse, base64, json, glob, os, re, subprocess, sys, tempfile
import kcore.common as C

# ---------- secrets
# Sorry- you'll need to get your own of these...

GOOGLE_TTS_API_KEY = ''

# ---------- helpers

def play(filename):
  if not os.path.isfile(filename):
    C.log_error('attempt to play non-existent file %s' % filename)
    return 1
  ok = subprocess.call(['/usr/bin/amixer', 'cset', 'numid=1', '--', '100%'], stdout=subprocess.DEVNULL)
  fileout = str(subprocess.check_output(['/usr/bin/file', filename]))
  if 'WAV' in fileout:
    ok |= subprocess.call(['/usr/bin/aplay', filename], stderr=subprocess.DEVNULL)
  else:
    # assume mp3
    ok |= subprocess.call(['/usr/bin/mpg123', '-q', filename], stdout=subprocess.DEVNULL)
  if ok != 0:
    C.log_error(f'error return {ok} when trying to play sound {filename}')
    return ok
  C.log(f'played sound {filename}')
  return 0


def sound_filename(name):
  x = glob.glob('/home/pi/sounds/%s*' % name)
  return x[0] if x else ''


def str_to_cachename(s):
  return '/var/cache/speak/%s' % re.sub('[^A-Za-z0-9]', '_', s)


# ---------- speech renderers

# https://cloud.google.com/text-to-speech/docs/basics#audio-config
def render_via_google_cloud_voice_api(text, outfile):
  # https://cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize#audioconfig
  data = '''{
  'input':{
    'text':'@@'
  },
  'voice':{
    'languageCode':'en-US',
    'name':'en-US-Wavenet-B'
  },
  'audioConfig':{
    'audioEncoding':'MP3',
    'speakingRate': 0.9
  }
}'''.replace('@@', text)
  url = 'https://texttospeech.googleapis.com/v1/text:synthesize'
  p = subprocess.Popen([
    '/usr/bin/curl', '-s', '-S',
    '-H', 'X-Goog-User-Project: speech-api-199404',
    '-H', 'Authorization: Bearer '+ GOOGLE_TTS_API_KEY,
    '-H', 'Content-Type: application/json; charset=utf-8',
    '--data', data, url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = p.communicate()
  if err:
    C.log_error(f'error during Google cloud API: {err}')
    return 1
  if p.returncode != 0:
    C.log_error(f'error return code from Google cloud API call: {p.returncode}')
    return p.returncode
  if 'error' in str(out):
    C.log_error(f'error contained in Google cloud API response: {out}')
    return 1
  j = json.loads(out)
  b = base64.b64decode(j.get('audioContent'))
  with open(outfile, 'wb') as f:
    f.write(b)
  return 0


def render_via_google_free_voice_api(text, outfile):
  from gtts import gTTS
  tmp = gTTS(text, slow=True, lang='en', tld='com')
  tmp.save(outfile)
  return 0


# For reasons not currently understood, aplay appears to truncate the last
# fraction of a second of playback, so I'm going to compensate by using the
# sox package to pad a little silence on the end.
def render_via_mimic(s, outfile):
  tmpfil = tempfile.NamedTemporaryFile().name + '.wav'
  tmp2 = outfile + '.wav'
  status = subprocess.call(['/home/pi/bin/mimic',
    '-voice', 'ap',
    '--setf', 'duration_stretch=1.1',
    '--setf', 'int_f0_target_mean=90',
    '-o', tmpfil, '-t', s])
  status |= subprocess.call(['/usr/bin/sox', tmpfil, tmp2, 'pad', '0', '0.3'])
  os.unlink(tmpfil)
  os.rename(tmp2, outfile)  # strip extension to match cache naming standard.
  return status


def speak_via_festival(s, _unused_outfile=None):
  p = subprocess.Popen(['/usr/bin/festival', '--tts'],
                       stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stdout)
  p.communicate(bytes(s, 'utf-8'))
  # if worked, return -1 to indicate already spoken, so no need to play cache.
  return p.returncode if p.returncode != 0 else -1


def speak_via_python(s, _unused_outfile=None):
  import pyttsx3
  p = pyttsx3.init()
  p.setProperty('rate', 90)
  p.setProperty('voice', 'english_rp')
  p.say(s)
  p.runAndWait()
  return -1


# ---------- main

def render_auto(s, cachename):
  things_to_try = ['google-cloud', 'google-free', 'mimic', 'python', 'festival']
  for voice in things_to_try:
    if render_by_voice(s, voice, cachename) == 0: return 0
  C.log_error('all renderers failed.')
  return 1


def render_by_voice(s, voice, cachename):
  if voice == 'auto': func = render_auto
  elif voice == 'mimic': func = render_via_mimic
  elif voice == 'google-cloud': func = render_via_google_cloud_voice_api
  elif voice == 'google-free': func = render_via_google_free_voice_api
  elif voice == 'python': func = speak_via_python
  elif voice == 'festival': func = speak_via_festival
  else:
    C.log_error(f'unknown voice renderer requested: {voice}')
    return 1
  status = func(s, cachename)
  if status == 0 or status == -1: C.log(f'render via {voice} success: {s}')
  else: C.log_error(f'render via {voice} failed with status {status}: {s}')
  return status


def speak(s, voice, nocache):
  # First see if we've already got it cached.
  cachename = tempfile.NamedTemporaryFile().name if nocache else str_to_cachename(s)
  if not nocache and os.path.isfile(cachename) and voice in ['auto', 'cache']:
    C.log(f'Playing from cache: {cachename}')
    status = play(cachename)
    if status == 0: return 0  # We're done here.
    # We thought cache was going to work, but playback failed for some reason...
    C.log_error('Cache play failed; trying to re-render')
  if voice == 'cache':
    C.log_warning('Only cache playback enabled, and it failed.')
    return 1

  # Next try re-rendering it.
  status = render_by_voice(s, voice, cachename)
  if status != 0:
    if status == -1: return 0  # both rendering and playback already done.  we're done here.
    C.log_error(f'all attempted renders failed. :-(')
    return 1

  # Play out re-rendered result.
  status = play(cachename)
  if status != 0: C.log_error(f'renderer worked but playback failed with {status} for {cachename}: {s}')
  if nocache: os.unlink(cachename)
  return status


def parse_args():
  ap = argparse.ArgumentParser(description='text-to-speech front-end for multiple services')
  ap.add_argument('--logfile', '-l', default='/var/log/pi1/speak.log')
  ap.add_argument('--nocache', '-n', action='store_true')
  ap.add_argument('--voice', '-v', default='auto', help='voice renderer to use.  {cache, google-cloud, google-free, mimic, python, festival}')
  ap.add_argument('words', nargs='+', help='words to say or @filename of sound to play. "," separate for a sequence.')
  return ap.parse_args()


def main(argv=None):
  args = parse_args()
  C.init_log('speak log', args.logfile)

  s = ' '.join(args.words).strip()
  if 'favicon' in s: return 0
  status = 0
  for item in s.split(','):
    if item[0] in ['#', '=']:
      C.log_warning(f'prefix code no longer supported: {item}')

    elif item[0] == '@':
      status |= play(sound_filename(item[1:]))

    else:
      status |= speak(item, args.voice, args.nocache)

  return status


if __name__ == '__main__':
  sys.exit(main())
