"""
CRIMESIGHT Revival - appearance mod packs (new stickers and avatars).

A mod is a normal folder with images (nothing needs zipping):

    mods/
      MyPack/
        stamps/     cat.png, ok.png ...
        avatars/    me.png ...
        mod.json    (optional) {"name": "My pack", "author": "Amras"}

The images adjust themselves: stickers to 128x128 with the game's white border, and
avatars to 256x256 with the drawing centred like the original icons. Mods only ADD
new slots; they never touch the game's stickers or avatars (not the paid ones either).

When someone joins a room with mods, the launcher downloads the host's pack as
temporary mods ("<id>+temp") and deletes them when the session closes. An internal zip travels over the network,
but the player never has to zip or unzip anything.
"""
import hashlib, io, json, os, re, shutil, zipfile

STICKER_SIZE = 128
STICKER_MARGIN = 7
AVATAR_SIZE = 256
AVATAR_BOX = (40, 33, 176)          # x, y and side of the area where the original icons draw (the visible one)
KINDS = ("stickers", "avatars")
# Folder of each kind on disk. Stickers are called "stamps" like in the game, but the kind keeps its old
# name inside the program and in the zip sent over the network, so older launchers and servers still
# understand the packs. The old "stickers" folder is not read any more (nothing is moved for the player).
DIRS = {"stickers": "stamps", "avatars": "avatars"}
OLD_DIRS = ("stickers",)
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
MAX_STICKERS = 60                   # per room
MAX_AVATARS = 30
MAX_INPUT_BYTES = 20 * 1024 * 1024  # per original image (it can be a sheet with many stickers)
MAX_PIECES = 64                     # pieces per sheet
MAX_PACK_BYTES = 24 * 1024 * 1024
TEMP_SUFFIX = "+temp"
FIRST_TYPE, LAST_TYPE = 1000, 4095  # free sticker types (the game uses 0-38)
AVATAR_PREFIX = "Icon_CSR_"


class ModError(ValueError):
    pass


# ------------------------------------------------------------------ images
def _open(data):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 40_000_000
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:  # noqa: BLE001
        raise ModError("imagen no valida")
    if getattr(img, "is_animated", False):
        img.seek(0)
    return img.convert("RGBA")


