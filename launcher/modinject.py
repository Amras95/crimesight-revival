"""
CRIMESIGHT Revival - installs the appearance mods into the game's files.

Mode without BepInEx: before opening the game, the files that store the stickers and avatars are rebuilt,
ALWAYS starting from the originals, adding new slots at the end of the
lists (the game's own aren't touched). Changing mods needs the game to be reopened.

  resources.assets      list of free stickers (set 0) + new stickers
  sharedassets3.assets  avatar data + new avatars
  level3 / level4       icon lists of the menu and the match

A copy of each original is kept (<file>.original) and "Restore the original game"
undoes everything. The saved settings (sticker wheel, avatar) are never touched.
"""
import copy, json, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "..", "server"), os.path.join(getattr(sys, "_MEIPASS", HERE), "server")):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
import modpack  # noqa: E402

DATA = "CrimeSight_Data"
STATE = "csr_mods.json"
FILES = ("resources.assets", "sharedassets3.assets", "level3", "level4")

# Game objects (final version of CRIMESIGHT; checked before touching anything)
STAMP_SET0 = 20998            # StampSet 0 (free stickers), resources.assets
STAMP_FIRST = "StampData_hello"
QUAD_STICKER = 2681           # 128x128 4-vertex sprite ("batsu1_frame"): mesh template
QUAD_STICKER_NAME = "batsu1_frame"
AVATAR_TEMPLATE = "CursorAvatarDataIcon_WolfMan"
QUAD_AVATAR_NAME = "CursorAvatarIcon_SecretSherlock"
ICON_SETS = {"level3": (11627, "sharedassets3.assets"), "level4": (814, "sharedassets3.assets")}
# Version of how the mods are inserted: when it changes, the files are rebuilt even if the mods are the same
# (2: stickers without a message carry empty texts instead of the "Hello" ones)
BUILD = 2
TEXT_KEY = b"ctg_name_log_stamp_hello"   # the text file (TextAsset "ctg_name") that contains it


class InjectError(RuntimeError):
    pass


# ------------------------------------------------------------------ binary helpers
def _str_at(raw, off):
    n = struct.unpack_from("<i", raw, off)[0]
    return raw[off + 4:off + 4 + n].decode("utf-8", "replace"), off + 4 + ((n + 3) & ~3)


def _pstr(s):
    b = s.encode()
    return struct.pack("<i", len(b)) + b + b"\0" * ((-len(b)) % 4)


def _clone(sf, orig, new_id):
    c = copy.copy(orig)
    c.path_id, c.data = new_id, None
    sf.objects[new_id] = c
    return c


def _add_image(sf, quad_sprite_id, img, name, tid, sid):
    """Embedded RGBA32 texture + sprite using it (4-vertex mesh, no cropping)."""
    from UnityPy.enums import TextureFormat
    so = sf.objects[quad_sprite_id]
    sp = so.read()
    tc = _clone(sf, sf.objects[sp.m_RD.texture.m_PathID], tid)
    t = tc.read()
    t.m_Name = name
    t.m_StreamData.path, t.m_StreamData.offset, t.m_StreamData.size = "", 0, 0
    t.m_MipCount = 1
    t.set_image(img, target_format=TextureFormat.RGBA32, mipmap_count=1)
    t.save()
    sc = _clone(sf, so, sid)
    s = sc.read()
    s.m_Name = name
    s.m_RD.texture.m_PathID = tid
    s.save()


def _load(path):
    import UnityPy
    env = UnityPy.load(path)
    return env, list(env.files.values())[0]


def _mb_name(obj):
    raw = obj.get_raw_data()
    if len(raw) < 32:
        return None, raw
    try:
        return _str_at(raw, 28)[0], raw
    except struct.error:
        return None, raw


