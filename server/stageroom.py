"""
CRIMESIGHT Revival - stage creator stages in a room.

The host puts their active stages in the room. On joining, each player's launcher
downloads them (GET /revival/stages), gets them ready for their game and reports which it has
(POST /revival/stages/have). A custom stage is only played if ALL the players in the
room have it exactly the same: if someone is missing it (or doesn't have the plugin), the server picks
a normal stage instead, just like it does with "Random". That way nobody is left with a black screen.

A stage is the layout the creator saves (rooms, closed doors, passages,
wolves, gas and exits): a small JSON. It carries nothing from the game.

While someone is missing the chosen stage, the room doesn't allow starting: the player shows marked
("loading stage..." while their launcher downloads it, "without the stage" if they can't have it).
"""
import hashlib, json, os, threading, time

PREFIX = "Stage_CSR_"               # stage name in the game: Stage_CSR_<id>
MAX_STAGES = 20
MAX_BYTES = 256 * 1024
FIELDS = ("base", "rooms", "blocked", "byways", "wolves", "gas", "spawns")
SYNC_GRACE = 30                     # seconds to wait for a launcher to catch up


def layout_hash(layout):
    """Fingerprint of a layout (without the name): two players have the same stage if it matches."""
    core = {k: layout.get(k) for k in FIELDS}
    return hashlib.sha1(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def load_dir(path):
    """Stages from a folder (the .json files the launcher saves), for a dedicated server."""
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
        self.have = {}          # player -> {id: fingerprint}
        self.seen = {}          # player -> room list (its fingerprint) it synced with
        self.since = {}         # player -> when we started waiting for them
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
        """Fingerprint of the room's stage list ("" if there are none)."""
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
        """"ok": that player has the stage; "sync": their launcher is still catching up;
        "missing": they don't have it and won't (without the plugin, or with an old launcher)."""
        now = now or time.time()
        player = str(player)
        with self.lock:
            mine = self.stages.get(stage)
            if mine is not None and self.have.get(player, {}).get(stage) == mine["hash"]:
                self.since.pop(player, None)
                return "ok"
            if mine is not None and self.seen.get(player) == self._key():
                return "missing"                      # already synced with this list and doesn't have it
            start = max(self.since.setdefault(player, now), self.changed)
            return "sync" if now - start < SYNC_GRACE else "missing"
