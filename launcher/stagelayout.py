"""
CRIMESIGHT Revival - creador de escenarios: de la distribucion del editor a lo que aplica el plugin.

Una distribucion (lo que guarda el editor) dice que habitaciones del escenario base se usan, en que
casilla y con que giro, y unas pocas decisiones del jugador: que conexiones entre habitaciones se
cierran con muebles en vez de con puerta, donde hay pasadizos, por que ventanas entran los lobos,
donde sale el gas y en que casillas empiezan los personajes.

Todo lo demas se deduce aqui, igual que lo monta el juego en sus escenarios:
  - cada hueco de pared que da al exterior lleva una ventana;
  - cada hueco entre dos habitaciones lleva una puerta, o dos muebles que lo tapan;
  - un hueco que da a una pared sin hueco lleva un mueble;
  - las puertas y muebles de las paredes interiores de una habitacion van con ella.

  default_layout(cat, scene)  -> la distribucion original del escenario
  derive(cat, layout)         -> piezas, aristas para dibujar y problemas (validacion)
  compile_layout(cat, layout) -> lo que lee el plugin (layout_test.json)
"""
import math

from stagedata import GRID, MIN_X, MAX_X, MIN_Z, MAX_Z, cell_to_id, edge_cells, rot_xz, _inside

FORMAT = 1
PLUGIN_FORMAT = 2
WANT_WOLVES = WANT_GAS = WANT_BYWAYS = 3            # lo que traen los escenarios del juego
MAX_ROOMS = 30


def ekey(x, z):
    return f"{int(round(x))},{int(round(z))}"


def _parse_key(k):
    x, z = str(k).split(",")
    return int(x), int(z)


def yaw_of(nx, nz):
    return round(math.degrees(math.atan2(nx, nz))) % 360


def _footprint(t, rot):
    return (t["w"], t["d"]) if rot % 2 == 0 else (t["d"], t["w"])


def place(cat, stage, r):
    """Habitacion colocada: posicion del pivote, giro y casillas que ocupa."""
    src = stage["rooms"][r["src"]]
    t = cat["types"][src["type"]]
    rot = int(r.get("rot", 0)) % 4
    w, d = _footprint(t, rot)
    i, j = int(r["i"]), int(r["j"])
    return {"src": r["src"], "type": src["type"], "name": src["name"], "rot": rot, "yaw": rot * 90, "i": i, "j": j,
            "w": w, "d": d, "x": GRID * i - 3 + 3 * w, "z": GRID * j - 3 + 3 * d, "entrance": src["entrance"],
            "cells": [(i + a, j + b) for a in range(w) for b in range(d)]}


def _world(p, lx, lz):
    x, z = rot_xz(lx, lz, p["yaw"])
    return p["x"] + x, p["z"] + z


def _local(p, x, z):
    return rot_xz(x - p["x"], z - p["z"], -p["yaw"])


def _free_floor(t, lx, lz):
    """El punto local esta sobre suelo y no dentro de un mueble."""
    tri = lambda f: ((f[0], f[1]), (f[2], f[3]), (f[4], f[5]))  # noqa: E731
    return any(_inside(lx, lz, *tri(f)) for f in t["floor"]) and not any(_inside(lx, lz, *tri(f)) for f in t["block"])


