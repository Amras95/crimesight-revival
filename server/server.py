#!/usr/bin/env python3
"""
CRIMESIGHT Revival - community server.

Phase 1: HTTP API (account.*, user.*, match.* queries without a room) to
be able to log in and reach the main menu without Konami's servers.
Phase 2: WebSocket/WAMP channel for rooms and matches (see match.py).

Usage: python server.py [--host 0.0.0.0] [--port 18080]
"""
import argparse, asyncio, hashlib, hmac, json, logging, os, secrets, sys, threading, time

from aiohttp import web, WSMsgType

import cscrypto
import match
import modelpack
import modelroom
import modpack
import modroom
import stageroom
import stats

API_PATH = "/cott/api/index.php"
WS_PATH = "/ws"
DATA_DIR = os.environ.get("CSR_DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
log = logging.getLogger("crimesight")


# ---------------------------------------------------------------- identity
# The same Steam account has the same player and the same token on ANY community
# server: that way you can play at a friend's or on your own server and come back without the
# game getting confused by the accounts, and profiles can be merged.
def derived_ids(platform, platform_id):
    base = f"{platform}:{platform_id}".encode()
    pid = hashlib.sha256(b"csr-player:" + base).hexdigest()[:16]
    token = hashlib.sha256(b"csr-token:" + base).hexdigest()[:32]
    return pid, token


# ---------------------------------------------------------------- storage
class Store:
    """Minimal persistence in a local JSON (one server per group of friends)."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.db = {"accounts": {}, "users": {}}
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                self.db.update(json.load(f))
        self.sessions = {}  # ssid -> player_id (in memory)
        for k in [k for k in self.db["users"] if k.startswith("bot")]:   # leftovers from old versions
            self.db["users"].pop(k)
        self._migrate_ids()

    def _migrate_ids(self):
        """Accounts created with random ids (earlier versions) -> ids derived from Steam."""
        changed = False
        for acc in self.db["accounts"].values():
            pid, token = derived_ids(acc.get("platform"), acc.get("platform_id"))
            if acc.get("player_id") != pid:
                old = acc["player_id"]
                data = self.db["users"].pop(old, None)
                if data is not None:
                    if pid in self.db["users"]:
                        stats.merge_into(self.db["users"][pid], stats.export_profile(data))
                    else:
                        self.db["users"][pid] = data
                acc["player_id"] = pid
                changed = True
                log.info("Cuenta %s: id %s -> %s", acc.get("platform_id"), old, pid)
            if acc.get("token") != token:
                acc.setdefault("legacy_tokens", []).append(acc.get("token"))   # the game may still use the old one
                acc["token"] = token
                changed = True
        if changed:
            self.save()

    def account_by_token(self, token):
        for a in self.db["accounts"].values():
            if a.get("token") == token or token in (a.get("legacy_tokens") or []):
                return a
        return None

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.db, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)

    def account_by_platform(self, platform, pid):
        return self.db["accounts"].get(f"{platform}:{pid}")

    def user(self, player_id):
        return self.db["users"].setdefault(player_id, {
            "name": "", "progress": 0, "tutorial_step": 0, "config": {}, "stats": [], "created": int(time.time()),
        })


# Client campaigns (events): NetworkManager.CAMPAIGN_PROJECT_WINTER = 1
EVENT_CAMPAIGNS = [1]
EVENT_OPEN_SECONDS = 10 * 365 * 24 * 3600


# ---------------------------------------------------------------- HTTP commands
class Api:
    def __init__(self, store: Store, public_url: str):
        self.s = store
        self.public_url = public_url      # None: the one each client uses to get here (Host header)
        self.request_base = "http://127.0.0.1:18080"
        self.hub = None

    def ws_url(self):
        return (self.public_url or self.request_base).replace("http", "ws", 1) + WS_PATH

    def player(self, ssid):
        return self.s.sessions.get(ssid)

    # --- account.*
    def account_HasAccount(self, p, ssid):
        acc = self.s.account_by_platform(p.get("platform"), p.get("platform_id"))
        # agreement_version 0: the client doesn't ask again to accept terms that no longer exist
        return {"exists": acc is not None, "agreement_version": 0}

    def account_Register(self, p, ssid):
        key = f"{p.get('platform')}:{p.get('platform_id')}"
        acc = self.s.db["accounts"].get(key)
        if not acc:
            pid, token = derived_ids(p.get("platform"), p.get("platform_id"))
            acc = {"player_id": pid, "token": token,
                   "platform": p.get("platform"), "platform_id": p.get("platform_id"),
                   "country": p.get("country", "")}
            self.s.db["accounts"][key] = acc
            self.s.user(acc["player_id"])
            self.s.save()
        return {"token": acc["token"], "player_id": acc["player_id"]}

    def account_SignIn(self, p, ssid):
        token = p.get("token") or p.get("account_token")
        acc = self.s.account_by_token(token)
        if acc is None:
            raise ApiError("ACC-102", "Cuenta desconocida en este servidor.")
        new_ssid = secrets.token_hex(16)
        self.s.sessions[new_ssid] = acc["player_id"]
        u = self.s.user(acc["player_id"])
        if p.get("lang"):
            # game language: used by the launcher (to translate itself) and the AI names
            u["lang"], u["lang_time"] = str(p["lang"]).upper(), int(time.time())
            self.s.save()
        return {"ssid": new_ssid, "player_id": acc["player_id"],
                "user_create": 0 if u["name"] else 1,
                "suspended": "", "message": "",
                # Events: there are no official events anymore, so all of them stay open with
                # participation done (unlocks its avatar). The rewards for points and level
                # and the Deluxe content stay as in the game (Deluxe = owning it on Steam).
                "campaigns": [{"id": cid, "up_to_start": -3600, "up_to_end": EVENT_OPEN_SECONDS}
                              for cid in EVENT_CAMPAIGNS],
                "campaign_entries": list(EVENT_CAMPAIGNS)}

    def account_SignOut(self, p, ssid):
        self.s.sessions.pop(ssid, None)
        return {}

    def account_GetPlayerIdByPlatformId(self, p, ssid):
        acc = self.s.account_by_platform(p.get("platform"), p.get("platform_id"))
        return {"player_id": acc["player_id"] if acc else ""}

    def account_UnregisterPlatformId(self, p, ssid):
        key = f"{p.get('platform')}:{p.get('platform_id')}"
        self.s.db["accounts"].pop(key, None)
        self.s.save()
        return {}

    def account_IssueInquiryCode(self, p, ssid):
        return {"code": "LOCAL", "confirm_message": "Servidor comunitario: no hay soporte de Konami."}

    # --- user.*
    def _me(self, ssid):
        pid = self.player(ssid)
        if not pid:
            raise ApiError("ACC-120", "Sesion caducada.")
        return self.s.user(pid)

    def user_Register(self, p, ssid):
        u = self._me(ssid)
        u["name"] = str(p.get("name", ""))[:32]
        u["updated"] = int(time.time())
        self.s.save()
        return {}

    user_SetUserName = user_Register

    def user_GetProgress(self, p, ssid):
        return {"progress": int(self._me(ssid)["progress"])}

    def user_SetProgress(self, p, ssid):
        u = self._me(ssid)
        u["progress"] = max(int(u.get("progress", 0) or 0), int(p.get("progress", 0)))
        self.s.save()
        return {}

    def user_GetTutorialStep(self, p, ssid):
        return {"step": int(self._me(ssid)["tutorial_step"])}

    def user_SetTutorialStep(self, p, ssid):
        u = self._me(ssid)
        u["tutorial_step"] = max(int(u.get("tutorial_step", 0) or 0), int(p.get("step", 0)))
        self.s.save()
        return {}

    def user_GetConfig(self, p, ssid):
        return {"config": json.dumps(self._me(ssid)["config"])}

    def user_SetConfig(self, p, ssid):
        u = self._me(ssid)
        now = time.time()
        for t, v in zip(p.get("types", []), p.get("values", [])):
            u["config"][str(t)] = v
            u.setdefault("config_time", {})[str(t)] = now
        u["updated"] = int(now)
        self.s.save()
        return {}

    def user_GetStats(self, p, ssid):
        return {"stats": stats.user_stats(self._me(ssid))}

    def user_GetReplay(self, p, ssid):
        return {"replay_data": []}

    # --- match.* that go over HTTP
    def match_GetUrl(self, p, ssid):
        return {"url": self.ws_url()}

    def match_CountWaiting(self, p, ssid):
        return {"count": 0}

    def match_CheckAvailableNotification(self, p, ssid):
        return {}

    def match_ListRooms(self, p, ssid):
        hub = self.hub
        rooms = []
        for r in (hub.public_rooms() if hub else [])[: int(p.get("limit", 50) or 50)]:
            info = r.settings_result()
            info["capacity"] = int(r.settings.get("capacity", 1))
            info.update({"owner_name": r.members.get(r.owner, {}).get("name", ""), "available": r.has_space(),
                         "turn": r.turn, "name": r.members.get(r.owner, {}).get("name", ""),
                         "url": self.ws_url(), "match_count": 0,
                         "members": [{"id": pid, "name": m["name"]} for pid, m in r.members.items()]})
            rooms.append(info)
        return {"rooms": rooms}

    def match_GetQuickRoom(self, p, ssid):
        hub = self.hub
        room = next((r for r in (hub.public_rooms() if hub else []) if r.has_space()), None)
        if room is None:
            return {"id": "", "url": ""}
        return {"id": room.id, "url": self.ws_url()}

    def match_GetStats(self, p, ssid):
        """Points of the last match (results screen)."""
        pid = self.player(ssid)
        if self.hub:
            self.hub.settle_kill(pid)      # if the match ended in a murder, it is recorded now
        return {"stats": self._me(ssid).get("last_result", [])}


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def reply(result=None, code=200, error=None):
    body = {"resultCode": code, "timestamp": int(time.time())}
    if result is not None:
        body["result"] = result
    if error:
        body["errorCode"], body["errorMessage"] = error
    return web.Response(body=cscrypto.encrypt(json.dumps(body, ensure_ascii=False).encode()),
                        content_type="application/octet-stream")


async def handle_api(request: web.Request):
    raw = await request.read()
    try:
        req = json.loads(cscrypto.decrypt(raw, "upstream"))
    except Exception as e:  # noqa: BLE001
        log.warning("Peticion ilegible (%s bytes): %s", len(raw), e)
        return web.Response(status=400)
    cmd = req.get("command_name", "")
    params = req.get("params") or {}
    ssid = req.get("ssid", "")
    api: Api = request.app["api"]
    api.request_base = f"http://{request.host}"   # the host comes in through 127.0.0.1 and their friend through the public IP
    fn = getattr(api, cmd.replace(".", "_"), None)
    if fn is None:
        log.warning("COMANDO SIN IMPLEMENTAR %s %s", cmd, json.dumps(params, ensure_ascii=False)[:500])
        return reply({})
    try:
        res = fn(params, ssid)
        log.info("%-36s %s -> %s", cmd, json.dumps(params, ensure_ascii=False)[:200],
                 json.dumps(res, ensure_ascii=False)[:200])
        return reply(res)
    except ApiError as e:
        log.info("%-36s ERROR %s %s", cmd, e.code, e.msg)
        return reply(code=400, error=(e.code, e.msg))


# ---------------------------------------------------------------- WebSocket (rooms and matches)
async def handle_ws(request: web.Request):
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=8 * 1024 * 1024)
    await ws.prepare(request)
    log.info("WS conectado desde %s", request.remote)
    await request.app["hub"].run(ws, remote=request.remote or "")
    return ws


async def handle_sync(request):
    """Profile sync for the launcher (unencrypted JSON).
    POST {"platform": 3, "platform_id": "...", "profile": {...}, "password": "..."}
    -> merges the received profile with the server's and returns the result."""
    api = request.app["api"]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "json"}, status=400)
    pw = request.app.get("password") or ""
    if pw and not hmac.compare_digest(str(body.get("password", "")), pw):
        return web.json_response({"error": "password"}, status=403)
    platform, platform_id = body.get("platform", 3), str(body.get("platform_id", ""))
    if not platform_id.isdigit():
        return web.json_response({"error": "platform_id"}, status=400)
    pid, token = derived_ids(platform, platform_id)
    key = f"{platform}:{platform_id}"
    if key not in api.s.db["accounts"]:
        api.s.db["accounts"][key] = {"player_id": pid, "token": token, "platform": platform,
                                     "platform_id": platform_id, "country": ""}
    user = api.s.user(pid)
    stats.merge_into(user, body.get("profile") or {}, prefer_other=True)   # their copy of their matches rules
    api.s.save()
    log.info("Perfil sincronizado: %s (%s)", user.get("name") or platform_id, stats.summary(user))
    return web.json_response({"player_id": pid, "profile": stats.export_profile(user)})


