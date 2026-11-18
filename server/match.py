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
import matchlog
import profiles
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
# Pawn.InstructData.InstructType
INSTRUCT_ATTACK, INSTRUCT_POTION, INSTRUCT_SPRAY, INSTRUCT_REPAIR = 4, 6, 9, 11
# Acciones con puntos (textos del propio juego, ver stats.ACTIONS)
ACT_REPAIR = "ctg_name_result_repair_switchboard"
ACT_TREAT = "ctg_name_result_action_treated_pawnForInjuries"
ACT_FOILED = "ctg_name_result_arrest_succeed"
ACT_SPRAY_KILLER = "ctg_name_result_apply_tearSpray_to_killer"
ACT_DEDUCED = "ctg_name_result_identified_killer_by_deduction"
ACT_ASSAIL_KILL = "ctg_name_result_action_targetKilledByAssail"
ACT_BLACKOUT = "ctg_name_result_blackOut_by_switchboard"
ACT_SPRAY_OTHER = "ctg_name_result_action_blockedSherlockWithSpray"
ACT_KNOCKOUT = "ctg_name_result_action_beCriticalNoKiller"
DEFAULT_PAWNS = 6            # personajes por partida (la mansion tiene 6 sospechosos)
COUNTDOWN_SECONDS = 3
DEFAULT_AI_DIFFICULTY = "normal"   # se puede cambiar con --ai-difficulty
STAGES = ["Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060"]
# Escenarios que anade el plugin de BepInEx (no salen en "Random"). El plugin carga el escenario real.
EXTRA_STAGES = ["Stage_Yokn_CSRTest"]
CUSTOM_STAGE_PREFIX = "Stage_CSR_"      # escenarios hechos con el creador de escenarios (uno por nombre)
# Mientras a un jugador le falta el escenario personalizado elegido, su nombre lo dice en la sala
# (en el idioma del anfitrion): (su lanzador se lo esta bajando, no lo tiene ni lo va a tener)
STAGE_WAIT = {
    "ES": ("cargando escenario…", "sin el escenario"),
    "EN": ("loading stage…", "stage missing"),
    "FR": ("chargement de la carte…", "carte manquante"),
    "IT": ("caricamento mappa…", "mappa mancante"),
    "DE": ("Karte wird geladen…", "Karte fehlt"),
    "PT": ("carregando cenário…", "sem o cenário"),
    "RU": ("загрузка карты…", "нет карты"),
    "JP": ("ステージ読み込み中…", "ステージなし"),
    "KO": ("스테이지 로딩 중…", "스테이지 없음"),
    "CN": ("正在加载场景…", "缺少场景"),
    "TW": ("正在載入場景…", "缺少場景"),
}

# Stickers gratuitos del juego con los que contestan las IA: (tipo, posicion en la lista, texto del registro).
# Sin los de sospecha (un sticker de una IA no debe parecer una pista) ni los de pago.
BOT_STAMPS = [(28, 0, "hello"), (8, 1, "goodJob"), (37, 2, "justMoment"), (29, 3, "smirk"), (1, 8, "why"),
              (31, 10, "worried"), (2, 11, "noWay"), (4, 12, "relieved"), (5, 13, "frightened"), (32, 14, "scream"),
              (34, 15, "please"), (0, 16, "roger")]
BOT_STAMP_CHANCE = 0.7          # probabilidad de que alguna IA conteste a un sticker
BOT_STAMP_QUIET = 2.5           # segundos sin contestar despues de hacerlo (para no llenar la pantalla)
ROOM_STAMP_ROW = 92.5           # en la sala, lo que baja el sticker por cada fila de la lista de jugadores

# Pings con los que un jugador dice "este personaje lo llevo yo": la IA de su bando lo deja y contesta
# "Entendido" (Pawn/Move/Search y los mismos de Irene, que solo ve Moriarty; Irene4 = "aqui tienes a tu asesino").
CLAIM_PINGS = {1, 4, 7, 26, 27, 28, 30}
# Pings automaticos al dar una orden ("X ordena a Y..."): la IA tambien deja ese personaje, sin contestar.
ORDER_PINGS = set(range(13, 26)) | {31}
ROGER_STAMP = (0, 16, "roger")
# Partidas en solitario (una sola persona contra IAs) con Irene o Watson: ayudas para el papel de apoyo
IRENE_PICK_PINGS = {27, 28, 29}   # pings de Irene sobre un personaje ("Aqui tienes a tu asesino!", mover,
                                  # registrar): Moriarty IA lo movera este turno