def _fit(img, side):
    from PIL import Image
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    k = min(side / img.width, side / img.height)
    img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.alpha_composite(img, ((side - img.width) // 2, (side - img.height) // 2))
    return out


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def normalize_many(kind, data):
    """Any image -> list of final PNGs. If it is a sheet with several stickers it is
    split automatically, and if it has no transparency its background is removed (see modimage)."""
    import modimage
    if len(data) > MAX_INPUT_BYTES:
        raise ModError("imagen demasiado grande (maximo 20 MB)")
    img = _open(data)
    if kind == "avatars" and not modimage._has_alpha(img) and not _plain_border(img):
        # a photo or a drawing that reaches the edges: it is used whole. Removing its "background" would open
        # holes in it (light areas touching the edge) that show as grey gaps in the game.
        return [_normalize_img(kind, img)]
    pieces = modimage.extract(img)[:MAX_PIECES]
    return [_normalize_img(kind, p) for p in pieces]


def _plain_border(img, tol=18, share=0.9):
    """True if the image's border is almost all the same colour (a character over a plain background)."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    k = min(1.0, 256 / max(w, h))
    if k < 1.0:
        rgb = rgb.resize((max(1, round(w * k)), max(1, round(h * k))))
        w, h = rgb.size
    px = rgb.load()
    edge = [px[i, 0] for i in range(w)] + [px[i, h - 1] for i in range(w)] + \
           [px[0, j] for j in range(h)] + [px[w - 1, j] for j in range(h)]
    ref = tuple(sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3))
    near = sum(1 for c in edge if max(abs(c[i] - ref[i]) for i in range(3)) <= tol)
    return near >= share * len(edge)


def _normalize_img(kind, img):
    from PIL import Image
    if kind == "stickers":
        canvas = Image.new("RGBA", (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
        inner = _fit(img, STICKER_SIZE - 2 * STICKER_MARGIN)
        canvas.alpha_composite(inner, (STICKER_MARGIN, STICKER_MARGIN))
        return _png(canvas)
    if _cut_off(img):
        return _png(_frame_fill(img))
    x, y, side = AVATAR_BOX
    canvas = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(_fit(img, side), (x, y))
    return _png(canvas)


def _cut_off(img):
    """True if the drawing reaches the edges (a photo, or a bust cut to a square)."""
    a = img.getchannel("A").point(lambda v: 255 if v > 64 else 0)
    bbox = a.getbbox()
    if not bbox:
        return False
    a = a.crop(bbox)
    w, h = a.size
    px = a.load()
    edge = [px[i, 0] for i in range(w)] + [px[i, h - 1] for i in range(w)] + \
           [px[0, j] for j in range(h)] + [px[w - 1, j] for j in range(h)]
    return sum(1 for v in edge if v) > 0.25 * len(edge)


def _place(img, k):
    """The image scaled by k and centred in the visible area (if it is tall, it moves up a bit: faces
    are usually at the top). Returns the final canvas."""
    from PIL import Image
    x, y, side = AVATAR_BOX
    im = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    canvas = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    left = x + (side - im.width) // 2
    top = y + (side - im.height) // 2 if im.height <= side else y - min(im.height - side, round(0.04 * im.height))
    canvas.alpha_composite(im.crop((max(0, -left), max(0, -top), im.width, im.height)), (max(0, left), max(0, top)))
    return canvas


def _coverage(canvas):
    """Share of the visible area that ends up covered (0..1)."""
    x, y, side = AVATAR_BOX
    a = canvas.getchannel("A").crop((x, y, x + side, y + side)).point(lambda v: 255 if v > 64 else 0)
    return a.histogram()[255] / float(side * side)


def _trim_border(img, tol=14, share=0.97):
    """Removes a photo's plain edges (frames, colour strips), which show as gaps in the game."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ref = tuple(sorted(c[i] for c in corners)[1] for i in range(3))

    def flat(cells):
        n = sum(1 for c in cells if max(abs(c[i] - ref[i]) for i in range(3)) <= tol)
        return n >= share * len(cells)

    top, bottom, left, right = 0, h, 0, w
    lim_y, lim_x = h // 4, w // 4
    while top < lim_y and flat([px[i, top] for i in range(left, right)]):
        top += 1
    while h - bottom < lim_y and flat([px[i, bottom - 1] for i in range(left, right)]):
        bottom -= 1
    while left < lim_x and flat([px[left, j] for j in range(top, bottom)]):
        left += 1
    while w - right < lim_x and flat([px[right - 1, j] for j in range(top, bottom)]):
        right -= 1
    if (top, bottom, left, right) != (0, h, 0, w) and right - left > 8 and bottom - top > 8:
        return img.crop((left, top, right, bottom))
    return img


def _frame_fill(img):
    """Photos and busts in the area the game shows (AVATAR_BOX). It zooms in just enough to leave no
    gaps: it tries from "whole" up to "covers the area" and keeps the first zoom that
    covers practically everything (what can't be covered, like a bust's shoulders, is left)."""
    bbox = img.getchannel("A").point(lambda v: 255 if v > 64 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    img = _trim_border(img)
    side = AVATAR_BOX[2]
    w, h = img.size
    k_in, k_out = side / max(w, h), side / min(w, h)
    best = _coverage(_place(img, k_out))
    target = min(0.985, best - 0.005)
    lo, hi = k_in, k_out
    if _coverage(_place(img, lo)) >= target:
        hi = lo
    else:
        for _ in range(12):                 # binary search for the minimum zoom
            mid = (lo + hi) / 2
            if _coverage(_place(img, mid)) >= target:
                hi = mid
            else:
                lo = mid
    out = _place(img, hi)
    return _extend(out)


def _extend(canvas, strip=4):
    """Some frames (the diamond, the hexagon) show a bit more than the AVATAR_BOX area. For each side
    where the image is cut (a photo, or a bust's clothes ending abruptly) its
    last rows are stretched to the edge, so it looks like it goes on. The inside doesn't change; the stretched part is smoothed."""
    from PIL import Image, ImageFilter
    W, H = canvas.size
    a = canvas.getchannel("A").point(lambda v: 255 if v > 200 else 0)
    bbox = a.getbbox()
    if not bbox:
        return canvas
    l, t, r, b = bbox
    if r - l < 16 or b - t < 16:
        return canvas
    px = a.load()

    def cut(points):
        pts = list(points)
        return sum(1 for p in pts if px[p]) >= 0.25 * max(1, len(pts))

    out = canvas.copy()
    if b < H and cut((x, b - 1) for x in range(l, r)):
        piece = out.crop((0, b - strip, W, b)).resize((W, H - b), Image.BILINEAR)
        layer = Image.new("RGBA", (W, H)); layer.paste(piece, (0, b)); layer.alpha_composite(out); out = layer
    if t > 0 and cut((x, t) for x in range(l, r)):
        piece = out.crop((0, t, W, t + strip)).resize((W, t), Image.BILINEAR)
        layer = Image.new("RGBA", (W, H)); layer.paste(piece, (0, 0)); layer.alpha_composite(out); out = layer
    if r < W and cut((r - 1, y) for y in range(t, b)):
        piece = out.crop((r - strip, 0, r, H)).resize((W - r, H), Image.BILINEAR)
        layer = Image.new("RGBA", (W, H)); layer.paste(piece, (r, 0)); layer.alpha_composite(out); out = layer
    if l > 0 and cut((l, y) for y in range(t, b)):
        piece = out.crop((l, 0, l + strip, H)).resize((l, H), Image.BILINEAR)
        layer = Image.new("RGBA", (W, H)); layer.paste(piece, (0, 0)); layer.alpha_composite(out); out = layer
    # only what was added is smoothed (outside the image's box), not the drawing's outline
    outside = Image.new("L", (W, H), 255)
    outside.paste(0, (l, t, r, b))
    out.paste(out.filter(ImageFilter.GaussianBlur(2)), (0, 0), outside)
    out.alpha_composite(canvas)
    return out


def sticker_background(png):
    """White silhouette a bit bigger than the drawing: the border the game's stickers have."""
    from PIL import Image, ImageFilter
    fg = _open(png)
    a = fg.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    a = a.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(0.8))
    bg = Image.new("RGBA", fg.size, (255, 255, 255, 0))
    bg.putalpha(a)
    return bg


def check_normalized(kind, png):
    img = _open(png)
    side = STICKER_SIZE if kind == "stickers" else AVATAR_SIZE
    if img.size != (side, side):
        raise ModError("imagen con un tamano inesperado")


# ------------------------------------------------------------------ mod folders
def _slug(text, n=24):
    s = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-")
    return (s[:n] or "mod").lower()


def _read_meta(folder):
    path = os.path.join(folder, "mod.json")
    try:
        with open(path, encoding="utf-8-sig") as f:
            meta = json.load(f)
        if isinstance(meta, dict):
            return meta
    except (OSError, ValueError):
        pass
    return {}


# ------------------------------------------------------------------ sticker texts
# What shows in the match log when sending a sticker ("Amras: <text>") and its name in
# the menu. By default it is the file name ("01_good night.png" -> "Good night"); in
# mod.json another one can be set, or one per language: "texts": {"01_greeting": {"es": "Hola", "en": "Hi"}}
LANGS = {"ja": "Japanese", "en": "English", "fr": "French", "it": "Italian", "de": "German", "es": "Spanish",
         "pt": "Portuguese", "ru": "Russian", "ko": "Korean", "zh-CN": "Chinese-cn", "zh-TW": "Chinese-tw"}
MAX_TEXT = 40


# Which game sticker each mod sticker is equivalent to (optional): the AIs reply to it as to that one.
# In mod.json: "means": {"01_greeting": "hello"}. Name -> game sticker type (Stamp.Type).
MEANS = {"hello": 28, "good": 8, "roger": 0, "why": 1, "no_way": 2, "relieved": 4, "frightened": 5,
         "scream": 32, "worried": 31, "please": 34, "hold_on": 37, "smirk": 29, "suspicious": 30,
         "killer_no_suspicion": 24, "killer_suspicion": 25, "target_no_suspicion": 26, "target_suspicion": 27}


def means_value(v):
    v = str(v or "").strip().lower()
    return v if v in MEANS else None


def clean_text(text):
    text = re.sub(r"[\x00-\x1f{}<>]", "", str(text or ""))   # without braces: the game uses {player}
    return re.sub(r"\s+", " ", text).strip()[:MAX_TEXT]


def text_value(v):
    """mod.json text: a string, or a dictionary per language. Returns a clean str or dict."""
    if isinstance(v, dict):
        out = {k: clean_text(x) for k, x in v.items() if k in LANGS and clean_text(x)}
        return out or None
    t = clean_text(v)
    return t or None


def text_for_game(text):
    """{game language: text} with the 11 languages (the missing ones use the first available)."""
    if isinstance(text, dict):
        first = next(iter(text.values()))
        return {LANGS[k]: text.get(k) or text.get("en") or first for k in LANGS}
    return {LANGS[k]: text for k in LANGS}


def _images(folder, kind):
    d = os.path.join(folder, DIRS[kind])
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(IMAGE_EXT) and os.path.isfile(os.path.join(d, f)))


_CACHE = {}


def _cached(path, kind, data):
    """Splitting sheets and removing backgrounds takes a while: it is remembered while the file doesn't change."""
    key = (path, kind, len(data), hashlib.sha1(data).hexdigest())
    if key not in _CACHE:
        if len(_CACHE) > 400:
            _CACHE.clear()
        _CACHE[key] = normalize_many(kind, data)
    return _CACHE[key]


def load_mod(folder, owner=""):
    """Reads a mod folder. Returns the mod with its images already adjusted (in memory).
    owner (the owner's Steam account) is part of the id: that way the "Main folder" of two
    different players doesn't clash when their mods come together in a room."""
    meta = _read_meta(folder)
    texts = meta.get("texts") if isinstance(meta.get("texts"), dict) else {}
    means = meta.get("means") if isinstance(meta.get("means"), dict) else {}
    name = str(meta.get("name") or os.path.basename(folder.rstrip("/\\")))[:60]
    author = str(meta.get("author") or "")[:40]
    items = {k: [] for k in KINDS}
    errors = []
    temp = os.path.basename(folder.rstrip("/\\")).endswith(TEMP_SUFFIX)
    for kind in KINDS:
        for fname in _images(folder, kind):
            path = os.path.join(folder, DIRS[kind], fname)
            try:
                with open(path, "rb") as f:
                    data = f.read()
                if temp:                      # already adjusted by the host: used as it is
                    check_normalized(kind, data)
                    pngs = [data]
                else:
                    pngs = _cached(path, kind, data)
            except (OSError, ModError) as e:
                errors.append(f"{kind}/{fname}: {e}")
                continue
            stem = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(fname)[0])[:36] or "img"
            orig_stem = os.path.splitext(fname)[0]
            for n, png in enumerate(pngs, 1):
                if temp:
                    # it already comes with its final name: trimming it again (stem[:36]) left all
                    # the pieces of a sheet with the same name ("..._01" -> "..."), so in the
                    # room they had other ids than on their owner's PC and didn't show in their wheel
                    piece = os.path.splitext(fname)[0]
                else:
                    piece = stem if len(pngs) == 1 else f"{stem}_{n:02d}"
                it = {"file": piece + ".png", "png": png}
                if kind == "stickers":
                    it["key"] = piece
                    t = None
                    for key in (piece, orig_stem if len(pngs) == 1 else None, fname):
                        if key and key in texts:
                            t = text_value(texts[key])
                            break
                    it["text"] = t               # without a message set, the sticker shows none
                    keys = [k for k in (piece, orig_stem if len(pngs) == 1 else None, fname) if k and k in means]
                    it["means"] = means_value(means[keys[0]]) if keys else None
                items[kind].append(it)
    base = os.path.basename(folder.rstrip("/\\"))
    if temp:                                 # downloaded temporary mod: keeps its original id
        uid = base[:-len(TEMP_SUFFIX)]
    else:
        # The id depends ONLY on the folder, not the content: that way, adding images, changing a
        # message or updating the launcher doesn't change the ids of the stickers/avatars you already
        # had set (if they changed, the game would remove them from the wheel and the chosen avatar).
        uid = f"{_slug(base)}-{hashlib.sha1((str(owner) + '/' + base.lower()).encode()).hexdigest()[:6]}"
    return {"uid": uid, "name": name, "author": author, "folder": folder, "temp": temp,
            "stickers": items["stickers"], "avatars": items["avatars"], "errors": errors}


