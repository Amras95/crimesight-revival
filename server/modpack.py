"""
CRIMESIGHT Revival - paquetes de mods de apariencia (stickers y avatares nuevos).

Un mod es una carpeta normal con imagenes (no hace falta comprimir nada):

    mods/
      MiPack/
        stickers/   gato.png, ok.png ...
        avatars/    yo.png ...
        mod.json    (opcional) {"name": "Mi pack", "author": "Amras"}

Las imagenes se ajustan solas: los stickers a 128x128 con el borde blanco del juego, y los
avatares a 256x256 con el dibujo centrado como los iconos originales. Los mods solo ANADEN
huecos nuevos; nunca tocan stickers ni avatares del juego (tampoco los de pago).

Cuando alguien se une a una sala con mods, el lanzador descarga el paquete del anfitrion como
mods temporales ("<id>+temp") y los borra al cerrar la sesion. Por la red viaja un zip interno,
pero el jugador nunca tiene que comprimir ni descomprimir nada.
"""
import hashlib, io, json, os, re, shutil, zipfile

STICKER_SIZE = 128
STICKER_MARGIN = 7
AVATAR_SIZE = 256
AVATAR_BOX = (40, 33, 176)          # x, y y lado de la zona donde dibujan los iconos originales (la que se ve)
KINDS = ("stickers", "avatars")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
MAX_STICKERS = 60                   # por sala
MAX_AVATARS = 30
MAX_INPUT_BYTES = 20 * 1024 * 1024  # por imagen original (puede ser una lamina con muchos stickers)
MAX_PIECES = 64                     # piezas por lamina
MAX_PACK_BYTES = 24 * 1024 * 1024
TEMP_SUFFIX = "+temp"
FIRST_TYPE, LAST_TYPE = 1000, 4095  # tipos de sticker libres (el juego usa 0-38)
AVATAR_PREFIX = "Icon_CSR_"


class ModError(ValueError):
    pass


# ------------------------------------------------------------------ imagenes
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


def normalize(kind, data):
    """PNG final listo para el juego (el tamano y la colocacion de los originales)."""
    return _normalize_img(kind, _open(data))


def normalize_many(kind, data):
    """Una imagen cualquiera -> lista de PNG finales. Si es una lamina con varios stickers se
    separa sola, y si no tiene transparencia se le quita el fondo (ver modimage)."""
    import modimage
    if len(data) > MAX_INPUT_BYTES:
        raise ModError("imagen demasiado grande (maximo 20 MB)")
    img = _open(data)
    if kind == "avatars" and not modimage._has_alpha(img) and not _plain_border(img):
        # una foto o un dibujo que llega a los bordes: se usa entera. Quitarle el "fondo" le abria
        # agujeros (zonas claras tocando el borde) que en el juego se ven como huecos grises.
        return [_normalize_img(kind, img)]
    pieces = modimage.extract(img)[:MAX_PIECES]
    return [_normalize_img(kind, p) for p in pieces]


def _plain_border(img, tol=18, share=0.9):
    """True si el borde de la imagen es casi todo de un mismo color (un personaje sobre fondo liso)."""
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
    """True si el dibujo llega hasta los bordes (una foto, o un busto cortado en cuadrado)."""
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
    """La imagen escalada por k y centrada en la zona visible (si es alta, se sube un poco: las caras
    suelen estar arriba). Devuelve el lienzo final."""
    from PIL import Image
    x, y, side = AVATAR_BOX
    im = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    canvas = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    left = x + (side - im.width) // 2
    top = y + (side - im.height) // 2 if im.height <= side else y - min(im.height - side, round(0.04 * im.height))
    canvas.alpha_composite(im.crop((max(0, -left), max(0, -top), im.width, im.height)), (max(0, left), max(0, top)))
    return canvas


def _coverage(canvas):
    """Parte de la zona visible que queda cubierta (0..1)."""
    x, y, side = AVATAR_BOX
    a = canvas.getchannel("A").crop((x, y, x + side, y + side)).point(lambda v: 255 if v > 64 else 0)
    return a.histogram()[255] / float(side * side)


def _trim_border(img, tol=14, share=0.97):
    """Quita los bordes lisos de una foto (marcos, franjas de color), que en el juego se ven como huecos."""
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
    """Fotos y bustos en la zona que ensena el juego (AVATAR_BOX). Se acerca lo justo para que no
    queden huecos: se prueba desde "entera" hasta "cubre la zona" y se queda con el primer zoom que
    tapa practicamente todo (lo que no se puede tapar, como los hombros de un busto, se deja)."""
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
        for _ in range(12):                 # busqueda binaria del zoom minimo
            mid = (lo + hi) / 2
            if _coverage(_place(img, mid)) >= target:
                hi = mid
            else:
                lo = mid
    out = _place(img, hi)
    return _extend(out)


