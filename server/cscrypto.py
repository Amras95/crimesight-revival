"""Encryption compatible with the client (Crypto.Encrypt / Crypto.Decrypt).

AES-256-CBC, PKCS7, random 16-byte IV prepended to the ciphertext.
- "upstream":   client -> server
- "downstream": server -> client
"""
import json, os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

_KEYS = None


def set_keys(keys):
    """For the launcher: keys already read ({"upstream": hex, "downstream": hex})."""
    global _KEYS
    _KEYS = {k: bytes.fromhex(v) for k, v in keys.items()}


def _keys():
    global _KEYS
    if _KEYS is None:
        path = os.environ.get("CSR_KEYS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys.json")
        if not os.path.isfile(path):
            raise SystemExit("Falta server/keys.json. Ejecuta antes tools/extract_keys.py con la carpeta del juego.")
        with open(path) as f:
            _KEYS = {k: bytes.fromhex(v) for k, v in json.load(f).items()}
    return _KEYS


def decrypt(blob: bytes, key: str = "upstream") -> bytes:
    iv, ct = blob[:16], blob[16:]
    p = AES.new(_keys()[key], AES.MODE_CBC, iv).decrypt(ct)
    return p[: -p[-1]]


def encrypt(plain: bytes, key: str = "downstream") -> bytes:
    iv = get_random_bytes(16)
    pad = 16 - len(plain) % 16
    return iv + AES.new(_keys()[key], AES.MODE_CBC, iv).encrypt(plain + bytes([pad]) * pad)
