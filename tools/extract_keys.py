#!/usr/bin/env python3
"""
CRIMESIGHT Revival - extractor de claves.

El cliente cifra todo el trafico con AES-256-CBC. Las claves viajan dentro
del propio juego (Resources/Keys). Este script las lee de TU instalacion y
las guarda en server/keys.json para que el servidor local pueda hablar con
el cliente. El proyecto no distribuye ninguna clave ni archivo de Konami.

Requisitos: pip install UnityPy pycryptodome
Uso:        python extract_keys.py "<carpeta del juego>"
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
    """Descifra una clave guardada en el juego; None si 'mask' no es la buena."""
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
    """Las claves del juego estan protegidas con una mascara que el propio juego lleva como texto
    (Crypto.LoadKeys). No se copia en este proyecto: se busca entre los textos de 32 caracteres de la
    instalacion del jugador y se prueba cual descifra las claves."""
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
    """Lee las claves de la instalacion del jugador. Devuelve {"upstream": hex, "downstream": hex}."""
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
