"""
CRIMESIGHT Revival - stage creator: reads the pieces of the game's stages.

From the player's copy of the game (nothing from Konami is ever distributed) it takes, for each stage:
the rooms (position, rotation, size and gaps in their walls), the pieces covering those
gaps (doors, shelves, windows, main door), the points of interest (wolves, gas,
passages) and the starting squares. Also the navigation meshes (NAV_*), which the plugin
needs in a readable version to rebuild navigation.

The game works with 6x6-unit squares: square (i, j) has its centre at (6i, 6j);
x from -6 to 6 and z from 0 to 9. Rooms take 1, 2, 3, 4 or 6 squares.

  read_game(game_dir)  -> raw data (with UnityPy; takes a few seconds)
  build_catalog(raw)   -> catalogue for the editor and for stagelayout
  load(game_dir)       -> catalogue, cached in the launcher's data folder
"""
import base64, json, math, os, struct

GRID = 6.0
MIN_X, MAX_X, MIN_Z, MAX_Z = -6, 6, 0, 9          # limits of the game's grid (13 x 10)
DATA = "CrimeSight_Data"
CATALOG_VERSION = 3
RAW_SCRIPTS = ("Stage", "Room")                    # components whose data is read by hand


class StageDataError(RuntimeError):
    pass


# ---------------------------------------------------------------- reading the game (UnityPy)
def _scripts_map(data_dir):
    import UnityPy
    env = UnityPy.load(os.path.join(data_dir, "globalgamemanagers.assets"))
    out = {}
    for o in env.objects:
        if o.type.name == "MonoScript":
            try:
                out[o.path_id] = o.read().m_ClassName
            except Exception:  # noqa: BLE001
                pass
    return out


def _read_level(path, scripts):
    import UnityPy
    env = UnityPy.load(path)
    sf = list(env.files.values())[0]
    ext = [os.path.basename(e.path) for e in sf.externals]
    gos = {}
    for o in sf.objects.values():
        if o.type.name == "GameObject":
            tt = o.read_typetree()
            gos[o.path_id] = {"name": tt["m_Name"], "active": bool(tt.get("m_IsActive", True)), "c": {}}
    for o in sf.objects.values():
        n = o.type.name
        try:
            if n == "Transform":
                tt = o.read_typetree()
                g = gos[tt["m_GameObject"]["m_PathID"]]
                g["t"] = {"id": o.path_id, "p": [tt["m_LocalPosition"][k] for k in "xyz"],
                          "r": [tt["m_LocalRotation"][k] for k in "xyzw"], "s": [tt["m_LocalScale"][k] for k in "xyz"],
                          "father": tt["m_Father"]["m_PathID"], "children": [c["m_PathID"] for c in tt["m_Children"]]}
            elif n == "MonoBehaviour":
                raw = o.get_raw_data()
                gid = struct.unpack_from("<iq", raw, 0)[1]
                fid, pid = struct.unpack_from("<iq", raw, 16)
                name = scripts.get(pid, "?") if fid and ext[fid - 1].startswith("globalgamemanagers.assets") else "?"
                e = {"id": o.path_id}
                if name in RAW_SCRIPTS:
                    e["raw"] = base64.b64encode(bytes(raw)).decode()
                gos[gid]["c"].setdefault("MB:" + name, []).append(e)
            elif n == "BoxCollider":
                tt = o.read_typetree()
                gos[tt["m_GameObject"]["m_PathID"]]["c"].setdefault(n, []).append(
                    {"id": o.path_id, "center": [tt["m_Center"][k] for k in "xyz"], "size": [tt["m_Size"][k] for k in "xyz"]})
            elif n == "MeshFilter":
                tt = o.read_typetree()
                fid, pid = tt["m_Mesh"]["m_FileID"], tt["m_Mesh"]["m_PathID"]
                gos[tt["m_GameObject"]["m_PathID"]]["c"].setdefault(n, []).append(
                    {"id": o.path_id, "file": ext[fid - 1] if fid else os.path.basename(path).replace(".original", ""),
                     "pid": pid})
        except (KeyError, IndexError, struct.error):
            continue
    return {"gos": gos}


