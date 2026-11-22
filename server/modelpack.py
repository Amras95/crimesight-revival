"""
CRIMESIGHT Revival - modelos 3D y animaciones de una sala (los .glb que ponen el anfitrion y los invitados).

Un "juego de modelos" es lo que cada uno ha elegido en el lanzador (Mods > Modelos):

    {"swaps": {"PawnTypeData_F": "file:<sha256>", "PawnTypeData_A": "PawnTypeData_B"},
     "anims": {"PawnTypeData_F": {"idle": "file:<sha256>"}},
     "files": {"<sha256>": {"kind": "model" | "anim", "size": bytes, "name": "Mi robot"}}}

Los archivos van por su sha256: cada PC solo descarga los que no tiene y nadie puede colar otro archivo con
el mismo nombre. Antes de usar un .glb que viene de otro PC se comprueba entero (check_glb): que sea un glTF
binario de verdad, con todo dentro del archivo, y que no se pase de tamano (mallas, texturas, animaciones).
"""
import hashlib, io, json, re, struct

SLOTS = ("PawnTypeData_A", "PawnTypeData_B", "PawnTypeData_C", "PawnTypeData_D", "PawnTypeData_E",
         "PawnTypeData_F", "ThreatTypeData_Survivor", "ThreatTypeData_Traitor")
ANIM_KINDS = ("idle", "walk", "run")
KINDS = ("model", "anim", "image")
FILE_PREFIX = "file:"
PAWNS = SLOTS[:6]                        # los 6 sitios de una partida (cada uno con su forma de jugar)
TRAITOR = "ThreatTypeData_Traitor"
MIN_PAWNS = 6
ROLES = ("pawn", "traitor")
MAX_CHARS = 32
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_TALK = 48
_CHAR = re.compile(r"^[a-z0-9]{10}$")
_TALK_KEY = re.compile(r"^[A-Za-z0-9_]{1,48}$")

MAX_FILE_BYTES = 64 * 1024 * 1024        # por archivo
MAX_ROOM_BYTES = 256 * 1024 * 1024       # todos los de una sala (o una oferta)
MAX_FILES = 24
MAX_VERTICES = 400_000                   # sumando todas las mallas de un archivo
MAX_INDICES = 3_000_000
MAX_IMAGES = 24
MAX_IMAGE_SIDE = 4096
MAX_NODES = 2000
MAX_ANIM_VALUES = 4_000_000              # floats de todas las curvas de animacion
_SHA = re.compile(r"^[0-9a-f]{64}$")