async def handle_match(request):
    """GET /revival/match?platform_id=... -> {"match": {"role", "match_id", "stage", "level"} or null}.
    A guest's launcher checks it during the match: if the host disappears midway, it counts
    as a win for whoever stays (the server can't record it because it is gone)."""
    platform_id = str(request.query.get("platform_id", ""))
    if not platform_id.isdigit():
        return web.json_response({"error": "platform_id"}, status=400)
    pid, _ = derived_ids(3, platform_id)
    return web.json_response({"match": request.app["hub"].match_state(pid, request.remote or "")})


async def handle_roster(request):
    """GET /revival/roster?platform_id=... -> character cast of that player's match (or null).
    Also says which characters are off in that player's room, the room's id and whether the player created it."""
    platform_id = str(request.query.get("platform_id", ""))
    if not platform_id.isdigit():
        return web.json_response({"error": "platform_id"}, status=400)
    pid, _ = derived_ids(3, platform_id)
    room = request.app["hub"].room_of(pid, request.remote or "")
    disabled = room.disabled if room is not None and room.disabled is not None else request.app["models"].disabled
    return web.json_response({"roster": getattr(room, "roster", None) if room is not None else None,
                              "disabled": sorted(disabled),
                              "room": room.id if room is not None else None,
                              "owner": room is not None and room.owner == pid})


