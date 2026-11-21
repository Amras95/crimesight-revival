"""CRIMESIGHT Revival - pasa un modelo .fbx a .glb (glTF binario) para ponerlo en un personaje.

Solo Python (y Pillow, que ya va con el lanzador, para texturas que no sean PNG ni JPG). Lee FBX binario y de
texto (ASCII) de 6.1 en adelante: la jerarquia de huesos en la postura de enlace (bind pose), las mallas con sus
normales, UV y materiales, los pesos de la piel, y las texturas de color (dentro del .fbx o junto a el). El
esqueleto se queda como viene: el plugin lo reconoce y lo adapta al del juego (CrimeSightRevivalHumanoid.cs).
"""
import io, json, math, os, struct, zlib
from array import array

# ------------------------------------------------------------------------------------------ avisos
# Los avisos y errores van como (clave, datos) para que el lanzador los traduzca (i18n: models_<clave>).
class FbxError(ValueError):
    def __init__(self, key, **kw):
        super().__init__("%s %s" % (key, kw))
        self.key, self.kw = key, kw


def note(notes, key, **kw):
    if (key, kw) not in notes:
        notes.append((key, kw))


# ------------------------------------------------------------------------------------------ leer el .fbx
class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def all(self, name):
        return [c for c in self.children if c.name == name]


_ARRAY = {b"f": ("f", 4), b"d": ("d", 8), b"l": ("q", 8), b"i": ("i", 4), b"b": ("b", 1), b"c": ("B", 1)}


def _read_binary(data):
    version = struct.unpack_from("<I", data, 23)[0]
    wide = version >= 7500
    hdr = "<QQQB" if wide else "<IIIB"
    hsize = struct.calcsize(hdr)

    def prop(o):
        t = data[o:o + 1]; o += 1
        if t == b"Y": return struct.unpack_from("<h", data, o)[0], o + 2
        if t == b"C": return data[o] != 0, o + 1
        if t == b"I": return struct.unpack_from("<i", data, o)[0], o + 4
        if t == b"F": return struct.unpack_from("<f", data, o)[0], o + 4
        if t == b"D": return struct.unpack_from("<d", data, o)[0], o + 8
        if t == b"L": return struct.unpack_from("<q", data, o)[0], o + 8
        if t in (b"S", b"R"):
            n = struct.unpack_from("<I", data, o)[0]; o += 4
            raw = data[o:o + n]
            return (raw if t == b"R" else raw.decode("utf-8", "replace")), o + n
        if t in _ARRAY:
            n, enc, clen = struct.unpack_from("<III", data, o); o += 12
            raw = data[o:o + clen]
            if enc == 1:
                raw = zlib.decompress(raw)
            code, size = _ARRAY[t]
            a = array(code)
            a.frombytes(raw[:n * size])
            if (array("i", [1]).tobytes()[0] != 1):
                a.byteswap()
            return a, o + clen
        raise ValueError("propiedad FBX desconocida %r" % t)

    def node(o):
        end, nprops, _plen, nlen = struct.unpack_from(hdr, data, o)
        if end == 0:
            return None, o + hsize
        o += hsize
        name = data[o:o + nlen].decode("ascii", "replace"); o += nlen
        props = []
        for _ in range(nprops):
            v, o = prop(o)
            props.append(v)
        children = []
        while o < end:
            c, o = node(o)
            if c is None:
                break
            children.append(c)
        return Node(name, props, children), end

    top, o = [], 27
    while o < len(data) - hsize:
        n, o2 = node(o)
        if n is None:
            break
        top.append(n)
        o = o2
    return Node("", [], top), version


def _read_ascii(text):
    """FBX de texto: 'Nombre: prop, prop { hijos }'."""
    i, n = 0, len(text)

    def skip():
        nonlocal i
        while i < n:
            c = text[i]
            if c in " \t\r\n,":
                i += 1
            elif c == ";":
                while i < n and text[i] != "\n":
                    i += 1
            else:
                break

    def value():
        nonlocal i
        c = text[i]
        if c == '"':
            j = text.index('"', i + 1)
            s = text[i + 1:j]; i = j + 1
            return s.replace("&quot;", '"')
        if c == "*":                                     # *N { a: ... }  (array)
            while i < n and text[i] != "{":
                i += 1
            i += 1
            skip()
            if text.startswith("a:", i):
                i += 2
            j = text.index("}", i)
            body = text[i:j]; i = j + 1
            vals = [float(x) if any(ch in x for ch in ".eE") else int(x) for x in body.replace("\n", "").split(",") if x.strip()]
            return vals
        j = i
        while j < n and text[j] not in ",\r\n{}":
            j += 1
        tok = text[i:j].strip(); i = j
        try:
            return int(tok)
        except ValueError:
            try:
                return float(tok)
            except ValueError:
                return tok

    def block():
        nonlocal i
        out = []
        while True:
            skip()
            if i >= n or text[i] == "}":
                i += 1
                return out
            j = text.index(":", i)
            name = text[i:j].strip(); i = j + 1
            props, children = [], []
            more = False                                 # una coma al final de la linea: sigue en la siguiente
            while True:
                while i < n and (text[i] in " \t" or (more and text[i] in "\r\n")):
                    i += 1
                if i < n and text[i] in "\r\n":                  # una cadena que sigue en la linea siguiente
                    j = i
                    while j < n and text[j] in " \t\r\n":
                        j += 1
                    if j < n and text[j] == '"' and props and isinstance(props[-1], str):
                        i = j; continue
                if i >= n or text[i] in "\r\n}":
                    break
                if text[i] == ",":
                    i += 1; more = True; continue
                more = False
                if text[i] == "{":
                    i += 1
                    children = block()
                    break
                props.append(value())
            # arrays "Name: *N { a: ... }" quedan como una lista en props
            out.append(Node(name, props, children))

    root = []
    while True:
        skip()
        if i >= n:
            break
        j = text.find(":", i)
        if j < 0:
            break
        i_before = i
        nodes = block_one = None
        # el nivel superior se lee como un bloque sin llaves
        i = i_before
        root = block()
        break
    ver = 7400
    for c in root:
        if c.name == "FBXHeaderExtension":
            v = c.find("FBXVersion")
            if v and v.props:
                ver = int(v.props[0])
    return Node("", [], root), ver


