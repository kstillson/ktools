#!/usr/bin/python3
'''Key Master (km) - local network secret bootstrapper.

This is a web-server that hosts a small database of secrets.  Clients request
secrets by providing the name of the secret they want via an https GET
request.

Clients are authenticated using k_auth.py tokens, which include a private
client-machine unique identifier and an optional username/password.  That is,
each keymaster secret is associated with a k_auth "shared secret" (shared
between the client machine and the keymaster server), and that secret is
hardware-locked to the machine on which it was generated, which should be the
machine that km requests are going to come from.

The km secrets database is stored in a symmetrically encypted GPG file, and
the server does not know the password to it.  This makes it safe to backup the
source directory without exposing secrets (although see notes below concerning
the security of the TLS private key).

To enable the server (i.e. decrypt the database), the service owner must
manually provide the GPG passphrase via a web client (a login-style form is
provided).  Once this is done, the service is up and can serve secrets.

The intended use for KM is services that require some sort of password in
order to initialize, but where you do not wish to build the password into the
service.  On startup, a service can contact the key-master and request its own
secrets.  Clients should be smart enough to auto-retry secret retieval,
in-case they contact the key-master at a time when the database has not yet
been unlocked.  A suitable client (both Python library and command-line) is
in tools_for_users/kmc.py

The vision is that in the event of a many-service restart, all the systems
that need secerts will go into retry loops until key-master admin enters the
one master password to unlock the KM database, and then all the services can
auto-restart without further intervention.

In addition to k_auth tokens, KM also checks the requesting client's source-IP
address.  If you don't want this, override the hostname with "*" when
registering a secret.  Make sure to do this on the client side when generating
the key registration (kmc.py -g ...), and when retrieving secrets, as the
hostname is mixed-in to the k_auth shared-secret generation.  Also note that
while a hostname of "*" disables source-ip checking, a k_auth shared secret
still has machine-specific data mixed in, and so by default will only work for
key retireval requests generated from the same machine as where the key
registration was generated.

If you really want to be able to retrieve a secret from multiple different
client machines, you'll need to set the $PUID environment variable to some
fixed-and-secret value (one that is unique to this key) both when generating
the key registration and when retrieving the secret.

By default, the server is deliberately hyper-sentitive, meaning that a single
unauthorized or not-understood request will cause the server to panic and
clear it's decrypted copy of the database.  The key-master owner must then
re-enter the GPG passphrase before any more secrets can be served.  This is
intended to discourage hacking or experimentation against the server.  It also
means you probably need to continuously monitor the KM; see the /healthz
handler for an easy way to do that.  If you don't want the hyper-sensitive
mode, for example in cases where curious or malicious network users might
cause a denial-of-service by panicing the server, use the --dont-panic flag to
turn it off.

The secrets database is formatted like a Windows-style .ini file; see
km-test.data.gpg for an example; the passphrase is "ken123".  Note that
various tests are dependent on this file's current contents, so probably best
not to change it.  Your real secrets database goes in private.d/km.data.gpg.

Note on TLS private key: 

'''

import ConfigParser, arpparse, os, subprocess, sys, syslog
import http.server, ssl
import k_auth


# ---------- global state

ARGS = {}

# ---------- other constants

HTML_CTYPE = 'text/html'
HTML_HEADER = '<html>\n<head><title>keymanager</title></head>\n<body>\n'
HTML_FOOTER = '\n</body>\n</html>\n'

# ---------- logging


def log(msg, alert=False):
    if alert:
        if RL_LOG.check(msg): msg = 'ALERT: %s' % msg
        else: msg = '(rate-limited): %s' % msg
    sys.stderr.write('%s\n' % msg)
    return msg


def log_f(msg, alert=False):
    log(msg, alert)
    return False

# ---------- Class for encapsulating GPG encrypted input data