def _mesh_data(mesh):
    """Vertices and triangles of a mesh (flat list of floats / of indices)."""
    from UnityPy.helpers.MeshHelper import MeshHandler
    h = MeshHandler(mesh)
    h.process()
    v = [round(float(c), 4) for p in h.m_Vertices for c in p[:3]]
    t = []
    for sub in h.get_triangles():
        for tri in sub:
            t += [int(i) for i in tri]
    return {"v": v, "t": t}


def _stage_files(data_dir):
    """Stage scenes (Stage_Yokn, Stage_Yokn_v1030...) -> levelN file, according to the game's list."""
    import re, UnityPy
    out = {}
    try:
        for o in UnityPy.load(os.path.join(data_dir, "globalgamemanagers")).objects:
            if o.type.name == "BuildSettings":
                for i, path in enumerate(o.read_typetree().get("scenes", [])):
                    scene = os.path.basename(str(path)).replace(".unity", "")
                    if re.fullmatch(r"Stage_Yokn(_v\d+)?", scene) and os.path.isfile(os.path.join(data_dir, f"level{i}")):
                        out[scene] = f"level{i}"
    except Exception:  # noqa: BLE001
        out = {}
    if not out:                                     # without the list: the files whose root is a stage
        for n in sorted((n for n in os.listdir(data_dir) if n.startswith("level") and n[5:].isdigit()),
                        key=lambda n: int(n[5:])):
            with open(os.path.join(data_dir, n), "rb") as f:
                m = re.search(rb"Stage_Yokn(_v\d+)?\x00", f.read())
            if m:
                out.setdefault(m.group(0)[:-1].decode(), n)
    return out