# ------------------------------------------------------------------ rebuild
def _build_stickers(src, dst, stickers):
    from PIL import Image
    env, sf = _load(src)
    objs = sf.objects
    setobj = objs.get(STAMP_SET0)
    if setobj is None:
        raise InjectError("version del juego no compatible (sin lista de stickers)")
    sraw = bytearray(setobj.get_raw_data())
    _, off = _str_at(sraw, 28)
    set_id, cnt = struct.unpack_from("<ii", sraw, off + 4)
    first = struct.unpack_from("<iq", sraw, off + 12)
    tmpl = objs.get(first[1])
    tname, traw = _mb_name(tmpl) if tmpl else (None, b"")
    quad = objs.get(QUAD_STICKER)
    if set_id != 0 or tname != STAMP_FIRST or quad is None or quad.peek_name() != QUAD_STICKER_NAME:
        raise InjectError("version del juego no compatible (stickers)")
    _, p = _str_at(traw, 28)
    q = p + 44
    log_id, q = _str_at(traw, q)
    doc_id, q = _str_at(traw, q)
    custom = _add_texts(sf, stickers)
    nid = max(objs) + 1
    for s in stickers:
        tid, sid, bt, bs, mid = nid, nid + 1, nid + 2, nid + 3, nid + 4
        nid += 5
        import io
        fg = Image.open(io.BytesIO(s["png"])).convert("RGBA")
        _add_image(sf, QUAD_STICKER, fg, s["name"], tid, sid)
        _add_image(sf, QUAD_STICKER, modpack.sticker_background(s["png"]), s["name"] + "_bg", bt, bs)
        raw = (traw[:28] + _pstr("StampData_" + s["name"]) + struct.pack("<ii", 0, s["type"])
               + struct.pack("<iq", 0, sid) + struct.pack("<iq", 0, bs) + struct.pack("<iq", 0, 0)
               + _pstr(custom.get(s["type"], (log_id, doc_id))[0]) + _pstr(custom.get(s["type"], (log_id, doc_id))[1])
               + _pstr("") + _pstr(""))
        _clone(sf, tmpl, mid).data = raw
        sraw += struct.pack("<iq", 0, mid)
        cnt += 1
    struct.pack_into("<i", sraw, off + 8, cnt)
    setobj.data = bytes(sraw)
    _write(dst, sf.save())


def _add_texts(sf, stickers):
    """Adds each sticker's message ("{player}: <text>") and its name to the game's text file,
    in the 11 languages. Returns {type: (message id, name id)}.
    A sticker without a message carries empty texts: otherwise, it would keep the ones of the copied sticker
    ("Hello"). Without the BepInEx plugin the log line can't be avoided, and it shows empty."""
    entries, ids = [], {}
    for s in stickers:
        log_id, doc_id = f"ctg_name_log_stamp_csr_{s['type']}", f"ctg_name_stamp_csr_{s['type']}"
        if s.get("text"):
            g = modpack.text_for_game(s["text"])
            entries.append({"msg_id": log_id, **{k: "{player}: " + v for k, v in g.items()}})
        else:
            g = {lang: "" for lang in modpack.LANGS.values()}
            entries.append({"msg_id": log_id, **g})
        entries.append({"msg_id": doc_id, **g})
        ids[s["type"]] = (log_id, doc_id)
    if not entries:
        return {}
    for o in sf.objects.values():
        if o.type.name != "TextAsset" or TEXT_KEY not in o.get_raw_data():
            continue
        t = o.read()
        script = t.m_Script if isinstance(t.m_Script, str) else t.m_Script.decode("utf-8-sig")
        bom = script.startswith("\ufeff")
        data = json.loads(script.lstrip("\ufeff"))
        if not isinstance(data, dict) or not isinstance(data.get("CTG"), list):
            break
        data["CTG"].extend(entries)
        t.m_Script = ("\ufeff" if bom else "") + json.dumps(data, ensure_ascii=False, indent=4)
        t.save()
        return ids
    return {}         # not found: they keep the "hello" text


