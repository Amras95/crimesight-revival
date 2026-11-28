#!/usr/bin/env python3
"""
CRIMESIGHT Revival - client patcher.

Replaces the address of the official server (now closed) inside
CrimeSight_Data/il2cpp_data/Metadata/global-metadata.dat with a
community server's. Keeps a copy of the original and can be reverted.

Usage:
  python patch_client.py "<game folder>"                      -> http://127.0.0.1:18080
  python patch_client.py "<game folder>" --url http://192.168.1.50:18080   (no length limit)
  python patch_client.py "<game folder>" --restore
"""
import argparse, os, shutil, struct, sys

ORIGINAL = "https://cott-game.cs.konami.net"
META_REL = os.path.join("CrimeSight_Data", "il2cpp_data", "Metadata", "global-metadata.dat")
SANITY = 0xFAB11BAF


def literal_table(buf):
    sanity, version = struct.unpack_from("<Ii", buf, 0)
    if sanity != SANITY:
        sys.exit("global-metadata.dat no tiene el formato esperado (cabecera desconocida).")
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<iiii", buf, 8)
    return version, lit_off, lit_size // 8, data_off


def find_server_literal(buf, candidates):
    version, lit_off, count, data_off = literal_table(buf)
    for i in range(count):
        length, idx = struct.unpack_from("<Ii", buf, lit_off + i * 8)
        s = bytes(buf[data_off + idx:data_off + idx + length])
        if s.startswith(b"https://cott-game.") or s in candidates:
            return lit_off + i * 8, data_off + idx, length, s.decode("utf-8", "replace")
    return None


def patch(game_dir, url="http://127.0.0.1:18080"):
    """Points the game at 'url'. Returns a text with what was done. Raises ValueError if something fails."""
    meta = os.path.join(game_dir, META_REL)
    backup = meta + ".original"
    if not os.path.isfile(meta):
        raise ValueError(f"No encuentro {meta}. ¿Es la carpeta de CrimeSight?")
    url = url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ValueError("La URL debe empezar por http:// o https://")
    if not os.path.isfile(backup):
        shutil.copy2(meta, backup)
    # We always start from the original: the server can be changed as many times as wanted.
    buf = bytearray(open(backup, "rb").read())
    hit = find_server_literal(buf, {ORIGINAL.encode()})
    if not hit:
        raise ValueError("No encuentro la direccion del servidor en el archivo. ¿Version distinta del juego?")
    entry_pos, data_pos, old_len, old = hit
    new = url.encode()
    if len(new) <= old_len:
        buf[data_pos:data_pos + old_len] = new + b"\x00" * (old_len - len(new))
        struct.pack_into("<I", buf, entry_pos, len(new))
    else:
        # Address longer than the original: it is appended at the end of the file and pointed to there.
        # (IL2CPP reads the strings as file_base + strings_start + index.)
        _, _, _, data_off = literal_table(buf)
        while len(buf) % 8:
            buf.append(0)
        idx = len(buf) - data_off
        buf += new + b"\x00"
        struct.pack_into("<Ii", buf, entry_pos, len(new), idx)
    open(meta, "wb").write(buf)
    return f"{old}  ->  {url}"


def restore(game_dir):
    meta = os.path.join(game_dir, META_REL)
    backup = meta + ".original"
    if not os.path.isfile(backup):
        return False
    shutil.copy2(backup, meta)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game_dir")
    ap.add_argument("--url", default="http://127.0.0.1:18080")
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    if a.restore:
        print("Restaurado el archivo original." if restore(a.game_dir) else "El juego no parece parcheado.")
        return
    try:
        print("Parcheado:", patch(a.game_dir, a.url))
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
