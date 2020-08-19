"""Print thumbprint."""
from __future__ import print_function

import json
import socket
import sys

import requests
from cryptography.hazmat.primitives import serialization
from OpenSSL import SSL
from OpenSSL.crypto import FILETYPE_PEM, load_certificate
from six.moves.urllib.parse import urlparse  # pylint: disable=E  # python 2 only

JWKS_URI = requests.get(
    url=json.loads(sys.stdin.read())["url"] + "/.well-known/openid-configuration"
).json()["jwks_uri"]

URL = urlparse(JWKS_URI).netloc
PORT = urlparse(JWKS_URI).port
DST = (URL, PORT if PORT else 443)
CTX = SSL.Context(SSL.SSLv23_METHOD)
CON = SSL.Connection(CTX, socket.create_connection(DST))
CON.set_connect_state()
if sys.version_info[0] < 3:
    HOSTNAME = bytes(DST[0])
    DATA_TO_SEND = bytes("HEAD / HTTP/1.0\n\n")
else:
    HOSTNAME = bytes(DST[0], "utf-8")
    DATA_TO_SEND = bytes("HEAD / HTTP/1.0\n\n", "utf-8")
CON.set_tlsext_host_name(HOSTNAME)

CON.sendall(DATA_TO_SEND)
CON.recv(16)

CERTS = CON.get_peer_cert_chain()
CACERT = load_certificate(
    FILETYPE_PEM, CERTS[-1].to_cryptography().public_bytes(serialization.Encoding.PEM)
)
if sys.version_info[0] < 3:
    THUMBPRINT = str(CACERT.digest("sha1")).encode("utf-8").replace(":", "").lower()
else:
    THUMBPRINT = str(CACERT.digest("sha1"), "utf-8").replace(":", "").lower()

print(json.dumps({"thumbprint": THUMBPRINT}))
