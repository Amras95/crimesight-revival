"""
CRIMESIGHT Revival - los modelos 3D y animaciones de una sala: los del anfitrion + los que acepte de cada jugador.

Funciona como los stickers (modroom.py), con una diferencia: los modelos pesan mucho, asi que el invitado no los
sube al ofrecerlos. Primero manda la lista (POST /revival/models/offer); al anfitrion le sale el aviso y, si
acepta, el invitado sube solo los archivos que faltan (PUT /revival/models/upload/<oferta>/<sha>). Cuando estan
todos, pasan a la sala y los descarga cada uno (solo los que no tiene). Los del anfitrion mandan: los del
invitado solo rellenan los personajes que el anfitrion no ha cambiado. Todo es temporal: al cerrar el servidor
se borra.
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
        self.base = modelpack.empty()          # los del anfitrion (con la ruta de cada archivo)
        self.pending = {}                      # id -> {"player", "ms"}
        self.accepted = {}                     # id -> {"player", "ms", "have": {sha: ruta}} (por orden)
        self.disabled = set()                  # personajes que el anfitrion no quiere que salgan ("orig:<sitio>" o id)
        self.rng = random.Random()
        if offers_dir:
            shutil.rmtree(offers_dir, ignore_errors=True)
        self.ms = self._build()

    def _build(self):
        parts = [self.base]
        for off in self.accepted.values():
            if all(s in off["have"] for s in off["ms"]["files"]):          # solo cuando han llegado todos
                ms = dict(off["ms"])
                ms["files"] = {s: dict(f, path=off["have"][s]) for s, f in ms["files"].items()}
                parts.append(ms)
        ms = modelpack.merge(parts)
        if ms["hash"]:
            s = modelpack.summary(ms)
            log.info("Modelos de la sala: %d modelo(s) y %d animacion(es), %.1f MB", s["models"], s["anims"], s["bytes"] / 1e6)
        return ms

    def set_base(self, ms):
        """Los modelos del anfitrion (o sus cambios en caliente). ms lleva la ruta local de cada archivo."""
        with self.lock:
            self.base = ms or modelpack.empty()
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
        """El juego de modelos de la sala con las rutas de este PC (para el juego del anfitrion)."""
        with self.lock:
            return {"hash": self.ms["hash"], "swaps": dict(self.ms["swaps"]),
                    "anims": {k: dict(v) for k, v in self.ms["anims"].items()},
                    "chars": {k: modelpack._char_copy(c) for k, c in self.ms.get("chars", {}).items()},
                    "files": {s: {"kind": f["kind"], "path": f["path"], "name": f.get("name", "")} for s, f in self.ms["files"].items()}}

    # ------------------------------------------------------------ modelos de los jugadores
    def offer(self, meta, player):
        """Un jugador ofrece sus modelos. Devuelve (estado, id, archivos que tiene que subir)."""
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
            # nada que aportar: lo que trae ya esta en la sala o los personajes ya estan cambiados
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
        """Archivos de la oferta que ya hay en la sala (no hace falta subirlos)."""
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
        """Tamano y tipo del archivo que puede subir esa oferta (None si no le toca)."""
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
        """Ya ha llegado (y comprobado) un archivo de una oferta aceptada."""
        with self.lock:
            off = self.accepted.get(oid)
            if not off:
                return self.ms
            off["have"][sha] = path
            for other in self.accepted.values():         # otra oferta con el mismo archivo tampoco lo sube
                if sha in other["ms"]["files"]:
                    other["have"].setdefault(sha, path)
            self.ms = self._build()
            return self.ms

    # ------------------------------------------------------------ que personajes pueden salir
    def set_disabled(self, ids):
        with self.lock:
            self.disabled = {str(i) for i in (ids or [])}
            return sorted(self.disabled)

    def pool(self):
        """Todos los personajes que pueden salir (para el Selector de personajes) y si estan activados."""
        with self.lock:
            out = [{"id": "orig:" + k, "key": k, "role": "pawn", "enabled": "orig:" + k not in self.disabled}
                   for k in modelpack.PAWNS]
            for cid, c in sorted(self.ms.get("chars", {}).items()):
                if c.get("role", "pawn") != "pawn":
                    continue
                out.append({"id": cid, "role": "pawn", "name": c.get("name", ""), "enabled": cid not in self.disabled})
            return modelpack.fill_enabled(out)

    def draw(self, disabled=None):
        """Reparto de una partida nueva (lo pide la sala al empezar la cuenta atras).
        disabled: the room's own Character Selection (None: the server's)."""
        with self.lock:
            return modelpack.draw(self.ms, self.disabled if disabled is None else disabled, self.rng)

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
