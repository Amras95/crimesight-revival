#!/usr/bin/env python3
"""
CRIMESIGHT Revival - servidor comunitario.

Fase 1: API HTTP (account.*, user.*, consultas de match.* sin sala) para
poder iniciar sesion y llegar al menu principal sin los servidores de Konami.
Fase 2: canal WebSocket/WAMP para salas y partidas (ver match.py).

Uso: python server.py [--host 0.0.0.0] [--port 18080]
"""
import argparse, hashlib, hmac, json, logging, os, secrets, sys, threading, time

from aiohttp import web, WSMsgType

import cscrypto
import match
import modpack
import modroom
import stats

API_PATH = "/cott/api/index.php"
WS_PATH = "/ws"
DATA_DIR = os.environ.get("CSR_DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
log = logging.getLogger("crimesight")


# ---------------------------------------------------------------- identidad
# La misma cuenta de Steam tiene el mismo jugador y el mismo token en CUALQUIER servidor de la
# comunidad: asi se puede jugar en casa de un amigo o en un servidor propio y volver sin que el
# juego se lie con las cuentas, y los perfiles se pueden juntar.
def derived_ids(platform, platform_id):
    base = f"{platform}:{platform_id}".encode()
    pid = hashlib.sha256(b"csr-player:" + base).hexdigest()[:16]
    token = hashlib.sha256(b"csr-token:" + base).hexdigest()[:32]
    return pid, token


# ---------------------------------------------------------------- almacenamiento
class Store:
    """Persistencia minima en un JSON local (un servidor por grupo de amigos)."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.db = {"accounts": {}, "users": {}}
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                self.db.update(json.load(f))
        self.sessions = {}  # ssid -> player_id (en memoria)
        for k in [k for k in self.db["users"] if k.startswith("bot")]:   # restos de versiones viejas
            self.db["users"].pop(k)
        self._migrate_ids()

    def _migrate_ids(self):
        """Cuentas creadas con ids aleatorios (versiones anteriores) -> ids derivados de Steam."""
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
                acc.setdefault("legacy_tokens", []).append(acc.get("token"))   # el juego aun puede usar el viejo
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


# Campanas (eventos) del cliente: NetworkManager.CAMPAIGN_PROJECT_WINTER = 1
EVENT_CAMPAIGNS = [1]
EVENT_OPEN_SECONDS = 10 * 365 * 24 * 3600


# ---------------------------------------------------------------- comandos HTTP
class Api:
    def __init__(self, store: Store, public_url: str):
        self.s = store
        self.public_url = public_url      # None: la que use cada cliente para llegar (cabecera Host)
        self.request_base = "http://127.0.0.1:18080"
        self.hub = None

    def ws_url(self):
        return (self.public_url or self.request_base).replace("http", "ws", 1) + WS_PATH

    def player(self, ssid):
        return self.s.sessions.get(ssid)

    # --- account.*
    def account_HasAccount(self, p, ssid):
        acc = self.s.account_by_platform(p.get("platform"), p.get("platform_id"))
        # agreement_version 0: el cliente no vuelve a pedir aceptar terminos que ya no existen
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
            # idioma del juego: lo usan el lanzador (para traducirse) y los nombres de las IA
            u["lang"], u["lang_time"] = str(p["lang"]).upper(), int(time.time())
            self.s.save()
        return {"ssid": new_ssid, "player_id": acc["player_id"],
                "user_create": 0 if u["name"] else 1,
                "suspended": "", "message": "",
                # Eventos: ya no hay eventos oficiales, asi que todos quedan abiertos y con la
                # participacion hecha (desbloquea su avatar). Las recompensas por puntos y nivel
                # y el contenido Deluxe siguen como en el juego (Deluxe = tenerlo en Steam).
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

    # --- match.* que van por HTTP
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
        """Puntos de la ultima partida (pantalla de resultados)."""
        pid = self.player(ssid)
        if self.hub:
            self.hub.settle_kill(pid)      # si la partida acabo en asesinato, se anota ya
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
    api.request_base = f"http://{request.host}"   # el anfitrion entra por 127.0.0.1 y su amigo por la IP publica
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


# ---------------------------------------------------------------- WebSocket (salas y partidas)
async def handle_ws(request: web.Request):
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=8 * 1024 * 1024)
    await ws.prepare(request)
    log.info("WS conectado desde %s", request.remote)
    await request.app["hub"].run(ws)
    return ws


async def handle_sync(request):
    """Sincronizacion de perfiles para el lanzador (JSON sin cifrar).
    POST {"platform": 3, "platform_id": "...", "profile": {...}, "password": "..."}
    -> junta el perfil recibido con el del servidor y devuelve el resultado."""
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
    stats.merge_into(user, body.get("profile") or {})
    api.s.save()
    log.info("Perfil sincronizado: %s (%s)", user.get("name") or platform_id, stats.summary(user))
    return web.json_response({"player_id": pid, "profile": stats.export_profile(user)})


async def handle_info(request):
    info = {"server": "crimesight-revival", "version": 1, "password": bool(request.app.get("password"))}
    rs = request.app["room"].rs
    if rs["hash"]:
        info["mods"] = modpack.summary(rs)
    return web.json_response(info)


def _password_ok(request):
    pw = request.app.get("password") or ""
    return not pw or hmac.compare_digest(request.headers.get("X-CSR-Password", ""), pw)


async def handle_mods(request):
    """Paquete con los mods de la sala (los descarga el lanzador al unirse y cuando cambian)."""
    if not _password_ok(request):
        return web.json_response({"error": "password"}, status=403)
    room = request.app["room"]
    data = room.pack()
    if not data:
        return web.json_response({"error": "no_mods"}, status=404)
    return web.Response(body=data, content_type="application/zip", headers={"X-CSR-Mods": room.rs["hash"]})


async def handle_mods_offer(request):
    """Un jugador ofrece sus mods a la sala; el anfitrion decide si los usa."""
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


def build_app(port=18080, password="", public_url=None, ai_difficulty="normal", data_dir=None, mods=None,
              mods_dir=None, owner="", player_mods="ask", mod_names=None):
    """player_mods: "ask" (el anfitrion decide desde el lanzador), "accept" (se aceptan solos) o
    "ignore" (servidor dedicado sin nadie que conteste)."""
    data_dir = data_dir or DATA_DIR
    os.makedirs(data_dir, exist_ok=True)
    cscrypto._keys()  # falla pronto si no hay claves
    app = web.Application(client_max_size=8 * 1024 * 1024)
    api = Api(Store(os.path.join(data_dir, "db.json")), public_url)
    match.DEFAULT_AI_DIFFICULTY = ai_difficulty
    api.hub = match.Hub(api)
    app["api"], app["hub"] = api, api.hub
    app.router.add_post(API_PATH, handle_api)
    app.router.add_get(WS_PATH, handle_ws)
    app.router.add_post("/revival/sync", handle_sync)
    app.router.add_get("/revival/info", handle_info)
    app.router.add_get("/revival/mods", handle_mods)
    app.router.add_post("/revival/mods/offer", handle_mods_offer)
    app["password"] = password or ""
    app["room"] = modroom.ModRoom(mods, mods_dir, owner=owner,
                                  offers_dir=None if player_mods == "ignore" else os.path.join(data_dir, "mods_offers"),
                                  auto_accept=player_mods == "accept", names=mod_names)
    return app


def setup_logging(data_dir, debug=False):
    os.makedirs(data_dir, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(asctime)s %(message)s",
                        datefmt="%H:%M:%S",
                        handlers=([logging.StreamHandler()] if sys.stderr else []) +
                                 [logging.FileHandler(os.path.join(data_dir, "server.log"), encoding="utf-8")])
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


class BackgroundServer:
    """Servidor en un hilo aparte (lo usa el lanzador)."""

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
        """Los mods de la sala (el lanzador del anfitrion los cambia y contesta a las ofertas)."""
        return self.app["room"]

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=18080)
    ap.add_argument("--debug", action="store_true", help="registra cada mensaje WebSocket")
    ap.add_argument("--ai-difficulty", choices=["easy", "normal", "hard"], default="normal",
                    help="dificultad inicial de los jugadores IA")
    ap.add_argument("--public-url", default=None,
                    help="URL fija con la que los clientes ven este servidor (por defecto, la que use cada uno)")
    ap.add_argument("--password", default=os.environ.get("CSR_PASSWORD", ""),
                    help="contrasena para sincronizar perfiles (servidores abiertos a internet)")
    ap.add_argument("--data-dir", default=None, help="carpeta de datos (por defecto server/data)")
    ap.add_argument("--mods-dir", default=None,
                    help="carpeta con mods de apariencia (stickers/avatares) que se ofrecen a los jugadores")
    ap.add_argument("--accept-player-mods", action="store_true",
                    help="usar en las salas los mods que traigan los jugadores (sin esto se ignoran)")
    a = ap.parse_args()
    data_dir = a.data_dir or DATA_DIR
    setup_logging(data_dir, a.debug)
    app = build_app(a.port, a.password, a.public_url, a.ai_difficulty, data_dir, mods_dir=a.mods_dir,
                    player_mods="accept" if a.accept_player_mods else "ignore")
    log.info("CRIMESIGHT Revival escuchando en http://%s:%d", a.host, a.port)
    web.run_app(app, host=a.host, port=a.port, print=None, access_log=None)


if __name__ == "__main__":
    main()