MAX_SELECT = 200


async def handle_roster_select(request):
    """POST /revival/roster/select {"platform_id", "disabled": [...]}: the Character Selection of a room, sent by
    the launcher of the player who created it (on a server nobody hosts from their launcher)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    try:
        body = await request.json()
        platform_id = str(body.get("platform_id", ""))
        ids = body.get("disabled") or []
        if not platform_id.isdigit() or not isinstance(ids, list) or len(ids) > MAX_SELECT:
            raise ValueError
        ids = {str(i)[:64] for i in ids}
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"error": "bad_request"}, status=400)
    pid, _ = derived_ids(3, platform_id)
    room = request.app["hub"].room_of(pid, request.remote or "")
    if room is None or room.owner != pid:
        return web.json_response({"error": "not_owner"}, status=403)
    room.disabled = ids
    log.info("Room %s: Character Selection changed (%d off)", room.id, len(ids))
    return web.json_response({"disabled": sorted(ids)})


async def handle_info(request):
    info = {"server": "crimesight-revival", "version": 1, "password": bool(request.app.get("password"))}
    rs = request.app["room"].rs
    if rs["hash"]:
        info["mods"] = modpack.summary(rs)
    ms = request.app["models"].ms
    if ms["hash"]:
        info["models"] = modelpack.summary(ms)
    stages = request.app["stages"].summary()
    if stages:
        info["stages"] = stages
    return web.json_response(info)


def _password_ok(request):
    pw = request.app.get("password") or ""
    return not pw or hmac.compare_digest(request.headers.get("X-CSR-Password", ""), pw)


async def handle_mods(request):
    """Pack with the room's mods (the launcher downloads them on joining and when they change)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    room = request.app["room"]
    data = room.pack()
    if not data:
        return web.json_response({"error": "no_mods"}, status=404)
    return web.Response(body=data, content_type="application/zip", headers={"X-CSR-Mods": room.rs["hash"]})