IRENE_PLACE_PINGS = {26, 27, 28, 30}   # despues, un ping de Irene en el suelo: a donde lo lleva
IRENE_KILLER_STAMP = 38         # el sticker de Irene "Aqui tienes a tu asesino!" (es un sticker, no un ping)
IRENE_MAX_PICKS = 2
# Watson: "Sospecho que es el asesino" (ping 9 o su sticker) o "Peligro" (ping 2) sobre alguien -> Sherlock IA
# lo vigila y al final lo acusa; "No creo que sea el asesino" (ping 10 o su sticker) -> lo olvida. Watson casi
# nunca tiene los pings de sospecha a mano: lo normal es usar los stickers (Stamp.Type 25/24) o "Peligro".
WATSON_SUSPECT_PINGS, WATSON_CLEAR_PINGS = {9, 2}, {10}
WATSON_SUSPECT_STAMPS, WATSON_CLEAR_STAMPS = {25}, {24}   # KILLER_SUSPICION / KILLER_NOSUSPICION
# Durante la partida la sala pasa de "playing" a "command" con la primera orden y ahi se queda: antes
# solo se miraba "playing" y, desde el primer turno, las IAs dejaban de atender a los pings (ordenes de
# Irene, sospechas de Watson, "lo llevo yo") y de avisar de sus personajes.
IN_MATCH = ("playing", "command")
GHOST_CRIMINAL = "csr-moriarty"   # Moriarty IA de las salas de entrenamiento (no es un jugador de la sala)  # Watson: "Sospecho que es el asesino" / "No creo que sea el asesino"
# El juego deja elegir "Random" como escenario y manda ese nombre tal cual: el servidor oficial lo
# cambiaba por uno real al empezar. Si le llega "Random", el juego intenta cargar una escena que no
# existe y se queda en negro.
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
        self.remote = ""

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

    async def stage_poll(self):
        """Avisa a las salas donde ha cambiado quien tiene (o no) el escenario personalizado elegido."""
        for room in list(self.rooms.values()):
            if room.phase == "lobby" and room.stage_wait() != room.stage_sig:
                room.refresh_vars()
                await room.control("ChangeSettings", None)

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

    def match_state(self, pid, remote):
        """Partida en curso de un jugador, solo si pregunta desde el mismo sitio que su juego (asi nadie
        puede mirar el papel de otro)."""
        for sess in self.sessions:
            if sess.player_id == pid and sess.remote == remote and sess.room is not None:
                return sess.room.match_state(pid)
        return None

    async def emit_now(self, topic, kw, var=None, exclude=None, eligible=None):
        """Como emit(), pero sin esperar al RESULT de la llamada en curso."""
        held, self.deferred = self.deferred, None
        try:
            await self.emit(topic, kw, var=var, exclude=exclude, eligible=eligible)
        finally:
            self.deferred = held

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
    async def run(self, ws, remote=""):
        sess = Session(self, ws)
        sess.remote = remote
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
        if room is not None and "tag" in kw:
            # Quien ve cada mensaje lo decide el juego con estas opciones: se apunta una vez por
            # papel, tipo de mensaje y opciones, para poder comprobar que el reparto es el del original
            who = ROLE_KEY.get(room.members.get(sess.player_id, {}).get("role"), "?")
            sig = (who, kw.get("tag"), json.dumps({k: v for k, v in opts.items() if k != "call"}, sort_keys=True))
            seen = room.__dict__.setdefault("vis_seen", set())
            if sig not in seen and len(seen) < 60:
                seen.add(sig)
                names = sorted(room.members.get(p, {}).get("name", p) for p in eligible) if eligible is not None else "todos"
                log.info("Sala %s: %s manda %r %s con %s -> lo ven %s", room.id, who, kw.get("tag"),
                         kw.get("type"), sig[2], names)
        await self.emit(topic, kw, var=room.vars if room else None, exclude=None if echo else sess, eligible=eligible)
        if room is not None and "tag" in kw:
            asyncio.ensure_future(room.on_player_message(sess, kw, eligible))
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
def grid_pos(grid_id):
    """Centro en el mundo de una casilla del juego (casillas de 6x6; id = 10*i + j, o 10*i - j si i < 0)."""
    try:
        g = int(grid_id)
    except (TypeError, ValueError):
        return 0.0, 0.0
    i, j = (g // 10, g % 10) if g >= 0 else (-((-g) // 10), (-g) % 10)
    return 6.0 * i, 6.0 * j


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
        self.current_stage = None     # escenario real de la partida en curso (si se eligio "Random")
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
        self.food_items, self.weapon_items, self.switch_items = set(), set(), set()
        self.events = {}           # jugador -> acciones con puntos conseguidas en la partida
        self.searched = {}         # mueble (cottage id) -> objeto que salio
        self.drops = {}            # objeto en el suelo (cottage id) -> indice de objeto
        self.disabled_objects = set()
        self.bot_orders = {}
        self.claims = {"sherlock": set(), "moriarty": set()}   # personajes que un humano dice que lleva este turno
        self.irene_cmds = []       # en solitario: personajes que Irene le pide a Moriarty IA que mueva (y a donde)
        self.watson_suspect = None # en solitario: personaje del que Watson sospecha (Sherlock IA lo vigila)
        self.watson_food = set()   # muebles con comida que Watson ya conoce
        self.watson_done = False   # ya se le dijo a Watson que no queda comida por descubrir
        self.ai_mem = ai.new_memory()   # lo que ha visto el bando de Sherlock (IA dificil)
        self.last_view = None
        self.turn_ref = {}         # reference_data del inicio del turno (para IA y peligros)
        self.hazard_prob = {}      # "threat"/"gaspipe" -> probabilidad actual (se dobla en cada fallo)
        self.recorded = False      # resultado ya anotado en las estadisticas
        self.assault = False       # hubo orden de Asalto este turno
        self.open_seats = 0        # huecos que el anfitrion reserva para humanos (expulsando a una IA)
        self.bot_task = None
        self.stage_sig = {}        # jugadores a los que se espera por el escenario (lo que dicen las variables)
        self.stamp_quiet = 0       # hasta cuando las IA no contestan a mas stickers
        self.stamp_seq = 0

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

    async def on_player_message(self, sess, kw, eligible=None):
        """Las IA contestan a los mensajes de coordinacion que se mandan los clientes entre si."""
        tag = kw.get("tag")
        if not self.bots() or not tag:
            return
        seen = self.__dict__.setdefault("tags_seen", set())
        if tag not in seen:
            seen.add(tag)
            log.info("Sala %s: primer mensaje %r de los jugadores: %s", self.id, tag,
                     {k: kw[k] for k in list(kw)[:14]})
        if tag == "stamp":
            if not await self.solo_command(sess, kw, eligible):
                await self.bot_stamp(sess, kw, eligible)
        elif tag == "ping":
            if not await self.solo_command(sess, kw, eligible):
                await self.bot_claim(sess, kw, eligible)
        elif tag == "startInstruct":
            await asyncio.sleep(0.5)
            await self.bot_say("instruct", list=[])
        elif tag == "gameEndTimeUp":
            await self.bot_say("gameEndTimeUp")
        elif tag in ("instruct", "timeUp"):
            await self.bot_say("endWaitInstruct")

    async def bot_stamp(self, sess, kw, eligible=None):
        """Un jugador manda un sticker: a veces una IA (rara vez dos) contesta, para que no parezca que
        juegas solo. Si es uno de los gratuitos del juego contesta con el mismo ("Hola" -> "Hola"); si no
        (de pago o de un mod), con uno gratuito al azar. Lo ve quien vio el del jugador."""
        now = time.time()
        if now < self.stamp_quiet or random.random() > BOT_STAMP_CHANCE or sess.player_id not in self.members:
            return
        self.stamp_quiet = now + BOT_STAMP_QUIET
        try:
            sender = int(kw.get("id", self.member_index(sess.player_id)))
            base_y = int(kw.get("posposY", 0))
        except (TypeError, ValueError):
            return
        try:
            same = next((st for st in BOT_STAMPS if st[0] == int(kw.get("type", -1))
                         and int(kw.get("setIndex", 0) or 0) == 0), None)
        except (TypeError, ValueError):
            same = None
        bots = self.bots()
        if eligible and any(b in eligible for b in bots):     # mensaje privado de un bando: contesta ese bando
            bots = [b for b in bots if b in eligible]
        if not bots:
            return
        for n, pid in enumerate(random.sample(bots, 2 if len(bots) > 1 and random.random() < 0.2 else 1)):
            await asyncio.sleep(random.uniform(0.9, 2.2) if n == 0 else random.uniform(0.4, 1.0))
            if self.hub.rooms.get(self.id) is not self or pid not in self.members:
                return
            idx = self.member_index(pid)
            typ, data_index, text = same or random.choice(BOT_STAMPS)
            msg = dict(kw, id=idx, type=typ, setIndex=0, dataIndex=data_index)
            if "createId" in kw:            # en partida: el sticker sale junto al del jugador y en el registro
                self.stamp_seq += 1
                msg.update(createId=(4000 + self.stamp_seq) * 16 + idx, parentCreateId=0, responseMsgId="",
                           name=self.members[pid]["name"], logMsgId="ctg_name_log_stamp_" + text)
                msg["posposX"] = int(kw.get("posposX", 0)) + random.choice((-14, 14)) * (n + 1)
            else:                           # en la sala: sale junto a la fila de la IA
                msg["posposY"] = round(base_y - ROOM_STAMP_ROW * (idx - sender))
            targets = None if eligible is None else set(eligible) | {sess.player_id}
            await self.hub.emit(self.topic, msg, var=self.vars, eligible=targets)

    async def bot_claim(self, sess, kw, eligible=None):
        """Un humano senala un personaje con un ping ("Yo controlare a X", "Movere a X"... o el que manda
        el juego al darle una orden): la IA de su bando deja ese personaje este turno y, si era un aviso,
        una de ellas contesta "Entendido" junto al personaje. Asi Irene puede jugar con un Moriarty IA."""
        try:
            typ = int(kw.get("type", -1))
            obj = str(kw.get("obj") or "")
            pawn = int(obj[4:]) - 1 if obj.startswith("pawn") else -1
        except (TypeError, ValueError):
            return
        if pawn < 0 or (typ not in CLAIM_PINGS and typ not in ORDER_PINGS) or sess.player_id not in self.members:
            return
        if self.phase not in IN_MATCH:
            return
        team = self.side(sess.player_id)
        mates = [b for b in self.bots() if self.side(b) == team and (eligible is None or b in eligible)]
        if not mates:
            return
        claims = self.claims.setdefault(team, set())
        new = pawn not in claims
        claims.add(pawn)
        if new and any(o.get("pawnId") == pawn for b in mates for o in self.bot_orders.get(b, [])):
            log.info("Sala %s turno %s: %s se queda con el personaje %s; la IA de su bando cambia de plan",
                     self.id, self.turn, self.members[sess.player_id]["name"], pawn)
            self.plan_bots(self.turn_ref)
            asyncio.ensure_future(self.bot_announce(0.3))
        if typ not in CLAIM_PINGS or not new:
            return
        await self.bot_roger(random.choice(mates), sess, kw, eligible)

    def solo(self):
        """Partida de una sola persona contra IAs."""
        return len(self.humans()) == 1

    def solo_support(self, team):
        """En solitario, la persona lleva a Irene o a Watson en ese bando."""
        if not self.solo():
            return False
        me = self.humans()[0]
        return self.members[me]["role"] in (ROLE_IRENE, ROLE_WATSON) and self.side(me) == team

    async def solo_command(self, sess, kw, eligible=None):
        """En solitario, Irene y Watson dirigen a la IA de su bando con sus pings:
        - Irene: "Aqui tienes a tu asesino!" sobre un personaje -> Moriarty IA lo movera este turno (hasta
          dos); despues, un ping suyo en el suelo -> a donde. Si es el asesino armado y lo lleva a la
          casilla de la victima, ataca.
        - Watson: "Sospecho que es el asesino" sobre alguien -> Sherlock IA aparta de el a quien este en su
          habitacion (todos los turnos); "No creo que sea el asesino" sobre el mismo -> lo olvida.
        Devuelve True si el ping era una de estas ordenes."""
        if self.phase not in IN_MATCH or not self.solo() or sess.player_id not in self.members:
            return False
        tag = kw.get("tag")
        try:
            typ = int(kw.get("type", -1))
            obj = str(kw.get("obj") or "")
            pawn = int(obj[4:]) - 1 if obj.startswith("pawn") else -1
            x, z = float(kw.get("posposX", 0) or 0) / 10, float(kw.get("posposZ", 0) or 0) / 10
        except (TypeError, ValueError):
            return False
        role = self.members[sess.player_id]["role"]
        if role not in (ROLE_IRENE, ROLE_WATSON):
            return False
        if pawn < 0 and tag == "stamp":
            pawn = self.pawn_near(x, z)          # los stickers no dicen a quien senalan: el mas cercano
        log.info("Sala %s turno %s: %s %s de %s sobre %r/%s en (%.0f, %.0f)", self.id, self.turn, tag, typ,
                 ROLE_KEY[role], obj, pawn, x, z)
        if role == ROLE_IRENE:
            mor = [b for b in self.bots() if self.members[b]["role"] == ROLE_CRIMINAL]
            if not mor:
                return False
            waiting = self.irene_cmds and self.irene_cmds[-1]["dest"] is None
            if tag == "ping" and typ in IRENE_PLACE_PINGS and waiting and (pawn < 0 or typ != 29):
                self.irene_cmds[-1]["dest"] = (x, z)          # "a donde": un ping de Irene despues de elegir
            elif pawn >= 0 and ((tag == "stamp" and (typ == IRENE_KILLER_STAMP or
                                                     str(kw.get("logMsgId") or "").endswith("_handle_killer"))) or
                                (tag == "ping" and typ in IRENE_PICK_PINGS)):
                self.irene_cmds = [c for c in self.irene_cmds if c["pawn"] != pawn][-(IRENE_MAX_PICKS - 1):]
                self.irene_cmds.append({"pawn": pawn, "dest": None})
                self.claims["moriarty"].discard(pawn)
            else:
                return False
            log.info("Sala %s turno %s: Irene pide a Moriarty IA %s", self.id, self.turn, self.irene_cmds)
            self.plan_bots(self.turn_ref)
            asyncio.ensure_future(self.bot_roger(mor[0], sess, kw, eligible))
            return True
        if role == ROLE_WATSON and pawn >= 0:
            det = [b for b in self.bots() if self.members[b]["role"] == ROLE_DETECTIVE]
            if not det:
                return False
            msg_id = str(kw.get("logMsgId") or "")
            if tag == "ping":
                suspect, clear = typ in WATSON_SUSPECT_PINGS, typ in WATSON_CLEAR_PINGS
            elif tag == "stamp":
                suspect = msg_id.endswith("_killerSuspicion") or (typ in WATSON_SUSPECT_STAMPS and "_csr_" not in msg_id)
                clear = msg_id.endswith("_killerNoSuspicion") or (typ in WATSON_CLEAR_STAMPS and "_csr_" not in msg_id)
            else:
                suspect = clear = False
            if suspect:
                self.watson_suspect = pawn
            elif clear and self.watson_suspect == pawn:
                self.watson_suspect = None
            else:
                return False
            log.info("Sala %s turno %s: Watson sospecha de %s", self.id, self.turn, self.watson_suspect)
            self.plan_bots(self.turn_ref)
            asyncio.ensure_future(self.bot_roger(det[0], sess, kw, eligible))
            return True
        return False

    def pawn_near(self, x, z, reach=7.0):
        """Personaje mas cercano a un punto del mundo (en el reference_data del turno)."""
        best, dist = -1, reach * reach
        for p in (self.turn_ref or {}).get("pawns") or []:
            if not isinstance(p, dict) or "pawnId" not in p:
                continue
            px, pz = grid_pos(p.get("gridId"))
            d = (px - x) ** 2 + (pz - z) ** 2
            if d < dist:
                best, dist = int(p["pawnId"]), d
        return best

    def irene_orders(self, view, idx, taken, rng):
        """Ordenes que Irene le ha pedido a Moriarty IA (en solitario)."""
        out = []
        for c in self.irene_cmds:
            p = c["pawn"]
            if p not in view.pawns or p in taken or not view.grids(p):
                continue
            if c["dest"] is None:
                o = ai.search_or_move(view, idx, p, view.grids(p), rng, prefer=self.target)
            else:
                dx, dz = c["dest"]
                g = min(view.grids(p), key=lambda g: (lambda q: (q[0] - dx) ** 2 + (q[1] - dz) ** 2)(grid_pos(g.get("gridId"))))
                killer = view.pawns.get(self.killer, {})
                if p == self.killer and killer.get("isHaveWeapon") and self.target in view.pawns \
                        and view.dist(g, self.target) == 0:
                    o = ai.assault_order(view, idx, self.killer, self.target)
                else:
                    o = ai.order(view, idx, p, ai.MOVE, g)
            if o:
                out.append(o)
                taken = set(taken) | {p}
        return out

    def watson_guard(self, view, idx, orders, n, taken):
        """Sherlock IA (en solitario con Watson): aparta del sospechoso a quien este en su habitacion."""
        s = self.watson_suspect
        if s is None or s not in view.pawns:
            return orders
        guard = []
        for q in view.room_mates(s):
            if len(guard) >= n:
                break
            if q != s and q not in taken and view.grids(q):
                guard.append(ai.order(view, idx, q, ai.MOVE, ai.away_from(view, q, s)))
        mine = {o["pawnId"] for o in guard}
        return (guard + [o for o in orders if o["pawnId"] not in mine])[:n]

    async def bot_roger(self, pid, sess, kw, eligible=None):
        """Una IA contesta "Entendido" con un sticker junto a donde senalo el ping."""
        await asyncio.sleep(random.uniform(0.7, 1.6))
        if self.hub.rooms.get(self.id) is not self or pid not in self.members:
            return
        idx = self.member_index(pid)
        typ_s, data_index, text = ROGER_STAMP
        self.stamp_seq += 1
        try:
            x, y, z = (int(kw.get(k, 0)) for k in ("posposX", "posposY", "posposZ"))
        except (TypeError, ValueError):
            x = y = z = 0
        msg = {"tag": "stamp", "createId": (4000 + self.stamp_seq) * 16 + idx, "id": idx, "type": typ_s,
               "setIndex": 0, "dataIndex": data_index, "posposX": x + 14, "posposY": y, "posposZ": z,
               "isClick": 1, "liveTime": 0, "parentCreateId": 0, "name": self.members[pid]["name"],
               "logMsgId": "ctg_name_log_stamp_" + text, "pingType": 34, "responseMsgId": "", "pingName": "",
               "pingPlayerName": "", "pingPlayerId": 0, "ignore": 0, "isCutScene": 0}
        targets = None if eligible is None else set(eligible) | {sess.player_id}
        await self.hub.emit(self.topic, msg, var=self.vars, eligible=targets)

    async def bot_announce(self, delay=None):
        """Como haria una persona, cada IA avisa a sus companeros humanos con un ping de que personajes
        va a mover este turno ("Yo controlare a X"). Asi sabes que hace tu companero IA, y las pistas del
        juego ("es posible que X haya recibido ordenes de...") funcionan en vez de decir que no se sabe."""
        await asyncio.sleep(random.uniform(1.5, 3.0) if delay is None else delay)
        if self.hub.rooms.get(self.id) is not self or self.phase not in IN_MATCH:
            return
        pawns = {int(p.get("pawnId", -1)): p for p in (self.turn_ref.get("pawns") or []) if isinstance(p, dict)}
        humans = self.humans()
        pinged = getattr(self, "bot_pinged", None)
        if pinged is None:
            pinged = self.bot_pinged = {}
        for bot, orders in list((self.bot_orders or {}).items()):
            if bot not in self.members:
                continue
            team = self.side(bot)
            mates = [h for h in humans if self.side(h) == team]
            if not mates:
                continue
            idx = self.member_index(bot)
            typ = 26 if self.members[bot]["role"] == ROLE_IRENE else 1
            done = pinged.setdefault(bot, set())
            for o in orders:
                pawn = int(o.get("pawnId", -1))
                if pawn in done or pawn not in pawns:
                    continue
                done.add(pawn)
                x, z = grid_pos(pawns[pawn].get("gridId"))
                msg = {"tag": "ping", "id": idx, "type": typ, "call": 2,
                       "posposX": round(x * 10), "posposY": 15, "posposZ": round(z * 10),
                       "callposposX": round(x * 10), "callposposY": 0, "callposposZ": round(z * 10),
                       "name": self.members[bot]["name"], "obj": "pawn%02d" % (pawn + 1), "ignore": 0}
                await self.hub.emit(self.topic, msg, var=self.vars, eligible=set(mates) | {bot})
                await asyncio.sleep(random.uniform(0.4, 0.9))

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
        if self.phase not in ("lobby", "ended") and not self.recorded and not self.members[pid].get("bot"):
            # Se va a mitad de partida (cierra el juego, se le cae la conexion...): cuenta como si se
            # rindiera. Pierde su bando y gana el otro; a los que quedan el juego les ensena el final.
            await self.forfeit(pid, reason="sale de la partida")
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
        if self.current_stage:
            v["setting_stage"] = self.current_stage
        wait = self.stage_sig = self.stage_wait()
        v["setting_capacity"] = self.shown_capacity()
        v["owner"] = self.owner
        # el juego solo deja empezar con la sala completa: mientras se espera a alguien, "falta uno"
        v["attendance"] = len(self.members) - (1 if wait else 0)
        v["detective_count"] = sum(1 for m in self.members.values() if m["role"] in (ROLE_DETECTIVE, ROLE_WATSON))
        v["criminal_count"] = sum(1 for m in self.members.values() if m["role"] in (ROLE_CRIMINAL, ROLE_IRENE))
        for pid in self.ordered_members():
            m = self.members[pid]
            v["player_" + pid] = f"{m['name']} ({wait[pid]})" if pid in wait else m["name"]
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

    def stage_wait(self, starting=False):
        """Jugadores a los que se espera antes de poder empezar, porque no tienen (todavia) el escenario
        personalizado elegido: {jugador: aviso que acompana a su nombre}. Vacio si se puede empezar."""
        stage = self.settings.get("stage") or ""
        if not starting and (self.phase != "lobby" or self.current_stage):
            return {}
        sync, missing = STAGE_WAIT.get(str(self.owner_lang() or "").upper(), STAGE_WAIT["EN"])
        humans = self.humans()
        if stage in EXTRA_STAGES:                    # "Escenario de pruebas": cada uno tiene el suyo
            return {p: missing for p in humans if p != self.owner}
        if not stage.startswith(CUSTOM_STAGE_PREFIX):
            return {}
        room_stages = getattr(self.hub.api, "stages", None)
        if room_stages is None:
            return {p: missing for p in humans}
        states = {p: room_stages.state(stage, p) for p in humans}
        return {p: sync if st == "sync" else missing for p, st in states.items() if st != "ok"}

    def clamp_turns(self):
        """Maximo de turnos: de 1 a 99 (el juego original dejaba de 6 a 15; por defecto son 10).
        Tiempo por turno: de 60 a 999 segundos."""
        try:
            self.settings["max_turn"] = max(1, min(99, int(self.settings.get("max_turn", 10))))
        except (TypeError, ValueError):
            self.settings["max_turn"] = 10
        # Tiempo por turno: de 60 a 999 segundos (el original: 10-999 en salas privadas, 60-180 en publicas)
        try:
            self.settings["time_limit"] = max(60, min(999, int(self.settings.get("time_limit", 180))))
        except (TypeError, ValueError):
            self.settings["time_limit"] = 180

    def match_state(self, pid):
        """Para el lanzador de un invitado: si esta en mitad de una partida, con que papel."""
        m = self.members.get(pid)
        if not m or self.phase in ("lobby", "ended") or self.recorded:
            return None
        return {"role": int(m["role"]), "match_id": getattr(self, "match_id", ""),
                "stage": self.current_stage or self.settings.get("stage", ""), "level": self.level()}

    def settings_result(self):
        keys = ["campaign_id", "stage", "capacity", "time_limit", "max_turn", "private", "quick", "specify_roles",
                "irene_count", "watson_count", "auto_start", "secret_passage", "switchboard_count",
                "wild_dog_count", "gaspipe_count", "fast_action", "attendance"]
        res = {k: self.settings[k] for k in keys if k in self.settings}
        if self.current_stage:
            res["stage"] = self.current_stage
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
        self.clamp_turns()
        self.fill_bots()
        if "killer" in p:
            self.killer = int(p["killer"])
        if "target" in p:
            self.target = int(p["target"])
        self.refresh_vars()
        if str(self.settings.get("capacity", 1)) == "1":
            # Sala en solitario del juego (el entrenamiento): nada mas crearla, el juego empieza la
            # partida con la lista de jugadores de la sala. Si esa lista le llega despues de la
            # respuesta, esta vacia y el juego se cierra. Asi que aqui va antes.
            await self.hub.emit_now(self.topic, {"Control": {"Enter": {
                "PlayerId": sess.player_id, "PlayerName": sess.name, "RandomSeed": "random_seed"}}}, var=self.vars)
        else:
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
        self.clamp_turns()
        self.refresh_vars()
        await self.control("ChangeSettings", None)
        return rc({})

    async def p_Kick(self, sess, p):
        pid = str(p.get("player_id") or "")
        if "#" in pid:
            # El plugin elige la dificultad con su ventana: "bot0001#expert", "bot0001#expert#all", "bot0001#free"
            pid, _, choice = pid.partition("#")
            return await self.set_bot_difficulty(sess, pid, choice)
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

    async def set_bot_difficulty(self, sess, pid, choice):
        """La ventana de la IA del plugin: dificultad de una IA (o de todas) o dejar su hueco libre."""
        bot = self.members.get(pid, {})
        if sess.player_id != self.owner or not bot.get("bot") or self.phase != "lobby":
            return rc({})
        parts = choice.split("#")
        diff, everyone = parts[0], "all" in parts[1:]
        if diff == "free":
            name = self.members.pop(pid)["name"]
            self.open_seats += 1
            self.refresh_vars()
            await self.control("Leave", {"PlayerId": pid, "PlayerName": name, "OwnerId": self.owner,
                                         "OwnerName": self.members[self.owner]["name"]})
            return rc({})
        if diff not in ai.DIFFICULTIES:
            return rc({})
        for b in (self.bots() if everyone else [pid]):
            m = self.members[b]
            m.pop("lobby_difficulty", None)
            m["difficulty"] = diff
            m["name"] = ai.bot_name(m["slot"], diff, self.owner_lang())
        log.info("Sala %s: IA %s -> %s", self.id, "todas" if everyone else pid, diff)
        self.refresh_vars()
        await self.control("ChangeSettings", None)
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
        self.boost_support()
        self.current_stage = self.pick_stage()
        self.refresh_vars()
        await self.control("StartCountDown", {"CountDownTimer": COUNTDOWN_SECONDS})
        self.countdown_task = asyncio.ensure_future(self._countdown())
        return rc({})

    def pick_stage(self):
        """Escenario real de esta partida: el elegido, o uno al azar si es "Random" (o desconocido).
        Un escenario del creador solo vale si todos los jugadores de la sala lo tienen igual (lo dice
        el lanzador de cada uno). La sala no deja empezar mientras falte alguien; si aun asi llega la
        orden, se juega uno normal y nadie se queda en negro."""
        stage = self.settings.get("stage") or ""
        if stage in STAGES:
            return stage
        if stage in EXTRA_STAGES or stage.startswith(CUSTOM_STAGE_PREFIX):
            if not self.stage_wait(starting=True):
                return stage
            log.info("Escenario %s: no lo tienen todos los jugadores; se juega uno normal", stage)
        return random.choice(STAGES)

    async def p_CancelCountDown(self, sess, p):
        self.current_stage = None
        self.restore_support()
        self.refresh_vars()
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
        try:
            self.mlog = matchlog.MatchLog(os.path.dirname(self.hub.api.s.path), self.match_id,
                                          self.current_stage or self.settings.get("stage", ""), self.settings,
                                          self.members, self.killer, self.target, ROLE_KEY)
        except Exception:  # noqa: BLE001  (el registro nunca debe parar una partida)
            log.exception("No pude empezar el registro de la partida")
            self.mlog = None
        self.profiles = {"moriarty": None, "sherlock": None}
        if any(m.get("difficulty") == "nightmare" for m in self.members.values() if m.get("bot")):
            try:
                recs = matchlog.read_all(os.path.dirname(self.hub.api.s.path))
                self.profiles = profiles.for_room(recs, self.members, ROLE_KEY)
                log.info("Sala %s: IA Pesadilla con %s partidas guardadas; perfiles: Moriarty %s, Sherlock %s",
                         self.id, len(recs),
                         (self.profiles["moriarty"] or {}).get("matches", "sin datos"),
                         (self.profiles["sherlock"] or {}).get("matches", "sin datos"))
            except Exception:  # noqa: BLE001
                log.exception("No pude leer los perfiles para la IA Pesadilla")
        log.info("Sala %s: empieza la partida (asesino %s, victima %s, roles %s)", self.id, self.killer, self.target,
                 {m["name"]: m["role"] for m in self.members.values()})
        await self.control("StartMatch", None)
        if self.bots():
            self.bot_task = asyncio.ensure_future(self._bot_heartbeat())

    def boost_support(self):
        """En solitario con Irene o Watson, la IA de tu bando juega en Dificil, y asi se llama en la
        partida (antes seguia poniendo "Normal" y no se entendia). Al volver a la sala recupera la suya."""
        self.restore_support()
        for pid in self.bots():
            m = self.members[pid]
            lvl = self.support_level()
            if self.solo_support(self.side(pid)) and m.get("difficulty") != lvl:
                m["lobby_difficulty"] = m.get("difficulty")
                m["difficulty"] = lvl
                m["name"] = ai.bot_name(m["slot"], lvl, self.owner_lang())
        self.refresh_vars()

    def support_level(self):
        """Nivel de la IA companera en solitario: Dificil, o Experto si los rivales son expertos."""
        rivals = [m.get("lobby_difficulty") or m.get("difficulty") for m in self.members.values() if m.get("bot")]
        return "expert" if {"expert", "nightmare"} & set(rivals) else "hard"

    def restore_support(self):
        for m in self.members.values():
            if m.get("bot") and m.get("lobby_difficulty"):
                m["difficulty"] = m.pop("lobby_difficulty")
                m["name"] = ai.bot_name(m["slot"], m["difficulty"], self.owner_lang())

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
        self.ai_mem = ai.new_memory()
        self.watson_food, self.watson_done = set(), False
        self.irene_cmds, self.watson_suspect = [], None
        self.food_items = set(range(food))
        self.weapon_items = set(range(food, food + weapons))
        # Planos del cuadro electrico: los ultimos de la lista (ItemManager.CreateMatchItemList)
        sw = int(self.settings.get("switchboard_count", 0) or 0)
        self.switch_items = set(range(max(0, n - sw), n))
        self.events = {}
        log.info("Sala %s: %s objetos repartidos (%s comida, %s armas)", self.id, n, food, weapons)

    def objects_with(self, items):
        """Muebles aun sin registrar que contienen alguno de esos objetos."""
        return sorted(o for o, i in self.object_items.items() if i in items and o not in self.searched)

    def role_data(self, pid):
        """Lo que sabe cada papel al empezar: Moriarty, todas las armas y toda la comida; Irene, toda la
        comida ("marcare las ubicaciones de los alimentos con una luz verde"); los demas, ninguna arma y
        solo unos pocos sitios con comida (MatchSettings.foodOpenCount)."""
        foods = self.objects_with(self.food_items)
        if self.members.get(pid, {}).get("role") == ROLE_IRENE:
            return {"weaponList": [], "foodList": foods}
        if self.members.get(pid, {}).get("role") != ROLE_CRIMINAL:
            foods = sorted(random.sample(foods, min(FOOD_OPEN_COUNT, len(foods))))
            if self.members.get(pid, {}).get("role") == ROLE_WATSON:
                self.watson_food |= set(foods)
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

    async def send_result(self, is_kill):
        """GameManager.ResultPhaseCallback: el resultado final de la partida en linea.
        isKill True -> KILL_SUCCESS (gana Moriarty); False -> ARREST_SUCCESS (detenido el asesino).
        Sin este mensaje el cliente se queda esperando (pantalla en negro)."""
        self.phase = "ended"

        def first(role):
            p = self.players_by_role([role])
            return (p[0], self.members[p[0]]["name"]) if p else ("", "")
        det, cri, ire, wat = (first(r) for r in (ROLE_DETECTIVE, ROLE_CRIMINAL, ROLE_IRENE, ROLE_WATSON))
        await self.control("StartResultPhase", {"Data": {
            "isKill": bool(is_kill), "killer": self.killer, "target": self.target,
            "detective_player": det[0], "detective_name": det[1], "criminal_player": cri[0], "criminal_name": cri[1],
            "irene_player": ire[0], "irene_name": ire[1], "watson_player": wat[0], "watson_name": wat[1]}})

    async def end_by_kill(self):
        log.info("Sala %s turno %s: la victima ha muerto", self.id, self.turn)
        self.log_call("killed", self.turn, self.assault)
        await self.send_result(True)
        self.conclude("moriarty", {ROLE_CRIMINAL: [ACT_ASSAIL_KILL] if self.assault else []})

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
            self.log_call("turn_state", self.turn, self.turn_ref)
            self.claims = {"sherlock": set(), "moriarty": set()}
            self.irene_cmds = []
            self.plan_bots(self.turn_ref)
            self.bot_pinged = {}
            asyncio.ensure_future(self.bot_announce())
            data = {}
            found = self.watson_reveal()
            if found is not None:
                data["watson"] = found
            await self.control("StartCommandPhase", {"Turn": self.turn, "Data": data, "RandomSeed": "random_seed"})
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
                if self.assault:     # hubo Asalto y la victima sigue viva: el bando de Sherlock lo frustro
                    for pid in self.members:
                        if self.side(pid) == "sherlock":
                            self.note(pid, ACT_FOILED)
                if int(ref.get("isLastTurn", 0) or 0):
                    # Era el turno final tras descubrirse al asesino (Asalto fallido o deduccion) y la
                    # victima sigue viva: resultado ARREST_SUCCESS, gana el bando de Sherlock.
                    log.info("Sala %s turno %s: fin del turno final sin asesinato, detenido el asesino", self.id, self.turn)
                    await self.send_result(False)
                    self.conclude("sherlock", {ROLE_DETECTIVE: [ACT_DEDUCED]})
                else:
                    await self.control("StartTransitionPhase", {"Turn": self.turn, "Data": {"isDanger": self.is_danger()}})
        if "answer" in self.pending and self._complete("answer"):
            await self.finish_answers()

    def watson_reveal(self):
        """Habilidad de Watson: al empezar cada turno descubre un mueble con comida que aun no conocia
        (el juego lo resalta, lo anade a su lista y Watson lo comenta). Cuando ya no queda, se lo dice una vez.
        Lo lee GameManager.CommandPhaseCallback del dato "watson" (solo en el juego de Watson)."""
        if not any(self.members[p]["role"] == ROLE_WATSON for p in self.humans()):
            return None
        hidden = [o for o in self.objects_with(self.food_items) if o not in self.watson_food]
        if not hidden:
            if self.watson_done or not self.object_items:
                return None
            self.watson_done = True
            return {"nextTargetId": -1}
        o = random.choice(hidden)
        self.watson_food.add(o)
        log.info("Sala %s turno %s: Watson descubre comida en el mueble %s", self.id, self.turn, o)
        return {"nextTargetId": o, "nextItemId": self.object_items[o]}

    def plan_bots(self, ref):
        """La IA decide sus ordenes con el estado del turno que manda el cliente."""
        self.bot_orders = {}
        bots = self.bots()
        if not bots or not ref.get("pawns"):
            return
        gone = set(self.searched) | self.disabled_objects
        views = {"moriarty": ai.View(ref, gone), "sherlock": ai.View(ref, gone)}   # cada bando, lo suyo
        views["moriarty"].weapon_objects = set(self.objects_with(self.weapon_items))
        views["moriarty"].food_objects = set(self.objects_with(self.food_items))
        for v in views.values():
            v.max_turn = int(self.settings.get("max_turn") or 0) or None
        prof = getattr(self, "profiles", None) or {}
        self.ai_mem["prof_moriarty"] = prof.get("moriarty")     # lo aprendido de las personas (Pesadilla)
        self.ai_mem["prof_sherlock"] = prof.get("sherlock")
        self.last_view = view = views["sherlock"]
        rng = random.Random()
        det_players = self.players_by_role([ROLE_DETECTIVE])
        cri_players = self.players_by_role([ROLE_CRIMINAL])
        # Cada bando solo sabe que personajes ha ordenado su propio equipo (y los que han reclamado
        # sus humanos con un ping este turno)
        taken = {team: set(c) for team, c in self.claims.items()}
        prio = {ROLE_CRIMINAL: 0, ROLE_IRENE: 1, ROLE_DETECTIVE: 2, ROLE_WATSON: 3}
        for pid in sorted(bots, key=lambda b: prio.get(self.members[b]["role"], 9)):
            m = self.members[pid]
            idx = self.member_index(pid)
            role, diff = m["role"], m["difficulty"]
            team = "moriarty" if role in (ROLE_CRIMINAL, ROLE_IRENE) else "sherlock"
            if self.solo_support(team):
                diff = self.support_level()  # en solitario, el companero de Irene/Watson juega en serio
            if role == ROLE_CRIMINAL:
                n = max(1, 2 // max(1, len(cri_players)))
                own, _ = ai.plan_moriarty(views[team], idx, self.killer, self.target, n, diff, rng, taken[team],
                                          memory=self.ai_mem)
                if self.solo_support(team) and self.irene_cmds:
                    # Lo que pide Irene va primero, salvo un asalto: si Moriarty puede matar este turno, mata
                    # (antes las ordenes de Irene ocupaban sus dos personajes y no atacaba nunca)
                    strike = [o for o in own if o["type"] == ai.TARGET]
                    busy = taken[team] | {o["pawnId"] for o in strike}
                    orders = (strike + self.irene_orders(views[team], idx, busy, rng))[:n]
                    used = {o["pawnId"] for o in orders}
                    orders += [o for o in own if o["pawnId"] not in used][:n - len(orders)]
                else:
                    orders = own
            elif role == ROLE_IRENE:
                orders = ai.plan_irene(views[team], idx, self.killer, self.target, diff, rng, taken[team],
                                       memory=self.ai_mem)
            elif role == ROLE_DETECTIVE:
                n = max(1, 3 // max(1, len(det_players)))
                orders = ai.plan_sherlock(views[team], idx, n, diff, rng, taken[team], self.ai_mem)
                if self.solo_support(team):
                    orders = self.watson_guard(views[team], idx, orders, n, taken[team])
            elif role == ROLE_WATSON:
                orders = ai.plan_watson(views[team], idx, diff, rng, taken[team], self.ai_mem)
            else:
                orders = []
            taken[team] |= {o["pawnId"] for o in orders}
            self.bot_orders[pid] = orders
            log.info("Sala %s turno %s: %s (%s, %s) -> %s", self.id, view.turn, m["name"], m["role"],
                     diff, [(o["pawnId"], o["type"], o["grid"], o["targetId"]) for o in orders])

    def build_action_data(self, payloads):
        """Junta las ordenes de todos. Si varios ordenan al mismo personaje: Moriarty gana a todos,
        Irene a Sherlock/Watson y entre los demas se sortea. Si Moriarty pisa una orden distinta de
        Sherlock/Watson, la orden va marcada (isBatting) y el bando de Sherlock lo detecta.
        Los personajes que nadie ha ordenado actuan por su cuenta (en linea lo decide el servidor)."""
        by_pawn, from_criminal, from_detective, kill, owner = {}, set(), {}, False, {}
        criminals = set(self.players_by_role([ROLE_CRIMINAL]))
        payloads = dict(payloads)
        # Lo que ordena un humano no lo pisa la IA de su mismo bando (p. ej. Irene con un Moriarty IA)
        human_pawns = {"sherlock": set(), "moriarty": set()}
        for pid, p in payloads.items():
            pl = p.get("payload") if isinstance(p, dict) else None
            if isinstance(pl, str):
                try:
                    pl = json.loads(pl)
                except ValueError:
                    pl = {}
            for item in (pl or {}).get("list", []) or [] if isinstance(pl, dict) else []:
                if isinstance(item, dict) and "pawnId" in item:
                    human_pawns[self.side(pid)].add(int(item["pawnId"]))
        for bot, orders in (getattr(self, "bot_orders", None) or {}).items():
            mine = human_pawns[self.side(bot)]
            orders = [o for o in orders or [] if int(o.get("pawnId", -1)) not in mine]
            if orders:
                payloads[bot] = {"payload": {"list": orders}}
        self.bot_orders = {}
        ghost = self.ghost_moriarty()
        if ghost:
            payloads[GHOST_CRIMINAL] = {"payload": {"list": ghost}}
            criminals.add(GHOST_CRIMINAL)
        rank = {ROLE_IRENE: 1, ROLE_CRIMINAL: 2}
        order = list(payloads)
        random.shuffle(order)
        for pid in sorted(order, key=lambda x: 2 if x == GHOST_CRIMINAL else rank.get(self.members.get(x, {}).get("role"), 0)):
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
                owner[pawn] = pid
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
        self.score_actions(commands, owner)
        commands += self.npc_orders(by_pawn)
        self.remember(commands, set(from_detective))
        sides = {p: ("M" if o == GHOST_CRIMINAL or self.side(o) == "moriarty" else "S") for p, o in owner.items()}
        self.log_call("turn_orders", self.turn, commands, sides, kill)
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

    def side(self, pid):
        role = self.members.get(pid, {}).get("role")
        return "sherlock" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "moriarty"

    def note(self, pid, action):
        if pid in self.members and not self.members[pid].get("bot"):
            self.events.setdefault(pid, set()).add(action)

    def score_actions(self, commands, owner):
        """Acciones con puntos que se ven en las ordenes de este turno (de quien la dio)."""
        ref = self.turn_ref or {}
        pawns = {int(x["pawnId"]): x for x in ref.get("pawns", []) if isinstance(x, dict) and "pawnId" in x}
        room_of_grid = {}
        for r in ref.get("roomList") or []:
            for g in r.get("gridList") or []:
                room_of_grid[g.get("gridId")] = r.get("roomId")
        target_uid = int(pawns.get(self.target, {}).get("uniqId", -2))
        for c in commands:
            pid = owner.get(int(c["pawnId"]))
            if pid is None:
                continue
            kind, side = int(c.get("type", 0)), self.side(pid)
            if side == "sherlock":
                if kind == INSTRUCT_REPAIR:
                    self.note(pid, ACT_REPAIR)
                elif kind == INSTRUCT_POTION:
                    self.note(pid, ACT_TREAT)
            if kind == INSTRUCT_SPRAY:
                room = room_of_grid.get(c.get("grid"))
                inside = [q for q, x in pawns.items() if room is not None and x.get("roomId") == room]
                if side == "sherlock" and self.killer in inside:
                    self.note(pid, ACT_SPRAY_KILLER)
                elif side == "moriarty" and any(q != self.killer for q in inside):
                    self.note(pid, ACT_SPRAY_OTHER)
            if side == "moriarty":
                if kind == INSTRUCT_ATTACK and int(c.get("targetId", -1)) == target_uid:
                    self.note(pid, ACT_KNOCKOUT)
                elif kind == INSTRUCT_SEARCH and c.get("itemId", -1) in self.switch_items:
                    self.note(pid, ACT_BLACKOUT)

    def level(self):
        """Nivel de la partida para los puntos: contra personas "online"; si no, el de la IA."""
        if len([p for p, m in self.members.items() if not m.get("bot")]) >= 2:
            return "online"
        order = ai.RANK
        diffs = [m.get("difficulty", "normal") for m in self.members.values() if m.get("bot")]
        return max(diffs, key=lambda d: order.get(d, 1)) if diffs else "normal"

    def remember(self, commands, ordered_by_sherlock):
        """Lo que ve el bando de Sherlock este turno: quien actuo sin que lo ordenaran ellos y en
        quien se noto la mano de Moriarty (orden pisada)."""
        mem = self.ai_mem
        ref = self.turn_ref or {}
        pawns = {int(x["pawnId"]): x for x in ref.get("pawns", []) if isinstance(x, dict) and "pawnId" in x}
        victims = [q for q, x in pawns.items() if x.get("isTargetCandidate", 1)]
        for c in commands:
            p = int(c["pawnId"])
            if c.get("isBatting"):
                mem["moriarty"].add(p)
            if p in ordered_by_sherlock or int(c.get("type", 0)) not in (2, 3, 4, 5):
                continue
            # Lo que llama la atencion: correr (nadie corre por su cuenta) o acercarse a una posible victima
            ran = bool(int(c.get("isRun", 0) or 0)) or int(c.get("type", 0)) in (4, 5)
            if int(c.get("type", 0)) == 3:
                mem.setdefault("search", {})[p] = mem["search"].get(p, 0) + 1
            score = 1 if ran else 0
            mem.setdefault("acts", {})[p] = mem["acts"].get(p, 0) + 1
            if ran:
                mem.setdefault("ran", {})[p] = mem["ran"].get(p, 0) + 1
            me = pawns.get(p, {})
            dest = next((g for g in me.get("gridList") or [] if g.get("gridId") == c.get("grid")), None)
            if dest is not None:
                before = {int(o.get("pawnId", -1)): int(o.get("distance", 99)) for o in me.get("pawnList") or []}
                after = dest.get("pawnDistance") or []
                for v in victims:
                    if v != p and v < len(after) and after[v] < before.get(v, 99) and after[v] <= 2:
                        score += 1
                        mem.setdefault("approach", {})[p] = mem["approach"].get(p, 0) + 1
                        break
            if score:
                mem["moved"][p] = mem["moved"].get(p, 0) + score

    def ghost_moriarty(self):
        """Entrenamiento en solitario del juego: la sala es de una sola persona y nadie lleva a
        Moriarty. El servidor oficial movia al asesino por su cuenta; sin esto no pasaba nada en toda
        la partida. Aqui juega un Moriarty IA que no esta en la sala (no sale en la lista)."""
        ref = self.turn_ref or {}
        if self.killer < 0 or not ref.get("pawns") or self.players_by_role([ROLE_CRIMINAL]) \
                or not self.players_by_role([ROLE_DETECTIVE, ROLE_WATSON]):
            return []
        view = ai.View(ref, set(self.searched) | self.disabled_objects)
        view.weapon_objects = set(self.objects_with(self.weapon_items))
        view.food_objects = set(self.objects_with(self.food_items))
        orders, _ = ai.plan_moriarty(view, -1, self.killer, self.target, 2, "normal", random.Random())
        if orders:
            log.info("Sala %s turno %s: Moriarty sin jugador -> %s", self.id, self.turn,
                     [(o["pawnId"], o["type"], o["grid"], o["targetId"]) for o in orders])
        return orders

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
        answers = self.pending.setdefault("answer", {})
        if self.phase != "selection" or sess.player_id in answers:
            # El juego guarda las respuestas por jugador y se cierra si le llega dos veces la misma
            # (paso con Sherlock IA y un Watson/Irene humano: la deduccion ya se habia cerrado y llego
            # otra respuesta). Las que llegan tarde o repetidas no se reenvian.
            if self.phase != "selection":
                self.pending.pop("answer", None)
            log.info("Sala %s: respuesta de %s ignorada (repetida o fuera de tiempo)", self.id, sess.player_id)
            return rc({})
        answers[sess.player_id] = int(p.get("killer", -1))
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
                guess = ai.accuse(self.last_view, self.killer, m["difficulty"], random.Random(), self.pawn_count,
                                  self.ai_mem)
                # en solitario con Watson, Sherlock IA acusa a quien Watson le ha dicho (si aun puede serlo)
                ws = self.watson_suspect
                if m["role"] == ROLE_DETECTIVE and ws is not None and self.solo_support(self.side(bot)):
                    pawns = (self.last_view.pawns if self.last_view else {}) or {}
                    if not pawns or pawns.get(ws, {}).get("isKillerCandidate", True):
                        guess = ws
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

    def log_call(self, name, *args):
        """Apunta algo en el registro de la partida (matchlog); si falla, la partida sigue igual."""
        ml = getattr(self, "mlog", None)
        if ml is None:
            return
        try:
            getattr(ml, name)(*args)
        except Exception:  # noqa: BLE001
            log.exception("Fallo apuntando la partida (%s)", name)

    def record_result(self, selections):
        self.log_call("accusations", [(s["player_id"], s["killer"], self.members.get(s["player_id"], {}).get("bot"))
                                      for s in selections])
        """Fin por deduccion: si Sherlock acierta gana su bando; si no, empate (no hubo asesinato)."""
        right = [s["player_id"] for s in selections if s["killer"] == self.killer
                 and self.members.get(s["player_id"], {}).get("role") == ROLE_DETECTIVE]
        extra = {pid: [ACT_DEDUCED] for pid in right}
        self.conclude("sherlock" if right else "draw", extra)

    def conclude(self, winner, extra=None, quitter=None):
        """winner: "sherlock", "moriarty" o "draw". extra: acciones con puntos, por rol o por jugador."""
        if self.recorded:
            return
        self.recorded = True
        ml = getattr(self, "mlog", None)
        reason = "abandon" if quitter else ("kill" if ml is not None and ml.rec.get("kill") else "deduction")
        self.log_call("finish", winner, reason)
        extra = extra or {}
        for pid, m in self.members.items():
            if m.get("bot"):
                continue
            role = int(m["role"])
            side = "sherlock" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "moriarty"
            outcome = "draw" if winner == "draw" else ("win" if side == winner else "lose")
            if pid == quitter:
                outcome = "abandon"
            acts = list(extra.get(role, [])) + list(extra.get(pid, [])) + sorted(self.events.get(pid, ()))
            u = self.hub.api.s.user(pid)
            pts = stats.record_match(u, role, outcome, acts, self.current_stage or self.settings.get("stage", ""),
                                     match_id=getattr(self, "match_id", None), level=self.level())
            log.info("Sala %s: %s (%s) %s, +%s puntos -> %s", self.id, m["name"], ROLE_KEY.get(role, role),
                     {"win": "GANA", "lose": "PIERDE", "draw": "EMPATA", "abandon": "ABANDONA"}[outcome],
                     pts, stats.summary(u))
        self.hub.api.s.save()

    async def p_Sync(self, sess, p):
        await self.control("Sync", {"Data": p.get("payload") if isinstance(p.get("payload"), dict) else {}})
        return rc({})

    async def p_Abandon(self, sess, p):
        await self.forfeit(sess.player_id, message=p.get("message", ""), reason="se rinde")
        return rc({})

    async def forfeit(self, pid, message="", reason=""):
        """pid se rinde o se va: pierde su bando, gana el otro, y la partida termina para todos."""
        self.phase = "ended"
        role = self.members.get(pid, {}).get("role")
        log.info("Sala %s: %s %s", self.id, self.members.get(pid, {}).get("name", pid), reason)
        winner = "moriarty" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "sherlock"
        self.conclude(winner, quitter=pid)
        crim = self.players_by_role([ROLE_CRIMINAL])
        det = self.players_by_role([ROLE_DETECTIVE])
        await self.control("Abandon", {"Data": {
            "killer": self.killer, "target": self.target,
            "criminal_player": crim[0] if crim else "", "criminal_name": self.members[crim[0]]["name"] if crim else "",
            "detective_player": det[0] if det else "", "detective_name": self.members[det[0]]["name"] if det else "",
            "message": message,       # "Rendirse" manda aqui quien se rinde (surrenderPlayerId)
            # El juego da por hecho que quien se rinde es Moriarty: el plugin usa esto para ensenar
            # victoria o derrota bien cuando se rinde (o se va) otro papel
            "csr_winner": winner,
            # y quien ha sido (papel) y si se ha rendido o se ha ido, para el texto del aviso
            "csr_quitter_role": ROLE_KEY.get(role, ""), "csr_reason": "surrender" if message else "left"}})

    async def p_Rematch(self, sess, p):
        self.phase = "lobby"
        self.restore_support()
        self.current_stage = None          # con "Random", la siguiente partida sortea otro escenario
        self.refresh_vars()
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
