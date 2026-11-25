"""
CRIMESIGHT Revival - credits line on the title screen.

Adds to the title screen's copyright line ("©2022 Konami Digital Entertainment") the
CREDITS text and, after it, "Contributions by Ashen" translated into each language (like in the game's
Revival credits and in the launcher). Konami's logo and copyright aren't touched.

How it works: the game's texts are indented JSON inside resources.assets. The affected JSON
is rewritten without indentation (it takes much less), the credit is added and it is padded with spaces
up to the original size, so the file changes neither size nor structure. A
copy of the original is kept (resources.assets.original) and it can be undone with --restore.

Usage:
  python credits_patch.py "<game folder>"
  python credits_patch.py "<game folder>" --restore
"""
import json, os, shutil, struct, sys

ASSETS_REL = os.path.join("CrimeSight_Data", "resources.assets")
MSG_ID = "ctg_outgame_title_copyright"
MARK = "CRIMESIGHT REVIVAL"

# --- Credits (edit here) ---------------------------------------------------------------
GITHUB = "Amras95"
TWITTER = "AmrasMithandir"
CREDITS = f"   ·   {MARK}  —  GitHub: {GITHUB}  ·  X: @{TWITTER}"
CONTRIBUTOR = "Ashen"
# "Contributions by" in each of the game's languages (same words as the in-game Revival Credits)
CONTRIBUTIONS = {
    "Japanese": f"協力: {CONTRIBUTOR}", "English": f"Contributions by {CONTRIBUTOR}",
    "French": f"Contributions d'{CONTRIBUTOR}", "Italian": f"Contributi di {CONTRIBUTOR}",
    "German": f"Beiträge von {CONTRIBUTOR}", "Spanish": f"Contribuciones de {CONTRIBUTOR}",
    "Portuguese": f"Contribuições de {CONTRIBUTOR}", "Russian": f"При участии {CONTRIBUTOR}",
    "Korean": f"기여: {CONTRIBUTOR}", "Chinese-cn": f"贡献者：{CONTRIBUTOR}", "Chinese-tw": f"貢獻者：{CONTRIBUTOR}",
}


def credits_for(lang):
    """The whole Revival part of the line for one of the game's languages (English if it isn't known)."""
    return CREDITS + "  ·  " + CONTRIBUTIONS.get(lang, CONTRIBUTIONS["English"])


def _find_blob(d, at):
    """Start and length of the JSON text (TextAsset) that contains position 'at'."""
    for p in range(at, max(0, at - 30_000_000), -1):
        if d[p] not in (0x7B, 0x5B, 0xEF):          # '{', '[', BOM
            continue
        length = struct.unpack_from("<i", d, p - 4)[0]
        if 1000 < length < 60_000_000 and p + length > at:
            try:
                data = json.loads(bytes(d[p:p + length]).decode("utf-8-sig"))
            except ValueError:
                continue
            return p, length, data
    return None


def _apply(data, text):
    changed = 0

    def walk(o):
        nonlocal changed
        if isinstance(o, dict):
            if o.get("msg_id") == MSG_ID:
                for k, v in list(o.items()):
                    if k != "msg_id" and isinstance(v, str):
                        base = v.split("   ·   " + MARK)[0]
                        o[k] = base + (text if text is not None else credits_for(k))
                        changed += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return changed


def patch(game_dir, text=None):
    path = os.path.join(game_dir, ASSETS_REL)
    if not os.path.isfile(path):
        raise ValueError(f"No encuentro {path}")
    backup = path + ".original"
    if not os.path.isfile(backup):
        shutil.copy2(path, backup)
    with open(path, "rb") as f:
        d = bytearray(f.read())
    key = f'"msg_id": "{MSG_ID}"'.encode()
    compact_key = f'"msg_id":"{MSG_ID}"'.encode()
    done = 0
    pos = 0
    edits = []                      # (position, bytes): the text block changes without changing size
    while True:
        a, b = d.find(key, pos), d.find(compact_key, pos)
        hits = [x for x in (a, b) if x >= 0]
        if not hits:
            break
        at = min(hits)
        found = _find_blob(d, at)
        if not found:
            pos = at + 1
            continue
        start, length, data = found
        bom = d[start:start + 3] == b"\xef\xbb\xbf"
        if _apply(data, text):
            new = (b"\xef\xbb\xbf" if bom else b"") + json.dumps(data, ensure_ascii=False,
                                                              separators=(",", ":")).encode("utf-8")
            if len(new) > length:
                raise ValueError("El credito no cabe en el archivo de textos.")
            block = new + b" " * (length - len(new))
            d[start:start + length] = block
            edits.append((start, bytes(block)))
            done += 1
        pos = start + length
    if not done:
        raise ValueError("No encuentro la linea de copyright de la pantalla de titulo.")
    # Only those bytes are written, in the same file: no copying the whole .assets (hundreds of MB)
    # to a .tmp and renaming it, which the antivirus scans right away and blocks ("Access denied").
    with open(path, "r+b") as f:
        for start, block in edits:
            f.seek(start)
            f.write(block)
    try:
        os.remove(path + ".tmp")    # the one earlier versions left if they failed
    except OSError:
        pass
    return done


def is_patched(game_dir, text=None):
    path = os.path.join(game_dir, ASSETS_REL)
    wanted = [text] if text is not None else [credits_for(k) for k in CONTRIBUTIONS]
    try:
        with open(path, "rb") as f:
            d = f.read()
        return all(w.encode("utf-8") in d for w in wanted)
    except OSError:
        return False


def restore(game_dir):
    path = os.path.join(game_dir, ASSETS_REL)
    if os.path.isfile(path + ".original"):
        shutil.copy2(path + ".original", path)
        return True
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if "--restore" in sys.argv:
        print("Textos originales restaurados." if restore(sys.argv[1]) else "No habia nada que restaurar.")
        return
    try:
        n = patch(sys.argv[1])
    except ValueError as e:
        sys.exit(str(e))
    print(f"Creditos anadidos a la pantalla de titulo ({n} archivo/s de textos).")


if __name__ == "__main__":
    main()
