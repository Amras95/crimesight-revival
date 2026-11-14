#!/usr/bin/env python3
"""
CRIMESIGHT Revival - parcheador del cliente.

Cambia la direccion del servidor oficial (ya cerrado) dentro de
CrimeSight_Data/il2cpp_data/Metadata/global-metadata.dat por la de un
servidor comunitario. Guarda una copia del original y se puede revertir.

Uso:
  python patch_client.py "<carpeta del juego>"                      -> http://127.0.0.1:18080
  python patch_client.py "<carpeta del juego>" --url http://192.168.1.50:18080   (sin limite de longitud)
  python patch_client.py "<carpeta del juego>" --restore
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
    """Apunta el juego a 'url'. Devuelve un texto con lo hecho. Lanza ValueError si algo falla."""
    meta = os.path.join(game_dir, META_REL)
    backup = meta + ".original"
    if not os.path.isfile(meta):
        raise ValueError(f"No encuentro {meta}. ¿Es la carpeta de CrimeSight?")
    url = url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ValueError("La URL debe empezar por http:// o https://")
    if not os.path.isfile(backup):
        shutil.copy2(meta, backup)
    # Siempre partimos del original: se puede cambiar de servidor cuantas veces se quiera.
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
        # Direccion mas larga que la original: se anade al final del archivo y se apunta alli.
        # (IL2CPP lee los textos como base_del_archivo + inicio_de_textos + indice.)
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


def current_url(game_dir):
    """Direccion a la que apunta ahora el juego (None si no se puede leer)."""
    meta = os.path.join(game_dir, META_REL)
    src = meta + ".original" if os.path.isfile(meta + ".original") else meta
    if not os.path.isfile(meta):
        return None
    hit = find_server_literal(bytearray(open(src, "rb").read()), {ORIGINAL.encode()})
    if not hit:
        return None
    buf = open(meta, "rb").read()
    _, _, _, data_off = literal_table(buf)
    length, idx = struct.unpack_from("<Ii", buf, hit[0])
    return buf[data_off + idx:data_off + idx + length].decode("utf-8", "replace")


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