def read_game(game_dir, progress=None):
    """Reads the stages from the game copy. Returns {"levels": {scene: {...}}, "nav": {mesh: {v, t}}}."""
    import UnityPy
    data_dir = os.path.join(game_dir, DATA)
    say = progress or (lambda pct: None)
    say(2)
    scripts = _scripts_map(data_dir)
    levels = {}
    files = _stage_files(data_dir)
    for k, (scene, name) in enumerate(sorted(files.items())):
        lv = _read_level(_source(game_dir, name), scripts)
        root = [g for g in lv["gos"].values() if "MB:Stage" in g["c"] and g.get("t", {}).get("father") == 0]
        if root and root[0]["name"] == scene:
            lv["file"] = name
            levels[scene] = lv
        say(5 + 35 * (k + 1) // len(files))
    if not levels:
        raise StageDataError("No encuentro los escenarios en esta copia del juego.")
    # navigation meshes: name and geometry
    need = {}
    for lv in levels.values():
        for g in lv["gos"].values():
            if g["name"].startswith("NAV_"):
                for c in g["c"].get("MeshFilter", []):
                    need.setdefault(c["file"], set()).add(c["pid"])
    nav, names_by = {}, {}
    for k, (fname, pids) in enumerate(sorted(need.items())):
        path = _source(game_dir, fname)
        if not os.path.isfile(path):
            continue
        sf = list(UnityPy.load(path).files.values())[0]
        say(45 + 40 * k // max(1, len(need)))
        for pid in pids:
            o = sf.objects.get(pid)
            if o is None or o.type.name != "Mesh":
                continue
            m = o.read()
            names_by[(fname, pid)] = m.m_Name
            if m.m_Name not in nav:
                nav[m.m_Name] = _mesh_data(m)
    for lv in levels.values():
        for g in lv["gos"].values():
            for c in g["c"].get("MeshFilter", []):
                c["mesh"] = names_by.get((c["file"], c["pid"]))
    say(90)
    return {"levels": levels, "nav": nav}


# ---------------------------------------------------------------- geometry
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return [vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)]


def q_yaw(q):
    """Rotation about the vertical axis, in degrees (0 = facing +z, 90 = +x)."""
    f = qrot(q, [0, 0, 1])
    return round(math.degrees(math.atan2(f[0], f[2])), 2) % 360


def rot_xz(x, z, yaw):
    """Rotates a local point (x, z) by the yaw angle (degrees) the way Unity does about the Y axis."""
    a = math.radians(yaw)
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, -x * s + z * c


def norm_yaw(a):
    return round(a) % 360


class Level:
    """Hierarchy of a stage with world positions."""

    def __init__(self, lv):
        self.gos = {int(k): v for k, v in lv["gos"].items()}
        self.by_t = {g["t"]["id"]: gid for gid, g in self.gos.items() if "t" in g}
        self.by_comp = {}
        for gid, g in self.gos.items():
            if "t" in g:
                self.by_comp[g["t"]["id"]] = gid
            for comps in g["c"].values():
                for e in comps:
                    self.by_comp[e["id"]] = gid
        roots = [gid for gid, g in self.gos.items() if "MB:Stage" in g["c"]]
        if not roots:
            raise StageDataError("Escenario sin componente Stage.")
        self.root = roots[0]
        self._w = {}

    def parent(self, gid):
        return self.by_t.get(self.gos[gid]["t"]["father"])

    def children(self, gid):
        return [self.by_t[c] for c in self.gos[gid]["t"]["children"] if c in self.by_t]

    def world(self, gid):
        if gid not in self._w:
            t = self.gos[gid]["t"]
            p = self.parent(gid)
            if p is None:
                self._w[gid] = (list(t["p"]), list(t["r"]), list(t["s"]))
            else:
                pp, pr, ps = self.world(p)
                lp = [t["p"][i] * ps[i] for i in range(3)]
                self._w[gid] = ([a + b for a, b in zip(pp, qrot(pr, lp))], qmul(pr, t["r"]),
                                [ps[i] * t["s"][i] for i in range(3)])
        return self._w[gid]

    def pose(self, gid):
        p, q, _ = self.world(gid)
        return round(p[0], 3), round(p[1], 3), round(p[2], 3), q_yaw(q)

    def walk(self, gid=None):
        gid = self.root if gid is None else gid
        yield gid
        for c in self.children(gid):
            yield from self.walk(c)

    def has(self, gid, comp):
        return comp in self.gos[gid]["c"]

    def ancestor_with(self, gid, comp):
        p = self.parent(gid)
        while p is not None:
            if comp in self.gos[p]["c"]:
                return p
            p = self.parent(p)
        return None


class _Reader:
    def __init__(self, raw):
        self.b, self.o = raw, 0

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.o)[0]
        self.o += 4
        return v

    def pptr(self):
        v = struct.unpack_from("<iq", self.b, self.o)[1]
        self.o += 12
        return v

    def string(self):
        n = self.i32()
        v = self.b[self.o:self.o + n].decode("utf-8", "replace")
        self.o = (self.o + n + 3) & ~3
        return v

    def header(self):          # m_GameObject, m_Enabled, m_Script, m_Name
        self.pptr()
        self.i32()
        self.pptr()
        return self.string()


def _stage_fields(L):
    """Fields of the Stage component: wolf, gas and passage locators, and starting squares."""
    r = _Reader(base64.b64decode(L.gos[L.root]["c"]["MB:Stage"][0]["raw"]))
    r.header()
    r.string()                  # stageNamelangId
    r.o += 16 + 4               # saturationColor, saturationValue
    get = L.by_comp.get
    threat = [(get(r.pptr()), get(r.pptr()), r.pptr())[:2] for _ in range(r.i32())]
    gas = [(get(r.pptr()), r.pptr())[0] for _ in range(r.i32())]
    byway = []
    for _ in range(r.i32()):
        loc = get(r.pptr())
        shelves = [get(r.pptr()) for _ in range(r.i32())]
        r.pptr()
        byway.append((loc, shelves))
    spawns = [r.i32() for _ in range(r.i32())]
    return threat, gas, byway, spawns


def _room_entrance(L, gid):
    r = _Reader(base64.b64decode(L.gos[gid]["c"]["MB:Room"][0]["raw"]))
    r.header()
    r.pptr()
    return bool(r.b[r.o])