def set_text(folder, key, text):
    """Saves a sticker's message in its folder's mod.json (empty = no
    message). From the launcher you can use characters Windows doesn't allow in names (? : " *)."""
    path = os.path.join(folder, "mod.json")
    meta = _read_meta(folder)
    texts = meta.get("texts") if isinstance(meta.get("texts"), dict) else {}
    value = clean_text(text)
    if value:
        texts[str(key)[:40]] = value
    else:
        texts.pop(str(key), None)
    meta["texts"] = texts
    meta.setdefault("name", "")
    meta.setdefault("author", "")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return value


def set_means(folder, key, value):
    """Saves which game sticker a sticker is equivalent to (empty = none: the AIs don't reply to it)."""
    path = os.path.join(folder, "mod.json")
    meta = _read_meta(folder)
    means = meta.get("means") if isinstance(meta.get("means"), dict) else {}
    value = means_value(value)
    if value:
        means[str(key)[:40]] = value
    else:
        means.pop(str(key), None)
    meta["means"] = means
    meta.setdefault("name", "")
    meta.setdefault("author", "")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return value


def list_folders(mods_dir):
    """Mod folders. If someone puts stickers/ or avatars/ directly in the mods folder
    (the most natural thing), the folder itself counts as one more mod."""
    if not mods_dir or not os.path.isdir(mods_dir):
        return []
    out = [mods_dir] if any(os.path.isdir(os.path.join(mods_dir, DIRS[k])) for k in KINDS) else []
    out += sorted(os.path.join(mods_dir, d) for d in os.listdir(mods_dir)
                  if os.path.isdir(os.path.join(mods_dir, d)) and not d.startswith((".", "_"))
                  and d.lower() not in set(DIRS.values()) | set(OLD_DIRS))
    return out