def _build_avatars(data_dir, orig, avatars):
    from PIL import Image
    import io
    env, sf = _load(orig("sharedassets3.assets"))
    objs = sf.objects
    tmpl = traw = None
    quad = None
    for o in objs.values():
        if o.type.name == "MonoBehaviour" and tmpl is None:
            name, raw = _mb_name(o)
            if name == AVATAR_TEMPLATE:
                tmpl, traw = o, raw
        elif o.type.name == "Sprite" and quad is None and o.peek_name() == QUAD_AVATAR_NAME:
            quad = o.path_id
    if tmpl is None or quad is None:
        raise InjectError("version del juego no compatible (avatares)")
    nid = max(objs) + 1
    new_ids = []
    for a in avatars:
        tid, sid, mid = nid, nid + 1, nid + 2
        nid += 3
        _add_image(sf, quad, Image.open(io.BytesIO(a["png"])).convert("RGBA"), a["name"], tid, sid)
        raw = (traw[:28] + _pstr("CursorAvatarData" + a["name"]) + struct.pack("<i", 0)
               + struct.pack("<iq", 0, sid) + _pstr(a["data_id"]) + _pstr("") + _pstr("") + _pstr("") + _pstr(""))
        _clone(sf, tmpl, mid).data = raw
        new_ids.append(mid)
    _write(os.path.join(data_dir, "sharedassets3.assets"), sf.save())

    for level, (set_id, target) in ICON_SETS.items():
        env, lf = _load(orig(level))
        ext = [os.path.basename(e.path) for e in lf.externals]
        if target not in ext or set_id not in lf.objects:
            raise InjectError("version del juego no compatible (lista de iconos)")
        fid = ext.index(target) + 1
        o = lf.objects[set_id]
        r = bytearray(o.get_raw_data())
        _, off = _str_at(r, 28)
        cnt = struct.unpack_from("<i", r, off)[0]
        if len(r) != off + 4 + cnt * 12:
            raise InjectError("version del juego no compatible (lista de iconos)")
        struct.pack_into("<i", r, off, cnt + len(new_ids))
        for mid in new_ids:
            r += struct.pack("<iq", fid, mid)
        o.data = bytes(r)
        _write(os.path.join(data_dir, level), lf.save())


def _write(path, data, tries=30, wait=0.5):
    """Writes to a .tmp and swaps it for the original. If the antivirus is scanning the freshly written .tmp
    (or the original), Windows won't rename it ("Access denied"): it retries for a few seconds."""
    import time
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    for i in range(tries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == tries - 1:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
            time.sleep(wait)


# ------------------------------------------------------------------ state and originals
def _data_dir(game_dir):
    return os.path.join(game_dir, DATA)


def _ensure_originals(data_dir, files):
    for f in files:
        path = os.path.join(data_dir, f)
        if not os.path.isfile(path + ".original"):
            if _state(data_dir).get("hash"):
                raise InjectError(f"falta la copia original de {f}; verifica los archivos del juego en Steam")
            shutil.copy2(path, path + ".original")


def _state(data_dir):
    try:
        with open(os.path.join(data_dir, STATE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(data_dir, st):
    path = os.path.join(data_dir, STATE)
    if st.get("hash"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f)
    elif os.path.isfile(path):
        os.remove(path)


def apply(game_dir, rs, log=None):
    """Leaves exactly the mod set 'rs' (modpack.room_set) in the game. Returns True if
    something changed. With an empty set, the original files are put back."""
    dd = _data_dir(game_dir)
    st = _state(dd)
    want = rs["hash"] if rs else ""
    if not want:
        return restore(game_dir)
    if st.get("hash", "") == want and st.get("build") == BUILD and all(
            os.path.isfile(os.path.join(dd, f)) and os.path.getsize(os.path.join(dd, f)) == n
            for f, n in st.get("sizes", {}).items()):
        return False                       # already in place (and nobody changed the files)

    def orig(name):
        return os.path.join(dd, name + ".original")
    _ensure_originals(dd, FILES)
    if log:
        log(len(rs["stickers"]), len(rs["avatars"]))
    if rs["stickers"]:
        _build_stickers(orig("resources.assets"), os.path.join(dd, "resources.assets"), rs["stickers"])
    else:
        shutil.copy2(orig("resources.assets"), os.path.join(dd, "resources.assets"))
    if rs["avatars"]:
        _build_avatars(dd, orig, rs["avatars"])
    else:
        for f in ("sharedassets3.assets", "level3", "level4"):
            if os.path.isfile(orig(f)):
                shutil.copy2(orig(f), os.path.join(dd, f))
    _save_state(dd, {"hash": want, "build": BUILD, "sizes": {f: os.path.getsize(os.path.join(dd, f)) for f in FILES},
                     "stickers": [s["type"] for s in rs["stickers"]],
                     "avatars": [a["data_id"] for a in rs["avatars"]]})
    return True


def restore(game_dir, fix=True):
    """Removes the mods: puts the original files back. resources.assets.original is
    shared with the credits line, which is added again when opening the game."""
    dd = _data_dir(game_dir)
    changed = False
    for f in FILES:
        o, cur = os.path.join(dd, f + ".original"), os.path.join(dd, f)
        # with mods the file grows; the credits line doesn't change resources.assets' size
        if os.path.isfile(o) and (not os.path.isfile(cur) or os.path.getsize(o) != os.path.getsize(cur)):
            shutil.copy2(o, cur)
            changed = True
    if _state(dd).get("hash") or changed:
        _save_state(dd, {})
    return changed