def _extend(canvas, strip=4):
    """Algunos marcos (el rombo, el hexagono) ensenan algo mas que la zona AVATAR_BOX. Por cada lado en
    el que la imagen esta cortada (una foto, o la ropa de un busto que acaba en seco) se estiran sus
    ultimas filas hasta el borde, asi parece que sigue. Lo de dentro no cambia; lo estirado se suaviza."""
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
    # solo se suaviza lo anadido (fuera del recuadro de la imagen), no el contorno del dibujo
    outside = Image.new("L", (W, H), 255)
    outside.paste(0, (l, t, r, b))
    out.paste(out.filter(ImageFilter.GaussianBlur(2)), (0, 0), outside)
    out.alpha_composite(canvas)
    return out


def sticker_background(png):
    """Silueta blanca algo mas grande que el dibujo: el borde que llevan los stickers del juego."""
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


# ------------------------------------------------------------------ carpetas de mods
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


# ------------------------------------------------------------------ textos de los stickers
# Lo que sale en el registro de la partida al mandar un sticker ("Amras: <texto>") y su nombre en
# el menu. Por defecto es el nombre del archivo ("01_buenas noches.png" -> "Buenas noches"); en
# mod.json se puede poner otro, o uno por idioma: "texts": {"01_saludo": {"es": "Hola", "en": "Hi"}}
LANGS = {"ja": "Japanese", "en": "English", "fr": "French", "it": "Italian", "de": "German", "es": "Spanish",
         "pt": "Portuguese", "ru": "Russian", "ko": "Korean", "zh-CN": "Chinese-cn", "zh-TW": "Chinese-tw"}
MAX_TEXT = 40


def clean_text(text):
    text = re.sub(r"[\x00-\x1f{}<>]", "", str(text or ""))   # sin llaves: el juego usa {player}
    return re.sub(r"\s+", " ", text).strip()[:MAX_TEXT]


def text_from_name(stem):
    t = re.sub(r"^\d+[\s._-]*", "", stem)                 # "01_" sirve para ordenar, no se ensena
    t = clean_text(t.replace("_", " "))
    return t[:1].upper() + t[1:] if t else ""


def text_value(v):
    """Texto de mod.json: una cadena, o un diccionario por idioma. Devuelve str o dict limpio."""
    if isinstance(v, dict):
        out = {k: clean_text(x) for k, x in v.items() if k in LANGS and clean_text(x)}
        return out or None
    t = clean_text(v)
    return t or None


def text_for_game(text):
    """{idioma del juego: texto} con los 11 idiomas (los que falten usan el primero que haya)."""
    if isinstance(text, dict):
        first = next(iter(text.values()))
        return {LANGS[k]: text.get(k) or text.get("en") or first for k in LANGS}
    return {LANGS[k]: text for k in LANGS}


def _images(folder, kind):
    d = os.path.join(folder, kind)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(IMAGE_EXT) and os.path.isfile(os.path.join(d, f)))


_CACHE = {}


def _cached(path, kind, data):
    """Separar laminas y quitar fondos tarda un poco: se recuerda mientras el archivo no cambie."""
    key = (path, kind, len(data), hashlib.sha1(data).hexdigest())
    if key not in _CACHE:
        if len(_CACHE) > 400:
            _CACHE.clear()
        _CACHE[key] = normalize_many(kind, data)
    return _CACHE[key]


def load_mod(folder, owner=""):
    """Lee una carpeta de mod. Devuelve el mod con sus imagenes ya ajustadas (en memoria).
    owner (la cuenta de Steam del dueno) forma parte del id: asi la "Carpeta principal" de dos
    jugadores distintos no choca cuando sus mods se juntan en una sala."""
    meta = _read_meta(folder)
    texts = meta.get("texts") if isinstance(meta.get("texts"), dict) else {}
    name = str(meta.get("name") or os.path.basename(folder.rstrip("/\\")))[:60]
    author = str(meta.get("author") or "")[:40]
    items = {k: [] for k in KINDS}
    errors = []
    temp = os.path.basename(folder.rstrip("/\\")).endswith(TEMP_SUFFIX)
    for kind in KINDS:
        for fname in _images(folder, kind):
            path = os.path.join(folder, kind, fname)
            try:
                with open(path, "rb") as f:
                    data = f.read()
                if temp:                      # ya viene ajustada del anfitrion: se usa tal cual
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
                piece = stem if len(pngs) == 1 else f"{stem}_{n:02d}"
                it = {"file": piece + ".png", "png": png}
                if kind == "stickers":
                    it["key"] = piece
                    it["default"] = text_from_name(orig_stem) or None
                    t = None
                    for key in (piece, orig_stem if len(pngs) == 1 else None, fname):
                        if key and key in texts:
                            t = text_value(texts[key])
                            break
                    it["text"] = t or text_from_name(orig_stem) or None
                items[kind].append(it)
    base = os.path.basename(folder.rstrip("/\\"))
    if temp:                                 # mod temporal descargado: conserva su id original
        uid = base[:-len(TEMP_SUFFIX)]
    else:
        # El id depende SOLO de la carpeta, no del contenido: asi, anadir imagenes, cambiar un
        # mensaje o actualizar el lanzador no cambia los ids de los stickers/avatares que ya
        # tenias puestos (si cambiaran, el juego los quitaria de la rueda y del avatar elegido).
        uid = f"{_slug(base)}-{hashlib.sha1((str(owner) + '/' + base.lower()).encode()).hexdigest()[:6]}"
    return {"uid": uid, "name": name, "author": author, "folder": folder, "temp": temp,
            "stickers": items["stickers"], "avatars": items["avatars"], "errors": errors}