# ------------------------------------------------------------------ a room's set
def room_set(mods):
    """Sorts the mods and gives each image a stable id (the same on every PC in the room).

    Stickers: type = 1000.. according to the hash of "<uid>/<file>" (if it clashes, the next free one).
    Avatars: data id "Icon_CSR_<hash>". Meets the per-room limits."""
    mods = sorted((m for m in mods if m["stickers"] or m["avatars"]), key=lambda m: m["uid"])
    seen, uniq = set(), []
    for m in mods:
        if m["uid"] not in seen:
            seen.add(m["uid"])
            uniq.append(m)
    used, stickers, avatars = set(), [], []
    span = LAST_TYPE - FIRST_TYPE + 1
    for m in uniq:
        for it in m["stickers"]:
            if len(stickers) >= MAX_STICKERS:
                break
            key = f"{m['uid']}/{it['file']}"
            t = FIRST_TYPE + int(hashlib.sha1(key.encode()).hexdigest(), 16) % span
            while t in used:
                t = FIRST_TYPE + (t - FIRST_TYPE + 1) % span
            used.add(t)
            stickers.append({"mod": m["uid"], "file": it["file"], "type": t, "png": it["png"],
                             "text": it.get("text"), "means": it.get("means"),
                             "name": f"CSR_{m['uid']}_{it['file'][:-4]}"})
        for it in m["avatars"]:
            if len(avatars) >= MAX_AVATARS:
                break
            key = f"{m['uid']}/{it['file']}"
            avatars.append({"mod": m["uid"], "file": it["file"], "png": it["png"],
                            "data_id": AVATAR_PREFIX + hashlib.sha1(key.encode()).hexdigest()[:12],
                            "name": f"CSR_{m['uid']}_{it['file'][:-4]}"})
    digest = hashlib.sha1()
    for s in stickers:
        digest.update(f"s{s['type']}:".encode() + hashlib.sha1(s["png"]).digest() +
                      json.dumps(s.get("text"), ensure_ascii=False, sort_keys=True).encode() +
                      (b"=" + s["means"].encode() if s.get("means") else b""))
    for a in avatars:
        digest.update(f"a{a['data_id']}:".encode() + hashlib.sha1(a["png"]).digest())
    return {"mods": uniq, "stickers": stickers, "avatars": avatars,
            "hash": digest.hexdigest()[:16] if (stickers or avatars) else ""}