class Data(object):
    def __init__(self): self._config = ConfigParser.SafeConfigParser()

    def read(self, filename, password):
        p = subprocess.Popen(['/usr/bin/gpg', '--passphrase-fd', '0', '-o', '-', '--batch', filename],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(password)
        if p.returncode != 0: return log_f('Error decrypting data: %s' % err, True)
        fp = StringIO(out)
        self._config.readfp(fp)
        if not self.ready(): return log_f('error reading config file', True)
        log('Read config file ok.')
        return True

    def ready(self): return len(self._config.sections()) >0
    def check(self, lookup_key): return self._config.has_section(lookup_key)

    def get(self, lookup_key, query_key):
        try: return self._config.get(lookup_key, query_key)
        except: return None

data = Data()


# ---------- web server

# ssl wrapper reference:
# http://rzemieniecki.wordpress.com/2012/08/10/quick-solution-to-ssl-in-simplexmlrpcserver-python-2-6-and-2-7/
#
# TODO: update to Python 3.

class SecureHTTPServer(HTTPServer):
    def __init__(self, server_address, HandlerClass):
        BaseServer.__init__(self, server_address, HandlerClass)
        self.socket = ssl.wrap_socket(socket.socket(), server_side=True,
                                      certfile=CERTKEYFILE, keyfile=CERTKEYFILE,
                                      ssl_version=ssl.PROTOCOL_TLSv1_2)
        self.server_bind()
        self.server_activate()


class SecureHTTPRequestHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def send(self, ctype, content, code=200):
        if ctype == HTML_CTYPE: content = HTML_HEADER + content + HTML_FOOTER
        self.send_response(code)
        self.send_header('Content-type', ctype)
        self.end_headers()
        self.wfile.write(content)
        self.wfile.flush()
        self.connection.shutdown(socket.SHUT_RDWR)
        self.connection.close()

    def send_data_form(self):
        html = '''
<form name="loader" method="post">\n password: <input type="password" name="password">\n
 <input type="submit" value="Submit">\n</form>
'''
        self.send(HTML_CTYPE, html)

    def check_host(self, want, have):
        if not want: return log_f('no required host entry found.', True)
        if want == '*': return True
        try:
            want_ip = socket.gethostbyname(want)
        except Exception as e:
            # Try once more before failing.
            try:
                time.sleep(2)
                want_ip = socket.gethostbyname(want)
            except Exception as e2:
                return log_f('unable to lookup ip for wanted host %s: %s' % (want, e2), True)
            log('gethostbyname failed, but recovered with retry.')
        if want_ip != have: return log_f('host mismatch %s != %s' % (want_ip, have), True)
        return True

    def key_lookup(self):
        key = self.path[1:]
        if not data.check(key): return log('ERR attempt to find non-existent key: %s' % self.path, True)
        secret = data.get(key, 'secret')
        if not secret: return log('ERR error looking up key: %s' % self.path, True)
        name = data.get(key, 'name') or key
        want_host = data.get(key, 'host')
        have_host = self.client_address[0]
        if not self.check_host(want_host, have_host):
            return log('ERR error performing host verification [%s/%s]' % (name, have_host), True)
        log('host %s success lookup key %s' % (have_host, name))
        return secret

    def do_GET(self):
        global data
        if self.path == '/favicon.ico': return None
        if self.path == '/':
            if data.ready():
                log('keymanager root page access; probe?', True)
                return self.send('text/plain', 'hi')
            else: return self.send_data_form()
        if self.path in ('/', '/healthz', '/healthz/'):
            if data.ready(): return self.send('text/plain', 'ok')
            else: return self.send('text/plain', 'error not ready; need password.')
        if self.path in ('/quit', '/quitquitquit', '/q', '/qqq'):
            data = Data()
            return self.send(HTML_CTYPE, log('km database cleared by GET request', True))
        if not data.ready():
            log('Attempt to retrieve key but km not ready: %s' % self.path, True)
            return self.send('text/plain', 'Error- km not ready')
        answer = self.key_lookup()
        if 'ERR' in answer: data = Data()
        self.send('text/plain', answer)

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = urlparse.parse_qs(self.rfile.read(length).decode('utf-8'))
        ok = data.read(DATAFILE, post_data['password'][0])
        self.send(HTML_CTYPE, 'ok' if ok else 'error')


def start_server(HandlerClass = SecureHTTPRequestHandler,
         ServerClass = SecureHTTPServer):
    log('starting km server')
    server_address = ('', PORT) # (address, port)
    ServerClass(server_address, HandlerClass).serve_forever()

# ============================================================

# ---------- helpers

    
              
  

# ---------- key retrieval


# ---------- webserver



# ---------- add new key

def register_new_key(gpg_password, gpg_filename):
    return -1


# ---------- main

def parse_argv(argv):
  ap = argparse.ArgumentParser(description='key manager  server')
  ap.add_argument('--certkeyfile', '-k', default='server.pem', help='name of file with both server TLS key and matching certificate.  set to blank to serve http rather than https (NOT RECOMMENDED!)')
  ap.add_argument('--certkey-password', '-P', default=None, help='password to decrypt private key in --certkeyfile.  Set to "-" to read from stdin.')
  ap.add_argument('--datafile', '-d', default='km.data.gpg', help='name of encrypted file with secrets database')
  ap.add_argument('--dont-panic', action='store_true', help='By default the server will panic (i.e. clear its decrypted secrets database) if just about anything unexpected happens, including any denied request for a key.  This flag disables that, favoring stability over pananoia.')
  ap.add_argument('--logfile', '-l', default='km.log', help='filename for operations log.  "-" for stderr, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=4443, help='port to listen on')
  ap.add_argument('--noratchet', '-R', action='store_true', help='By default each request for a key must come after the last successful request for that key; this prevents request replay attacks.  It also limits key retrievals to one-per-second (for each key).  This disables that limit, and relies just on --window to prevent replay attacks.')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  ap.add_argument('--timeout', '-t', type=int, default=5, help='timeout in seconds for clients')
  ap.add_argument('--window', '-w', type=int, default=30, help='max seconds time difference between client key request and server receipt (i.e. max clock skew between clients and servers).  Set to 0 for "unlimited".')

  group1 = ap.add_argument_group('special', 'alternate modes')
  group1.add_argument('--register', '-r', default=None, help='Add a new key registration blob (generated by "kmc -g") to the database (blob read from stdin), and attempt to reload any running km instances.  Pass the database decryption key as the argument, or specify "-" to read the key from stdin, or "$varname" to read it from an environment variable.')
  return ap.parse_args(argv)


def main(argv):
  args = parse_argv(argv)

  global ARGS
  ARGS = args  # easy communication to things like logging
  
  if args.register: return register_new_key(args.register, args.datafile)

  if args.syslog_ratelimit:
      global RATELIMITER
      RATELIMITER = ratelimiter.RateLimiter(args.syslog_ratelimit)
  

  
if __name__ == '__main__':
    sys.exit(main(argv[1:]))