async def handle_mods_offer(request):
    """A player offers their mods to the room; the host decides whether to use them."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    if (request.content_length or 0) > modpack.MAX_PACK_BYTES:
        return web.json_response({"error": "too_big"}, status=413)
    data = await request.read()
    from urllib.parse import unquote
    player = unquote(request.headers.get("X-CSR-Player", ""))[:40]
    import asyncio
    try:
        status = await asyncio.get_running_loop().run_in_executor(None, request.app["room"].offer, data, player)
    except modpack.ModError as e:
        return web.json_response({"error": str(e)}, status=400)
    return web.json_response({"status": status})


# ------------------------------------------------------------ the room's 3D models and animations
async def handle_models(request):
    """List of the room's models (which character each one is on and the sha256 of each file)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    return web.json_response(request.app["models"].manifest())


async def handle_model_file(request):
    """A .glb of the room, by its sha256 (only the ones in use)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    path = request.app["models"].path_of(request.match_info["sha"])
    if not path or not os.path.isfile(path):
        return web.json_response({"error": "not_found"}, status=404)
    return web.FileResponse(path, headers={"Content-Type": "model/gltf-binary"})


async def handle_models_offer(request):
    """A player offers their models (only the list; the files are uploaded if the host accepts)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    try:
        meta = await request.json()
        from urllib.parse import unquote
        status, oid, need = request.app["models"].offer(meta, unquote(request.headers.get("X-CSR-Player", ""))[:40])
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)[:200]}, status=400)
    return web.json_response({"status": status, "id": oid, "need": need})


