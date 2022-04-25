
import time

#argparse- import kcore.auth as A
import kcore.common as C
import kcore.gpio as G
import kcore.html as H
import kcore.neo as N
import kcore.webserver_circpy as W
import kcore.varz as V


def default_handler(request):
    name = request.get_params['name'] or 'world'
    return f'Hello {name}!'


def main():
    W.connect_wifi('dhcp-hostname', 'ssid', 'wifi-password')
    svr = W.WebServer({'.*': default_handler}, port=1234)
    while True:
        status = svr.listen()
        time.sleep(0.3)


if __name__ == '__main__':
    main()