def set_text(folder, key, text):
    """Guarda el mensaje de un sticker en el mod.json de su carpeta (vacio = el del nombre del
    archivo). Desde el lanzador se pueden poner signos que Windows no deja en los nombres (? : " *)."""
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


def list_folders(mods_dir):
    """Carpetas de mods. Si alguien pone stickers/ o avatars/ directamente en la carpeta de mods
    (lo mas natural), la propia carpeta cuenta como un mod mas."""
    if not mods_dir or not os.path.isdir(mods_dir):
        return []
    out = [mods_dir] if any(os.path.isdir(os.path.join(mods_dir, k)) for k in KINDS) else []
    out += sorted(os.path.join(mods_dir, d) for d in os.listdir(mods_dir)
                  if os.path.isdir(os.path.join(mods_dir, d)) and not d.startswith((".", "_"))
                  and d.lower() not in KINDS)
    return out


def load_all(mods_dir, disabled=(), root_name=None, owner=""):
    """Todos los mods de una carpeta (los desactivados se devuelven marcados)."""
    out = []
    for folder in list_folders(mods_dir):
        m = load_mod(folder, owner)
        if os.path.normpath(folder) == os.path.normpath(mods_dir) and root_name:
            m["name"] = root_name
        m["enabled"] = os.path.basename(folder) not in set(disabled)
        out.append(m)
    return out


# ------------------------------------------------------------------ conjunto de una sala
def room_set(mods):
    """Ordena los mods y asigna a cada imagen un id estable (igual en todos los PCs de la sala).

    Stickers: tipo = 1000.. segun el hash de "<uid>/<archivo>" (si choca, el siguiente libre).
    Avatares: id de datos "Icon_CSR_<hash>". Cumple los limites por sala."""
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
                             "text": it.get("text"), "name": f"CSR_{m['uid']}_{it['file'][:-4]}"})
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
                      json.dumps(s.get("text"), ensure_ascii=False, sort_keys=True).encode())
    for a in avatars:
        digest.update(f"a{a['data_id']}:".encode() + hashlib.sha1(a["png"]).digest())
    return {"mods": uniq, "stickers": stickers, "avatars": avatars,
            "hash": digest.hexdigest()[:16] if (stickers or avatars) else ""}


def summary(rs):
    """Lo que se ensena antes de unirse a una sala con mods."""
    return {"hash": rs["hash"], "stickers": len(rs["stickers"]), "avatars": len(rs["avatars"]),
            "mods": [{"uid": m["uid"], "name": m["name"], "author": m["author"],
                      "stickers": len(m["stickers"]), "avatars": len(m["avatars"])} for m in rs["mods"]]}


# ------------------------------------------------------------------ envio por la red
def pack(rs):
    """Zip interno con las imagenes ya ajustadas de la sala."""
    buf = io.BytesIO()
    manifest = {"format": "crimesight-revival-mods", "version": 1, "hash": rs["hash"], "mods": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for m in rs["mods"]:
            entry = {"uid": m["uid"], "name": m["name"], "author": m["author"], "stickers": [], "avatars": [],
                     "texts": {it["file"][:-4]: it["text"] for it in m["stickers"] if it.get("text")}}
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
    """Guarda un paquete descargado como carpetas de mods temporales ("<id>+temp").
    Valida todo: nombres, tamanos e imagenes. Devuelve las carpetas creadas."""
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
                os.makedirs(os.path.join(folder, kind), exist_ok=True)
            for fname in files:
                if not _SAFE_FILE.match(str(fname)):
                    raise ModError("nombre de imagen no valido")
                png = z.read(f"{uid}/{kind}/{fname}")
                check_normalized(kind, png)
                with open(os.path.join(folder, kind, fname), "wb") as f:
                    f.write(png)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "mod.json"), "w", encoding="utf-8") as f:
            texts = m.get("texts") if isinstance(m.get("texts"), dict) else {}
            texts = {str(k)[:40]: text_value(v) for k, v in list(texts.items())[:MAX_STICKERS] if text_value(v)}
            json.dump({"name": str(m.get("name", uid))[:60], "author": str(m.get("author", ""))[:40],
                       "texts": texts}, f,
                      ensure_ascii=False)
        made.append(folder)
    return made


def clear_temp(dest_dir):
    """Borra los mods temporales descargados de otras salas."""
    if not os.path.isdir(dest_dir):
        return 0
    n = 0
    for d in os.listdir(dest_dir):
        if d.endswith(TEMP_SUFFIX):
            shutil.rmtree(os.path.join(dest_dir, d), ignore_errors=True)
            n += 1
    return n