async def handle_models_offer_state(request):
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    status, need = request.app["models"].state(request.match_info["oid"])
    return web.json_response({"status": status, "need": need})


async def handle_models_upload(request):
    """The guest uploads a file of their accepted offer. It is saved bit by bit and checked before use."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    room = request.app["models"]
    oid, sha = request.match_info["oid"], request.match_info["sha"]
    want = room.expect(oid, sha)
    if want is None:
        return web.json_response({"error": "not_expected"}, status=409)
    size, kind = want
    path = room.upload_path(sha)
    h, n = hashlib.sha256(), 0
    try:
        with open(path + ".part", "wb") as f:
            async for chunk in request.content.iter_chunked(1 << 16):
                n += len(chunk)
                if n > size:
                    raise modelpack.ModelError("archivo mas grande de lo anunciado")
                h.update(chunk)
                f.write(chunk)
        if n != size or h.hexdigest() != sha:
            raise modelpack.ModelError("el archivo no coincide")
        with open(path + ".part", "rb") as f:
            data = f.read()
        await asyncio.get_running_loop().run_in_executor(None, modelpack.check_file, data, kind)
        os.replace(path + ".part", path)
    except modelpack.ModelError as e:
        try:
            os.remove(path + ".part")
        except OSError:
            pass
        return web.json_response({"error": str(e)}, status=400)
    room.add_file(oid, sha, path)
    return web.json_response({"ok": True})


async def handle_stages(request):
    """Creator stages in the room (the launcher downloads them on joining and when they change)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    return web.json_response(request.app["stages"].pack())