class ModelError(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def empty():
    return {"swaps": {}, "anims": {}, "chars": {}, "files": {}, "hash": ""}


def set_hash(ms):
    """Huella de un juego de modelos (igual en todos los PCs): cambia si cambia cualquier eleccion o archivo."""
    if not ms.get("swaps") and not ms.get("anims") and not ms.get("chars"):
        return ""
    key = json.dumps({"s": ms.get("swaps", {}), "a": ms.get("anims", {}), "c": ms.get("chars", {}),
                      "f": sorted(ms.get("files", {}))}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _used(ms):
    used = {v[len(FILE_PREFIX):] for v in ms["swaps"].values() if v.startswith(FILE_PREFIX)}
    used |= {v[len(FILE_PREFIX):] for k in ms["anims"].values() for v in k.values()}
    for c in ms.get("chars", {}).values():
        for v in [c.get("model"), c.get("image")] + list((c.get("anims") or {}).values()):
            if v:
                used.add(v[len(FILE_PREFIX):])
    return used


def summary(ms):
    """Lo que se ensena antes de unirse (y en el aviso al anfitrion)."""
    files = ms.get("files", {})
    return {"hash": ms.get("hash", ""), "models": sum(1 for f in files.values() if f["kind"] == "model"),
            "anims": sum(1 for f in files.values() if f["kind"] == "anim"), "chars": len(ms.get("chars", {})),
            "bytes": sum(int(f.get("size", 0)) for f in files.values()),
            "slots": sorted(set(ms.get("swaps", {})) | set(ms.get("anims", {})))}


def manifest(ms):
    """El juego de modelos sin rutas locales (lo que viaja por la red)."""
    return {"hash": ms.get("hash", ""), "swaps": dict(ms.get("swaps", {})),
            "anims": {k: dict(v) for k, v in ms.get("anims", {}).items()},
            "chars": {k: _char_copy(c) for k, c in ms.get("chars", {}).items()},
            "files": {s: {"kind": f["kind"], "size": int(f["size"]), "name": str(f.get("name", ""))[:60]}
                      for s, f in ms.get("files", {}).items()}}


def _char_copy(c):
    out = {"name": c.get("name", ""), "role": c.get("role", "pawn"), "model": c.get("model", ""),
           "anim_from": c.get("anim_from") if c.get("anim_from") in PAWNS else PAWNS[0],
           "anims": dict(c.get("anims") or {}), "talk": dict(c.get("talk") or {})}
    if c.get("image"):
        out["image"] = c["image"]
    return out


def clean_text(v, n):
    """Texto de otro PC: sin caracteres de control ni etiquetas (el juego interpreta <...>)."""
    return re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", str(v or ""))[:n].strip()


def clean(meta):
    """Valida un juego de modelos que llega de otro PC (sin los archivos). Lanza ModelError si algo no vale."""
    if not isinstance(meta, dict):
        raise ModelError("juego de modelos no valido")
    files = {}
    for s, f in list((meta.get("files") or {}).items())[:MAX_FILES + 1]:
        if not _SHA.match(str(s)) or not isinstance(f, dict) or f.get("kind") not in KINDS:
            raise ModelError("archivo de modelo no valido")
        size = int(f.get("size", 0))
        if size <= 0 or size > (MAX_IMAGE_BYTES if f["kind"] == "image" else MAX_FILE_BYTES):
            raise ModelError("modelo demasiado grande")
        files[s] = {"kind": f["kind"], "size": size, "name": re.sub(r"[\x00-\x1f]", "", str(f.get("name", "")))[:60]}
    if len(files) > MAX_FILES or sum(f["size"] for f in files.values()) > MAX_ROOM_BYTES:
        raise ModelError("demasiados modelos")

    def target_ok(v, kind):
        if isinstance(v, str) and v.startswith(FILE_PREFIX):
            s = v[len(FILE_PREFIX):]
            return s in files and files[s]["kind"] == kind
        return kind == "model" and v in SLOTS
    swaps = {}
    for slot, v in (meta.get("swaps") or {}).items():
        if slot not in SLOTS or not target_ok(v, "model"):
            raise ModelError("cambio de modelo no valido")
        if v != slot:
            swaps[slot] = v
    anims = {}
    for slot, kinds in (meta.get("anims") or {}).items():
        if slot not in SLOTS or not isinstance(kinds, dict):
            raise ModelError("animacion no valida")
        k = {}
        for kind, v in kinds.items():
            if kind not in ANIM_KINDS or not target_ok(v, "anim"):
                raise ModelError("animacion no valida")
            k[kind] = v
        if k:
            anims[slot] = k
    chars = {}
    for cid, c in list((meta.get("chars") or {}).items())[:MAX_CHARS + 1]:
        if not _CHAR.match(str(cid)) or not isinstance(c, dict) or c.get("role", "pawn") not in ROLES:
            raise ModelError("personaje no valido")
        if not target_ok(c.get("model"), "model") or not str(c.get("model", "")).startswith(FILE_PREFIX):
            raise ModelError("personaje sin modelo")
        if c.get("image") and not target_ok(c["image"], "image"):
            raise ModelError("imagen de personaje no valida")
        an = {}
        for kind, v in (c.get("anims") or {}).items():
            if kind not in ANIM_KINDS or not target_ok(v, "anim"):
                raise ModelError("animacion de personaje no valida")
            an[kind] = v
        talk = {}
        for k, v in list((c.get("talk") or {}).items())[:MAX_TALK]:
            if _TALK_KEY.match(str(k)) and clean_text(v, 240):
                talk[str(k)] = clean_text(v, 240)
        out_c = {"name": clean_text(c.get("name"), 24), "role": c.get("role", "pawn"), "model": c["model"],
                 "anim_from": c.get("anim_from") if c.get("anim_from") in PAWNS else PAWNS[0], "anims": an, "talk": talk}
        if c.get("image"):
            out_c["image"] = c["image"]
        chars[str(cid)] = out_c
    if len(chars) > MAX_CHARS:
        raise ModelError("demasiados personajes")
    out = {"swaps": swaps, "anims": anims, "chars": chars, "files": files}
    used = _used(out)
    out["files"] = {s: f for s, f in files.items() if s in used}
    out["hash"] = set_hash(out)
    return out


def fill_enabled(items):
    """With fewer than 6 ticked (e.g. a ticked new character was removed), the unticked originals that draw()
    brings back show as ticked, in the same order, so the Character Selection shows what a match will use."""
    on = sum(1 for it in items if it.get("enabled"))
    for it in items:
        if on >= MIN_PAWNS:
            break
        if str(it.get("id", "")).startswith("orig:") and not it.get("enabled"):
            it["enabled"] = True
            on += 1
    return items


def draw(ms, disabled, rng):
    """Reparto de una partida: que personaje se ve en cada uno de los 6 sitios y que traidor. Salen 6 de los
    activados (originales y nuevos con la misma probabilidad); un original sale en su propio sitio y los nuevos
    rellenan los demas al azar. Si hay menos de 6 activados, se completan con originales."""
    disabled = set(disabled or ())
    chars = ms.get("chars", {})
    pool = [("orig", k) for k in PAWNS if "orig:" + k not in disabled]
    pool += [("char", cid) for cid, c in sorted(chars.items()) if c.get("role") == "pawn" and cid not in disabled]
    if len(pool) < MIN_PAWNS:                                    # siempre 6: vuelven originales desactivados
        pool += [("orig", k) for k in PAWNS if ("orig", k) not in pool][:MIN_PAWNS - len(pool)]
    picked = rng.sample(pool, MIN_PAWNS) if len(pool) > MIN_PAWNS else list(pool)
    positions = {k: None for k in PAWNS}
    free = [k for k in PAWNS if ("orig", k) not in picked]
    rng.shuffle(free)
    for (kind, cid) in picked:
        if kind == "char":
            positions[free.pop()] = cid
    # el traidor siempre es el original por ahora (sus variantes llegaran mas adelante)
    return {"positions": positions, "traitor": None}


def merge(parts):
    """Junta varios juegos de modelos: el primero manda (el anfitrion) y los siguientes (invitados aceptados,
    por orden) solo rellenan los personajes y animaciones que quedan libres. Conserva las rutas locales."""
    swaps, anims, chars, files = {}, {}, {}, {}
    for ms in parts:
        for cid, c in ms.get("chars", {}).items():
            chars.setdefault(cid, c)
        for slot, v in ms.get("swaps", {}).items():
            if slot not in swaps:
                swaps[slot] = v
        for slot, kinds in ms.get("anims", {}).items():
            for kind, v in kinds.items():
                anims.setdefault(slot, {}).setdefault(kind, v)
        for s, f in ms.get("files", {}).items():
            files.setdefault(s, f)
    out = {"swaps": swaps, "anims": anims, "chars": chars, "files": files}
    used = _used(out)
    out["files"] = {s: f for s, f in files.items() if s in used}
    out["hash"] = set_hash(out)
    return out


# ------------------------------------------------------------------ comprobar un .glb
def check_file(data, kind):
    """Comprueba un archivo de la sala segun su tipo (modelo, animacion o imagen de personaje)."""
    if kind == "image":
        if len(data) > MAX_IMAGE_BYTES:
            raise ModelError("imagen demasiado grande")
        _check_image(data)
        return
    check_glb(data, kind)


def check_glb(data, kind):
    """Lanza ModelError si el archivo no es un .glb que se pueda usar sin riesgo (y del tipo esperado)."""
    if len(data) > MAX_FILE_BYTES:
        raise ModelError("modelo demasiado grande")
    if len(data) < 20 or data[:4] != b"glTF":
        raise ModelError("no es un .glb")
    version, length = struct.unpack_from("<II", data, 4)
    if version != 2 or length != len(data):
        raise ModelError(".glb danado")
    jlen, jtype = struct.unpack_from("<II", data, 12)
    if jtype != 0x4E4F534A or 20 + jlen > len(data):
        raise ModelError(".glb danado")
    try:
        gltf = json.loads(data[20:20 + jlen].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ModelError(".glb danado")
    off = 20 + ((jlen + 3) & ~3)
    bin_len = 0
    if off + 8 <= len(data):
        bin_len, btype = struct.unpack_from("<II", data, off)
        if btype != 0x004E4942 or off + 8 + bin_len > len(data):
            raise ModelError(".glb danado")
    bin_start = off + 8
    if not isinstance(gltf, dict):
        raise ModelError(".glb danado")
    for k in gltf.get("extensionsRequired", []) or []:
        raise ModelError("el .glb necesita la extension %s" % str(k)[:40])
    buffers = gltf.get("buffers", []) or []
    if len(buffers) > 1 or any("uri" in b for b in buffers):
        raise ModelError("el .glb tiene archivos fuera")          # todo tiene que ir dentro
    if buffers and int(buffers[0].get("byteLength", 0)) > bin_len:
        raise ModelError(".glb danado")
    views = gltf.get("bufferViews", []) or []
    for v in views:
        o, n = int(v.get("byteOffset", 0)), int(v.get("byteLength", 0))
        if o < 0 or n < 0 or o + n > bin_len or v.get("buffer", 0) != 0:
            raise ModelError(".glb danado")
    sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
    comp = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    accessors = gltf.get("accessors", []) or []
    for a in accessors:
        cnt = int(a.get("count", 0))
        if cnt < 0 or a.get("type") not in sizes or a.get("componentType") not in comp:
            raise ModelError(".glb con datos no admitidos")
        sp = a.get("sparse")
        if sp:                                   # los usan las expresiones de VRM (no se usan, pero no se rechazan)
            if not isinstance(sp, dict) or int(sp.get("count", 0)) > cnt:
                raise ModelError(".glb danado")
            for part in ("indices", "values"):
                bv = int((sp.get(part) or {}).get("bufferView", -1))
                if not 0 <= bv < len(views):
                    raise ModelError(".glb danado")
        if "bufferView" in a:
            v = views[int(a["bufferView"])] if 0 <= int(a["bufferView"]) < len(views) else None
            if v is None:
                raise ModelError(".glb danado")
            elem = sizes[a["type"]] * comp[a["componentType"]]
            stride = int(v.get("byteStride", 0)) or elem
            if cnt and int(a.get("byteOffset", 0)) + stride * (cnt - 1) + elem > int(v.get("byteLength", 0)):
                raise ModelError(".glb danado")
    verts = idx = 0
    for m in gltf.get("meshes", []) or []:
        for p in m.get("primitives", []) or []:
            pa = (p.get("attributes") or {}).get("POSITION")
            if isinstance(pa, int) and 0 <= pa < len(accessors):
                verts += int(accessors[pa].get("count", 0))
            pi = p.get("indices")
            if isinstance(pi, int) and 0 <= pi < len(accessors):
                idx += int(accessors[pi].get("count", 0))
    if verts > MAX_VERTICES or idx > MAX_INDICES:
        raise ModelError("modelo con demasiados vertices")
    if len(gltf.get("nodes", []) or []) > MAX_NODES:
        raise ModelError("modelo con demasiados huesos")
    values = 0
    for an in gltf.get("animations", []) or []:
        for s in an.get("samplers", []) or []:
            for key in ("input", "output"):
                i = s.get(key)
                if isinstance(i, int) and 0 <= i < len(accessors):
                    a = accessors[i]
                    values += int(a.get("count", 0)) * sizes.get(a.get("type"), 1)
    if values > MAX_ANIM_VALUES:
        raise ModelError("animacion demasiado larga")
    images = gltf.get("images", []) or []
    if len(images) > MAX_IMAGES:
        raise ModelError("demasiadas texturas")
    for im in images:
        if "uri" in im or "bufferView" not in im:
            raise ModelError("el .glb tiene texturas fuera")
        v = views[int(im["bufferView"])]
        raw = data[bin_start + int(v.get("byteOffset", 0)): bin_start + int(v.get("byteOffset", 0)) + int(v.get("byteLength", 0))]
        _check_image(raw)
    if kind == "model" and not (gltf.get("meshes") and gltf.get("skins")):
        raise ModelError("el .glb no tiene un modelo con esqueleto")
    if kind == "anim" and not gltf.get("animations"):
        raise ModelError("el .glb no tiene animaciones")


def _check_image(raw):
    if not (raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:3] == b"\xff\xd8\xff"):
        raise ModelError("textura que no es PNG ni JPG")
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_SIDE * MAX_IMAGE_SIDE
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        im.verify()
    except Exception:  # noqa: BLE001
        raise ModelError("textura danada")
    if w > MAX_IMAGE_SIDE or h > MAX_IMAGE_SIDE:
        raise ModelError("textura demasiado grande")
