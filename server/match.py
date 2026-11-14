"""
CRIMESIGHT Revival - canal WebSocket (WAMP v2 cifrado) y logica de salas/partidas.

Reconstruido a partir del cliente (NetworkManager, Wamp*, GameManager):
- El servidor original era un router WAMP (tipo Crossbar) con procedimientos match.*.
- Los eventos de sala llegan como EVENT con details {"var": {...variables de sala...}}
  y kwargs {"Control": {"<Comando>": {...}}}.
- La simulacion de la partida va en el cliente; el servidor reparte roles, sincroniza
  las fases de cada turno, junta las ordenes de todos y arbitra el final.
"""
import asyncio, json, logging, random, secrets, time

import os

import ai
import stats
import cscrypto

log = logging.getLogger("crimesight.match")
FULL_LOG = os.path.join(os.environ.get("CSR_DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), "ws_full.log")


def full_log(direction, pid, data):
    """Registro completo (sin recortar) del trafico WebSocket, para depurar."""
    if not log.isEnabledFor(logging.DEBUG):
        return
    try:
        with open(FULL_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {direction} {pid} {data}\n")
    except OSError:
        pass

# Mensajes WAMP
HELLO, WELCOME, ABORT, GOODBYE, ERROR = 1, 2, 3, 6, 8
PUBLISH, PUBLISHED, SUBSCRIBE, SUBSCRIBED, UNSUBSCRIBE, UNSUBSCRIBED, EVENT = 16, 17, 32, 33, 34, 35, 36
CALL, RESULT = 48, 50

# Roles (MatchRoomMember)
ROLE_RANDOM, ROLE_DETECTIVE, ROLE_CRIMINAL, ROLE_IRENE, ROLE_WATSON = 0, 1, 2, 3, 4
ROLE_KEY = {ROLE_DETECTIVE: "detective", ROLE_CRIMINAL: "criminal", ROLE_IRENE: "irene", ROLE_WATSON: "watson"}

INSTRUCT_TARGET = 5          # Pawn.InstructData.InstructType.TARGET -> "Asalto" de Moriarty
INSTRUCT_SEARCH = 3          # buscar en un mueble: el servidor decide que objeto aparece
INSTRUCT_PICK = 7            # recoger un objeto del suelo
FOOD_OPEN_COUNT = 2          # MatchSettings.foodOpenCount: comida que ven los que no son Moriarty
DEFAULT_PAWNS = 6            # personajes por partida (la mansion tiene 6 sospechosos)
COUNTDOWN_SECONDS = 3
DEFAULT_AI_DIFFICULTY = "normal"   # se puede cambiar con --ai-difficulty
STAGES = ["Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060"]
SELECTION_SECONDS = 60

SETTING_KEYS = {  # parametro de CreateRoom -> (variable de sala, tipo)
    "stage": ("setting_stage", str), "capacity": ("setting_capacity", int),
    "time_limit": ("setting_time_limit", int), "max_turn": ("setting_max_turn", int),
    "specify_roles": ("setting_specify_roles", bool), "irene_count": ("setting_irene_count", int),
    "watson_count": ("setting_watson_count", int), "auto_start": ("setting_auto_start", bool),
    "secret_passage": ("setting_secret_passage", bool), "switchboard_count": ("setting_switchboard_count", int),
    "wild_dog_count": ("setting_wild_dog_count", int), "gaspipe_count": ("setting_gaspipe_count", int),
    "fast_action": ("setting_fast_action", bool),
}


def rc(result=None):
    return {"resultCode": 200, "result": result if result is not None else {}}


def rc_error(code, msg):
    return {"resultCode": 400, "errorCode": code, "errorMessage": msg}


# ------------------------------------------------------------------ sesiones WAMP
class Session:
    def __init__(self, hub, ws):
        self.hub, self.ws = hub, ws
        self.id = random.randint(1, 2**53)
        self.player_id = None
        self.name = ""
        self.subs = {}       # sub_id -> topic
        self.room = None

    async def send(self, msg):
        if self.ws.closed:
            return
        txt = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
        log.debug("WS -> %s %s", self.player_id, txt[:400])
        full_log("->", self.player_id, txt)
        await self.ws.send_bytes(cscrypto.encrypt(txt.encode()))

    def sub_for(self, topic):
        return next((s for s, t in self.subs.items() if t == topic), None)


class Hub:
    def __init__(self, api):
        self.api = api          # para nombres y estadisticas (server.Api)
        self.sessions = set()
        self.rooms = {}         # room_id -> Room
        self.next_sub = 1000
        self.next_pub = 1
        self.deferred = None    # eventos que se envian despues del RESULT de la llamada en curso

    # ---------------- utilidades de router
    def settle_kill(self, player_id):
        """La pantalla de resultados pide los puntos: si su partida acabo en asesinato, anotarla."""
        for room in list(self.rooms.values()):
            if player_id in room.members:
                room.settle_kill()

    def subscribe(self, sess, topic):
        sid = sess.sub_for(topic)
        if sid is None:
            self.next_sub += 1
            sid = self.next_sub
            sess.subs[sid] = topic
        return sid

    def unsubscribe(self, sess, topic):
        sid = sess.sub_for(topic)
        if sid is not None:
            sess.subs.pop(sid, None)
        return sid

    async def emit(self, topic, kw, var=None, exclude=None, eligible=None):
        """Publica un EVENT a quien este suscrito al tema."""
        if self.deferred is not None:
            snap = json.loads(json.dumps(var)) if var is not None else None
            self.deferred.append((topic, kw, snap, exclude, eligible))
            return
        self.next_pub += 1
        details = {"var": var} if var is not None else {}
        for s in list(self.sessions):
            if s is exclude or (eligible is not None and s.player_id not in eligible):
                continue
            sid = s.sub_for(topic)
            if sid is not None:
                await s.send([EVENT, sid, self.next_pub, details, [], kw])

    # ---------------- bucle de una conexion
    async def run(self, ws):
        sess = Session(self, ws)
        self.sessions.add(sess)
        try:
            async for msg in ws:
                if msg.type.name not in ("BINARY", "TEXT"):
                    continue
                raw = msg.data if isinstance(msg.data, (bytes, bytearray)) else msg.data.encode()
                try:
                    data = json.loads(cscrypto.decrypt(raw, "upstream"))
                except Exception as e:  # noqa: BLE001
                    log.warning("WS trama ilegible: %s", e)
                    continue
                log.debug("WS <- %s %s", sess.player_id, json.dumps(data, ensure_ascii=False)[:400])
                if not (len(data) > 5 and isinstance(data[5], dict) and data[5].get("tag") == "cursor"):
                    full_log("<-", sess.player_id, json.dumps(data, ensure_ascii=False))
                try:
                    await self.dispatch(sess, data)
                except Exception:  # noqa: BLE001
                    log.exception("Error procesando %s", str(data)[:300])
        finally:
            self.sessions.discard(sess)
            if sess.room:
                await sess.room.leave(sess, disconnected=True)
            log.info("WS desconectado %s", sess.player_id)

    async def dispatch(self, sess, m):
        t = m[0]
        if t == HELLO:
            details = m[2] if len(m) > 2 else {}
            ssid = details.get("ssid", "")
            sess.player_id = self.api.s.sessions.get(ssid)
            if not sess.player_id:
                await sess.send([ABORT, {}, "wamp.error.not_authorized"])
                return
            sess.name = self.api.s.user(sess.player_id).get("name", "")
            log.info("WAMP sesion de %s (%s)", sess.name, sess.player_id)
            await sess.send([WELCOME, sess.id, {"roles": {"broker": {}, "dealer": {}}}])
        elif t == GOODBYE:
            if sess.room:
                await sess.room.leave(sess)
            await sess.send([GOODBYE, {}, "wamp.error.goodbye_and_out"])
        elif t == SUBSCRIBE:
            await sess.send([SUBSCRIBED, m[1], self.subscribe(sess, m[3])])
        elif t == UNSUBSCRIBE:
            sess.subs.pop(m[2], None)
            await sess.send([UNSUBSCRIBED, m[1]])
        elif t == CALL:
            req, proc = m[1], m[3]
            kw = m[5] if len(m) > 5 and isinstance(m[5], dict) else {}
            self.deferred = []
            try:
                res = await self.call(sess, proc, kw)
            finally:
                pending, self.deferred = self.deferred, None
            await sess.send([RESULT, req, {}, [], res])
            for args in pending:
                await self.emit(*args)
        elif t == PUBLISH:
            await self.publish(sess, m)
        else:
            log.info("WAMP mensaje no soportado %s", m[:3])

    async def publish(self, sess, m):
        opts = m[2] if len(m) > 2 and isinstance(m[2], dict) else {}
        topic = m[3]
        kw = m[5] if len(m) > 5 and isinstance(m[5], dict) else {}
        room = sess.room if sess.room and sess.room.topic == topic else None
        if room and isinstance(opts.get("var"), list):
            room.apply_var_ops(opts["var"])
        eligible = set(opts["eligible_authid"]) if opts.get("eligible_authid") else None
        if room and opts.get("eligible_authrole"):
            roles = set(opts["eligible_authrole"])
            ids = {p for p, mbr in room.members.items() if room.authrole(p) in roles}
            eligible = ids if eligible is None else eligible & ids
        if opts.get("exclude_authid"):
            base = eligible if eligible is not None else {s.player_id for s in self.sessions}
            eligible = base - set(opts["exclude_authid"])
        if room and opts.get("exclude_authrole"):
            roles = set(opts["exclude_authrole"])
            base = eligible if eligible is not None else {s.player_id for s in self.sessions}
            eligible = {p for p in base if room.authrole(p) not in roles}
        echo = room is not None and "Control" in kw
        await self.emit(topic, kw, var=room.vars if room else None, exclude=None if echo else sess, eligible=eligible)
        if room is not None and "tag" in kw:
            asyncio.ensure_future(room.on_player_message(sess, kw))
        call = opts.get("call")
        if isinstance(call, dict) and call.get("procedure"):
            self.deferred = []
            try:
                res = await self.call(sess, call["procedure"], call.get("parameters") or {})
            finally:
                pending, self.deferred = self.deferred, None
            await sess.send([RESULT, call.get("requestId", 0), {}, [], res])
            for args in pending:
                await self.emit(*args)

    # ---------------- procedimientos match.*
    async def call(self, sess, proc, p):
        name = proc.replace("match.", "", 1)
        fn = getattr(self, "p_" + name, None)
        room = sess.room
        if fn is None and room is not None:
            fn = getattr(room, "p_" + name, None)
            if fn is not None:
                res = await fn(sess, p)
                log.info("%-26s %s -> %s", proc, json.dumps(p, ensure_ascii=False)[:160], json.dumps(res, ensure_ascii=False)[:160])
                return res
        if fn is None:
            log.warning("PROCEDIMIENTO SIN IMPLEMENTAR %s %s", proc, json.dumps(p, ensure_ascii=False)[:300])
            return rc({})
        res = await fn(sess, p)
        log.info("%-26s %s -> %s", proc, json.dumps(p, ensure_ascii=False)[:160], json.dumps(res, ensure_ascii=False)[:160])
        return res

    async def p_ReserveRoom(self, sess, p):
        if sess.room:
            await sess.room.leave(sess)
        rid = self._new_room_id()
        room = Room(self, rid, owner=sess)
        self.rooms[rid] = room
        sid = room.join(sess)
        return rc({"id": rid, "subscribed": {room.topic: sid}})

    async def p_EnterRoom(self, sess, p):
        room = self.rooms.get(str(p.get("id", "")))
        if room is None:
            return rc({"not_found": True, "success": False})
        if not room.has_space() and sess.player_id not in room.members:
            return rc({"full": True, "success": False})
        if sess.room and sess.room is not room:
            await sess.room.leave(sess)
        sid = room.join(sess)
        res = room.settings_result()
        res.update({"success": True, "subscribed": {room.topic: sid}})
        await room.announce_enter(sess)
        return rc(res)

    async def p_LeaveRoom(self, sess, p):
        room = sess.room
        if room is None:
            return rc({})
        topic = room.topic
        sid = sess.sub_for(topic)
        await room.leave(sess)
        return rc({"unsubscribed": {topic: sid}} if sid is not None else {})

    def _new_room_id(self):
        while True:
            rid = f"{random.randint(0, 999999):06d}"
            if rid not in self.rooms:
                return rid

    def public_rooms(self):
        return [r for r in self.rooms.values() if not r.settings.get("private") and r.phase == "lobby"]


# ------------------------------------------------------------------ sala / partida
def same_order(a, b):
    """Dos ordenes que hacen lo mismo (Pawn.CheckInstructAllSame)."""
    keys = ("type", "grid", "targetId")
    return all(int(a.get(k, -1) if a.get(k) is not None else -1) == int(b.get(k, -1) if b.get(k) is not None else -1)
               for k in keys)


class Room:
    def __init__(self, hub, rid, owner):
        self.hub, self.id = hub, rid
        self.topic = f"crimesight.room.{rid}"
        self.owner = owner.player_id
        self.members = {}          # player_id -> {"name", "role"}
        self.sessions = {}         # player_id -> Session
        self.settings = {"capacity": 1, "private": True, "stage": "", "time_limit": 180, "max_turn": 10}
        self.vars = {"random_seed": random.randint(1, 2**31 - 1)}
        self.phase = "lobby"
        self.turn = 0
        self.killer = self.target = -1
        self.pawn_count = DEFAULT_PAWNS
        self.pending = {}          # fase -> {player_id: payload}
        self.reference = {}        # ultimo reference_data por jugador
        self.selections = {}
        self.countdown_task = None
        self.created = time.time()
        self.bot_seq = 0
        self.object_items = {}     # mueble (cottage id) -> objeto que contiene (se reparte al empezar)
        self.food_items, self.weapon_items = set(), set()
        self.searched = {}         # mueble (cottage id) -> objeto que salio
        self.drops = {}            # objeto en el suelo (cottage id) -> indice de objeto
        self.disabled_objects = set()
        self.bot_orders = {}
        self.last_view = None
        self.turn_ref = {}         # reference_data del inicio del turno (para IA y peligros)
        self.hazard_prob = {}      # "threat"/"gaspipe" -> probabilidad actual (se dobla en cada fallo)
        self.recorded = False      # resultado ya anotado en las estadisticas
        self.assault = False       # hubo orden de Asalto este turno
        self.open_seats = 0        # huecos que el anfitrion reserva para humanos (expulsando a una IA)
        self.bot_task = None

    # ---- miembros y variables
    def authrole(self, pid):
        role = self.members.get(pid, {}).get("role", ROLE_DETECTIVE)
        return "Criminal" if role in (ROLE_CRIMINAL, ROLE_IRENE) else "Detective"

    def has_space(self):
        """Un humano puede entrar si hay hueco libre o una IA a la que sustituir."""
        return len(self.humans()) < int(self.settings.get("capacity", 1))

    def shown_capacity(self):
        return int(self.settings.get("capacity", 1))

    # ---- jugadores IA (IA_1, IA_2...): ocupan los huecos libres para que la partida sea "normal"
    def bots(self):
        return [pid for pid, m in self.members.items() if m.get("bot")]

    def fill_bots(self):
        cap = int(self.settings.get("capacity", 1))
        self.open_seats = max(0, min(self.open_seats, cap - len(self.humans())))
        target = cap - self.open_seats
        while len(self.members) > target and self.bots():
            self.members.pop(self.bots()[-1])
        while len(self.members) < target:
            self.bot_seq += 1
            used = {m.get("slot") for m in self.members.values() if m.get("bot")}
            n = 1
            while n in used:
                n += 1
            diff = DEFAULT_AI_DIFFICULTY
            self.members[f"bot{self.bot_seq:04d}"] = {"name": ai.bot_name(n, diff, self.owner_lang()), "slot": n,
                                                       "difficulty": diff, "role": ROLE_RANDOM,
                                                       "match_count": 0, "bot": True, "ready": True}

    def owner_lang(self):
        """Idioma del juego del anfitrion (lo manda al iniciar sesion); los nombres de las IA lo usan."""
        try:
            return self.hub.api.s.user(self.owner).get("lang") if self.owner else None
        except Exception:  # noqa: BLE001
            return None

    def ordered_members(self):
        """Orden de los jugadores: anfitrion, resto de humanos y despues las IA."""
        pids = list(self.members)
        return sorted(pids, key=lambda p: (p != self.owner, bool(self.members[p].get("bot")), pids.index(p)))

    def member_index(self, pid):
        return self.ordered_members().index(pid)

    async def bot_say(self, tag, **extra):
        for pid in self.bots():
            kw = {"tag": tag, "id": self.member_index(pid)}
            kw.update(extra)
            await self.hub.emit(self.topic, kw, var=self.vars)

    async def on_player_message(self, sess, kw):
        """Las IA contestan a los mensajes de coordinacion que se mandan los clientes entre si."""
        tag = kw.get("tag")
        if not self.bots() or not tag:
            return
        if tag == "startInstruct":
            await asyncio.sleep(0.5)
            await self.bot_say("instruct", list=[])
        elif tag == "gameEndTimeUp":
            await self.bot_say("gameEndTimeUp")
        elif tag in ("instruct", "timeUp"):
            await self.bot_say("endWaitInstruct")

    async def _bot_heartbeat(self):
        """Durante la partida las IA confirman cada pocos segundos que estan listas."""
        try:
            while self.phase not in ("lobby", "ended") and self.hub.rooms.get(self.id) is self:
                if self.bots():
                    await self.bot_say("returnInstruct")
                    await self.bot_say("endWaitInstruct")
                await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass

    def join(self, sess):
        sess.room = self
        if sess.player_id not in self.members:
            if self.open_seats > 0:
                self.open_seats -= 1
            elif len(self.members) >= int(self.settings.get("capacity", 1)) and self.bots():
                self.members.pop(self.bots()[-1])   # el humano sustituye a una IA
        user = self.hub.api.s.user(sess.player_id)
        self.members.setdefault(sess.player_id, {"name": sess.name, "role": ROLE_RANDOM,
                                                  "match_count": int(user.get("match_count", 0))})
        self.sessions[sess.player_id] = sess
        self.refresh_vars()
        return self.hub.subscribe(sess, self.topic)

    async def leave(self, sess, disconnected=False):
        pid = sess.player_id
        if pid not in self.members:
            return
        name = self.members.pop(pid)["name"]
        self.sessions.pop(pid, None)
        self.hub.unsubscribe(sess, self.topic)
        if sess.room is self:
            sess.room = None
        if not self.humans():
            self.hub.rooms.pop(self.id, None)
            if self.bot_task:
                self.bot_task.cancel()
            log.info("Sala %s cerrada", self.id)
            return
        if self.owner == pid:
            self.owner = self.humans()[0]
        if self.phase == "lobby":
            self.fill_bots()
        self.refresh_vars()
        owner = self.members[self.owner]
        await self.control("Leave", {"PlayerId": pid, "PlayerName": name,
                                     "OwnerId": self.owner, "OwnerName": owner["name"]})
        if self.phase not in ("lobby", "ended"):
            await self.check_phase_complete()

    def refresh_vars(self):
        v = {k: val for k, val in self.vars.items() if not k.startswith(("player_", "role_", "ready_", "match_count_"))}
        for key, (var, typ) in SETTING_KEYS.items():
            if key in self.settings:
                v[var] = typ(self.settings[key])
        v["setting_capacity"] = self.shown_capacity()
        v["owner"] = self.owner
        v["attendance"] = len(self.members)
        v["detective_count"] = sum(1 for m in self.members.values() if m["role"] in (ROLE_DETECTIVE, ROLE_WATSON))
        v["criminal_count"] = sum(1 for m in self.members.values() if m["role"] in (ROLE_CRIMINAL, ROLE_IRENE))
        for pid in self.ordered_members():
            m = self.members[pid]
            v["player_" + pid] = m["name"]
            v["role_" + pid] = int(m["role"])
            v["ready_" + pid] = bool(m.get("ready", False))
            v["match_count_" + pid] = int(m.get("match_count", 0))
        self.vars = v

    def apply_var_ops(self, ops):
        for op in ops:
            for k, val in (op.get("set") or {}).items():
                if k.startswith("role_") and k[5:] in self.members:
                    self.members[k[5:]]["role"] = int(val)
                elif k.startswith("ready_") and k[6:] in self.members:
                    self.members[k[6:]]["ready"] = bool(val)
                else:
                    self.vars[k] = val
            for k in op.get("unset") or op.get("delete") or []:
                self.vars.pop(k, None)
        self.refresh_vars()

    async def control(self, cmd, data=None):
        await self.hub.emit(self.topic, {"Control": {cmd: data}}, var=self.vars)

    async def control_to(self, pids, cmd, data=None):
        """Como control(), pero solo para esos jugadores."""
        await self.hub.emit(self.topic, {"Control": {cmd: data}}, var=self.vars, eligible=set(pids))

    def humans(self):
        return [pid for pid in self.members if pid in self.sessions and not self.sessions[pid].ws.closed]

    def settings_result(self):
        keys = ["campaign_id", "stage", "capacity", "time_limit", "max_turn", "private", "quick", "specify_roles",
                "irene_count", "watson_count", "auto_start", "secret_passage", "switchboard_count",
                "wild_dog_count", "gaspipe_count", "fast_action", "attendance"]
        res = {k: self.settings[k] for k in keys if k in self.settings}
        res["attendance"] = len(self.members)
        res["capacity"] = self.shown_capacity()
        res["id"] = self.id
        return res

    async def announce_enter(self, sess):
        await self.control("Enter", {"PlayerId": sess.player_id, "PlayerName": sess.name, "RandomSeed": "random_seed"})

    # ---- procedimientos de sala
    async def p_CreateRoom(self, sess, p):
        for k, v in p.items():
            self.settings[k] = v
        self.settings.setdefault("campaign_id", 0)
        if not self.settings.get("stage"):
            self.settings["stage"] = random.choice(STAGES)
        self.settings.setdefault("time_limit", 180)
        self.settings.setdefault("max_turn", 10)
        self.fill_bots()
        if "killer" in p:
            self.killer = int(p["killer"])
        if "target" in p:
            self.target = int(p["target"])
        self.refresh_vars()
        await self.announce_enter(sess)
        return rc(self.settings_result())

    async def p_ChangeCapacity(self, sess, p):
        self.settings["capacity"] = max(len(self.humans()), min(4, int(p.get("capacity", self.settings["capacity"]))))
        self.open_seats = 0     # al cambiar el numero de jugadores, las IA vuelven a ocupar los huecos
        self.fill_bots()
        self.refresh_vars()
        await self.control("ChangeCapacity", None)
        return rc({"changed": True})

    async def p_ChangeSettings(self, sess, p):
        self.settings.update(p)
        self.refresh_vars()
        await self.control("ChangeSettings", None)
        return rc({})

    async def p_Kick(self, sess, p):
        pid = p.get("player_id")
        bot = self.members.get(pid, {})
        if sess.player_id == self.owner and bot.get("bot"):
            # Expulsar a una IA cambia su dificultad: Normal -> Dificil -> Facil -> hueco libre
            cycle = [DEFAULT_AI_DIFFICULTY] + [d for d in ai.DIFFICULTIES if d != DEFAULT_AI_DIFFICULTY]
            nxt = cycle.index(bot["difficulty"]) + 1 if bot.get("difficulty") in cycle else 0
            if nxt < len(cycle):
                bot["difficulty"] = cycle[nxt]
                bot["name"] = ai.bot_name(bot["slot"], bot["difficulty"], self.owner_lang())
                self.refresh_vars()
                await self.control("ChangeSettings", None)
                return rc({})
            name = self.members.pop(pid)["name"]
            self.open_seats += 1
            self.refresh_vars()
            await self.control("Leave", {"PlayerId": pid, "PlayerName": name, "OwnerId": self.owner,
                                         "OwnerName": self.members[self.owner]["name"]})
            return rc({})
        target = self.sessions.get(pid)
        if target and sess.player_id == self.owner:
            await self.control("Kick", {"PlayerId": target.player_id, "PlayerName": target.name, "Kicked": True})
            await self.leave(target)
        return rc({})

    async def p_SetRoles(self, sess, p):
        for pid, role in zip(p.get("player_ids", []), p.get("roles", [])):
            if pid in self.members:
                self.members[pid]["role"] = int(role)
        self.refresh_vars()
        await self.control("ChangeSettings", None)
        return rc({})

    async def p_StartCountDown(self, sess, p):
        for pid, role in zip(p.get("player_ids", []), p.get("roles", [])):
            if pid in self.members:
                self.members[pid]["role"] = int(role)
        self.static_data = p.get("static_data")
        self.assign_roles()
        self.refresh_vars()
        await self.control("StartCountDown", {"CountDownTimer": COUNTDOWN_SECONDS})
        self.countdown_task = asyncio.ensure_future(self._countdown())
        return rc({})

    async def p_CancelCountDown(self, sess, p):
        if self.countdown_task:
            self.countdown_task.cancel()
        await self.control("CancelCountDown", None)
        return rc({})

    async def _countdown(self):
        await asyncio.sleep(COUNTDOWN_SECONDS)
        self.phase = "starting"
        self.turn = 0
        self.pending.clear()
        for m in self.members.values():
            m["ready"] = False
        self.refresh_vars()
        self.match_id = f"{self.id}-{int(time.time())}-{secrets.token_hex(3)}"
        log.info("Sala %s: empieza la partida (asesino %s, victima %s, roles %s)", self.id, self.killer, self.target,
                 {m["name"]: m["role"] for m in self.members.values()})
        await self.control("StartMatch", None)
        if self.bots():
            self.bot_task = asyncio.ensure_future(self._bot_heartbeat())

    def assign_roles(self):
        """Reparte los roles con las plazas de la partida: 1 Moriarty, las Irene/Watson que pida la
        sala y el resto Sherlock. Se respeta lo que eligio cada uno; si mas gente pide un papel del
        que hay plazas, se sortea entre ellos (las personas antes que la IA) y a los que se quedan
        fuera, como a los "aleatorio", les toca al azar una de las plazas que quedan."""
        everyone = list(self.members)
        irene = int(self.settings.get("irene_count", 0) or 0)
        watson = int(self.settings.get("watson_count", 0) or 0)
        slots = {ROLE_CRIMINAL: 1, ROLE_IRENE: irene, ROLE_WATSON: watson,
                 ROLE_DETECTIVE: max(1, len(everyone) - 1 - irene - watson)}
        wanted = {pid: self.members[pid]["role"] for pid in everyone}
        for pid in everyone:
            self.members[pid]["role"] = ROLE_RANDOM
        for role in (ROLE_CRIMINAL, ROLE_IRENE, ROLE_WATSON, ROLE_DETECTIVE):
            asking = [pid for pid in everyone if wanted[pid] == role]
            random.shuffle(asking)
            asking.sort(key=lambda pid: bool(self.members[pid].get("bot")))   # personas primero
            for pid in asking[:slots[role]]:
                self.members[pid]["role"] = role
                slots[role] -= 1
        rest = [pid for pid in everyone if self.members[pid]["role"] == ROLE_RANDOM]
        random.shuffle(rest)
        rest.sort(key=lambda pid: bool(self.members[pid].get("bot")))
        for pid in rest:
            pool = [r for r, n in slots.items() for _ in range(n)]
            role = random.choice(pool) if pool else ROLE_DETECTIVE
            self.members[pid]["role"] = role
            if pool:
                slots[role] -= 1
        if self.killer < 0 or self.target < 0 or self.killer == self.target:
            self.killer, self.target = random.sample(range(self.pawn_count), 2)

    def players_by_role(self, roles):
        return [pid for pid, m in self.members.items() if m["role"] in roles]

    async def p_GetRole(self, sess, p):
        m = self.members.get(sess.player_id, {})
        role = m.get("role", ROLE_DETECTIVE)
        res = {"role": role, "killer": -1, "target": -1}
        if role in (ROLE_CRIMINAL, ROLE_IRENE):
            res.update({"killer": self.killer, "target": self.target})
        crim = self.players_by_role([ROLE_CRIMINAL])
        ire = self.players_by_role([ROLE_IRENE])
        if crim:
            res.update({"criminal_id": crim[0], "criminal_name": self.members[crim[0]]["name"]})
        if ire:
            res.update({"irene_id": ire[0], "irene_name": self.members[ire[0]]["name"]})
        return rc(res)

    async def p_PrepareMatchData(self, sess, p):
        """Cada cliente manda los datos de su escenario; cuando estan todos, RoleData arranca la partida."""
        ad = p.get("additional_data")
        if isinstance(ad, str):
            try:
                ad = json.loads(ad)
            except ValueError:
                ad = {}
        self.match_data = ad or {}
        if self.phase != "playing" and not self.pending.get("prepare"):
            self.hazard_prob = {}
        if not self.object_items and not self.searched:
            self.deal_items()
        self.pending.setdefault("prepare", {})[sess.player_id] = True
        if self._complete("prepare"):
            self.pending.pop("prepare", None)
            self.phase = "playing"
            # Cada jugador recibe lo que sabe su papel (GameManager.SelectOpenWeapon/SelectOpenFood)
            for pid in self.humans():
                await self.control_to([pid], "RoleData", self.role_data(pid))
        return rc({})

    def deal_items(self):
        """Reparte los objetos de la partida entre los muebles, como el servidor original.
        Los indices siguen ItemManager.CreateMatchItemList en linea: primero la comida, luego
        las armas y despues el resto (pizarras, bocetos, notas, pociones, sprays). Hay un mueble
        por objeto (MatchSettings.GetNeedSearchObjectCount)."""
        md = self.match_data or {}
        n = int(md.get("matchItemCount", 42) or 42)
        food = int(md.get("foodCount", 17) or 0)
        weapons = int(md.get("weaponCount", 15) or 0)
        items = list(range(n))
        random.shuffle(items)
        self.object_items = dict(enumerate(items))
        self.food_items = set(range(food))
        self.weapon_items = set(range(food, food + weapons))
        log.info("Sala %s: %s objetos repartidos (%s comida, %s armas)", self.id, n, food, weapons)

    def objects_with(self, items):
        """Muebles aun sin registrar que contienen alguno de esos objetos."""
        return sorted(o for o, i in self.object_items.items() if i in items and o not in self.searched)

    def role_data(self, pid):
        """Lo que sabe cada papel al empezar: Moriarty, todas las armas y toda la comida; los demas,
        ninguna arma y solo unos pocos sitios con comida (MatchSettings.foodOpenCount)."""
        foods = self.objects_with(self.food_items)
        if self.members.get(pid, {}).get("role") != ROLE_CRIMINAL:
            foods = sorted(random.sample(foods, min(FOOD_OPEN_COUNT, len(foods))))
            return {"weaponList": [], "foodList": foods}
        return {"weaponList": self.objects_with(self.weapon_items), "foodList": foods}

    # ---- fases de turno
    def _store(self, phase, sess, p):
        self.pending.setdefault(phase, {})[sess.player_id] = p
        ref = p.get("reference_data")
        if isinstance(ref, str):
            try:
                ref = json.loads(ref)
            except ValueError:
                ref = None
        res = p.get("resumption_data")
        if isinstance(res, str) and res:
            try:
                res = json.loads(res)
            except ValueError:
                res = None
        if isinstance(res, dict):
            for d in res.get("spawnDropItems") or []:
                if isinstance(d, dict) and "id" in d and "itemId" in d:
                    self.drops[int(d["id"])] = int(d["itemId"])
            for d in res.get("disableSearchObjects") or []:
                if isinstance(d, dict) and "id" in d:
                    self.disabled_objects.add(int(d["id"]))
            for d in res.get("pickDropItems") or []:
                if isinstance(d, dict) and "id" in d:
                    self.drops.pop(int(d["id"]), None)
        if isinstance(ref, dict):
            self.reference[sess.player_id] = ref
            if isinstance(ref.get("pawns"), list) and ref["pawns"]:
                self.pawn_count = len(ref["pawns"])

    def _complete(self, phase):
        got = self.pending.get(phase, {})
        who = self.humans()
        if phase == "answer":  # solo acusan los del bando de Sherlock
            who = [p for p in who if self.members[p]["role"] in (ROLE_DETECTIVE, ROLE_WATSON)]
        return all(pid in got for pid in who)

    def detect_kill(self, ref):
        """GameManager.CheckKill del cliente: asesino armado en la casilla de la victima y ningun
        testigo despierto en la habitacion. Con apagon solo ve quien esta en una habitacion con luz
        o en la misma casilla. Algunas amenazas tambien cuentan como testigo."""
        pawns = {int(p["pawnId"]): p for p in ref.get("pawns", []) if isinstance(p, dict) and "pawnId" in p}
        k, t = pawns.get(self.killer), pawns.get(self.target)
        if not k or not t or not k.get("isHaveWeapon") or k.get("gridId") != t.get("gridId"):
            return False
        room, grid = t.get("roomId"), t.get("gridId")
        dark = bool(int(ref.get("isBlack", 0) or 0)) and not t.get("isNoBlack")
        for q, p in pawns.items():
            if q in (self.killer, self.target) or p.get("roomId") != room or p.get("isBlind"):
                continue
            if not dark or p.get("gridId") == grid:
                return False
        for x in ref.get("threatList") or []:
            if isinstance(x, dict) and x.get("isWitness") and not x.get("isDie") and x.get("roomId") == room:
                if not dark or x.get("gridId") == grid:
                    return False
        return True

    async def end_by_kill(self):
        log.info("Sala %s turno %s: la victima ha muerto", self.id, self.turn)
        self.phase = "ended"

        def first(role):
            p = self.players_by_role([role])
            return (p[0], self.members[p[0]]["name"]) if p else ("", "")
        det, cri, ire, wat = (first(r) for r in (ROLE_DETECTIVE, ROLE_CRIMINAL, ROLE_IRENE, ROLE_WATSON))
        await self.control("StartResultPhase", {"Data": {
            "isKill": True, "killer": self.killer, "target": self.target,
            "detective_player": det[0], "detective_name": det[1], "criminal_player": cri[0], "criminal_name": cri[1],
            "irene_player": ire[0], "irene_name": ire[1], "watson_player": wat[0], "watson_name": wat[1]}})
        self.conclude("moriarty", {ROLE_CRIMINAL: ["ctg_name_result_action_targetKilledByAssail"] if self.assault else []})

    def settle_kill(self):
        """Compatibilidad: el asesinato ya se anota en el momento."""

    async def p_SetCommandPhase(self, sess, p):
        self.phase = "command"
        self._store("command", sess, p)
        await self.check_phase_complete()
        return rc({})

    async def p_SetActionPhase(self, sess, p):
        self._store("action", sess, p)
        await self.control("SetActionPhase", {"Ready": len(self.pending["action"]), "Playing": len(self.humans())})
        await self.check_phase_complete()
        return rc({})

    async def p_SetTurnEnd(self, sess, p):
        self._store("turnend", sess, p)
        await self.control("SetTurnEnd", {"Ready": len(self.pending["turnend"]), "Playing": len(self.humans())})
        await self.check_phase_complete()
        return rc({})

    async def check_phase_complete(self):
        if "command" in self.pending and self._complete("command"):
            self.pending.pop("command")
            ref = next(iter(self.reference.values()), {})
            self.turn = int(ref.get("turn", self.turn + 1)) if isinstance(ref, dict) else self.turn + 1
            self.vars["random_seed"] = random.randint(1, 2**31 - 1)
            self.turn_ref = ref if isinstance(ref, dict) else {}
            self.plan_bots(self.turn_ref)
            await self.control("StartCommandPhase", {"Turn": self.turn, "Data": {}, "RandomSeed": "random_seed"})
        if "action" in self.pending and self._complete("action"):
            data = self.build_action_data(self.pending.pop("action"))
            await self.control("StartActionPhase", {"Turn": self.turn, "Data": data})
        if "turnend" in self.pending and self._complete("turnend"):
            self.pending.pop("turnend")
            ref = next(iter(self.reference.values()), {})
            ref = ref if isinstance(ref, dict) else {}
            if self.detect_kill(ref):
                # En linea el servidor decide el asesinato (el cliente no lo comprueba por su cuenta)
                await self.end_by_kill()
            else:
                await self.control("StartTransitionPhase", {"Turn": self.turn, "Data": {"isDanger": self.is_danger()}})
                if int(ref.get("isLastTurn", 0) or 0):
                    # Era el turno final tras descubrirse al asesino (Asalto fallido o deduccion) y la
                    # victima sigue viva: el cliente muestra la detencion, gana el bando de Sherlock.
                    log.info("Sala %s turno %s: fin del turno final sin asesinato, detenido el asesino", self.id, self.turn)
                    self.phase = "ended"
                    self.conclude("sherlock", {ROLE_DETECTIVE: ["ctg_name_result_pattern_arrest_success"]})
        if "answer" in self.pending and self._complete("answer"):
            await self.finish_answers()

    def plan_bots(self, ref):
        """La IA decide sus ordenes con el estado del turno que manda el cliente."""
        self.bot_orders = {}
        bots = self.bots()
        if not bots or not ref.get("pawns"):
            return
        gone = set(self.searched) | self.disabled_objects
        views = {"moriarty": ai.View(ref, gone), "sherlock": ai.View(ref, gone)}   # cada bando, lo suyo
        views["moriarty"].weapon_objects = set(self.objects_with(self.weapon_items))
        self.last_view = view = views["sherlock"]
        rng = random.Random()
        det_players = self.players_by_role([ROLE_DETECTIVE])
        cri_players = self.players_by_role([ROLE_CRIMINAL])
        # Cada bando solo sabe que personajes ha ordenado su propio equipo
        taken = {"sherlock": set(), "moriarty": set()}
        prio = {ROLE_CRIMINAL: 0, ROLE_IRENE: 1, ROLE_DETECTIVE: 2, ROLE_WATSON: 3}
        for pid in sorted(bots, key=lambda b: prio.get(self.members[b]["role"], 9)):
            m = self.members[pid]
            idx = self.member_index(pid)
            role, diff = m["role"], m["difficulty"]
            team = "moriarty" if role in (ROLE_CRIMINAL, ROLE_IRENE) else "sherlock"
            if role == ROLE_CRIMINAL:
                n = max(1, 2 // max(1, len(cri_players)))
                orders, _ = ai.plan_moriarty(views[team], idx, self.killer, self.target, n, diff, rng, taken[team])
            elif role == ROLE_IRENE:
                orders = ai.plan_irene(views[team], idx, self.killer, self.target, diff, rng, taken[team])
            elif role == ROLE_DETECTIVE:
                n = max(1, 3 // max(1, len(det_players)))
                orders = ai.plan_sherlock(views[team], idx, n, diff, rng, taken[team])
            elif role == ROLE_WATSON:
                orders = ai.plan_watson(views[team], idx, diff, rng, taken[team])
            else:
                orders = []
            taken[team] |= {o["pawnId"] for o in orders}
            self.bot_orders[pid] = orders
            log.info("Sala %s turno %s: %s (%s, %s) -> %s", self.id, view.turn, m["name"], m["role"],
                     m["difficulty"], [(o["pawnId"], o["type"], o["grid"], o["targetId"]) for o in orders])

    def build_action_data(self, payloads):
        """Junta las ordenes de todos. Si varios ordenan al mismo personaje: Moriarty gana a todos,
        Irene a Sherlock/Watson y entre los demas se sortea. Si Moriarty pisa una orden distinta de
        Sherlock/Watson, la orden va marcada (isBatting) y el bando de Sherlock lo detecta.
        Los personajes que nadie ha ordenado actuan por su cuenta (en linea lo decide el servidor)."""
        by_pawn, from_criminal, from_detective, kill = {}, set(), {}, False
        criminals = set(self.players_by_role([ROLE_CRIMINAL]))
        payloads = dict(payloads)
        for bot, orders in (getattr(self, "bot_orders", None) or {}).items():
            if orders:
                payloads[bot] = {"payload": {"list": orders}}
        self.bot_orders = {}
        rank = {ROLE_IRENE: 1, ROLE_CRIMINAL: 2}
        order = list(payloads)
        random.shuffle(order)
        for pid in sorted(order, key=lambda x: rank.get(self.members.get(x, {}).get("role"), 0)):
            role = self.members.get(pid, {}).get("role")
            pl = payloads[pid].get("payload")
            if isinstance(pl, str):
                try:
                    pl = json.loads(pl)
                except ValueError:
                    pl = {}
            for item in (pl or {}).get("list", []) or []:
                if not isinstance(item, dict) or "pawnId" not in item:
                    continue
                pawn = int(item["pawnId"])
                by_pawn[pawn] = item
                if role in (ROLE_DETECTIVE, ROLE_WATSON):
                    from_detective.setdefault(pawn, item)
                if pid in criminals:
                    from_criminal.add(pawn)
                    if int(item.get("type", 0)) == INSTRUCT_TARGET:
                        kill = True
        commands = []
        for k in sorted(by_pawn):
            c = self.resolve_item(by_pawn[k])
            det = from_detective.get(k)
            c["isBatting"] = bool(k in from_criminal and det is not None and not same_order(det, by_pawn[k]))
            if c["isBatting"]:
                log.info("Sala %s turno %s: Moriarty pisa la orden de Sherlock sobre %s", self.id, self.turn, k)
            commands.append(c)
        commands += self.npc_orders(by_pawn)
        threat_i, gas_i = self.roll_hazard("threat"), self.roll_hazard("gaspipe")
        self.assault = kill
        data = {}
        for role, key in ROLE_KEY.items():
            view = []
            for c in commands:
                c2 = dict(c)
                if role == ROLE_CRIMINAL:
                    c2["isMoriarty"] = int(c["pawnId"]) in from_criminal
                view.append(c2)
            d = {"commandList": view, "threatIndex": threat_i, "gaspipeIndex": gas_i, "isKillInstruct": kill}
            if kill:
                d.update({"killer": self.killer, "target": self.target})
            data[key] = d
        return data

    def npc_orders(self, by_pawn):
        """Pawn.RunNpcAction: quien no recibe ordenes registra algo cercano o da un paseo."""
        ref = self.turn_ref or {}
        if not ref.get("pawns"):
            return []
        busy = {int(c.get("targetId", -1)) for c in by_pawn.values() if int(c.get("type", 0)) == INSTRUCT_SEARCH}
        view = ai.View(ref, set(self.searched) | self.disabled_objects | busy)
        rng, out = random.Random(), []
        for pid in view.ids():
            if pid in by_pawn or pid >= self.pawn_count:
                continue
            o = ai.npc_order(view, pid, rng)
            if o:
                out.append(dict(self.resolve_item(o), isBatting=False))
        if out:
            log.info("Sala %s turno %s: actuan por su cuenta %s", self.id, self.turn,
                     [(o["pawnId"], o["type"], o["grid"], o["targetId"]) for o in out])
        return out

    def roll_hazard(self, kind):
        """Aparicion de perros/amenazas y escapes de gas, con las mismas reglas que el cliente offline:
        entre el turno inicial y final, mientras no se haya llegado al maximo de la sala, se tira un
        dado contra una probabilidad que empieza baja y se dobla cada vez que falla."""
        md, ref = self.match_data or {}, self.turn_ref or {}
        turn = int(ref.get("turn", self.turn) or self.turn)
        if kind == "threat":
            start = int(md.get("threatSpawnStartTurn", 5)); end = int(md.get("threatSpawnEndTurn", 8))
            base = int(md.get("threatSpawnProb", 6)); maxc = int(self.settings.get("wild_dog_count", 2) or 0)
            locates = int(ref.get("threatLocateCount", 0) or 0)
            active = [t for t in ref.get("threatList") or [] if isinstance(t, dict)]
            alive = [t for t in active if not t.get("isDie")]
        else:
            start = int(md.get("gaspipeSpawnStartTurn", 4)); end = int(md.get("gaspipeSpawnEndTurn", 8))
            base = int(md.get("gaspipeSpawnProb", 6)); maxc = int(self.settings.get("gaspipe_count", 1) or 0)
            locates = int(ref.get("gaspipeLocateCount", 0) or 0)
            active = alive = [g for g in ref.get("gaspipeList") or [] if isinstance(g, dict)]
        if not (start <= turn <= end) or maxc <= 0 or locates < maxc or len(alive) >= maxc:
            return -1
        if turn == start or kind not in self.hazard_prob:
            self.hazard_prob[kind] = base
        if random.randrange(100) >= self.hazard_prob[kind]:
            self.hazard_prob[kind] *= 2
            return -1
        self.hazard_prob[kind] = base
        used = {int(x.get("spawnLocateIndex", -1)) for x in active}
        free = [i for i in range(locates) if i not in used] or list(range(locates))
        idx = random.choice(free)
        log.info("Sala %s turno %s: aparece %s en el punto %s", self.id, turn,
                 "una amenaza" if kind == "threat" else "un escape de gas", idx)
        return idx

    def resolve_item(self, c):
        """Buscar/recoger: el servidor dice que objeto obtiene el personaje (igual para todos)."""
        c = dict(c)
        kind = int(c.get("type", 0))
        target = int(c.get("targetId", -1))
        if kind == INSTRUCT_SEARCH and target >= 0:
            if target not in self.searched:
                self.searched[target] = self.object_items.get(target, -1)
                log.info("Sala %s: mueble %s -> objeto %s (%s)", self.id, target, self.searched[target],
                         "arma" if self.searched[target] in self.weapon_items else
                         "comida" if self.searched[target] in self.food_items else "otro")
                c["itemId"] = self.searched[target]
            else:
                c["itemId"] = -1   # ya registrado: no queda nada
        elif kind == INSTRUCT_PICK and target >= 0:
            c["itemId"] = self.drops.pop(target, -1)
        return c

    def is_danger(self):
        """Pista nocturna: asesino y victima a 3 casillas o menos (dato que calcula el propio cliente)."""
        for ref in self.reference.values():
            for pawn in ref.get("pawns", []) if isinstance(ref, dict) else []:
                if int(pawn.get("pawnId", -1)) != self.killer:
                    continue
                for other in pawn.get("pawnList", []) or []:
                    if int(other.get("pawnId", -1)) == self.target:
                        return int(other.get("distance", 99)) <= 3
        return False

    async def p_SetSelectionPhase(self, sess, p):
        if self.phase != "selection":
            self.phase = "selection"
            self.pending["answer"] = {}
            await self.control("StartSelectionPhase", {"CountDownTimer": SELECTION_SECONDS})
            if not any(self.members[x]["role"] in (ROLE_DETECTIVE, ROLE_WATSON) for x in self.humans()):
                # Sherlock lo lleva la IA: "piensa" unos segundos y acusa
                self.selection_task = asyncio.ensure_future(self._ai_answer())
            else:
                self.selection_task = asyncio.ensure_future(self._selection_timeout())
        return rc({})

    async def _ai_answer(self):
        await asyncio.sleep(4)
        if self.phase == "selection":
            await self.finish_answers()

    async def _selection_timeout(self):
        await asyncio.sleep(SELECTION_SECONDS + 5)
        if self.phase == "selection" and "answer" in self.pending:
            log.info("Sala %s: fin del tiempo de deduccion", self.id)
            await self.finish_answers()

    async def p_SetAnswerPhase(self, sess, p):
        self.pending.setdefault("answer", {})[sess.player_id] = int(p.get("killer", -1))
        await self.control("SelectionData", {"Data": {"player_id": sess.player_id, "killer": int(p.get("killer", -1)),
                                                      "ready": len(self.pending["answer"])}})
        await self.check_phase_complete()
        return rc({})

    async def finish_answers(self):
        if self.phase == "ended":
            return
        task = getattr(self, "selection_task", None)
        if task and task is not asyncio.current_task():
            task.cancel()
        answers = self.pending.pop("answer", {})
        selections = [{"player_id": pid, "killer": k} for pid, k in answers.items()
                      if self.members.get(pid, {}).get("role") in (ROLE_DETECTIVE, ROLE_WATSON)]
        # Los Sherlock/Watson IA acusan segun su dificultad
        for bot in self.bots():
            m = self.members[bot]
            if m["role"] in (ROLE_DETECTIVE, ROLE_WATSON):
                guess = ai.accuse(self.last_view, self.killer, m["difficulty"], random.Random(), self.pawn_count)
                selections.append({"player_id": bot, "killer": guess})

        def ids(roles):
            p = self.players_by_role(roles)
            return p, [self.members[x]["name"] for x in p]

        det_ids, det_names = ids([ROLE_DETECTIVE])
        cri_ids, cri_names = ids([ROLE_CRIMINAL])
        ire_ids, ire_names = ids([ROLE_IRENE])
        wat_ids, wat_names = ids([ROLE_WATSON])
        self.phase = "ended"
        await self.control("StartAnswerPhase", {"Data": {
            "complete": True, "killer": self.killer, "target": self.target, "selections": selections,
            "detective_ids": det_ids, "detective_names": det_names, "criminal_ids": cri_ids,
            "criminal_names": cri_names, "irene_ids": ire_ids, "irene_names": ire_names,
            "watson_ids": wat_ids, "watson_names": wat_names}})
        self.record_result(selections)

    def record_result(self, selections):
        """Fin por deduccion: si Sherlock acierta gana su bando; si no, empate (no hubo asesinato)."""
        right = [s["player_id"] for s in selections if s["killer"] == self.killer
                 and self.members.get(s["player_id"], {}).get("role") == ROLE_DETECTIVE]
        extra = {pid: ["ctg_name_result_pattern_arrest_success"] for pid in right}
        self.conclude("sherlock" if right else "draw", extra)

    def conclude(self, winner, extra=None, quitter=None):
        """winner: "sherlock", "moriarty" o "draw". extra: acciones con puntos, por rol o por jugador."""
        if self.recorded:
            return
        self.recorded = True
        extra = extra or {}
        for pid, m in self.members.items():
            if m.get("bot"):
                continue
            role = int(m["role"])
            side = "sherlock" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "moriarty"
            outcome = "draw" if winner == "draw" else ("win" if side == winner else "lose")
            if pid == quitter:
                outcome = "abandon"
            acts = list(extra.get(role, [])) + list(extra.get(pid, []))
            u = self.hub.api.s.user(pid)
            pts = stats.record_match(u, role, outcome, acts, self.settings.get("stage", ""),
                                     match_id=getattr(self, "match_id", None))
            log.info("Sala %s: %s (%s) %s, +%s puntos -> %s", self.id, m["name"], ROLE_KEY.get(role, role),
                     {"win": "GANA", "lose": "PIERDE", "draw": "EMPATA", "abandon": "ABANDONA"}[outcome],
                     pts, stats.summary(u))
        self.hub.api.s.save()

    async def p_Sync(self, sess, p):
        await self.control("Sync", {"Data": p.get("payload") if isinstance(p.get("payload"), dict) else {}})
        return rc({})

    async def p_Abandon(self, sess, p):
        self.phase = "ended"
        role = self.members.get(sess.player_id, {}).get("role")
        self.conclude("moriarty" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "sherlock", quitter=sess.player_id)
        crim = self.players_by_role([ROLE_CRIMINAL])
        det = self.players_by_role([ROLE_DETECTIVE])
        await self.control("Abandon", {"Data": {
            "killer": self.killer, "target": self.target,
            "criminal_player": crim[0] if crim else "", "criminal_name": self.members[crim[0]]["name"] if crim else "",
            "detective_player": det[0] if det else "", "detective_name": self.members[det[0]]["name"] if det else ""}})
        return rc({})

    async def p_Rematch(self, sess, p):
        self.phase = "lobby"
        self.killer = self.target = -1
        self.object_items, self.searched, self.drops = {}, {}, {}
        self.disabled_objects = set()
        self.recorded, self.hazard_prob = False, {}
        self.vars["random_seed"] = random.randint(1, 2**31 - 1)
        await self.control("Rematch", {"RandomSeed": "random_seed"})
        return rc({})

    async def p_PingLog(self, sess, p):
        return rc({})

    async def p_StampLog(self, sess, p):
        return rc({})