async def handle_stages_have(request):
    """A player's launcher says which stages it has ready: {"platform_id": ..., "have": {id: fingerprint}}."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    if (request.content_length or 0) > stageroom.MAX_BYTES:
        return web.json_response({"error": "too_big"}, status=413)
    try:
        body = await request.json()
        pid, _ = derived_ids(int(body.get("platform", 3)), str(body["platform_id"]))
    except (ValueError, KeyError, TypeError):
        return web.json_response({"error": "bad_request"}, status=400)
    request.app["stages"].report(pid, body.get("have"), body.get("seen"))
    await request.app["hub"].stage_poll()        # the rooms find out right away
    return web.json_response({"ok": True})


async def _stage_watch(app):
    """Watches which rooms are waiting for someone to have the chosen stage (and when they stop waiting)."""
    async def loop():
        while True:
            await asyncio.sleep(1)
            try:
                await app["hub"].stage_poll()
            except Exception:  # noqa: BLE001
                log.exception("Fallo vigilando los escenarios de las salas")
    task = asyncio.ensure_future(loop())
    yield
    task.cancel()


IDLE_RESET = 120      # seconds with nobody connected before a standalone server drops the players' mods


@web.middleware
async def _seen(request, handler):
    """Remembers the last time anyone (a game or a launcher) talked to the server."""
    request.app["last_seen"] = time.time()
    return await handler(request)


async def _idle_reset(app):
    """Standalone server: once nobody has been connected for a while, the players' mods and models go away
    (when someone hosts from their launcher, they only last for that session anyway)."""
    async def loop():
        while True:
            await asyncio.sleep(15)
            try:
                if app["hub"].sessions or time.time() - app.get("last_seen", 0) < IDLE_RESET:
                    continue
                mods = app["room"].reset_players()
                models = app["models"].reset_players()
                if mods or models:
                    log.info("Nobody connected: players' mods and models removed")
            except Exception:  # noqa: BLE001
                log.exception("Could not remove the players' mods")
    task = asyncio.ensure_future(loop())
    yield
    task.cancel()


def build_app(port=18080, password="", public_url=None, ai_difficulty="normal", data_dir=None, mods=None,
              mods_dir=None, owner="", player_mods="ask", mod_names=None, stages=None, stages_dir=None,
              idle_reset=False):
    """player_mods: "ask" (the host decides from the launcher), "accept" (accepted automatically) or
    "ignore" (dedicated server with nobody to answer).
    idle_reset: standalone server, drop the players' mods when nobody is left."""
    data_dir = data_dir or DATA_DIR
    os.makedirs(data_dir, exist_ok=True)
    cscrypto._keys()  # fails early if there are no keys
    app = web.Application(client_max_size=8 * 1024 * 1024, middlewares=[_seen])
    app["last_seen"] = time.time()
    api = Api(Store(os.path.join(data_dir, "db.json")), public_url)
    match.DEFAULT_AI_DIFFICULTY = ai_difficulty
    api.hub = match.Hub(api)
    app["api"], app["hub"] = api, api.hub
    app.router.add_post(API_PATH, handle_api)
    app.router.add_get(WS_PATH, handle_ws)
    app.router.add_post("/revival/sync", handle_sync)
    app.router.add_get("/revival/info", handle_info)
    app.router.add_get("/revival/match", handle_match)
    app.router.add_get("/revival/mods", handle_mods)
    app.router.add_post("/revival/mods/offer", handle_mods_offer)
    app.router.add_get("/revival/models", handle_models)
    app.router.add_get("/revival/roster", handle_roster)
    app.router.add_post("/revival/roster/select", handle_roster_select)
    app.router.add_get("/revival/models/file/{sha:[0-9a-f]{64}}", handle_model_file)
    app.router.add_post("/revival/models/offer", handle_models_offer)
    app.router.add_get("/revival/models/offer/{oid:[0-9a-f]{12}}", handle_models_offer_state)
    app.router.add_put("/revival/models/upload/{oid:[0-9a-f]{12}}/{sha:[0-9a-f]{64}}", handle_models_upload)
    app.router.add_get("/revival/stages", handle_stages)
    app.router.add_post("/revival/stages/have", handle_stages_have)
    app["stages"] = api.stages = stageroom.StageRoom(list(stages or []) + stageroom.load_dir(stages_dir))
    app.cleanup_ctx.append(_stage_watch)
    app["password"] = password or ""
    app["room"] = modroom.ModRoom(mods, mods_dir, owner=owner,
                                  offers_dir=None if player_mods == "ignore" else os.path.join(data_dir, "mods_offers"),
                                  auto_accept=player_mods == "accept", names=mod_names)
    api.hub.mod_room = app["room"]      # the AIs check which game sticker each mod sticker is equivalent to
    app["models"] = modelroom.ModelRoom(
        offers_dir=None if player_mods == "ignore" else os.path.join(data_dir, "models_offers"),
        auto_accept=player_mods == "accept")
    api.hub.model_room = app["models"]  # each match draws which characters appear
    if idle_reset:
        app.cleanup_ctx.append(_idle_reset)
    return app