def id_to_cell(gid):
    """Game square id -> (i, j). id = 10*i + j with i >= 0, 10*i - j with i < 0."""
    a = abs(gid)
    return (-(a // 10), a % 10) if gid < 0 else (a // 10, a % 10)


def cell_to_id(i, j):
    return 10 * i + (-j if i < 0 else j)


def edge_of(x, z):
    """Midpoint of the edge between squares closest to (x, z): (ex, ez) in world units."""
    best = None
    ci, cj = round(x / GRID), round(z / GRID)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            cx, cz = GRID * (ci + di), GRID * (cj + dj)
            for ex, ez in ((cx + 3, cz), (cx - 3, cz), (cx, cz + 3), (cx, cz - 3)):
                d = (ex - x) ** 2 + (ez - z) ** 2
                if best is None or d < best[0] - 1e-9:
                    best = (d, (int(ex), int(ez)))
    return best[1]


def edge_cells(ex, ez):
    """The two squares an edge separates and its normal (from the first to the second)."""
    if ex % 6:                  # vertical edge: separates squares in x
        return ((ex - 3) // 6, ez // 6), ((ex + 3) // 6, ez // 6), (1, 0)
    return (ex // 6, (ez - 3) // 6), (ex // 6, (ez + 3) // 6), (0, 1)


def _inside(px, pz, a, b, c):
    def s(p, q, r):
        return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
    d1, d2, d3 = s((px, pz), a, b), s((px, pz), b, c), s((px, pz), c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def _flat_tris(mesh):
    """Triangles of a mesh seen from above (without the vertical ones)."""
    v, t = mesh["v"], mesh["t"]
    pts = [(v[i], v[i + 2]) for i in range(0, len(v), 3)]
    out = []
    for i in range(0, len(t) - 2, 3):
        a, b, c = pts[t[i]], pts[t[i + 1]], pts[t[i + 2]]
        if abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) > 2e-4:
            out.append((a, b, c))
    return out


def _outline(tris):
    """Border edges of a flat mesh (the ones touching only one triangle): they are the walls."""
    cnt = {}
    for tri in tris:
        for k in range(3):
            a = (round(tri[k][0], 2), round(tri[k][1], 2))
            b = (round(tri[(k + 1) % 3][0], 2), round(tri[(k + 1) % 3][1], 2))
            if a != b:
                key = (a, b) if a < b else (b, a)
                cnt[key] = cnt.get(key, 0) + 1
    return [[a[0], a[1], b[0], b[1]] for (a, b), n in cnt.items() if n == 1]


def _local_cells(w, d):
    """Squares of a w x d room with the pivot at its centre: local centres (x, z)."""
    return [(GRID * (i - (w - 1) / 2), GRID * (j - (d - 1) / 2)) for i in range(w) for j in range(d)]


# ---------------------------------------------------------------- catalogue
def _room_type(L, gid, nav):
    """Data of a room type, in local coordinates."""
    box = L.gos[gid]["c"]["BoxCollider"][0]
    w, d = round(box["size"][0] / GRID), round(box["size"][2] / GRID)
    floor, block = [], []
    for c in L.children(gid):
        g = L.gos[c]
        mf = g["c"].get("MeshFilter")
        if not g["name"].startswith("NAV_") or not mf or mf[0].get("mesh") not in nav:
            continue
        lp, lq, ls = g["t"]["p"], g["t"]["r"], g["t"]["s"]
        tris = []
        for tri in _flat_tris(nav[mf[0]["mesh"]]):
            pts = []
            for x, z in tri:
                p = qrot(lq, [x * ls[0], 0, z * ls[2]])
                pts.append((round(p[0] + lp[0], 3), round(p[2] + lp[2], 3)))
            tris.append(tuple(pts))
        (floor if g["name"].startswith("NAV_FLOOR") else block).extend(tris)
    cells = _local_cells(w, d)
    child = set()                                   # squares of the interior rooms
    for c in L.children(gid):
        if L.has(c, "MB:Room") and L.gos[c]["c"].get("BoxCollider"):
            cb = L.gos[c]["c"]["BoxCollider"][0]
            cp, cq = L.gos[c]["t"]["p"], L.gos[c]["t"]["r"]
            sx, sz = cb["size"][0], cb["size"][2]
            if round(q_yaw(cq)) % 180 == 90:
                sx, sz = sz, sx
            for cx, cz in cells:
                if abs(cx - cp[0]) < sx / 2 and abs(cz - cp[2]) < sz / 2:
                    child.add((cx, cz))
    covered = lambda x, z: any(_inside(x, z, *t) for t in floor)  # noqa: E731
    cellset = set(cells)
    edges, inner = [], []
    for cx, cz in cells:
        for nx, nz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            mx, mz = cx + 3 * nx, cz + 3 * nz
            other = (cx + 6 * nx, cz + 6 * nz)
            if other not in cellset:                # perimeter edge
                edges.append({"x": mx, "z": mz, "nx": nx, "nz": nz, "open": covered(mx - 0.15 * nx, mz - 0.15 * nz)})
            elif (nx > 0 or nz > 0) and ((cx, cz) in child) != (other in child):
                if covered(mx - 0.15 * nx, mz - 0.15 * nz) and covered(mx + 0.15 * nx, mz + 0.15 * nz):
                    inner.append({"x": mx, "z": mz, "nx": nx, "nz": nz})
    flat = lambda tris: [[c for p in t for c in p] for t in tris]  # noqa: E731
    return {"w": w, "d": d, "cells": [list(c) for c in cells], "child": [list(c) for c in sorted(child)],
            "edges": edges, "inner": inner, "floor": flat(floor), "block": flat(block), "outline": _outline(floor)}


def _piece_kind(L, gid):
    g = L.gos[gid]
    if g["name"].startswith("Out_door"):
        return None
    parent = L.parent(gid)
    if parent is not None and L.gos[parent]["name"].startswith("Out_door"):
        return None                                 # part of the main door
    if "MB:Door" in g["c"]:
        return "door"
    if "MB:WindowShelf" in g["c"]:
        return "window"
    if "MB:Shelf" in g["c"]:
        return "shelf"
    return None


def _build_stage(scene, lv, nav, types):
    L = Level(lv)
    rooms, cell_room = [], {}
    for gid in L.walk():
        if not L.has(gid, "MB:Room") or L.ancestor_with(gid, "MB:Room") is not None:
            continue
        g = L.gos[gid]
        if not g["c"].get("BoxCollider"):
            continue
        floor = [c for c in L.children(gid) if L.gos[c]["name"].startswith("NAV_FLOOR")]
        mesh = (L.gos[floor[0]]["c"].get("MeshFilter") or [{}])[0].get("mesh") if floor else None
        tname = (mesh or g["name"]).replace("NAV_FLOOR_", "").replace("_Model", "").replace("Yokn_", "")
        if tname not in types:
            types[tname] = _room_type(L, gid, nav)
        x, y, z, yaw = L.pose(gid)
        room = {"name": g["name"], "type": tname, "x": x, "z": z, "yaw": norm_yaw(yaw),
                "entrance": _room_entrance(L, gid), "carried": []}
        w, d = types[tname]["w"], types[tname]["d"]
        if room["yaw"] % 180:
            w, d = d, w
        room["i"], room["j"] = round((x - 3 * (w - 1)) / GRID), round((z - 3 * (d - 1)) / GRID)
        for a in range(w):
            for b in range(d):
                cell_room[(room["i"] + a, room["j"] + b)] = len(rooms)
        rooms.append(room)

    def to_local(room, x, z):
        return rot_xz(x - room["x"], z - room["z"], -room["yaw"])

    pieces = []
    for gid in L.walk():
        g = L.gos[gid]
        kind = _piece_kind(L, gid)
        if g["name"].startswith("Out_door") and any(L.has(c, "MB:OutDoor") for c in L.children(gid)):
            kind = "outdoor"
        if not kind:
            continue
        x, y, z, yaw = L.pose(gid)
        ex, ez = edge_of(x, z)
        a, b, n = edge_cells(ex, ez)
        ra, rb = cell_room.get(a), cell_room.get(b)
        names = " ".join(L.gos[c]["name"] for c in L.walk(gid))
        p = {"name": g["name"], "kind": kind, "model": g["name"].split(" (")[0], "x": x, "y": y, "z": z,
             "yaw": norm_yaw(yaw), "edge": [ex, ez], "breakable": kind == "window" and "roken" in names}
        if ra is not None and ra == rb:
            p["where"] = "inner"                    # a room's interior wall: goes with it
            owner = ra
        elif ra is None or rb is None:
            p["where"] = "ext"
            owner = ra if rb is None else rb
        else:
            p["where"] = "int"
            owner = None
            # side the piece faces: a piece of furniture has its body forward and the pivot 0.1 behind
            fx, fz = rot_xz(0, 1, p["yaw"])
            p["side"] = 1 if fx * n[0] + fz * n[1] > 0 else -1
        if owner is not None:
            room = rooms[owner]
            lx, lz = to_local(room, x, z)
            mx, mz = to_local(room, ex, ez)
            p["room"] = owner
            room["carried"].append({"piece": len(pieces), "kind": kind, "where": p["where"],
                                    "lx": round(lx, 3), "lz": round(lz, 3), "lyaw": norm_yaw(p["yaw"] - room["yaw"]),
                                    "ex": round(mx), "ez": round(mz)})
        pieces.append(p)

    threat, gas, byway, spawns = _stage_fields(L)
    xz = lambda gid: [L.pose(gid)[0], L.pose(gid)[2]]  # noqa: E731
    stage = {"scene": scene, "file": lv.get("file"), "rooms": rooms, "pieces": pieces,
             "wolves": [list(edge_of(*xz(win))) if win is not None else list(edge_of(*xz(loc))) for loc, win in threat
                        if loc is not None],
             "gas": [[round(v, 2) for v in xz(loc)] for loc in gas if loc is not None],
             "byways": [list(edge_of(*xz(loc))) for loc, _ in byway if loc is not None],
             "spawns": [list(id_to_cell(s)) for s in spawns]}
    return stage


def build_catalog(raw):
    types, stages = {}, {}
    for scene in sorted(raw["levels"]):
        stages[scene] = _build_stage(scene, raw["levels"][scene], raw["nav"], types)
    return {"version": CATALOG_VERSION, "types": types, "stages": stages}


# ---------------------------------------------------------------- cache
def _signature(game_dir):
    data_dir = os.path.join(game_dir, DATA)
    sig = [CATALOG_VERSION]
    for n in sorted(os.listdir(data_dir)):
        if n == "resources.assets" or (n.startswith("level") and n[5:].isdigit()):
            orig = os.path.join(data_dir, n + ".original")      # with mods without BepInEx, the original
            st = os.stat(orig if os.path.isfile(orig) else os.path.join(data_dir, n))
            sig.append([n, st.st_size])
    return sig


def _source(game_dir, name):
    """Mods without BepInEx rewrite some files: the original is always read if it exists."""
    p = os.path.join(game_dir, DATA, name)
    return p + ".original" if os.path.isfile(p + ".original") else p


def load(game_dir, cache_dir, progress=None):
    """Stage catalogue (from the cache if the game hasn't changed). Also leaves navsrc.json."""
    os.makedirs(cache_dir, exist_ok=True)
    cpath, npath = os.path.join(cache_dir, "catalog.json"), os.path.join(cache_dir, "navsrc.json")
    sig = _signature(game_dir)
    try:
        with open(cpath, encoding="utf-8") as f:
            cat = json.load(f)
        if cat.get("signature") == sig and os.path.isfile(npath):
            return cat
    except (OSError, ValueError):
        pass
    raw = read_game(game_dir, progress)
    cat = build_catalog(raw)
    cat["signature"] = sig
    with open(npath, "w", encoding="utf-8") as f:
        json.dump({"meshes": raw["nav"]}, f, separators=(",", ":"))
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(cat, f, separators=(",", ":"))
    if progress:
        progress(100)
    return cat


def nav_path(cache_dir):
    return os.path.join(cache_dir, "navsrc.json")
