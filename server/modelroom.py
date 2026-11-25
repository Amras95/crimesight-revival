"""
CRIMESIGHT Revival - a room's 3D models and animations: the host's + the ones they accept from each player.

It works like the stickers (modroom.py), with one difference: models are heavy, so the guest doesn't
upload them when offering them. First it sends the list (POST /revival/models/offer); the host gets the notice and, if they
accept, the guest uploads only the missing files (PUT /revival/models/upload/<offer>/<sha>). When they are
all there, they move into the room and each one downloads them (only the ones they don't have). The host's rule: the
guest's only fill the characters the host hasn't changed. Everything is temporary: when the server closes
it is deleted.
"""
import hashlib, json, logging, os, random, shutil, threading

import modelpack

log = logging.getLogger("crimesight")
MAX_OFFERS = 16


class ModelRoom:
    def __init__(self, offers_dir=None, auto_accept=False):
        self.lock = threading.Lock()
        self.offers_dir = offers_dir
        self.auto_accept = auto_accept
        self.base = modelpack.empty()          # the host's (with each file's path)
        self.pending = {}                      # id -> {"player", "ms"}
        self.accepted = {}                     # id -> {"player", "ms", "have": {sha: path}} (in order)
        self.disabled = set()                  # characters the host doesn't want to appear ("orig:<seat>" or id)
        self.known = set()                     # new characters the host has already been shown
        self.rng = random.Random()
        if offers_dir:
            shutil.rmtree(offers_dir, ignore_errors=True)
        self.ms = self._build()

    def _build(self):
        ms = self._merge()
        # New characters that come with another player's models start unticked in the Character Selection: the
        # host turns them on if they want them (before, every model mod joined the draw as soon as it arrived)
        for cid, c in ms.get("chars", {}).items():
            if cid not in self.known:
                self.known.add(cid)
                if cid not in self.base.get("chars", {}):
                    self.disabled.add(cid)
        return ms

    def _merge(self):
        parts = [self.base]
        for off in self.accepted.values():
            if all(s in off["have"] for s in off["ms"]["files"]):          # only when all have arrived
                ms = dict(off["ms"])
                ms["files"] = {s: dict(f, path=off["have"][s]) for s, f in ms["files"].items()}
                parts.append(ms)
        ms = modelpack.merge(parts)
        if ms["hash"]:
            s = modelpack.summary(ms)
            log.info("Modelos de la sala: %d modelo(s) y %d animacion(es), %.1f MB", s["models"], s["anims"], s["bytes"] / 1e6)
        return ms

    def set_base(self, ms):
        """The host's models (or their live changes). ms carries each file's local path."""
        with self.lock:
            self.base = ms or modelpack.empty()
            self.known |= set(self.base.get("chars", {}))     # the host's own: their saved Selector decides
            self.ms = self._build()
            return self.ms

    def path_of(self, sha):
        with self.lock:
            f = self.ms["files"].get(sha)
            return f.get("path") if f else None

    def manifest(self):
        with self.lock:
            return modelpack.manifest(self.ms)

    def local(self):
        """The room's model set with this PC's paths (for the host's game)."""
        with self.lock:
            return {"hash": self.ms["hash"], "swaps": dict(self.ms["swaps"]),
                    "anims": {k: dict(v) for k, v in self.ms["anims"].items()},
                    "chars": {k: modelpack._char_copy(c) for k, c in self.ms.get("chars", {}).items()},
                    "files": {s: {"kind": f["kind"], "path": f["path"], "name": f.get("name", "")} for s, f in self.ms["files"].items()}}

    # ------------------------------------------------------------ the players' models
    def offer(self, meta, player):
        """A player offers their models. Returns (state, id, files they have to upload)."""
        if not self.offers_dir:
            return "ignored", "", []
        ms = modelpack.clean(meta)
        if not ms["hash"]:
            return "known", "", []
        oid = hashlib.sha1(json.dumps(modelpack.manifest(ms), sort_keys=True).encode()).hexdigest()[:12]
        with self.lock:
            if oid in self.accepted:
                return "accepted", oid, self._need(oid)
            if oid in self.pending:
                return "pending", oid, []
            # nothing to contribute: what they bring is already in the room or the characters are already changed
            if not self._adds(ms):
                return "known", oid, []
            if len(self.pending) + len(self.accepted) >= MAX_OFFERS:
                return "ignored", "", []
            entry = {"player": str(player or "?")[:40], "ms": ms}
            if self.auto_accept:
                self.accepted[oid] = dict(entry, have=self._known_files(ms))
                self.ms = self._build()
                return "accepted", oid, self._need(oid)
            self.pending[oid] = entry
            s = modelpack.summary(ms)
            log.info("%s ofrece %d modelo(s) y %d animacion(es)", entry["player"], s["models"], s["anims"])
            return "pending", oid, []

    def _adds(self, ms):
        if any(cid not in self.ms.get("chars", {}) for cid in ms.get("chars", {})):
            return True
        for slot in ms["swaps"]:
            if slot not in self.ms["swaps"]:
                return True
        for slot, kinds in ms["anims"].items():
            for kind in kinds:
                if kind not in self.ms["anims"].get(slot, {}):
                    return True
        return False

    def _known_files(self, ms):
        """Files of the offer already in the room (no need to upload them)."""
        have = {}
        for s in ms["files"]:
            f = self.ms["files"].get(s)
            if f and f.get("path"):
                have[s] = f["path"]
            else:
                for off in self.accepted.values():
                    if s in off["have"]:
                        have[s] = off["have"][s]
        return have

    def _need(self, oid):
        off = self.accepted.get(oid)
        return [s for s in off["ms"]["files"] if s not in off["have"]] if off else []

    def state(self, oid):
        with self.lock:
            if oid in self.accepted:
                return "accepted", self._need(oid)
            if oid in self.pending:
                return "pending", []
            return "rejected", []

    def pending_list(self):
        with self.lock:
            return [{"id": k, "player": v["player"], **modelpack.summary(v["ms"])} for k, v in self.pending.items()]

    def answer(self, oid, accept):
        with self.lock:
            entry = self.pending.pop(oid, None)
            if entry and accept:
                self.accepted[oid] = dict(entry, have=self._known_files(entry["ms"]))
                self.ms = self._build()
            return self.ms

    def expect(self, oid, sha):
        """Size and type of the file that offer can upload (None if it isn't its turn)."""
        with self.lock:
            off = self.accepted.get(oid)
            if not off or sha not in off["ms"]["files"] or sha in off["have"]:
                return None
            f = off["ms"]["files"][sha]
            return f["size"], f["kind"]

    def upload_path(self, sha):
        d = os.path.join(self.offers_dir, "files")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, sha + ".glb")

    def add_file(self, oid, sha, path):
        """A file of an accepted offer has arrived (and been checked)."""
        with self.lock:
            off = self.accepted.get(oid)
            if not off:
                return self.ms
            off["have"][sha] = path
            for other in self.accepted.values():         # another offer with the same file doesn't upload it either
                if sha in other["ms"]["files"]:
                    other["have"].setdefault(sha, path)
            self.ms = self._build()
            return self.ms

    # ------------------------------------------------------------ which characters can appear
    def set_disabled(self, ids):
        with self.lock:
            self.disabled = {str(i) for i in (ids or [])}
            return sorted(self.disabled)

    def pool(self):
        """Every character that can appear (for the Character Selector) and whether they are enabled."""
        with self.lock:
            out = [{"id": "orig:" + k, "key": k, "role": "pawn", "enabled": "orig:" + k not in self.disabled}
                   for k in modelpack.PAWNS]
            for cid, c in sorted(self.ms.get("chars", {}).items()):
                if c.get("role", "pawn") != "pawn":
                    continue
                out.append({"id": cid, "role": "pawn", "name": c.get("name", ""), "enabled": cid not in self.disabled})
            return modelpack.fill_enabled(out)

    def draw(self, disabled=None, must=()):
        """Cast of a new match (the room asks for it when the countdown starts).
        disabled: the room's own Character Selection (None: the server's)."""
        with self.lock:
            return modelpack.draw(self.ms, self.disabled if disabled is None else disabled, self.rng, must)

    def reset_players(self):
        """Drops every player's models (standalone server with nobody left). True if there were any."""
        with self.lock:
            if not self.pending and not self.accepted:
                return False
            self.pending, self.accepted = {}, {}
            if self.offers_dir:
                shutil.rmtree(self.offers_dir, ignore_errors=True)
            self.ms = self._build()
            return True