def setup_logging(data_dir, debug=False):
    os.makedirs(data_dir, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(asctime)s %(message)s",
                        datefmt="%H:%M:%S",
                        handlers=([logging.StreamHandler()] if sys.stderr else []) +
                                 [logging.FileHandler(os.path.join(data_dir, "server.log"), encoding="utf-8")])
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


class BackgroundServer:
    """Server on a separate thread (used by the launcher)."""

    def __init__(self, host="127.0.0.1", port=18080, **kw):
        import asyncio
        self.host, self.port, self.kw = host, port, kw
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.error = None
        self._ready = threading.Event()

    def _run(self):
        import asyncio
        asyncio.set_event_loop(self.loop)
        try:
            app = build_app(port=self.port, **self.kw)
            self.app = app
            self.runner = web.AppRunner(app, access_log=None)
            self.loop.run_until_complete(self.runner.setup())
            self.loop.run_until_complete(web.TCPSite(self.runner, self.host, self.port).start())
            log.info("CRIMESIGHT Revival escuchando en http://%s:%d", self.host, self.port)
        except BaseException as e:  # noqa: BLE001
            self.error = e
            self._ready.set()
            return
        self._ready.set()
        self.loop.run_forever()
        self.loop.run_until_complete(self.runner.cleanup())

    def start(self, timeout=15):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._ready.wait(timeout)
        if self.error:
            raise self.error
        return self

    @property
    def room(self):
        """The room's mods (the host's launcher changes them and answers the offers)."""
        return self.app["room"]

    @property
    def models(self):
        """The room's 3D models and animations (same as the mods)."""
        return self.app["models"]

    @property
    def stages(self):
        """The creator stages in the room."""
        return self.app["stages"]

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=18080)
    ap.add_argument("--debug", action="store_true", help="registra cada mensaje WebSocket")
    ap.add_argument("--ai-difficulty", choices=["easy", "normal", "hard", "expert", "nightmare"], default="normal",
                    help="dificultad inicial de los jugadores IA")
    ap.add_argument("--public-url", default=None,
                    help="URL fija con la que los clientes ven este servidor (por defecto, la que use cada uno)")
    ap.add_argument("--password", default=os.environ.get("CSR_PASSWORD", ""),
                    help="contrasena para sincronizar perfiles (servidores abiertos a internet)")
    ap.add_argument("--data-dir", default=None, help="carpeta de datos (por defecto server/data)")
    ap.add_argument("--mods-dir", default=None,
                    help="carpeta con mods de apariencia (stamps/ y avatars/, como la carpeta de mods del lanzador) que se ofrecen a los jugadores")
    ap.add_argument("--accept-player-mods", action="store_true",
                    help="usar en las salas los mods que traigan los jugadores (sin esto se ignoran)")
    ap.add_argument("--stages-dir", default=None,
                    help="carpeta con escenarios del creador de escenarios (.json) que se ofrecen a los jugadores")
    a = ap.parse_args()
    data_dir = a.data_dir or DATA_DIR
    setup_logging(data_dir, a.debug)
    app = build_app(a.port, a.password, a.public_url, a.ai_difficulty, data_dir, mods_dir=a.mods_dir,
                    player_mods="accept" if a.accept_player_mods else "ignore", stages_dir=a.stages_dir,
                    idle_reset=True)
    log.info("CRIMESIGHT Revival escuchando en http://%s:%d", a.host, a.port)
    web.run_app(app, host=a.host, port=a.port, print=None, access_log=None)


if __name__ == "__main__":
    main()
