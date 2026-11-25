#!/usr/bin/env python3
"""
CRIMESIGHT Revival - key extractor.

The client encrypts all traffic with AES-256-CBC. The keys travel inside
the game itself (Resources/Keys). This script reads them from YOUR install and
saves them in server/keys.json so the local server can talk to
the client. The project distributes no key or Konami file.

Requirements: pip install UnityPy pycryptodome
Usage:        python extract_keys.py "<game folder>"
"""
import json, os, sys

try:
    import UnityPy
    from Crypto.Cipher import AES
except ImportError:
    sys.exit("Faltan dependencias: pip install UnityPy pycryptodome")

WANTED = {"upstream", "downstream"}
META_REL = os.path.join("CrimeSight_Data", "il2cpp_data", "Metadata", "global-metadata.dat")


def _unwrap(mask: bytes, blob: bytes):
    """Decrypts a key stored in the game; None if 'mask' isn't the right one."""
    iv, ct = blob[:16], blob[16:]
    if len(ct) == 0 or len(ct) % 16:
        return None
    p = AES.new(mask, AES.MODE_CBC, iv).decrypt(ct)
    pad = p[-1]
    if not 1 <= pad <= 16 or p[-pad:] != bytes([pad]) * pad:
        return None
    key = p[:-pad]
    return key if len(key) == 32 else None


def _candidate_masks(game_dir):
    """The game's keys are protected with a mask the game itself carries as text
    (Crypto.LoadKeys). It isn't copied into this project: it is searched for among the 32-character texts of the
    player's install, trying which one decrypts the keys."""
    import struct
    meta = os.path.join(game_dir, META_REL)
    src = meta + ".original" if os.path.isfile(meta + ".original") else meta
    buf = open(src, "rb").read()
    lit_off, lit_size, data_off, _ = struct.unpack_from("<iiii", buf, 8)
    for i in range(lit_size // 8):
        length, idx = struct.unpack_from("<Ii", buf, lit_off + i * 8)
        if length == 32:
            yield bytes(buf[data_off + idx:data_off + idx + 32])


def extract(game_dir):
    """Reads the keys from the player's install. Returns {"upstream": hex, "downstream": hex}."""
    assets = os.path.join(game_dir, "CrimeSight_Data", "resources.assets")
    if not os.path.isfile(assets):
        raise ValueError(f"No encuentro {assets}")
    blobs = {}
    env = UnityPy.load(assets)
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        d = obj.read()
        name = d.m_Name.lower()
        if name in WANTED:
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode("utf-8", "surrogateescape")
            blobs[name] = bytes(raw)
    if set(blobs) != WANTED:
        raise ValueError(f"Solo he encontrado {sorted(blobs)}; ¿version distinta del juego?")
    for mask in _candidate_masks(game_dir):
        keys = {n: _unwrap(mask, b) for n, b in blobs.items()}
        if all(keys.values()):
            return {n: k.hex() for n, k in keys.items()}
    raise ValueError("No he podido leer las claves de tu copia del juego. ¿Version distinta del juego?")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        keys = extract(sys.argv[1])
    except ValueError as e:
        sys.exit(str(e))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server", "keys.json")
    with open(out, "w") as f:
        json.dump(keys, f, indent=1)
    print(f"Claves guardadas en {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
