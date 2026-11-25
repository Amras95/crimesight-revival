"""
CRIMESIGHT Revival - a room's mods: the host's plus the ones they accept from each player.

When joining, each player downloads the room's mods and, if they have mods of their own, offers them to the
host (POST /revival/mods/offer). The host gets a prompt ("Raven brings 4 mods, download them?"); if they
accept, the mods become part of the room and reach everyone (hot-loaded with the BepInEx plugin). Everything
is temporary: it is deleted when the server closes.

On a dedicated server (no host to answer) the players' mods are ignored, unless it is started with
--accept-player-mods.
"""
import hashlib, logging, os, shutil, threading

import modpack

log = logging.getLogger("crimesight")
MAX_OFFERS = 16


class ModRoom:
    def __init__(self, folders=None, mods_dir=None, owner="", offers_dir=None, auto_accept=False, names=None):
        self.lock = threading.Lock()
        self.names = dict(names or {})       # folder -> name to show (e.g. "Main folder")
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

    # ------------------------------------------------------------ the room's set
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
        """The host's mods changed (hot reload)."""
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

    # ------------------------------------------------------------ the players' mods
    def offer(self, data, player):
        """A player offers their mods. Returns 'pending', 'accepted', 'known' or 'ignored'."""
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
        folders = modpack.unpack(data, folder)          # checks everything (raises ModError if it is not valid)
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

    def reset_players(self):
        """Drops every player's mods (standalone server with nobody left). True if there were any."""
        with self.lock:
            if not self.pending and not self.accepted:
                return False
            self.pending, self.accepted = {}, {}
            if self.offers_dir:
                shutil.rmtree(self.offers_dir, ignore_errors=True)
            self.rs = self._build()
            return True

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
