"""Utility functions for JWKS RSA library."""
import base64
import codecs
import logging
import re

LOGGER = logging.getLogger(__name__)


def prepad_signed(hex_str):
    """Given a hexadecimal string prepad with 00 if not within range.

    Keyword Args:
        hex_str (string): The hexadecimal string
    """
    msb = hex_str[0]
    if (msb < '0' or msb > '7'):
        return '00%s' % hex_str
    return hex_str


def to_hex(number):
    """Convert an integer to appropriate hex.

    Keyword Args:
        number (int): The number to convert
    """
    n_str = format(int(number), 'x')
    if len(n_str) % 2:
        return '0%s' % n_str
    return n_str


def encode_length_hex(number):
    """Encode the length value to a hexadecimal.

    Keyword Args:
        number (int): The number to convert
    """
    if number <= 127:
        return to_hex(number)
    n_hex = to_hex(number)
    length = int(128 + len(n_hex) / 2)
    return to_hex(length) + n_hex


def rsa_public_key_to_pem(modulus_b64, exponent_b64):
    """Given an modulus and exponent convert an RSA public key to public PEM.

    Keyword Args:
        modulus_b64 (string): Base64 encoded modulus
        exponent_b64 (string): Base64 encoded exponent
    """
    modulus = base64.urlsafe_b64decode(modulus_b64 + "===")
    exponent = base64.urlsafe_b64decode(exponent_b64 + "===")
    modulus_hex = prepad_signed(modulus.hex())
    exponent_hex = prepad_signed(exponent.hex())
    mod_len = int(len(modulus_hex) / 2)
    exp_len = int(len(exponent_hex) / 2)

    encoded_mod_len = encode_length_hex(mod_len)
    encoded_exp_len = encode_length_hex(exp_len)

    encoded_pub_key = '30'
    encoded_pub_key += encode_length_hex(
        mod_len + exp_len + len(encoded_mod_len) / 2 + len(encoded_exp_len) / 2 + 2
    )
    encoded_pub_key += '02' + encoded_mod_len + modulus_hex
    encoded_pub_key += '02' + encoded_exp_len + exponent_hex

    der = base64.b64encode(codecs.decode(encoded_pub_key, 'hex'))

    pem = '-----BEGIN RSA PUBLIC KEY-----\n'
    pem += '\n'.join(re.findall('.{1,64}', der.decode()))
    pem += '\n-----END RSA PUBLIC KEY-----\n'
    return pem