def default_layout(cat, scene):
    stage = cat["stages"][scene]
    lay = {"format": FORMAT, "name": "", "base": scene,
           "rooms": [{"src": k, "i": r["i"], "j": r["j"], "rot": (r["yaw"] // 90) % 4} for k, r in enumerate(stage["rooms"])],
           "blocked": [], "byways": [ekey(*e) for e in stage["byways"]], "wolves": [ekey(*e) for e in stage["wolves"]],
           "gas": [list(g) for g in stage["gas"]], "spawns": [list(s) for s in stage["spawns"]]}
    doors = {ekey(*p["edge"]) for p in stage["pieces"] if p["kind"] == "door" and p["where"] == "int"}
    shelves = {ekey(*p["edge"]) for p in stage["pieces"] if p["kind"] == "shelf" and p["where"] == "int"}
    lay["blocked"] = sorted(shelves - doors)
    return lay


def _clean(layout, stage):
    lay = {"format": FORMAT, "name": str(layout.get("name") or "")[:60], "base": layout.get("base"), "rooms": []}
    for r in layout.get("rooms") or []:
        try:
            src, i, j, rot = int(r["src"]), int(r["i"]), int(r["j"]), int(r.get("rot", 0)) % 4
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= src < len(stage["rooms"]) and len(lay["rooms"]) < MAX_ROOMS:
            lay["rooms"].append({"src": src, "i": i, "j": j, "rot": rot})
    for name in ("blocked", "byways", "wolves"):
        out = []
        for k in layout.get(name) or []:
            try:
                out.append(ekey(*_parse_key(k)))
            except (TypeError, ValueError):
                pass
        lay[name] = sorted(set(out))
    lay["gas"] = [[round(float(g[0]), 2), round(float(g[1]), 2)] for g in layout.get("gas") or []
                  if isinstance(g, (list, tuple)) and len(g) == 2][:12]
    lay["spawns"] = [[int(s[0]), int(s[1])] for s in layout.get("spawns") or []
                     if isinstance(s, (list, tuple)) and len(s) == 2][:12]
    return lay


def derive(cat, layout):
    """Calcula todo lo que sale de una distribucion. Devuelve un dict con:
    layout (limpia), rooms, edges (para dibujar), pieces/hide/locators (para el plugin) y problems."""
    stage = cat["stages"].get(layout.get("base"))
    if stage is None:
        raise ValueError("Escenario base desconocido.")
    lay = _clean(layout, stage)
    types = cat["types"]
    problems = []
    err = lambda code, **kw: problems.append({"level": "error", "code": code, **kw})  # noqa: E731
    warn = lambda code, **kw: problems.append({"level": "warn", "code": code, **kw})  # noqa: E731

    # ---- habitaciones y casillas
    rooms = [place(cat, stage, r) for r in lay["rooms"]]
    if not rooms:
        err("no_rooms")
    cell_room, bad = {}, set()
    for k, p in enumerate(rooms):
        for c in p["cells"]:
            if not (MIN_X <= c[0] <= MAX_X and MIN_Z <= c[1] <= MAX_Z):
                bad.add(("out", k))
            elif c in cell_room:
                bad.add(("overlap", min(k, cell_room[c]), max(k, cell_room[c])))
            else:
                cell_room[c] = k
    for b in sorted(bad):
        if b[0] == "out":
            err("out_of_bounds", room=b[1])
        else:
            err("overlap", room=b[1], other=b[2])

    # ---- aristas del perimetro de cada habitacion, en el mundo
    sides = {}                                      # clave -> [(habitacion, hueco abierto, normal hacia fuera, arista local)]
    for k, p in enumerate(rooms):
        for e in types[p["type"]]["edges"]:
            x, z = _world(p, e["x"], e["z"])
            nx, nz = rot_xz(e["nx"], e["nz"], p["yaw"])
            sides.setdefault(ekey(x, z), []).append((k, e["open"], (round(nx), round(nz)), e))

    # ---- piezas del escenario base: reservadas (van con su habitacion) y libres
    base = stage["pieces"]
    pools = {"door": [], "shelf": [], "window": [], "outdoor": []}
    at_edge = {}
    for n, pc in enumerate(base):
        if pc["where"] == "inner" or pc["kind"] == "outdoor":
            continue
        pools[pc["kind"]].append(n)
        at_edge.setdefault((pc["kind"], ekey(*pc["edge"])), []).append(n)
    closed_window = set()                           # (tipo, arista local): pared sin hueco que lleva ventana
    for st in cat["stages"].values():
        for r in st["rooms"]:
            closed = {(e["x"], e["z"]) for e in types[r["type"]]["edges"] if not e["open"]}
            for c in r["carried"]:
                if c["kind"] == "window" and c["where"] == "ext" and (c["ex"], c["ez"]) in closed:
                    closed_window.add((r["type"], c["ex"], c["ez"]))

    used, pieces, edges = set(), [], []
    by_edge = {}                                    # clave -> indices en pieces

    def add(src, x, z, yaw, key):
        pieces.append({"src": src, "x": round(x, 3), "z": round(z, 3), "yaw": round(yaw) % 360, "edge": key})
        by_edge.setdefault(key, []).append(len(pieces) - 1)
        return len(pieces) - 1

    def keep(n, key):                               # pieza del juego que se queda donde estaba
        used.add(n)
        return add(n, base[n]["x"], base[n]["z"], base[n]["yaw"], key)

    def take(kind, want=None):
        """Una pieza libre de ese tipo (o, si no quedan, una repetida: el plugin la duplica)."""
        pool = pools[kind]
        ok = [n for n in pool if want is None or want(base[n])]
        for n in ok:
            if n not in used:
                used.add(n)
                return n
        if ok:
            take.turn[kind] = take.turn.get(kind, 0) + 1
            return ok[take.turn[kind] % len(ok)]
        return None
    take.turn = {}

    # ---- piezas que van con cada habitacion: paredes interiores y puerta principal
    outdoor_edges = set()
    for k, p in enumerate(rooms):
        for c in stage["rooms"][p["src"]]["carried"]:
            if c["where"] != "inner" and c["kind"] != "outdoor":
                continue
            x, z = _world(p, c["lx"], c["lz"])
            ex, ez = _world(p, c["ex"], c["ez"])
            key = ekey(ex, ez)
            if c["kind"] == "outdoor":
                if len(sides.get(key, [])) != 1:
                    err("entrance_blocked", room=k)
                    continue
                outdoor_edges.add(key)
                edges.append({"key": key, "x": round(ex), "z": round(ez), "kind": "entrance"})
            used.add(c["piece"])
            add(c["piece"], x, z, c["lyaw"] + p["yaw"], key)
        for e in types[p["type"]]["inner"]:
            ex, ez = _world(p, e["x"], e["z"])
            key = ekey(ex, ez)
            has_door = any(c["kind"] == "door" and c["where"] == "inner" and (c["ex"], c["ez"]) == (round(e["x"]), round(e["z"]))
                           for c in stage["rooms"][p["src"]]["carried"])
            edges.append({"key": key, "x": round(ex), "z": round(ez), "kind": "inner_door" if has_door else "inner_blocked"})

    # ---- huecos del perimetro
    blocked, byways, wolves = set(lay["blocked"]), set(lay["byways"]), set(lay["wolves"])
    blocked |= byways
    pending = []                                    # huecos que necesitan una pieza libre
    links = []                                      # (habitacion, habitacion) unidas por una puerta
    locators = {"byways": [], "wolves": []}
    valid = {"blocked": set(), "byways": set(), "wolves": set()}
    for key in sorted(sides, key=_parse_key):
        ex, ez = _parse_key(key)
        ss = sides[key]
        if len(ss) == 1:                            # exterior
            if key in outdoor_edges:
                continue
            k, is_open, out, e = ss[0]
            if not is_open and (rooms[k]["type"], e["x"], e["z"]) not in closed_window:
                continue
            wolf = key in wolves and is_open
            same = [n for n in at_edge.get(("window", key), []) if n not in used and (base[n]["breakable"] or not wolf)]
            if same:
                keep(same[0], key)
            else:
                pending.append(("window", "breakable" if wolf else "plain", ex, ez, yaw_of(-out[0], -out[1]), key))
            if wolf:
                valid["wolves"].add(key)
                locators["wolves"].append({"x": ex - out[0], "z": ez - out[1], "yaw": yaw_of(*out), "window": key})
            edges.append({"key": key, "x": ex, "z": ez, "kind": "wolf" if wolf else ("window" if is_open else "wall_window"),
                          "toggle": bool(is_open)})
            continue
        if len(ss) != 2:
            continue
        _a, _b, n = edge_cells(ex, ez)
        (ka, open_a, out_a, _), (kb, open_b, out_b, _) = ss
        if (out_a[0], out_a[1]) != n:               # ka queda en el lado negativo de la normal
            (ka, open_a), (kb, open_b) = (kb, open_b), (ka, open_a)
        if open_a and open_b:
            if key in blocked:
                valid["blocked"].add(key)
                same = [m for m in at_edge.get(("shelf", key), []) if m not in used]
                got = {-1: False, 1: False}
                for m in same:
                    keep(m, key)
                    got[base[m].get("side", 1)] = True
                for s in (-1, 1):
                    if not got[s]:
                        pending.append(("shelf", None, ex - s * 0.1 * n[0], ez - s * 0.1 * n[1], yaw_of(s * n[0], s * n[1]), key))
                if key in byways:
                    valid["byways"].add(key)
                    locators["byways"].append({"x": ex, "z": ez, "yaw": 90 if n[0] else 0, "shelves": key})
                edges.append({"key": key, "x": ex, "z": ez, "kind": "byway" if key in byways else "blocked", "toggle": True})
            else:
                same = [m for m in at_edge.get(("door", key), []) if m not in used]
                if same:
                    keep(same[0], key)
                else:
                    yaw = yaw_of(*n)
                    dx, dz = rot_xz(0.5, 0, yaw)
                    pending.append(("door", None, ex + dx, ez + dz, yaw, key))
                links.append((ka, kb))
                edges.append({"key": key, "x": ex, "z": ez, "kind": "door", "toggle": True})
        elif open_a or open_b:                      # hueco contra pared: un mueble que da al lado del hueco
            s = -1 if open_a else 1
            same = [m for m in at_edge.get(("shelf", key), []) if m not in used and base[m].get("side", 1) == s]
            if same:
                keep(same[0], key)
            else:
                pending.append(("shelf", None, ex - s * 0.1 * n[0], ez - s * 0.1 * n[1], yaw_of(s * n[0], s * n[1]), key))
            edges.append({"key": key, "x": ex, "z": ez, "kind": "single"})

    # ---- huecos sin pieza propia: se usan las piezas libres del escenario (y, si faltan, repetidas)
    for kind, want, x, z, yaw, key in pending:
        src = None
        if want:
            src = take(kind, (lambda b: b["breakable"]) if want == "breakable" else (lambda b: not b["breakable"]))
        if src is None:
            src = take(kind)
        if src is not None:
            add(src, x, z, yaw, key)
    for w in locators["wolves"]:
        w["window"] = (by_edge.get(w["window"]) or [-1])[0]
    for b in locators["byways"]:
        b["shelves"] = list(by_edge.get(b["shelves"], []))

    # ---- decisiones del jugador que ya no encajan con las habitaciones
    lay["blocked"] = sorted(valid["blocked"] - valid["byways"])
    lay["byways"] = sorted(valid["byways"])
    lay["wolves"] = sorted(valid["wolves"])

    # ---- conexion entre habitaciones
    if rooms and not bad:
        seen, todo = {0}, [0]
        while todo:
            a = todo.pop()
            for x, y in links:
                for u, v in ((x, y), (y, x)):
                    if u == a and v not in seen:
                        seen.add(v)
                        todo.append(v)
        for k in range(len(rooms)):
            if k not in seen:
                err("unreachable", room=k)

    # ---- salidas, gas y recomendaciones
    def spot(x, z):
        k = cell_room.get((round(x / GRID), round(z / GRID)))
        if k is None:
            return None
        lx, lz = _local(rooms[k], x, z)
        return _free_floor(types[rooms[k]["type"]], lx, lz)

    spawns = []
    for i, j in lay["spawns"]:
        ok = spot(GRID * i, GRID * j)
        if ok is None:
            err("spawn_outside", cell=[i, j])
        elif not ok:
            err("spawn_blocked", cell=[i, j])
        else:
            spawns.append(cell_to_id(i, j))
    if not lay["spawns"]:
        err("no_spawns")
    gas = []
    for x, z in lay["gas"]:
        if spot(x, z) is None:
            err("gas_outside", pos=[x, z])
        else:
            gas.append({"x": x, "z": z})
    if len(locators["wolves"]) < WANT_WOLVES:
        warn("few_wolves", n=len(locators["wolves"]), want=WANT_WOLVES)
    if len(gas) < WANT_GAS:
        warn("few_gas", n=len(gas), want=WANT_GAS)
    if len(locators["byways"]) < WANT_BYWAYS:
        warn("few_byways", n=len(locators["byways"]), want=WANT_BYWAYS)
    if any(r["entrance"] for r in stage["rooms"]) and not any(p["entrance"] for p in rooms):
        warn("no_entrance")

    hide = [n for n, pc in enumerate(base) if n not in used]
    clones = len(pieces) - len({p["src"] for p in pieces})
    return {"layout": lay, "rooms": rooms, "edges": edges, "pieces": pieces, "hide": hide, "locators": locators,
            "gas": gas, "spawns": spawns, "problems": problems, "ok": not any(p["level"] == "error" for p in problems),
            "stats": {"rooms": len(rooms), "cells": len(cell_room), "pieces": len(pieces), "clones": clones,
                      "doors": len(links), "wolves": len(locators["wolves"]), "gas": len(gas),
                      "byways": len(locators["byways"]), "spawns": len(spawns)}}


def compile_layout(cat, layout):
    """Lo que aplica el plugin: de donde sale cada pieza del escenario base y donde va."""
    d = derive(cat, layout)
    if not d["ok"]:
        raise ValueError("La distribucion tiene errores.")
    stage = cat["stages"][d["layout"]["base"]]
    src_room = lambda r: {"name": r["name"], "sx": r["x"], "sz": r["z"], "syaw": r["yaw"]}  # noqa: E731
    src_piece = lambda p: {"name": p["name"], "sx": p["x"], "sz": p["z"], "syaw": p["yaw"]}  # noqa: E731
    rooms = [dict(src_room(stage["rooms"][p["src"]]), x=p["x"], z=p["z"], yaw=p["yaw"], w=GRID * p["w"], d=GRID * p["d"])
             for p in d["rooms"]]
    used_rooms = {p["src"] for p in d["rooms"]}
    cells = [c for p in d["rooms"] for c in p["cells"]]
    return {"format": PLUGIN_FORMAT, "name": d["layout"]["name"], "base": d["layout"]["base"], "navmesh": "rebuild",
            "rooms": rooms,
            "hide_rooms": [src_room(r) for k, r in enumerate(stage["rooms"]) if k not in used_rooms],
            "pieces": [dict(src_piece(stage["pieces"][p["src"]]), x=p["x"], z=p["z"], yaw=p["yaw"]) for p in d["pieces"]],
            "hide": [src_piece(stage["pieces"][n]) for n in d["hide"]],
            "byways": d["locators"]["byways"], "wolves": d["locators"]["wolves"], "gas": d["gas"], "spawns": d["spawns"],
            "bounds": [GRID * min(c[0] for c in cells) - 3, GRID * min(c[1] for c in cells) - 3,
                       GRID * max(c[0] for c in cells) + 3, GRID * max(c[1] for c in cells) + 3]}
