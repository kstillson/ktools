#!/usr/bin/python

'''Key Master - local network secret bootstrapper.

This is a web-server that hosts a small database of secrets.  Clients request
secrets by providing the name of the secret they want via an http GET request,
and the server checks to see if the source-IP address of the requestor is
allowed for that entry.

The database is stored in a symmetrically encypted GPG file, and the server
does not know the password to it.  This makes it safe to backup the source
directory without exposing secrets (although see notes below concerning the
security of the TLS private key).

To enable the server (i.e. decrypt the database), the service owner must
manually provide the GPG passphrase via a web client (a login-style form is
provided).  Once this is done, the service is up and can serve secrets.

The use-case is services that require some sort of password in order to
initialize, but where you do not wish to build the password into the service.
The service can instead contact the key-master and request its own secrets,
then use those secrets to start-up.  Clients should be smart enough to
auto-retry secret retieval, in-case they contact the key-master at a time when
the database has not yet been unlocked.  A suitable CLI client is provided in
tools_for_users/kmc.sh

The vision is that in the event of a many-service restart, all the systems
that need secerts will go into retry loops until key-master admin enters the
one master password to unlock the database, and then all the services can
auto-restart without further intervention.

This system uses source-IP as the primary access control mechanism.  It is
therefore not suitable for use in networks where source-IP impersonation is
likely to work, or where multiple users have access to IP addresses authorized
to request secrets.  The name of the secret being retrieved can also be used
as a weak second access control, if desired.  (i.e. the client is essentially
exchanging a low-value secret which is stored in its source-code or
configuration for a higher-value secret stored in key-master).

The server is deliberately hyper-sentitive.  A single unauthorized or
not-understood request will cause the server to panic and clear it's decrypted
copy of the database.  The key-master owner must then re-enter the GPG
passphrase before any more secrets can be served.  Thus: (a) use of this
system is not suitable in cases where curious or malicious network users might
cause a denial-of-service by panicing the server, and (b) continuous
monitoring of the service is probably necessary.

The secrets database is formatted like a Windows-style .ini file; see
km-test.data.gpg for an example; the passphrase is "ken123".  Note that the
outside-container Test is currently dependent on this file's current contents.
'''

# ssl wrapper reference:
# http://rzemieniecki.wordpress.com/2012/08/10/quick-solution-to-ssl-in-simplexmlrpcserver-python-2-6-and-2-7/
# TODO: update to Python 3.

# Note 1: the provided server.pem is an expired cert that only works for the
# author's domain anyway.  You should either replace it with your own, or
# disable certificate checking.  If you disable cert checking, be aware that
# you expose this serviec to a man-in-the-middle attack, so make sure you
# trust your network before going down that path.  (You really need to trust
# your local network anyway, as source-IP checks are critical to the security
# model here.)

# Note 2: unless you have some sort of meta-keymaster to bootstrap the
# keymaster, it's not possible to password protect the private key embedded in
# the CERTKEYFILE.  So either protect your source code (think about where it's
# getting backed up, etc), or make sure it's not a particularly valuable
# certificate!
# TODO: build in support for a creating a self-signed CA with matching client
#       code to check against it.


DATAFILE = '/home/km/km.data.gpg'
CERTKEYFILE = '/home/km/server.pem'
PORT = 4443

HTML_CTYPE = 'text/html'
HTML_HEADER = '<html>\n<head><title>keymanager</title></head>\n<body>\n'
HTML_FOOTER = '\n</body>\n</html>\n'

import ConfigParser, socket, ssl, subprocess, sys, time, urlparse
import ratelimiter
from cStringIO import StringIO
from SocketServer import BaseServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


# Unique message can only be emitted as alerts once per hour.
RL_LOG = ratelimiter.RateLimiter(60 * 60)


def log(msg, alert=False):
    if alert:
        if RL_LOG.check(msg): msg = 'ALERT: %s' % msg
        else: msg = '(rate-limited): %s' % msg
    sys.stderr.write('%s\n' % msg)
    return msg


def log_f(msg, alert=False):
    log(msg, alert)
    return False


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


if __name__ == '__main__':
    start_server()

