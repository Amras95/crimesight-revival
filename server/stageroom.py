"""
CRIMESIGHT Revival - escenarios del creador de escenarios en una sala.

El anfitrion pone en la sala sus escenarios activos. Al unirse, el lanzador de cada jugador se los
baja (GET /revival/stages), los deja listos para su juego y avisa de cuales tiene
(POST /revival/stages/have). Un escenario personalizado solo se juega si TODOS los jugadores de la
sala lo tienen exactamente igual: si a alguien le falta (o no tiene el plugin), el servidor elige
un escenario normal en su lugar, igual que hace con "Aleatorio". Asi nadie se queda en negro.

Un escenario es la distribucion que guarda el creador (habitaciones, puertas cerradas, pasadizos,
lobos, gas y salidas): un JSON pequeno. No lleva nada del juego.

Mientras a alguien le falta el escenario elegido, la sala no deja empezar: el jugador sale marcado
("cargando escenario..." mientras su lanzador se lo baja, "sin el escenario" si no puede tenerlo).
"""
import hashlib, json, os, threading, time

PREFIX = "Stage_CSR_"               # nombre de escenario en el juego: Stage_CSR_<id>
TEST_STAGE = "Stage_Yokn_CSRTest"   # "Escenario de pruebas": solo para una persona
MAX_STAGES = 20
MAX_BYTES = 256 * 1024
FIELDS = ("base", "rooms", "blocked", "byways", "wolves", "gas", "spawns")
SYNC_GRACE = 30                     # segundos que se espera a que un lanzador se ponga al dia


def layout_hash(layout):
    """Huella de una distribucion (sin el nombre): dos jugadores tienen el mismo escenario si coincide."""
    core = {k: layout.get(k) for k in FIELDS}
    return hashlib.sha1(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def load_dir(path):
    """Escenarios de una carpeta (los .json que guarda el lanzador), para un servidor dedicado."""
    out = []
    if not path or not os.path.isdir(path):
        return out
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(path, fn), encoding="utf-8") as f:
                lay = json.load(f)
            if isinstance(lay, dict) and lay.get("rooms"):
                out.append({"id": PREFIX + fn[:-5], "name": lay.get("name") or fn[:-5], "layout": lay})
        except (OSError, ValueError):
            continue
    return out[:MAX_STAGES]


class StageRoom:
    def __init__(self, stages=None):
        self.lock = threading.Lock()
        self.stages = {}        # id -> {"id", "name", "hash", "layout"}
        self.have = {}          # jugador -> {id: huella}
        self.seen = {}          # jugador -> lista de la sala (su huella) con la que se sincronizo
        self.since = {}         # jugador -> cuando se le empezo a esperar
        self.changed = time.time()
        self.set(stages or [])

    def set(self, stages):
        new = {}
        for s in list(stages)[:MAX_STAGES]:
            sid, lay = str(s.get("id") or ""), s.get("layout")
            if sid.startswith(PREFIX) and isinstance(lay, dict):
                new[sid] = {"id": sid, "name": str(s.get("name") or sid)[:60], "hash": layout_hash(lay), "layout": lay}
        with self.lock:
            if {k: v["hash"] for k, v in new.items()} != {k: v["hash"] for k, v in self.stages.items()}:
                self.changed = time.time()
            self.stages = new

    def _key(self):
        if not self.stages:
            return ""
        pairs = sorted((s["id"], s["hash"]) for s in self.stages.values())
        return hashlib.sha1(json.dumps(pairs).encode()).hexdigest()[:16]

    def key(self):
        """Huella de la lista de escenarios de la sala ("" si no hay ninguno)."""
        with self.lock:
            return self._key()

    def summary(self):
        with self.lock:
            lst = [{"id": s["id"], "name": s["name"], "hash": s["hash"]} for s in self.stages.values()]
            key = self._key()
        return {"hash": key, "list": lst} if lst else None

    def pack(self):
        with self.lock:
            return {"stages": list(self.stages.values())}

    def report(self, player, have, seen=None):
        if not isinstance(have, dict):
            have = {}
        clean = {str(k): str(v)[:40] for k, v in list(have.items())[:MAX_STAGES * 2] if str(k).startswith(PREFIX)}
        with self.lock:
            self.have[str(player)] = clean
            self.seen[str(player)] = None if seen is None else str(seen)[:40]

    def state(self, stage, player, now=None):
        """"ok": ese jugador tiene el escenario; "sync": su lanzador aun se esta poniendo al dia;
        "missing": no lo tiene ni lo va a tener (sin el plugin, o con un lanzador antiguo)."""
        now = now or time.time()
        player = str(player)
        with self.lock:
            mine = self.stages.get(stage)
            if mine is not None and self.have.get(player, {}).get(stage) == mine["hash"]:
                self.since.pop(player, None)
                return "ok"
            if mine is not None and self.seen.get(player) == self._key():
                return "missing"                      # ya se sincronizo con esta lista y no lo tiene
            start = max(self.since.setdefault(player, now), self.changed)
            return "sync" if now - start < SYNC_GRACE else "missing"

    def ready(self, stage, players):
        """Todos esos jugadores tienen ese escenario de la sala, y el mismo."""
        return bool(players) and all(self.state(stage, p) == "ok" for p in players)
