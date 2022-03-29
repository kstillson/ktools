
import requests

def Session(unused_pool, unused_ssl_context=None):
    return requests

def set_socket(socket, esp):
    pass

def get(*argv, **kwargs):
    return requests.get(*argv, **kwargs)

def post(*argv, **kwargs):
    return requests.post(*argv, **kwargs)

    