def summary(rs):
    """What is shown before joining a room with mods."""
    return {"hash": rs["hash"], "stickers": len(rs["stickers"]), "avatars": len(rs["avatars"]),
            "mods": [{"uid": m["uid"], "name": m["name"], "author": m["author"],
                      "stickers": len(m["stickers"]), "avatars": len(m["avatars"])} for m in rs["mods"]]}


# ------------------------------------------------------------------ sending over the network
def pack(rs):
    """Internal zip with the room's already adjusted images."""
    buf = io.BytesIO()
    manifest = {"format": "crimesight-revival-mods", "version": 1, "hash": rs["hash"], "mods": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for m in rs["mods"]:
            entry = {"uid": m["uid"], "name": m["name"], "author": m["author"], "stickers": [], "avatars": [],
                     "texts": {it["file"][:-4]: it["text"] for it in m["stickers"] if it.get("text")},
                     "means": {it["file"][:-4]: it["means"] for it in m["stickers"] if it.get("means")}}
            for kind in KINDS:
                for it in m[kind]:
                    z.writestr(f"{m['uid']}/{kind}/{it['file']}", it["png"])
                    entry[kind].append(it["file"])
            manifest["mods"].append(entry)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    return buf.getvalue()


_SAFE = re.compile(r"^[a-z0-9-]{1,40}$")
_SAFE_FILE = re.compile(r"^[A-Za-z0-9_-]{1,40}\.png$")


def unpack(data, dest_dir):
    """Saves a downloaded pack as temporary mod folders ("<id>+temp").
    Validates everything: names, sizes and images. Returns the created folders."""
    if len(data) > MAX_PACK_BYTES:
        raise ModError("paquete de mods demasiado grande")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(z.read("manifest.json"))
    except Exception as e:  # noqa: BLE001
        raise ModError(f"paquete de mods ilegible ({e})")
    if manifest.get("format") != "crimesight-revival-mods":
        raise ModError("paquete de mods desconocido")
    os.makedirs(dest_dir, exist_ok=True)
    made = []
    for m in manifest.get("mods", [])[:64]:
        uid = str(m.get("uid", ""))
        if not _SAFE.match(uid):
            raise ModError("id de mod no valido")
        folder = os.path.join(dest_dir, uid + TEMP_SUFFIX)
        shutil.rmtree(folder, ignore_errors=True)
        for kind in KINDS:
            files = m.get(kind, [])[:MAX_STICKERS if kind == "stickers" else MAX_AVATARS]
            if files:
                os.makedirs(os.path.join(folder, DIRS[kind]), exist_ok=True)
            for fname in files:
                if not _SAFE_FILE.match(str(fname)):
                    raise ModError("nombre de imagen no valido")
                png = z.read(f"{uid}/{kind}/{fname}")
                check_normalized(kind, png)
                with open(os.path.join(folder, DIRS[kind], fname), "wb") as f:
                    f.write(png)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "mod.json"), "w", encoding="utf-8") as f:
            texts = m.get("texts") if isinstance(m.get("texts"), dict) else {}
            texts = {str(k)[:40]: text_value(v) for k, v in list(texts.items())[:MAX_STICKERS] if text_value(v)}
            means = m.get("means") if isinstance(m.get("means"), dict) else {}
            means = {str(k)[:40]: means_value(v) for k, v in list(means.items())[:MAX_STICKERS] if means_value(v)}
            json.dump({"name": str(m.get("name", uid))[:60], "author": str(m.get("author", ""))[:40],
                       "texts": texts, "means": means}, f,
                      ensure_ascii=False)
        made.append(folder)
    return made


def clear_temp(dest_dir):
    """Deletes the temporary mods downloaded from other rooms."""
    if not os.path.isdir(dest_dir):
        return 0
    n = 0
    for d in os.listdir(dest_dir):
        if d.endswith(TEMP_SUFFIX):
            shutil.rmtree(os.path.join(dest_dir, d), ignore_errors=True)
            n += 1
    return n