def read_fbx(data):
    if data[:20] == b"Kaydara FBX Binary  ":
        return _read_binary(data)
    return _read_ascii(data.decode("utf-8", "replace"))


# ------------------------------------------------------------------------------------------ matrices (columnas)
def mat_id():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def mat_mul(a, b):
    r = [0.0] * 16
    for c in range(4):
        for rr in range(4):
            r[c * 4 + rr] = a[rr] * b[c * 4] + a[4 + rr] * b[c * 4 + 1] + a[8 + rr] * b[c * 4 + 2] + a[12 + rr] * b[c * 4 + 3]
    return r


def mat_inv(m):
    a = [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    inv = [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
    for col in range(4):
        piv = max(range(col, 4), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            return mat_id()
        a[col], a[piv] = a[piv], a[col]; inv[col], inv[piv] = inv[piv], inv[col]
        p = a[col][col]
        a[col] = [x / p for x in a[col]]; inv[col] = [x / p for x in inv[col]]
        for r in range(4):
            if r != col and a[r][col] != 0:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
                inv[r] = [x - f * y for x, y in zip(inv[r], inv[col])]
    return [inv[r][c] for c in range(4) for r in range(4)]


def mat_t(x, y, z):
    m = mat_id(); m[12], m[13], m[14] = x, y, z
    return m


def mat_s(x, y, z):
    m = mat_id(); m[0], m[5], m[10] = x, y, z
    return m


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return [1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


_ORDERS = ["XYZ", "XZY", "YZX", "YXZ", "ZXY", "ZYX", "XYZ"]


def mat_euler(deg, order=0):
    """Euler de FBX en grados: el primer eje del orden se aplica primero."""
    rot = {"X": _rx(math.radians(deg[0])), "Y": _ry(math.radians(deg[1])), "Z": _rz(math.radians(deg[2]))}
    m = mat_id()
    for ax in _ORDERS[order if 0 <= order < len(_ORDERS) else 0]:
        m = mat_mul(rot[ax], m)
    return m


def point(m, x, y, z):
    return (m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14])


def direction(m, x, y, z):
    return (m[0] * x + m[4] * y + m[8] * z, m[1] * x + m[5] * y + m[9] * z, m[2] * x + m[6] * y + m[10] * z)


def normal_matrix(m):
    inv = mat_inv(m)
    return [inv[0], inv[4], inv[8], 0, inv[1], inv[5], inv[9], 0, inv[2], inv[6], inv[10], 0, 0, 0, 0, 1]


# ------------------------------------------------------------------------------------------ la escena
def _props70(node):
    out = {}
    if node is None:
        return out
    p = node.find("Properties70") or node.find("Properties60")
    if p is None:
        return out
    for c in p.children:
        if c.props:
            vals = c.props[4:] if c.name == "P" else c.props[3:]
            out[c.props[0]] = vals[0] if len(vals) == 1 else list(vals)
    return out


def _vec(v, default):
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        return [float(v[0]), float(v[1]), float(v[2])]
    return list(default)


def _clean_name(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if "\x00\x01" in raw:                     # binario: "Nombre\x00\x01Clase"
        return raw.split("\x00\x01")[0]
    if "::" in raw:                           # texto: "Clase::Nombre"
        return raw.split("::", 1)[1]
    return raw


def _arr(node, name):
    c = node.find(name) if node is not None else None
    if c is None or not c.props:
        return None
    v = c.props[0]
    if isinstance(v, (array, list, tuple)):
        return v
    if isinstance(v, (bytes, bytearray, str)):
        return None
    return list(c.props)


class Obj:
    def __init__(self, node, v6=False):
        self.node = node
        self.id = node.props[0]
        self.cls = node.name
        if v6:                                   # FBX 6: sin id, el nombre es la clave ("Nombre\x00\x01Clase", tipo)
            self.name = _clean_name(node.props[0]) if node.props else ""
            self.sub = node.props[1] if len(node.props) > 1 else ""
        else:
            self.name = _clean_name(node.props[1]) if len(node.props) > 1 else ""
            self.sub = node.props[2] if len(node.props) > 2 else ""
        if isinstance(self.sub, bytes):
            self.sub = self.sub.decode("utf-8", "replace")
        self.props = _props70(node)
        self.parent = None          # Model padre
        self.children = []          # Model hijos
        self.src = []               # objetos conectados a este (hijos en el grafo)
        self.dst = []               # a los que se conecta
        self.srcp = []              # (objeto, propiedad) conexiones OP


def convert(path, notes=None):
    """Lee un .fbx y devuelve los bytes del .glb. notes: lista donde dejar avisos."""
    notes = notes if notes is not None else []
    with open(path, "rb") as f:
        data = f.read()
    root, version = read_fbx(data)
    if version < 6100:
        raise FbxError("fbx_old")

    # sistema de ejes y unidades
    v6 = version < 7000
    gnode = root.find("GlobalSettings") or (root.find("Objects").find("GlobalSettings") if root.find("Objects") else None)
    gs = _props70(gnode)
    up_ax, up_sg = int(gs.get("UpAxis", 1)), int(gs.get("UpAxisSign", 1))
    fr_ax, fr_sg = int(gs.get("FrontAxis", 2)), int(gs.get("FrontAxisSign", 1))
    unit = float(gs.get("UnitScaleFactor", 1.0)) / 100.0             # a metros
    e = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    u = [x * up_sg for x in e[up_ax]]
    fwd = [x * fr_sg for x in e[fr_ax]]
    if up_ax == fr_ax:
        fwd = [0.0, 0.0, 1.0] if up_ax != 2 else [0.0, -1.0, 0.0]
    rgt = [u[1] * fwd[2] - u[2] * fwd[1], u[2] * fwd[0] - u[0] * fwd[2], u[0] * fwd[1] - u[1] * fwd[0]]
    # filas: la nueva X es la derecha, Y arriba, Z delante (glTF mira a +Z, la X es la izquierda del modelo... da igual:
    # el plugin lo orienta por los huesos; lo que importa es que sea un giro)
    axis = [rgt[0], u[0], fwd[0], 0, rgt[1], u[1], fwd[1], 0, rgt[2], u[2], fwd[2], 0, 0, 0, 0, 1]
    axis = mat_mul(mat_s(unit, unit, unit), axis)

    objs = {}
    objects = root.find("Objects")
    if objects is None:
        raise FbxError("fbx_empty")
    for c in objects.children:
        if c.props and c.name != "GlobalSettings":
            o = Obj(c, v6)
            objs[o.id] = o
    conns = root.find("Connections")
    for c in (conns.children if conns else []):
        if len(c.props) < 3:
            continue
        kind, a, b = c.props[0], c.props[1], c.props[2]
        if isinstance(kind, bytes):
            kind = kind.decode()
        ca, cb = objs.get(a), objs.get(b)
        if ca is None or cb is None:
            continue
        cb.src.append(ca); ca.dst.append(cb)
        if kind == "OP" and len(c.props) > 3:
            pn = c.props[3]
            cb.srcp.append((ca, pn.decode() if isinstance(pn, bytes) else pn))
        if ca.cls == "Model" and cb.cls == "Model":
            ca.parent = cb; cb.children.append(ca)

    models = [o for o in objs.values() if o.cls == "Model"]

    # transformaciones locales y globales (escena tal cual)
    parts_of = {}

    def local(o, t=None, r=None, s=None):
        """L = T * Roff * Rp * Rpre * R * Rpost^-1 * Rp^-1 * Soff * Sp * S * Sp^-1 (con T, R o S animados si se dan)."""
        p = o.props
        if o.id not in parts_of:
            pre = mat_euler(_vec(p.get("PreRotation"), (0, 0, 0)))
            post = mat_euler(_vec(p.get("PostRotation"), (0, 0, 0)))
            roff, rp = _vec(p.get("RotationOffset"), (0, 0, 0)), _vec(p.get("RotationPivot"), (0, 0, 0))
            soff, sp = _vec(p.get("ScalingOffset"), (0, 0, 0)), _vec(p.get("ScalingPivot"), (0, 0, 0))
            a = mat_mul(mat_mul(mat_t(*roff), mat_t(*rp)), pre)
            b = mat_mul(mat_mul(mat_mul(mat_inv(post), mat_t(*[-v for v in rp])), mat_t(*soff)), mat_t(*sp))
            parts_of[o.id] = (a, b, mat_t(*[-v for v in sp]), int(p.get("RotationOrder", 0) or 0))
        a, b, c, order = parts_of[o.id]
        t = t or _vec(p.get("Lcl Translation"), (0, 0, 0))
        r = r or _vec(p.get("Lcl Rotation"), (0, 0, 0))
        s = s or _vec(p.get("Lcl Scaling"), (1, 1, 1))
        m = mat_mul(mat_t(*t), a)
        m = mat_mul(m, mat_euler(r, order))
        m = mat_mul(m, b)
        m = mat_mul(m, mat_s(*s))
        return mat_mul(m, c)

    glob = {}

    def g(o):
        if o.id in glob:
            return glob[o.id]
        glob[o.id] = mat_id()
        glob[o.id] = mat_mul(g(o.parent), local(o)) if o.parent is not None else local(o)
        return glob[o.id]

    def geometric(o):
        p = o.props
        m = mat_t(*_vec(p.get("GeometricTranslation"), (0, 0, 0)))
        m = mat_mul(m, mat_euler(_vec(p.get("GeometricRotation"), (0, 0, 0))))
        return mat_mul(m, mat_s(*_vec(p.get("GeometricScaling"), (1, 1, 1))))

    # postura de enlace: la del BindPose y la de los clusters (la de los huesos al pegarles la malla)
    bind = {}
    for o in objs.values():
        if o.cls == "Pose" and (o.sub == "BindPose" or "bind" in str(o.name).lower()):
            for pn in o.node.all("PoseNode"):
                nid = pn.find("Node")
                v = _arr(pn, "Matrix")                   # una lista de 16, o 16 numeros sueltos segun el exportador
                if nid is not None and nid.props and v is not None and len(v) == 16:
                    bind.setdefault(nid.props[0], [float(x) for x in v])
    clusters = []
    for o in objs.values():
        if o.cls == "Deformer" and o.sub == "Cluster":
            bone = next((s for s in o.src if s.cls == "Model"), None)
            skin = next((d for d in o.dst if d.cls == "Deformer"), None)
            geom = next((d for d in (skin.dst if skin else []) if d.cls == "Geometry"
                         or (d.cls == "Model" and d.node.find("Vertices") is not None)), None)
            if bone is None or geom is None:
                continue
            tl, tr = _arr(o.node, "TransformLink"), _arr(o.node, "Transform")
            if tl is not None and len(tl) == 16:
                bind[bone.id] = [float(x) for x in tl]
            # "Transform" es la malla vista desde el hueso al enlazarla: la malla en el mundo es TransformLink * Transform
            mesh_bind = None
            if tr is not None and len(tr) == 16 and tl is not None and len(tl) == 16:
                mesh_bind = mat_mul([float(x) for x in tl], [float(x) for x in tr])
            clusters.append((o, bone, geom, mesh_bind))

    bones = {b.id for _, b, _, _ in clusters}
    for o in models:
        if o.sub in ("LimbNode", "Limb", "Root") or (o.sub == "Null" and any(c.id in bones for c in _desc(o))):
            bones.add(o.id)
    # tambien los padres de los huesos (hasta la raiz) para que la jerarquia quede entera
    for bid in list(bones):
        o = objs[bid].parent
        while o is not None and o.cls == "Model" and o.sub != "Mesh":
            bones.add(o.id); o = o.parent

    def bind_global(o):
        """Postura de enlace del hueso: la del cluster / BindPose, o la de su padre por su local."""
        if o.id in bind:
            return bind[o.id]
        if o.parent is not None and o.parent.id in bones:
            m = mat_mul(bind_global(o.parent), local(o))
        else:
            m = g(o)
        bind[o.id] = m
        return m

    bone_list = [o for o in models if o.id in bones]
    order = sorted(bone_list, key=lambda o: _depth(o))
    names = {}
    for o in order:                                                  # nombres unicos
        nm = o.name or "hueso"
        k = 1
        while nm in names.values():
            k += 1; nm = "%s.%d" % (o.name, k)
        names[o.id] = nm
    bidx = {o.id: i for i, o in enumerate(order)}

    # mallas
    meshes = []
    images, image_of = [], {}
    # imagenes incluidas en el .fbx por nombre de archivo (a veces una textura apunta a una copia sin contenido)
    embedded = {}
    for v in [x for x in objs.values() if x.cls == "Video"]:
        c = v.node.find("Content")
        if c is None or not c.props or not isinstance(c.props[0], (bytes, bytearray)) or len(c.props[0]) <= 16:
            continue
        for k in ("RelativeFilename", "FileName", "Filename"):
            n = v.node.find(k)
            if n is not None and n.props and isinstance(n.props[0], str) and n.props[0]:
                embedded.setdefault(os.path.basename(n.props[0].replace("\\", "/")).lower(), bytes(c.props[0]))
    fbx_dir = os.path.dirname(os.path.abspath(path))
    for o in models:
        geoms = [s for s in o.src if s.cls == "Geometry" and (s.sub == "Mesh" or s.node.find("Vertices") is not None)]
        if not geoms and o.node.find("Vertices") is not None:      # FBX 6: la malla va dentro del propio modelo
            geoms = [o]
        if not geoms:
            continue
        mats = [s for s in o.src if s.cls == "Material"]
        for geo in geoms:
            m = _mesh(geo, o, mats, clusters, bidx, bind_global, g, geometric, axis, notes)
            if m is None:
                continue
            for prim in m["prims"]:
                mat = prim.pop("mat")
                prim["image"] = -1
                prim["color"] = [1.0, 1.0, 1.0, 1.0]
                if mat is not None:
                    dc = mat.props.get("DiffuseColor") or mat.props.get("Diffuse")
                    if isinstance(dc, list) and len(dc) >= 3:
                        prim["color"] = [float(dc[0]), float(dc[1]), float(dc[2]), 1.0]
                    op = mat.props.get("Opacity")
                    tex = _texture_for(mat)
                    if tex is not None:
                        key = tex.id
                        if key not in image_of:
                            img = _image(tex, fbx_dir, notes, embedded)
                            image_of[key] = len(images) if img else -1
                            if img:
                                images.append(img)
                        prim["image"] = image_of[key]
                        if prim["image"] >= 0:
                            prim["color"] = [1.0, 1.0, 1.0, 1.0]
            meshes.append(m)
    # nodos de huesos (postura de enlace, ya en ejes glTF y metros)
    ax_inv = mat_inv(axis)
    node_glob = {o.id: _unscaled(mat_mul(mat_mul(axis, bind_global(o)), ax_inv)) for o in order}
    anims = _bake_anims(objs, order, local, g, axis, ax_inv, node_glob)
    if not meshes and not anims:
        raise FbxError("fbx_empty")
    return _write_glb(order, names, node_glob, meshes, images, notes, anims)


FBX_TICKS = 46186158000.0


def _bake_anims(objs, order, local, g, axis, ax_inv, node_glob, fps=30.0):
    """Cada AnimationStack, a 30 fotogramas por segundo: posicion y giro local de cada hueso (en la misma escena sin
    escala que el reposo)."""
    out = []
    bone_ids = {o.id for o in order}
    for st in [o for o in objs.values() if o.cls == "AnimationStack"]:
        curves = {}                                                  # (modelo, "T"/"R"/"S") -> [cx, cy, cz, defaults]
        t0, t1 = None, None
        for layer in [x for x in st.src if x.cls == "AnimationLayer"]:
            for cn in [x for x in layer.src if x.cls == "AnimationCurveNode"]:
                for mdl, prop in [(d, pn) for d in cn.dst for (x, pn) in d.srcp if x is cn and d.cls == "Model"]:
                    kind = {"Lcl Translation": "T", "Lcl Rotation": "R", "Lcl Scaling": "S"}.get(prop)
                    if kind is None or mdl.id not in bone_ids:
                        continue
                    dflt = [cn.props.get("d|X", 0.0), cn.props.get("d|Y", 0.0), cn.props.get("d|Z", 0.0)]
                    chans = [None, None, None]
                    for cv, pn in cn.srcp:
                        if cv.cls != "AnimationCurve":
                            continue
                        k = {"d|X": 0, "d|Y": 1, "d|Z": 2}.get(pn)
                        kt, kv = _arr(cv.node, "KeyTime"), _arr(cv.node, "KeyValueFloat")
                        if k is None or kt is None or kv is None or not len(kt):
                            continue
                        times = [x / FBX_TICKS for x in kt]
                        chans[k] = (times, [float(x) for x in kv])
                        t0 = times[0] if t0 is None else min(t0, times[0])
                        t1 = times[-1] if t1 is None else max(t1, times[-1])
                    if any(chans):
                        curves[(mdl.id, kind)] = (chans, [float(x) if isinstance(x, (int, float)) else 0.0 for x in dflt])
        if not curves or t0 is None or t1 <= t0:
            continue
        frames = max(2, int(round((t1 - t0) * fps)) + 1)
        tracks = {o.id: ([], []) for o in order}
        for f in range(frames):
            t = t0 + (t1 - t0) * f / (frames - 1)
            glob = {}

            def ga(o):
                if o.id in glob:
                    return glob[o.id]
                vals = {}
                for kind in ("T", "R", "S"):
                    c = curves.get((o.id, kind))
                    if c:
                        vals[kind] = [_curve_at(c[0][i], t, c[1][i]) if c[0][i] else None for i in range(3)]
                if vals:
                    base = {"T": _vec(o.props.get("Lcl Translation"), (0, 0, 0)), "R": _vec(o.props.get("Lcl Rotation"), (0, 0, 0)),
                            "S": _vec(o.props.get("Lcl Scaling"), (1, 1, 1))}
                    for kind, v in vals.items():
                        vals[kind] = [v[i] if v[i] is not None else base[kind][i] for i in range(3)]
                    lm = local(o, vals.get("T"), vals.get("R"), vals.get("S"))
                else:
                    lm = local(o)
                par = o.parent
                m = mat_mul(ga(par) if par is not None and par.id in bone_ids else (g(par) if par is not None else mat_id()), lm)
                glob[o.id] = m
                return m
            norm = {o.id: _unscaled(mat_mul(mat_mul(axis, ga(o)), ax_inv)) for o in order}
            for o in order:
                par = o.parent
                while par is not None and par.id not in norm:
                    par = par.parent
                loc = norm[o.id] if par is None else mat_mul(mat_inv(norm[par.id]), norm[o.id])
                tr, q = _trs(loc)
                tracks[o.id][0].extend(tr); tracks[o.id][1].extend(q)
        times = [(t1 - t0) * f / (frames - 1) for f in range(frames)]
        out.append({"name": st.name or "anim", "times": times, "tracks": tracks})
    return out


def _curve_at(ch, t, default):
    times, vals = ch
    if not times:
        return default
    if t <= times[0]:
        return vals[0]
    if t >= times[-1]:
        return vals[-1]
    lo, hi = 0, len(times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            lo = mid
        else:
            hi = mid
    f = (t - times[lo]) / max(times[hi] - times[lo], 1e-9)
    return vals[lo] + (vals[hi] - vals[lo]) * f


def _trs(m):
    """Posicion y giro (x, y, z, w) de una matriz sin escala."""
    c0, c1, c2 = (m[0], m[1], m[2]), (m[4], m[5], m[6]), (m[8], m[9], m[10])
    tr = c0[0] + c1[1] + c2[2]
    if tr > 0:
        s = math.sqrt(tr + 1) * 2
        q = ((c1[2] - c2[1]) / s, (c2[0] - c0[2]) / s, (c0[1] - c1[0]) / s, 0.25 * s)
    elif c0[0] > c1[1] and c0[0] > c2[2]:
        s = math.sqrt(1 + c0[0] - c1[1] - c2[2]) * 2
        q = (0.25 * s, (c1[0] + c0[1]) / s, (c2[0] + c0[2]) / s, (c1[2] - c2[1]) / s)
    elif c1[1] > c2[2]:
        s = math.sqrt(1 + c1[1] - c0[0] - c2[2]) * 2
        q = ((c1[0] + c0[1]) / s, 0.25 * s, (c2[1] + c1[2]) / s, (c2[0] - c0[2]) / s)
    else:
        s = math.sqrt(1 + c2[2] - c0[0] - c1[1]) * 2
        q = ((c2[0] + c0[2]) / s, (c2[1] + c1[2]) / s, 0.25 * s, (c0[1] - c1[0]) / s)
    l = math.sqrt(sum(x * x for x in q)) or 1.0
    return [m[12], m[13], m[14]], [x / l for x in q]


def _unscaled(m):
    """La misma postura sin escala (los huesos de 100 de Blender en cm): giro limpio + posicion. La malla ya esta en
    su sitio, asi que da igual para la piel y cualquier programa la lee bien."""
    x = [m[0], m[1], m[2]]; y = [m[4], m[5], m[6]]

    def nrm(v):
        l = math.sqrt(sum(c * c for c in v)) or 1.0
        return [c / l for c in v]
    x = nrm(x)
    d = sum(a * b for a, b in zip(x, y))
    y = nrm([b - d * a for a, b in zip(x, y)])
    z = [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]
    return [x[0], x[1], x[2], 0, y[0], y[1], y[2], 0, z[0], z[1], z[2], 0, m[12], m[13], m[14], 1]


def _desc(o):
    out, st = [], list(o.children)
    while st:
        c = st.pop(); out.append(c); st.extend(c.children)
    return out


def _depth(o):
    d = 0
    while o.parent is not None:
        d += 1; o = o.parent
    return d


def _texture_for(mat):
    best = None
    for s, pn in mat.srcp:
        if s.cls != "Texture":
            continue
        p = (pn or "").lower()
        if "diffuse" in p or "basecolor" in p or "base_color" in p or p in ("maintex", "albedo"):
            return s
        if best is None and "normal" not in p and "bump" not in p and "spec" not in p and "rough" not in p \
                and "metal" not in p and "emiss" not in p and "opac" not in p and "transp" not in p and "occl" not in p:
            best = s
    if best is None:
        best = next((s for s in mat.src if s.cls == "Texture"), None)
    return best


def _image(tex, fbx_dir, notes, embedded=None):
    """Bytes PNG/JPEG de una textura: la que va dentro del .fbx o el archivo que nombra (buscandolo cerca)."""
    raw, fname = None, None
    for v in [s for s in tex.src if s.cls == "Video"]:
        c = v.node.find("Content")
        if c is not None and c.props and isinstance(c.props[0], (bytes, bytearray)) and len(c.props[0]) > 16:
            raw = bytes(c.props[0])
        elif c is not None and c.props and all(isinstance(x, str) for x in c.props):     # FBX de texto: base64
            import base64
            parts = [x.strip() for x in c.props if x.strip()]
            for attempt in ("".join(parts), None):                  # entero, o trozo a trozo (cada uno con su relleno)
                try:
                    b = base64.b64decode(attempt) if attempt is not None else b"".join(base64.b64decode(x) for x in parts)
                except ValueError:
                    continue
                if len(b) > 16:
                    raw = b
                    break
        for k in ("RelativeFilename", "FileName", "Filename"):
            n = v.node.find(k)
            if n is not None and n.props and not fname:
                fname = n.props[0]
    for k in ("RelativeFilename", "FileName", "Filename"):
        n = tex.node.find(k)
        if n is not None and n.props and n.props[0] and not fname:
            fname = n.props[0]
    if isinstance(fname, bytes):
        fname = fname.decode("utf-8", "replace")
    if raw is None and fname and embedded:
        raw = embedded.get(os.path.basename(fname.replace("\\", "/")).lower())
    if raw is None and fname:
        p = _find_file(fname, fbx_dir)
        if p:
            with open(p, "rb") as f:
                raw = f.read()
    if raw is None:
        if fname:
            note(notes, "tex_missing", name=os.path.basename(fname.replace("\\", "/")))
        return None
    return _to_web_image(raw, fname or "", notes)


def _find_file(fname, base):
    fname = fname.replace("\\", "/")
    leaf = os.path.basename(fname)
    stem = os.path.splitext(leaf)[0].lower()
    cands = [fname, os.path.join(base, fname), os.path.join(base, leaf)]
    for c in cands:
        if os.path.isfile(c):
            return c
    exts = (".png", ".jpg", ".jpeg", ".tga", ".bmp", ".tif", ".tiff", ".psd", ".dds", ".webp")
    best = None
    for top in (base, os.path.dirname(base)):
        for dp, _dn, fs in os.walk(top):
            if dp.count(os.sep) - top.count(os.sep) > 3:
                continue
            for f in fs:
                if f.lower() == leaf.lower():
                    return os.path.join(dp, f)
                if best is None and os.path.splitext(f)[0].lower() == stem and f.lower().endswith(exts):
                    best = os.path.join(dp, f)
        if best:
            return best
    return best


def _to_web_image(raw, name, notes):
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return ("image/png", raw)
    if raw[:3] == b"\xff\xd8\xff":
        return ("image/jpeg", raw)
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        im.load()
        im = im.convert("RGBA")
        out = io.BytesIO()
        im.save(out, "PNG")
        return ("image/png", out.getvalue())
    except Exception as e:                                           # noqa: BLE001
        note(notes, "tex_bad", name=os.path.basename(name.replace("\\", "/")) or "?")
        return None


def _layer(geo, kind, data_name, index_name):
    el = geo.find(kind)
    if el is None:
        return None
    data = _arr(el, data_name)
    if data is None:
        return None
    mapping = el.find("MappingInformationType")
    ref = el.find("ReferenceInformationType")
    mapping = (mapping.props[0] if mapping and mapping.props else "ByPolygonVertex")
    ref = (ref.props[0] if ref and ref.props else "Direct")
    if isinstance(mapping, bytes): mapping = mapping.decode()
    if isinstance(ref, bytes): ref = ref.decode()
    idx = _arr(el, index_name) if ref in ("IndexToDirect", "Index") else None
    return mapping, idx, data


def _layer_index(layer, corner, cp, poly):
    mapping, idx, _ = layer
    if mapping == "ByPolygonVertex":
        i = corner
    elif mapping in ("ByVertice", "ByVertex", "ByControlPoint"):
        i = cp
    elif mapping == "ByPolygon":
        i = poly
    else:                                                            # AllSame
        i = 0
    if idx is not None:
        i = idx[i] if i < len(idx) else 0
    return i


def _mesh(geo_obj, model, mats, clusters, bidx, bind_global, g, geometric, axis, notes):
    geo = geo_obj.node
    verts = _arr(geo, "Vertices")
    pvi = _arr(geo, "PolygonVertexIndex")
    if not verts or not pvi:
        return None
    nrm = _layer(geo, "LayerElementNormal", "Normals", "NormalsIndex")
    uv = _layer(geo, "LayerElementUV", "UV", "UVIndex")
    mat_layer = None
    ml = geo.find("LayerElementMaterial")
    if ml is not None:
        mm = ml.find("MappingInformationType")
        mapping = mm.props[0] if mm and mm.props else "AllSame"
        if isinstance(mapping, bytes): mapping = mapping.decode()
        mat_layer = (mapping, _arr(ml, "Materials"))

    # pesos por punto de control
    ncp = len(verts) // 3
    weights = [[] for _ in range(ncp)]
    mesh_bind = None
    for cl, bone, cgeo, tr in clusters:
        if cgeo is not geo_obj:
            continue
        if mesh_bind is None and tr is not None:
            mesh_bind = tr
        ind, w = _arr(cl.node, "Indexes"), _arr(cl.node, "Weights")
        if ind is None or w is None:
            continue
        b = bidx.get(bone.id)
        if b is None:
            continue
        for i, wt in zip(ind, w):
            if 0 <= i < ncp and wt > 0:
                weights[i].append((b, float(wt)))
    skinned = any(weights)
    if skinned:
        to_world = mat_mul(mesh_bind if mesh_bind is not None else g(model), geometric(model))
    else:
        to_world = mat_mul(g(model), geometric(model))
        # si cuelga de un hueso, va pegada a el
        o = model.parent
        while o is not None and o.id not in bidx:
            o = o.parent
        if o is not None:
            for i in range(ncp):
                weights[i] = [(bidx[o.id], 1.0)]
            skinned = True
        elif bidx:
            note(notes, "mesh_static", name=model.name)
    m = mat_mul(axis, to_world)
    nm = normal_matrix(m)

    # esquinas -> vertices unicos por (punto, normal, uv, material)
    prims = {}
    poly, corner, start = 0, 0, 0
    n = len(pvi)
    while start < n:
        end = start
        while end < n and pvi[end] >= 0:
            end += 1
        if end >= n:
            break
        cps = [pvi[k] if pvi[k] >= 0 else ~pvi[k] for k in range(start, end + 1)]
        mi = 0
        if mat_layer and mat_layer[1]:
            mi = mat_layer[1][poly] if mat_layer[0] == "ByPolygon" and poly < len(mat_layer[1]) else mat_layer[1][0]
        pr = prims.get(mi)
        if pr is None:
            pr = prims[mi] = {"key": {}, "pos": [], "nrm": [], "uv": [], "j": [], "w": [], "idx": []}
        ids = []
        for k, cp in enumerate(cps):
            c = start + k
            nn = None
            if nrm:
                i = _layer_index(nrm, c, cp, poly)
                d = nrm[2]
                if 0 <= i * 3 + 2 < len(d):
                    nn = (round(d[i * 3], 4), round(d[i * 3 + 1], 4), round(d[i * 3 + 2], 4))
            tt = None
            if uv:
                i = _layer_index(uv, c, cp, poly)
                d = uv[2]
                if 0 <= i * 2 + 1 < len(d):
                    tt = (round(d[i * 2], 5), round(d[i * 2 + 1], 5))
            key = (cp, nn, tt)
            vi = pr["key"].get(key)
            if vi is None:
                vi = pr["key"][key] = len(pr["pos"]) // 3
                pr["pos"].extend(point(m, verts[cp * 3], verts[cp * 3 + 1], verts[cp * 3 + 2]))
                if nn is not None:
                    x, y, z = direction(nm, *nn)
                    l = math.sqrt(x * x + y * y + z * z) or 1.0
                    pr["nrm"].extend((x / l, y / l, z / l))
                if tt is not None:
                    pr["uv"].extend((tt[0], 1.0 - tt[1]))               # glTF: V hacia abajo
                ws = sorted(weights[cp], key=lambda x: -x[1])[:4] if cp < ncp else []
                tot = sum(x[1] for x in ws)
                jj = [x[0] for x in ws] + [0] * (4 - len(ws))
                ww = [x[1] / tot for x in ws] + [0.0] * (4 - len(ws)) if tot > 0 else [1.0, 0, 0, 0]
                pr["j"].extend(jj); pr["w"].extend(ww)
            ids.append(vi)
        for k in range(1, len(ids) - 1):                             # abanico
            pr["idx"].extend((ids[0], ids[k], ids[k + 1]))
        start, poly = end + 1, poly + 1
    out = []
    for mi, pr in sorted(prims.items()):
        if not pr["idx"]:
            continue
        out.append({"pos": pr["pos"], "nrm": pr["nrm"] if len(pr["nrm"]) == len(pr["pos"]) else None,
                    "uv": pr["uv"] if len(pr["uv"]) * 3 == len(pr["pos"]) * 2 else None,
                    "j": pr["j"], "w": pr["w"], "idx": pr["idx"],
                    "mat": mats[mi] if 0 <= mi < len(mats) else (mats[0] if mats else None)})
    return {"name": model.name or "malla", "prims": out, "skinned": skinned}


# ------------------------------------------------------------------------------------------ escribir el .glb
def _write_glb(order, names, node_glob, meshes, images, notes, anims=()):
    buf = bytearray()
    views, accessors = [], []

    def add_view(b, target=None):
        while len(buf) % 4:
            buf.append(0)
        v = {"buffer": 0, "byteOffset": len(buf), "byteLength": len(b)}
        if target:
            v["target"] = target
        buf.extend(b)
        views.append(v)
        return len(views) - 1

    def add_acc(values, code, ctype, typ, target=None, minmax=False):
        a = array(code, values)
        acc = {"bufferView": add_view(a.tobytes(), target), "componentType": ctype, "count": len(values) // {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[typ], "type": typ}
        if minmax:
            n = {"VEC3": 3}[typ]
            acc["min"] = [min(values[i::n]) for i in range(n)]
            acc["max"] = [max(values[i::n]) for i in range(n)]
        accessors.append(acc)
        return len(accessors) - 1

    nodes = []
    index = {}
    for o in order:
        index[o.id] = len(nodes)
        nodes.append({"name": names[o.id]})
    roots = []
    for o in order:
        par = o.parent
        while par is not None and par.id not in index:
            par = par.parent
        gm = node_glob[o.id]
        if par is None:
            loc = gm; roots.append(index[o.id])
        else:
            loc = mat_mul(mat_inv(node_glob[par.id]), gm)
            nodes[index[par.id]].setdefault("children", []).append(index[o.id])
        tr, q = _trs(loc)
        nodes[index[o.id]]["translation"] = [round(x, 7) for x in tr]
        nodes[index[o.id]]["rotation"] = [round(x, 7) for x in q]

    skin = None
    if order:
        ibm = []
        for o in order:
            ibm.extend(mat_inv(node_glob[o.id]))
        skin = {"joints": [index[o.id] for o in order], "inverseBindMatrices": add_acc(ibm, "f", 5126, "MAT4")}

    materials, mat_of = [], {}
    gl_meshes = []
    for m in meshes:
        prims = []
        for p in m["prims"]:
            key = (p["image"], tuple(round(x, 4) for x in p["color"]))
            if key not in mat_of:
                mat = {"name": "mat%d" % len(materials), "pbrMetallicRoughness": {"baseColorFactor": p["color"], "metallicFactor": 0.0}}
                if p["image"] >= 0:
                    mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": p["image"]}
                mat_of[key] = len(materials); materials.append(mat)
            attr = {"POSITION": add_acc(p["pos"], "f", 5126, "VEC3", 34962, True)}
            if p["nrm"]:
                attr["NORMAL"] = add_acc(p["nrm"], "f", 5126, "VEC3", 34962)
            if p["uv"]:
                attr["TEXCOORD_0"] = add_acc(p["uv"], "f", 5126, "VEC2", 34962)
            if skin and m["skinned"]:
                attr["JOINTS_0"] = add_acc(p["j"], "H", 5123, "VEC4", 34962)
                attr["WEIGHTS_0"] = add_acc(p["w"], "f", 5126, "VEC4", 34962)
            big = max(p["idx"]) > 65535
            ind = add_acc(p["idx"], "I" if big else "H", 5125 if big else 5123, "SCALAR", 34963)
            prims.append({"attributes": attr, "indices": ind, "material": mat_of[key]})
        gl_meshes.append({"name": m["name"], "primitives": prims})
        node = {"name": m["name"], "mesh": len(gl_meshes) - 1}
        if skin and m["skinned"]:
            node["skin"] = 0
        roots.append(len(nodes))
        nodes.append(node)

    gl_anims = []
    for an in anims:
        samplers, channels = [], []
        tacc = add_acc(an["times"], "f", 5126, "SCALAR")
        accessors[tacc]["min"] = [an["times"][0]]; accessors[tacc]["max"] = [an["times"][-1]]
        for o in order:
            tr, q = an["tracks"][o.id]
            for path, vals, typ in (("translation", tr, "VEC3"), ("rotation", q, "VEC4")):
                samplers.append({"input": tacc, "output": add_acc(vals, "f", 5126, typ), "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1, "target": {"node": index[o.id], "path": path}})
        gl_anims.append({"name": an["name"], "samplers": samplers, "channels": channels})

    gl_images, textures = [], []
    for mime, b in images:
        gl_images.append({"bufferView": add_view(b), "mimeType": mime})
        textures.append({"source": len(gl_images) - 1})
    while len(buf) % 4:
        buf.append(0)
    gltf = {"asset": {"version": "2.0", "generator": "CRIMESIGHT Revival fbx2glb"}, "scene": 0,
            "scenes": [{"nodes": roots}], "nodes": nodes, "meshes": gl_meshes, "materials": materials,
            "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    for k in ("meshes", "materials"):
        if not gltf[k]:
            del gltf[k]
    if skin and meshes:
        gltf["skins"] = [skin]
    if gl_anims:
        gltf["animations"] = gl_anims
    if gl_images:
        gltf["images"] = gl_images; gltf["textures"] = textures
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    out = bytearray(b"glTF") + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(buf))
    out += struct.pack("<I", len(js)) + b"JSON" + js
    out += struct.pack("<I", len(buf)) + b"BIN\x00" + buf
    return bytes(out)


if __name__ == "__main__":
    import sys
    msgs = []
    glb = convert(sys.argv[1], msgs)
    with open(sys.argv[2], "wb") as f:
        f.write(glb)
    for x in msgs:
        print("aviso:", x[0], x[1])
    print("ok", len(glb), "bytes")
