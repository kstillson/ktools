#!/usr/bin/python

'''Convert the text on the command-line into speech, and say it.

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

'''

# TODO(defer): update to python3 and kcore

# Sorry- you'll need to get your own of these...
VOICE_RSS_KEY = ''
GOOGLE_API_KEY = ''


import base64, json, glob, os, re, subprocess, sys, syslog, tempfile, urllib, urllib2

def log(msg):
  print msg
  syslog.syslog(msg)


def str_to_cachename(s):
  return '/var/cache/speak/%s' % re.sub('[^A-Za-z0-9]', '_', s)


def render_via_voice_rss(s, outfile, voice='en-us'):
  # http://www.voicerss.org/api/documentation.aspx
  # interesting voices: en-au, en-ca, en-gb, en-in, en-us
  url = 'http://api.voicerss.org/?key=%s&hl=en-us&src=#%s' % (VOICE_RSS_KEY, urllib.quote(s.replace('+', ' ')))
  return subprocess.call(['/usr/bin/curl', '-o', outfile, '-s', '-S', url])


def render_via_google_voice_api(text, outfile, voice='en-US'):
  # API doc: https://cloud.google.com/text-to-speech/
  try:
    voice_sel = {
        "languageCode": 'en-US',
        "ssmlGender": 'male',
    }
    if voice: voice_sel['name'] = voice
    data = {
        "input": { "text": text.replace('+', ' ') },
        "voice": voice_sel,
        "audioConfig": { 
            "audioEncoding": "MP3",
            "pitch": 0,
            "speakingRate": 0.8,
        }
    }
    url = 'https://texttospeech.googleapis.com/v1beta1/text:synthesize?key=' + GOOGLE_API_KEY
    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')
    resp = urllib2.urlopen(req, json.dumps(data) if data else None).read()
    j = json.loads(resp)
    mp3_mimed = j.get('audioContent', '')
    with open(outfile, 'w') as f:
      f.write(base64.b64decode(mp3_mimed))
    return 0
  except Exception as e:
    log('Error during Google API sequence: %s' % e)
    return 1


def sound_filename(name):
  x = glob.glob('/home/pi/sounds/%s*' % name)
  return x[0] if x else ''


def speak_via_festival(s):
  p = subprocess.Popen(['/usr/bin/festival', '--tts'],
                       stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stdout)
  p.communicate(s)
  return p.returncode


def play(filename):
  if not os.path.isfile(filename):
    log('Error- attempt to play non-existent file %s' % filename)
    return 1
  subprocess.call(['/usr/bin/amixer', 'cset', 'numid=1', '--', '100%'])
  return subprocess.call(['/usr/bin/mpg123', '-q', filename])


def speak(s, voice=None):
  cachename = str_to_cachename(s)
  if os.path.isfile(cachename):
    log('Playing from cache: %s' % cachename)
    status = play(cachename)
    if status == 0: return status
    log('Cache play failed; trying to re-get')

  status = render_via_google_voice_api(s, cachename, voice)
  if status == 0:
    log('Retrieved via Google voice API and cached: %s' % cachename)
    status = play(cachename)
    if status == 0: return status
    log('Play of retrieved cache file failed; falling back')
  else:
    log('Unable to render via voice_rss gspeak; falling back')

#  status = render_via_voice_rss(s, cachename, voice)
#  if status == 0:
#    log('Retrieved from voice_rss and cached: %s' % cachename)
#    status = play(cachename)
#    if status == 0: return status
#    log('Play of retrieved cache file failed; falling back to festival')
#  else:
#    log('Unable to render via voice_rss gspeak; falling back to festival')

  status = speak_via_festival(s)
  if status == 0:
    log('Rendered via festival: %s' % s)
    return status
  else:
    log('Fallback to festival also failed :-( - %s' % s)
    return 1


def main(argv):
  syslog.openlog('speak')
  s = ' '.join(argv[1:])
  if 'favicon' in s: return 0
  status = 0
  level = '?'
  voice = None
  for item in s.split(','):
    if item[0] == '#':
      level = item[1].lower()
    elif item[0] == '@':
      log('[L%s] Playing sound %s' % (level, item))
      status |= play(sound_filename(item[1:]))
    elif item[0] == '=':
      voice = item[1:]
    else:
      status |= speak(item, voice)
  return status


if __name__ == '__main__':
  sys.exit(main(sys.argv))
