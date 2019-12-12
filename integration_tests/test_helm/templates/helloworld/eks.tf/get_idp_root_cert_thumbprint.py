"""Print thumbprint."""
from __future__ import print_function
import json
import socket
import sys
# This false pylint error is only an issue on py2
from six.moves.urllib.parse import urlparse  # pylint: disable=relative-import
import requests
from cryptography.hazmat.primitives import serialization
from OpenSSL import SSL
from OpenSSL.crypto import load_certificate, FILETYPE_PEM


JWKS_URI = requests.get(
    url=json.loads(sys.stdin.read())['url'] + '/.well-known/openid-configuration'
).json()['jwks_uri']

URL = urlparse(JWKS_URI).netloc
PORT = urlparse(JWKS_URI).port
DST = (URL, PORT if PORT else 443)
CTX = SSL.Context(SSL.SSLv23_METHOD)
CON = SSL.Connection(CTX, socket.create_connection(DST))
CON.set_connect_state()
HOSTNAME = bytes(DST[0], 'utf-8')
CON.set_tlsext_host_name(HOSTNAME)

CON.sendall(bytes('HEAD / HTTP/1.0\n\n', 'utf-8'))
CON.recv(16)

CERTS = CON.get_peer_cert_chain()
CACERT = load_certificate(
    FILETYPE_PEM,
    CERTS[-1].to_cryptography().public_bytes(serialization.Encoding.PEM)
)
THUMBPRINT = str(CACERT.digest('sha1'), 'utf-8').replace(':', '').lower()

print(json.dumps({'thumbprint': THUMBPRINT}))
