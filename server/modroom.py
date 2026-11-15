"""
CRIMESIGHT Revival - los mods de una sala: los del anfitrion + los que acepte de cada jugador.

Al unirse, cada jugador descarga los mods de la sala y, si tiene mods propios, se los ofrece al
anfitrion (POST /revival/mods/offer). Al anfitrion le sale un aviso ("Raven lleva 4 mods, los
descargas?"); si acepta, pasan a formar parte de la sala y les llegan a todos (en caliente con el
plugin de BepInEx). Todo es temporal: al cerrar el servidor se borra.

En un servidor dedicado (sin anfitrion que conteste) los mods de los jugadores se ignoran, salvo
que se arranque con --accept-player-mods.
"""
import hashlib, logging, os, shutil, threading

import modpack

log = logging.getLogger("crimesight")
MAX_OFFERS = 16


class ModRoom:
    def __init__(self, folders=None, mods_dir=None, owner="", offers_dir=None, auto_accept=False, names=None):
        self.lock = threading.Lock()
        self.names = dict(names or {})       # carpeta -> nombre que ensenar (p. ej. "Carpeta principal")
        self.owner = owner or ""
        self.base = list(folders or []) + modpack.list_folders(mods_dir)
        self.offers_dir = offers_dir
        self.auto_accept = auto_accept
        self.pending = {}        # id -> {"player", "folders", "summary"}
        self.accepted = {}       # id -> {"player", "folders"}
        self._pack = None
        if offers_dir:
            shutil.rmtree(offers_dir, ignore_errors=True)
        self.rs = self._build()

    # ------------------------------------------------------------ conjunto de la sala
    def _build(self):
        loaded = []
        for f in self.base:
            m = modpack.load_mod(f, self.owner)
            if f in self.names:
                m["name"] = self.names[f]
            for err in m["errors"]:
                log.warning("Mod %s: %s", m["name"], err)
            loaded.append(m)
        for off in self.accepted.values():
            loaded += [modpack.load_mod(f) for f in off["folders"]]
        rs = modpack.room_set(loaded)
        self._pack = None
        if rs["hash"]:
            log.info("Mods de la sala: %d stickers y %d avatares (%s)", len(rs["stickers"]), len(rs["avatars"]),
                     ", ".join(m["name"] for m in rs["mods"]))
        return rs

    def set_base(self, folders, names=None):
        """Los mods del anfitrion cambiaron (recarga en caliente)."""
        with self.lock:
            self.base = list(folders)
            if names:
                self.names = dict(names)
            self.rs = self._build()
            return self.rs

    def pack(self):
        with self.lock:
            if self._pack is None and self.rs["hash"]:
                self._pack = modpack.pack(self.rs)
            return self._pack

    # ------------------------------------------------------------ mods de los jugadores
    def offer(self, data, player):
        """Un jugador ofrece sus mods. Devuelve 'pending', 'accepted', 'known' o 'ignored'."""
        if not self.offers_dir:
            return "ignored"
        oid = hashlib.sha1(data).hexdigest()[:12]
        with self.lock:
            if oid in self.accepted:
                return "accepted"
            if oid in self.pending:
                return "pending"
            if len(self.pending) + len(self.accepted) >= MAX_OFFERS:
                return "ignored"
        folder = os.path.join(self.offers_dir, oid)
        shutil.rmtree(folder, ignore_errors=True)
        folders = modpack.unpack(data, folder)          # valida todo (lanza ModError si no vale)
        mods = [modpack.load_mod(f) for f in folders]
        with self.lock:
            have = {m["uid"] for m in self.rs["mods"]}
            mods = [m for m in mods if m["uid"] not in have and (m["stickers"] or m["avatars"])]
            if not mods:
                shutil.rmtree(folder, ignore_errors=True)
                return "known"
            summary = modpack.summary(modpack.room_set(mods))
            entry = {"player": str(player or "?")[:40], "folders": [m["folder"] for m in mods],
                     "summary": summary}
            if self.auto_accept:
                self.accepted[oid] = entry
                self.rs = self._build()
                return "accepted"
            self.pending[oid] = entry
            log.info("%s ofrece %d stickers y %d avatares", entry["player"], summary["stickers"], summary["avatars"])
            return "pending"

    def pending_list(self):
        with self.lock:
            return [{"id": k, "player": v["player"], **v["summary"]} for k, v in self.pending.items()]

    def answer(self, oid, accept):
        with self.lock:
            entry = self.pending.pop(oid, None)
            if not entry:
                return self.rs
            if accept:
                self.accepted[oid] = entry
                self.rs = self._build()
            else:
                shutil.rmtree(os.path.join(self.offers_dir, oid), ignore_errors=True)
            return self.rs
