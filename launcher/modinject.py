"""
CRIMESIGHT Revival - instala los mods de apariencia en los archivos del juego.

Modo sin BepInEx: antes de abrir el juego se reconstruyen, partiendo SIEMPRE de los originales,
los archivos que guardan los stickers y los avatares, anadiendo huecos nuevos al final de las
listas (los del juego no se tocan). Cambiar de mods necesita volver a abrir el juego.

  resources.assets      lista de stickers gratuitos (set 0) + stickers nuevos
  sharedassets3.assets  datos de los avatares + avatares nuevos
  level3 / level4       listas de iconos del menu y de la partida

Se guarda una copia de cada original (<archivo>.original) y "Dejar el juego original" lo
deshace todo. Los ajustes del juego que apunten a un mod que ya no esta se corrigen solos.
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

# Objetos del juego (version final de CRIMESIGHT; se comprueban antes de tocar nada)
STAMP_SET0 = 20998            # StampSet 0 (stickers gratuitos), resources.assets
STAMP_FIRST = "StampData_hello"
QUAD_STICKER = 2681           # sprite 128x128 de 4 vertices ("batsu1_frame"): plantilla de malla
QUAD_STICKER_NAME = "batsu1_frame"
AVATAR_TEMPLATE = "CursorAvatarDataIcon_WolfMan"
QUAD_AVATAR_NAME = "CursorAvatarIcon_SecretSherlock"
ICON_SETS = {"level3": (11627, "sharedassets3.assets"), "level4": (814, "sharedassets3.assets")}
DEFAULT_STAMP = 28            # "hello": sustituye a un sticker de mod que ya no esta
TEXT_KEY = b"ctg_name_log_stamp_hello"   # el archivo de textos (TextAsset "ctg_name") que lo contiene


class InjectError(RuntimeError):
    pass


# ------------------------------------------------------------------ utilidades binarias
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
    """Textura RGBA32 incrustada + sprite que la usa (malla de 4 vertices, sin recortes)."""
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


# ------------------------------------------------------------------ reconstruccion
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
    """Anade al archivo de textos del juego el mensaje de cada sticker ("{player}: <texto>") y su
    nombre, en los 11 idiomas. Devuelve {tipo: (id del mensaje, id del nombre)}."""
    entries, ids = [], {}
    for s in stickers:
        if not s.get("text"):
            continue
        g = modpack.text_for_game(s["text"])
        log_id, doc_id = f"ctg_name_log_stamp_csr_{s['type']}", f"ctg_name_stamp_csr_{s['type']}"
        entries.append({"msg_id": log_id, **{k: "{player}: " + v for k, v in g.items()}})
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
    return {}         # no se encontro: se quedan con el texto de "hola"


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


def _write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


# ------------------------------------------------------------------ estado y originales
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


def current_hash(game_dir):
    return _state(_data_dir(game_dir)).get("hash", "")


def apply(game_dir, rs, log=None):
    """Deja en el juego exactamente el conjunto de mods 'rs' (modpack.room_set). Devuelve True si
    cambio algo. Con un conjunto vacio, vuelve a dejar los archivos originales."""
    dd = _data_dir(game_dir)
    st = _state(dd)
    want = rs["hash"] if rs else ""
    if not want:
        return restore(game_dir)
    if st.get("hash", "") == want and all(
            os.path.isfile(os.path.join(dd, f)) and os.path.getsize(os.path.join(dd, f)) == n
            for f, n in st.get("sizes", {}).items()):
        return False                       # ya estaban puestos (y nadie ha cambiado los archivos)

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
    _save_state(dd, {"hash": want, "sizes": {f: os.path.getsize(os.path.join(dd, f)) for f in FILES},
                     "stickers": [s["type"] for s in rs["stickers"]],
                     "avatars": [a["data_id"] for a in rs["avatars"]]})
    fix_prefs(game_dir, {s["type"] for s in rs["stickers"]}, {a["data_id"] for a in rs["avatars"]})
    return True


def restore(game_dir, fix=True):
    """Quita los mods: vuelve a poner los archivos originales. resources.assets.original lo
    comparte con la linea de creditos, que se vuelve a anadir al abrir el juego."""
    dd = _data_dir(game_dir)
    changed = False
    for f in FILES:
        o, cur = os.path.join(dd, f + ".original"), os.path.join(dd, f)
        # con mods el archivo crece; la linea de creditos no cambia el tamano de resources.assets
        if os.path.isfile(o) and (not os.path.isfile(cur) or os.path.getsize(o) != os.path.getsize(cur)):
            shutil.copy2(o, cur)
            changed = True
    if _state(dd).get("hash") or changed:
        _save_state(dd, {})
        if fix:                       # con la recarga en caliente los mods siguen ahi: no se tocan
            fix_prefs(game_dir, set(), set())
    return changed


# ------------------------------------------------------------------ ajustes guardados del juego
def _prefs_key(game_dir):
    """Clave del registro donde Unity guarda los ajustes (PlayerPrefs): Software\\<empresa>\\<juego>."""
    try:
        with open(os.path.join(_data_dir(game_dir), "app.info"), encoding="utf-8") as f:
            company, product = [ln.strip() for ln in f.read().splitlines()[:2]]
        return f"Software\\{company}\\{product}"
    except (OSError, ValueError):
        return None


def fix_prefs(game_dir, stickers, avatars):
    """Si la rueda de stickers o el avatar elegido apuntan a un mod que ya no esta, los cambia
    por uno del juego para que no falle al abrirse."""
    if sys.platform != "win32":
        return 0
    key = _prefs_key(game_dir)
    if not key:
        return 0
    import winreg
    fixed = 0
    try:
        h = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        return 0
    with h:
        i, values = 0, []
        while True:
            try:
                values.append(winreg.EnumValue(h, i))
            except OSError:
                break
            i += 1
        for name, val, typ in values:
            if name.startswith("stampTypeMenu") and typ == winreg.REG_DWORD:
                v = val & 0xFFFFFFFF
                if (v & 4095) >= modpack.FIRST_TYPE and (v >> 12) == 0 and v not in stickers:
                    winreg.SetValueEx(h, name, 0, winreg.REG_DWORD, DEFAULT_STAMP)
                    fixed += 1
            elif name.startswith("cursorAvatarIconName") and typ == winreg.REG_BINARY:
                s = bytes(val).rstrip(b"\0").decode("utf-8", "replace")
                if s.startswith(modpack.AVATAR_PREFIX) and s not in avatars:
                    winreg.DeleteValue(h, name)        # el juego vuelve a su avatar por defecto
                    fixed += 1
    return fixed
