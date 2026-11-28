"""
CRIMESIGHT Revival - WebSocket channel (encrypted WAMP v2) and room/match logic.

Rebuilt from the client (NetworkManager, Wamp*, GameManager):
- The original server was a WAMP router (Crossbar-style) with match.* procedures.
- Room events arrive as EVENT with details {"var": {...room variables...}}
  and kwargs {"Control": {"<Command>": {...}}}.
- The match simulation runs in the client; the server hands out roles, syncs
  the phases of each turn, gathers everyone's orders and decides the end.
"""
import asyncio, json, logging, random, secrets, time

import os

import ai
import modelpack
import modpack
import matchlog
import profiles
import stats
import cscrypto

log = logging.getLogger("crimesight.match")
FULL_LOG = os.path.join(os.environ.get("CSR_DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), "ws_full.log")


def full_log(direction, pid, data):
    """Full (untrimmed) log of the WebSocket traffic, for debugging."""
    if not log.isEnabledFor(logging.DEBUG):
        return
    try:
        with open(FULL_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {direction} {pid} {data}\n")
    except OSError:
        pass

# WAMP messages
HELLO, WELCOME, ABORT, GOODBYE, ERROR = 1, 2, 3, 6, 8
PUBLISH, PUBLISHED, SUBSCRIBE, SUBSCRIBED, UNSUBSCRIBE, UNSUBSCRIBED, EVENT = 16, 17, 32, 33, 34, 35, 36
CALL, RESULT = 48, 50

# Roles (MatchRoomMember)
ROLE_RANDOM, ROLE_DETECTIVE, ROLE_CRIMINAL, ROLE_IRENE, ROLE_WATSON = 0, 1, 2, 3, 4
ITEM_MISS, ITEM_MEMO = 0, 9      # Item.Type in the game (0 miss, 1 food, 2 weapon, ... 9 memo)

# Launcher developer mode: a function returning {"killer": character, "target": character} (each one
# "orig:PawnTypeData_X", the id of a new character, or None = random) to pick the killer and the target of this
# server's matches. Only the launcher sets it, on its local server; without it everything stays random.
forced_roles = None
ROLE_KEY = {ROLE_DETECTIVE: "detective", ROLE_CRIMINAL: "criminal", ROLE_IRENE: "irene", ROLE_WATSON: "watson"}

INSTRUCT_TARGET = 5          # Pawn.InstructData.InstructType.TARGET -> "Asalto" de Moriarty
INSTRUCT_SEARCH = 3          # search a piece of furniture: the server decides which item turns up
INSTRUCT_PICK = 7            # pick up an item from the floor
FOOD_OPEN_COUNT = 2          # MatchSettings.foodOpenCount: food seen by everyone who is not Moriarty
# Pawn.InstructData.InstructType
INSTRUCT_ATTACK, INSTRUCT_POTION, INSTRUCT_SPRAY, INSTRUCT_REPAIR = 4, 6, 9, 11
INSTRUCT_BOARD, INSTRUCT_GASPIPE, INSTRUCT_BYWAY = 10, 12, 13    # break the switchboard, fix the gas, secret passage
# Actions with points (the game's own texts, see stats.ACTIONS)
ACT_REPAIR = "ctg_name_result_repair_switchboard"
ACT_TREAT = "ctg_name_result_action_treated_pawnForInjuries"
ACT_SPRAY_KILLER = "ctg_name_result_apply_tearSpray_to_killer"
ACT_DEDUCED = "ctg_name_result_identified_killer_by_deduction"
ACT_ASSAIL_KILL = "ctg_name_result_action_targetKilledByAssail"
ACT_BLACKOUT = "ctg_name_result_blackOut_by_switchboard"
ACT_SPRAY_OTHER = "ctg_name_result_action_blockedSherlockWithSpray"
ACT_KNOCKOUT = "ctg_name_result_action_beCriticalNoKiller"
ACT_BYWAY = "ctg_name_result_action_activateSecretPassage"
ACT_GAS_REPAIR = "ctg_name_result_action_repair_gasPipe"
ACT_DOG_KILL = "ctg_name_result_action_exterminateWildDog"          # dogs and other threats (traitors)
ACT_FOUND_SWITCH = "ctg_name_result_action_foundSwitchboard"
ACT_FOUND_SWITCH_FIRST = "ctg_name_result_action_foundSwitchboardBeforeSherlock"
ACT_FOOD = "ctg_name_result_action_obtainFoodFromFoodPoint"
ACT_TREAT_KILLER = "ctg_name_result_action_treated_killerForInjuries"
ACT_NOT_KILLER = "ctg_name_result_action_proven_pawnNotKiller"
ACT_NOT_TARGET = "ctg_name_result_action_proven_pawnNotTarget"
ACT_DOG_HIT = "ctg_name_result_action_wildDogAttackedEveryoneButKiller"
ACT_GAS_HIT = "ctg_name_result_action_injured_noKillerWithGasLeak"
ACT_FOUND_SWITCH_BEFORE_MORIARTY = "ctg_name_result_discover_switchboard_before_moriarty"
ACT_FIRST_CLASH = "ctg_name_result_first_batting"          # "Initial command conflict detected with each pawn."
ACT_CLASH_AGAIN = "ctg_name_result_after_the_first_batting"  # "Interfered with Sherlock's command."
DEFAULT_PAWNS = 6            # characters per match (the mansion has 6 suspects)
DEFAULT_TURNS = 10           # turns of a normal match (the one the dogs and the gas are made for)


def hazard_window(start, end, base, max_turn):
    """Dogs and gas with another number of turns. The turns they can show up in (the stage's, made
    for 10 turns) are stretched or shrunk in proportion: from 4 to 8 in 10 turns is from 2 to 5 in 6 and from 8 to 16
    in 20. And the probability, which starts at `base` and doubles on each miss, grows more slowly or more
    quickly so that the chance of them showing up over the whole span is the same as with 10 turns.
    Returns (start, end, how much the probability is multiplied on each miss)."""
    if max_turn == DEFAULT_TURNS or end < start:
        return start, end, 2.0
    f = max_turn / DEFAULT_TURNS
    s = max(1, int(start * f + 0.5))
    e = min(max_turn, max(s, int(end * f + 0.5)))
    n0, n = end - start + 1, e - s + 1

    def chance(g, rolls):
        miss, p = 1.0, float(base)
        for _ in range(rolls):
            miss *= 1 - min(p, 100.0) / 100
            p *= g
        return 1 - miss

    target = chance(2.0, n0)
    lo, hi = 0.25, 64.0
    for _ in range(60):                       # binary search for the g that gives the same probability
        mid = (lo + hi) / 2
        if chance(mid, n) < target:
            lo = mid
        else:
            hi = mid
    return s, e, (lo + hi) / 2
COUNTDOWN_SECONDS = 3
# The game's Quick Match modes: (players, Irenes, Watsons). "No preference" gets one of them at random.
QUICK_MODES = [(4, 1, 1), (4, 0, 0), (3, 0, 0), (2, 0, 0)]
SURRENDER_VOTE_SECONDS = 20          # a teammate who is a person has this long to agree to forfeit
DEFAULT_AI_DIFFICULTY = "normal"   # can be changed with --ai-difficulty
STAGES = ["Stage_Yokn", "Stage_Yokn_v1030", "Stage_Yokn_v1040", "Stage_Yokn_v1050", "Stage_Yokn_v1060"]
# Stages the BepInEx plugin adds (they don't come up in "Random"). The plugin loads the real stage.
EXTRA_STAGES = ["Stage_Yokn_CSRTest"]
CUSTOM_STAGE_PREFIX = "Stage_CSR_"      # stages made with the stage creator (one per name)
# While a player lacks the chosen custom stage, their name says so in the room
# (in the host's language): (their launcher is downloading it, they don't have it and won't get it)
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

# The game's free stickers the AIs answer with: (type, place in the list, log text).
# Without the suspicion ones (an AI's sticker must not look like a clue) or the paid ones.
BOT_STAMPS = [(28, 0, "hello"), (8, 1, "goodJob"), (37, 2, "justMoment"), (29, 3, "smirk"), (1, 8, "why"),
              (31, 10, "worried"), (2, 11, "noWay"), (4, 12, "relieved"), (5, 13, "frightened"), (32, 14, "scream"),
              (34, 15, "please"), (0, 16, "roger")]
_BOT_STAMP = {st[0]: st for st in BOT_STAMPS}
# What an AI answers each sticker with (by type: it works for all its versions, the normal one, each
# character's and the paid ones). If there are two, it picks one at random.
BOT_REPLIES = {28: (28,),        # Hola -> Hola
               8: (8,),          # Bien -> Bien
               0: (8,),          # Understood -> Good ("Understood" is not answered with "Understood")
               1: (37,),         # Why? -> Just a moment
               2: (2, 5),        # It can't be! -> It can't be! or Scared
               4: (4, 8),        # Relieved -> Relieved or Good
               5: (31, 5),       # Scared -> Worried or Scared
               32: (5, 32),      # Scream -> Scared or Scream
               31: (31, 34),     # Worried -> Worried or Please
               34: (0, 37),      # Please -> Understood or Just a moment
               37: (0,),         # Just a moment -> Got it
               29: (29, 1),      # Sly smile -> Sly smile or Why?
               30: (1,)}         # Suspicious -> Why?
# A mod's sticker is only answered if its mod says which game sticker it stands for ("means" in mod.json);
# otherwise nobody answers: nobody knows what it says and any answer might not fit.
# Killer/victim suspicion (24-27) and Irene's "Here's your killer!" (38): only an AI on the sender's side answers
# "Understood" (the other side reacting would look like a clue)
TEAM_ROGER_STAMPS = {24, 25, 26, 27, 38}
BOT_STAMP_CHANCE = 0.7          # probability that some AI replies to a sticker
BOT_STAMP_QUIET = 2.5           # seconds without answering after doing it (so the screen doesn't fill up)
ROOM_STAMP_ROW = 92.5           # in the room, how far down the sticker goes per row of the player list

# Pings a player uses to say "I'm handling this character": their side's AI leaves it alone and answers
# "Understood" (Pawn/Move/Search and Irene's same ones, which only Moriarty sees; Irene4 = "here's your killer").
CLAIM_PINGS = {1, 4, 7, 26, 27, 28, 30}
# Automatic pings when giving an order ("X orders Y..."): the AI also leaves that character, without answering.
ORDER_PINGS = set(range(13, 26)) | {31}
ROGER_STAMP = (0, 16, "roger")
# Solo matches (a single person against AIs) with Irene or Watson: help for the support role
IRENE_PICK_PINGS = {27, 28, 29}   # Irene's pings on a character ("Here's your killer!", move,
                                  # search): the Moriarty AI will move it this turn
IRENE_PLACE_PINGS = {26, 27, 28, 30}   # then, an Irene ping on the floor: where it takes it
IRENE_KILLER_STAMP = 38         # Irene's "Here's your killer!" sticker (it is a sticker, not a ping)
# Irene and Moriarty's private channel: the top row of both their pings (26-30, IRENE_1-5), the stickers that
# answer them and Irene's sticker are only seen by Moriarty's side. NO_PING: pingType of a sticker that doesn't
# answer a ping.
IRENE_PINGS = range(26, 31)
NO_PING = 34
IRENE_MAX_PICKS = 2
# Watson: "I suspect they're the killer" (ping 9 or its sticker) or "Danger" (ping 2) on someone -> the Sherlock AI
# watches them and accuses them at the end; "I don't think they're the killer" (ping 10 or its sticker) -> it forgets
# them.
# Watson hardly ever has the suspicion pings at hand: the usual thing is to use the stickers (Stamp.Type 25/24) or
# "Danger".
WATSON_SUSPECT_PINGS, WATSON_CLEAR_PINGS = {9, 2}, {10}
PING_SEARCH = 7   # Ping.Type.SEARCH ("Search"): the Watson AI puts it on the food it discovers
WATSON_SUSPECT_STAMPS, WATSON_CLEAR_STAMPS = {25}, {24}   # KILLER_SUSPICION / KILLER_NOSUSPICION
# During the match the room goes from "playing" to "command" with the first order and stays there: before,
# only "playing" was checked and, from the first turn, the AIs stopped paying attention to pings (Irene's
# orders, Watson's suspicions, "I'm handling it") and stopped announcing their characters.
IN_MATCH = ("playing", "command")
GHOST_CRIMINAL = "csr-moriarty"   # Moriarty AI of the training rooms (it is not a player of the room)
SELECTION_SECONDS = 60
SELECTION_WAIT = 20             # seconds to wait for everyone to reach the final deduction

SETTING_KEYS = {  # CreateRoom parameter -> (room variable, type)
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


# ------------------------------------------------------------------ WAMP sessions
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
        self.api = api          # for names and stats (server.Api)
        self.sessions = set()
        self.rooms = {}         # room_id -> Room
        self.next_sub = 1000
        self.next_pub = 1
        self.deferred = None    # events sent after the RESULT of the current call

    # ---------------- router helpers
    async def stage_poll(self):
        """Tells the rooms where who has (or not) the chosen custom stage has changed."""
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

    def room_of(self, pid, remote):
        """The room a player is in, only if asked from the same place as their game (None otherwise)."""
        for sess in self.sessions:
            if sess.player_id == pid and sess.remote == remote and sess.room is not None:
                return sess.room
        return None

    def match_state(self, pid, remote):
        """A player's ongoing match, only if they ask from the same place as their game (so nobody
        can look at someone else's role)."""
        for sess in self.sessions:
            if sess.player_id == pid and sess.remote == remote and sess.room is not None:
                return sess.room.match_state(pid)
        return None

    async def emit_now(self, topic, kw, var=None, exclude=None, eligible=None):
        """Like emit(), but without waiting for the RESULT of the current call."""
        held, self.deferred = self.deferred, None
        try:
            await self.emit(topic, kw, var=var, exclude=exclude, eligible=eligible)
        finally:
            self.deferred = held

    async def emit(self, topic, kw, var=None, exclude=None, eligible=None):
        """Publishes an EVENT to whoever is subscribed to the topic."""
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

    # ---------------- a connection's loop
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
        if room is not None and "tag" in kw and room.phase in IN_MATCH and room.private_team(sess, kw) == "moriarty":
            # Private channel of Moriarty and Irene (see private_team): the game sends it to everyone and each game
            # hides it, but replies to it still showed on Sherlock's side. Only Moriarty's side gets it now.
            eligible = room.team_members("moriarty", eligible) | {sess.player_id}
        await self.emit(topic, kw, var=room.vars if room else None, exclude=None if echo else sess, eligible=eligible)
        if room is not None and room.__dict__.pop("redealt", False):
            await room.control("ChangeSettings", None)      # everyone (the sender too) sees the roles dealt again
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

    # ---------------- match.* procedures
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
        if room.members.get(sess.player_id, {}).get("replaced"):
            return rc({"full": True, "success": False})   # left mid-match: an AI plays their role until it ends
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


# ------------------------------------------------------------------ room / match
def grid_pos(grid_id):
    """World centre of a game square (6x6 squares; id = 10*i + j, or 10*i - j if i < 0)."""
    try:
        g = int(grid_id)
    except (TypeError, ValueError):
        return 0.0, 0.0
    i, j = (g // 10, g % 10) if g >= 0 else (-((-g) // 10), (-g) % 10)
    return 6.0 * i, 6.0 * j


def same_order(a, b):
    """Two orders that do the same (Pawn.CheckInstructAllSame)."""
    keys = ("type", "grid", "targetId")
    return all(int(a.get(k, -1) if a.get(k) is not None else -1) == int(b.get(k, -1) if b.get(k) is not None else -1)
               for k in keys)


class Room:
    def __init__(self, hub, rid, owner):
        self.hub, self.id = hub, rid
        self.topic = f"crimesight.room.{rid}"
        self.owner = owner.player_id
        self.disabled = None       # this room's Character Selection (None: the server's own choice)
        self.members = {}          # player_id -> {"name", "role"}
        self.sessions = {}         # player_id -> Session
        self.settings = {"capacity": 1, "private": True, "stage": "", "time_limit": 180, "max_turn": 10}
        self.current_stage = None     # real stage of the ongoing match (if "Random" was chosen)
        self.vars = {"random_seed": random.randint(1, 2**31 - 1)}
        self.phase = "lobby"
        self.turn = 0
        self.killer = self.target = -1
        self.pawn_count = DEFAULT_PAWNS
        self.pending = {}          # phase -> {player_id: payload}
        self.reference = {}        # last reference_data per player
        self.selections = {}
        self.countdown_task = None
        self.created = time.time()
        self.bot_seq = 0
        self.object_items = {}     # furniture (cottage id) -> item it holds (dealt at the start)
        self.item_types = []       # Item.Type of each item of the match list (sent by the plugin)
        self.food_items, self.weapon_items, self.switch_items = set(), set(), set()
        self.events = {}           # player -> actions with points earned in the match
        self.switch_found = set()  # sides that have already found a switchboard plan
        self.turn_attacks = {}     # uniqId attacked this turn -> player who gave the order
        self.turn_potions = set()  # players who gave a heal order this turn
        self.turn_spray_rooms = set()  # rooms gassed with the spray this turn (it also injures)
        self.candidates = {}       # character -> (can be the killer, can be the victim) the last time it was checked
        self.critical = {}         # character -> was in critical state (isBlind) the last time it was checked
        self.pending_success = []  # actions that only count if they succeed: (player, action, type, leak/character, room/square, dark)
        self.clashed = set()       # characters where Moriarty has already clashed with a Sherlock order
        self.searched = {}         # furniture (cottage id) -> item that came out
        self.searched_now = {}     # furniture -> (turn it was searched, memo data): same-turn searches share the item
        self.picked_now = {}       # item on the floor -> (turn it was picked up, item): the same for pick-ups
        self.drops = {}            # item on the floor (cottage id) -> item index
        self.disabled_objects = set()
        self.bot_orders = {}
        self.claims = {"sherlock": set(), "moriarty": set()}   # characters a human says they're handling this turn
        self.irene_cmds = []       # solo: characters Irene asks the Moriarty AI to move (and where to)
        self.watson_suspect = None # solo: character Watson suspects (the Sherlock AI watches it)
        self.watson_food = set()   # furniture with food that Watson already knows
        self.bot_food = {}         # AI -> furniture with food it knows (the same as a person in its role)
        self.bot_new_food = {}     # Watson AI -> furniture with food it has just discovered this turn
        self.furniture = {}        # furniture -> square, for the whole stage (added by the plugin: "searchMap")
        self.furniture_at = {}     # furniture -> (x, y, z) in the world x10, above the furniture (for the pings)
        self.watson_done = False   # Watson has already been told there is no food left to discover
        self.ai_mem = ai.new_memory()   # what Sherlock's side has seen (hard AI)
        self.last_view = None
        self.turn_ref = {}         # reference_data from the start of the turn (for the AI and the hazards)
        self.hazard_prob = {}      # "threat"/"gaspipe" -> current probability (doubles on each miss)
        self.recorded = False      # result already written to the stats
        self.assault = False       # there was an Assault order this turn
        self.open_seats = 0        # seats the host keeps for humans (kicking an AI)
        self.bot_task = None
        self.match_order = []      # player order frozen when the match starts (the game keeps its own list)
        self.taking_orders = False # between StartCommandPhase and StartActionPhase (AI orders for this turn are ready)
        self.vote = None           # surrender vote running: {"from", "waiting", "message", "task"}
        self.stage_sig = {}        # players being waited for because of the stage (what the variables say)
        self.stamp_quiet = 0       # until when the AIs don't answer any more stickers
        self.stamp_seq = 0

    # ---- members and variables
    def authrole(self, pid):
        role = self.members.get(pid, {}).get("role", ROLE_DETECTIVE)
        return "Criminal" if role in (ROLE_CRIMINAL, ROLE_IRENE) else "Detective"

    def has_space(self):
        """A human can join if there is a free seat or an AI to replace."""
        return len(self.humans()) < int(self.settings.get("capacity", 1))

    def shown_capacity(self):
        return int(self.settings.get("capacity", 1))

    # ---- AI players (IA_1, IA_2...): they fill the free seats so the match is "normal"
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
        """Language of the host's game (sent at login); the AI names use it."""
        try:
            return self.hub.api.s.user(self.owner).get("lang") if self.owner else None
        except Exception:  # noqa: BLE001
            return None

    def ordered_members(self):
        """Order of the players: host, the rest of the humans and then the AIs."""
        pids = list(self.members)
        if self.phase != "lobby" and self.match_order:
            # During a match the order stays as it was at the start: the game keeps its own player list, so a
            # new host or an AI taking over a player who left must not move anyone (pings use this place)
            return [p for p in self.match_order if p in self.members] + [p for p in pids if p not in self.match_order]
        return sorted(pids, key=lambda p: (p != self.owner, bool(self.members[p].get("bot")), pids.index(p)))

    def member_index(self, pid):
        return self.ordered_members().index(pid)

    async def bot_say(self, tag, **extra):
        for pid in self.bots():
            kw = {"tag": tag, "id": self.member_index(pid)}
            kw.update(extra)
            await self.hub.emit(self.topic, kw, var=self.vars)

    async def on_player_message(self, sess, kw, eligible=None):
        """The AIs answer the coordination messages the clients send each other."""
        tag = kw.get("tag")
        if not self.bots() or not tag:
            return
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
        """A player sends a sticker: sometimes an AI (rarely two) answers, so it doesn't feel like
        you're playing alone, with whatever fits according to BOT_REPLIES (always a free sticker). Whoever saw the
        player's sticker sees it. A mod sticker counts as the game sticker it stands for; if it stands for
        none, it is not answered."""
        try:
            stamp, ping = int(kw.get("type", -1)), int(kw.get("pingType", NO_PING))
        except (TypeError, ValueError):
            return
        if ping != NO_PING:          # replying to a ping (e.g. "Got it" to "I'll control X"): nobody steps in
            return
        stamp = self.mod_means(stamp)
        if stamp not in BOT_REPLIES and stamp not in TEAM_ROGER_STAMPS:
            return
        now = time.time()
        if now < self.stamp_quiet or random.random() > BOT_STAMP_CHANCE or sess.player_id not in self.members:
            return
        self.stamp_quiet = now + BOT_STAMP_QUIET
        try:
            sender = int(kw.get("id", self.member_index(sess.player_id)))
            base_y = int(kw.get("posposY", 0))
        except (TypeError, ValueError):
            return
        bots = self.bots()
        if eligible and any(b in eligible for b in bots):     # a side's private message: that side replies
            bots = [b for b in bots if b in eligible]
        team = self.private_team(sess, kw)
        if team:                     # private: only that side answers, and only they see it
            bots = [b for b in bots if self.side(b) == team]
            eligible = self.team_members(team, eligible)
        if stamp in TEAM_ROGER_STAMPS:
            replies = (0,)
            if self.phase in IN_MATCH:
                bots = [b for b in bots if self.side(b) == self.side(sess.player_id)]
        else:
            replies = BOT_REPLIES[stamp]
        if not bots:
            return
        for n, pid in enumerate(random.sample(bots, 2 if len(bots) > 1 and random.random() < 0.2 else 1)):
            await asyncio.sleep(random.uniform(0.9, 2.2) if n == 0 else random.uniform(0.4, 1.0))
            if self.hub.rooms.get(self.id) is not self or pid not in self.members:
                return
            idx = self.member_index(pid)
            typ, data_index, text = _BOT_STAMP[random.choice(replies)]
            msg = dict(kw, id=idx, type=typ, setIndex=0, dataIndex=data_index)
            if "createId" in kw:            # in a match: the sticker shows next to the player's and in the log
                self.stamp_seq += 1
                msg.update(createId=(4000 + self.stamp_seq) * 16 + idx, parentCreateId=0, responseMsgId="",
                           name=self.members[pid]["name"], logMsgId="ctg_name_log_stamp_" + text)
                msg["posposX"] = int(kw.get("posposX", 0)) + random.choice((-14, 14)) * (n + 1)
            else:                           # in the room: it shows next to the AI's row
                msg["posposY"] = round(base_y - ROOM_STAMP_ROW * (idx - sender))
            targets = None if eligible is None else set(eligible) | {sess.player_id}
            await self.hub.emit(self.topic, msg, var=self.vars, eligible=targets)

    def mod_means(self, stamp):
        """Type of the game sticker a mod sticker stands for (its own type if it isn't from a mod or
        stands for none)."""
        room = getattr(self.hub, "mod_room", None)
        if room is None or stamp in BOT_REPLIES or stamp in TEAM_ROGER_STAMPS:
            return stamp
        means = next((s.get("means") for s in room.rs.get("stickers", []) if s.get("type") == stamp), None)
        return modpack.MEANS.get(means, stamp)

    def private_team(self, sess, kw):
        """Side that can see a private message, or None if everyone sees it. Only private to Moriarty's
        side: the top row of Moriarty's and Irene's pings (Order, Move, Search, "Here's your killer!"),
        Irene's "Here's your killer!" sticker and the stickers that answer those pings."""
        try:
            typ, ping = int(kw.get("type", -1)), int(kw.get("pingType", NO_PING))
        except (TypeError, ValueError):
            return None
        tag = kw.get("tag")
        if (tag == "stamp" and (typ == IRENE_KILLER_STAMP or ping in IRENE_PINGS)) or \
                (tag == "ping" and typ in IRENE_PINGS):
            return "moriarty"
        return None

    def team_members(self, team, eligible=None):
        return {p for p in self.members if self.side(p) == team and (eligible is None or p in eligible)}

    async def bot_claim(self, sess, kw, eligible=None):
        """A human points at a character with a ping ("I'll control X", "I'll move X"... or the one the game sends
        when giving it an order): their side's AI leaves that character this turn and, if it was a notice,
        one of them answers "Understood" next to the character. That way Irene can play with an AI Moriarty."""
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
        """Match of a single person against AIs."""
        return len(self.humans()) == 1

    def solo_support(self, team):
        """Solo, the person plays Irene or Watson on that side."""
        if not self.solo():
            return False
        me = self.humans()[0]
        return self.members[me]["role"] in (ROLE_IRENE, ROLE_WATSON) and self.side(me) == team

    async def solo_command(self, sess, kw, eligible=None):
        """Solo, Irene and Watson direct their side's AI with their pings:
        - Irene: "Here's your killer!" on a character -> the Moriarty AI will move it this turn (up to
          two); then, a ping of hers on the floor -> where to. If it is the armed killer and she takes it to the
          victim's square, it attacks.
        - Watson: "I suspect they're the killer" on someone -> the Sherlock AI moves whoever is in their room
          away from them (every turn); "I don't think they're the killer" on the same one -> it forgets them.
        Returns True if the ping was one of these orders."""
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
            pawn = self.pawn_near(x, z)          # stickers don't say who they point at: the closest one
        log.info("Sala %s turno %s: %s %s de %s sobre %r/%s en (%.0f, %.0f)", self.id, self.turn, tag, typ,
                 ROLE_KEY[role], obj, pawn, x, z)
        if role == ROLE_IRENE:
            mor = [b for b in self.bots() if self.members[b]["role"] == ROLE_CRIMINAL]
            if not mor:
                return False
            waiting = self.irene_cmds and self.irene_cmds[-1]["dest"] is None
            if tag == "ping" and typ in IRENE_PLACE_PINGS and waiting and (pawn < 0 or typ != 29):
                self.irene_cmds[-1]["dest"] = (x, z)          # "where to": an Irene ping after choosing
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
        """Character closest to a point of the world (in the turn's reference_data)."""
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
        """Orders Irene has asked the Moriarty AI for (solo)."""
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
        """Sherlock AI (solo with Watson): moves whoever is in the suspect's room away from them."""
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
        """An AI answers "Understood" with a sticker next to where the ping pointed."""
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
        team = self.private_team(sess, kw)
        if team:                     # it answers something private of its side: only they see it
            eligible = self.team_members(team, eligible)
        msg = {"tag": "stamp", "createId": (4000 + self.stamp_seq) * 16 + idx, "id": idx, "type": typ_s,
               "setIndex": 0, "dataIndex": data_index, "posposX": x + 14, "posposY": y, "posposZ": z,
               "isClick": 1, "liveTime": 0, "parentCreateId": 0, "name": self.members[pid]["name"],
               "logMsgId": "ctg_name_log_stamp_" + text, "pingType": NO_PING, "responseMsgId": "", "pingName": "",
               "pingPlayerName": "", "pingPlayerId": 0, "ignore": 0, "isCutScene": 0}
        targets = None if eligible is None else set(eligible) | {sess.player_id}
        await self.hub.emit(self.topic, msg, var=self.vars, eligible=targets)

    def bot_ping_audience(self, bot, typ):
        """Who sees an AI's ping: everyone, like a person's pings, except the private top row (Moriarty's side only)."""
        return self.team_members("moriarty") if typ in IRENE_PINGS else None

    async def bot_announce(self, delay=None):
        """Like a person would, each AI tells its human teammates with a ping which characters
        it will move this turn ("I'll control X"). That way you know what your AI teammate does, and the game's
        hints ("X may have received orders from...") work instead of saying nobody knows."""
        await asyncio.sleep(random.uniform(1.5, 3.0) if delay is None else delay)
        if self.hub.rooms.get(self.id) is not self or self.phase not in IN_MATCH:
            return
        pawns = {int(p.get("pawnId", -1)): p for p in (self.turn_ref.get("pawns") or []) if isinstance(p, dict)}
        humans = self.humans()
        pinged = getattr(self, "bot_pinged", None)
        if pinged is None:
            pinged = self.bot_pinged = {}
        # Watson AI: the furniture with food it has just discovered (its ability), with a "Search" ping
        # (Ping.Type.SEARCH) on it, like a person would so that Sherlock goes for it
        for bot, obj in list((getattr(self, "bot_new_food", None) or {}).items()):
            mates = [h for h in humans if self.side(h) == self.side(bot)] if bot in self.members else []
            grid = self.object_grid(obj)
            if not mates or grid is None:
                continue
            x, z = grid_pos(grid)
            cx, cz = round(x * 10), round(z * 10)
            # above the furniture if the plugin sent it; otherwise, in the centre of its square
            px, py, pz = self.furniture_at.get(obj, (cx, 10, cz))
            msg = {"tag": "ping", "id": self.member_index(bot), "type": PING_SEARCH, "call": 2,
                   "posposX": px, "posposY": py, "posposZ": pz,
                   "callposposX": cx, "callposposY": 0, "callposposZ": cz,
                   "name": self.members[bot]["name"], "obj": "", "ignore": 0}
            await self.hub.emit(self.topic, msg, var=self.vars, eligible=self.bot_ping_audience(bot, PING_SEARCH))
            log.info("Sala %s turno %s: Watson IA senala la comida del mueble %s", self.id, self.turn, obj)
            self.bot_new_food.pop(bot, None)       # pinged once: not again if the AI announces again this turn
            await asyncio.sleep(random.uniform(0.4, 0.9))
        for bot, orders in list((self.bot_orders or {}).items()):
            if bot not in self.members:
                continue
            team = self.side(bot)
            mates = [h for h in humans if self.side(h) == team]
            if not mates:
                continue
            idx = self.member_index(bot)
            typ = 26 if team == "moriarty" else 1   # Moriarty's side: the command ping of its private top row
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
                await self.hub.emit(self.topic, msg, var=self.vars, eligible=self.bot_ping_audience(bot, typ))
                await asyncio.sleep(random.uniform(0.4, 0.9))

    async def _bot_heartbeat(self):
        """During the match the AIs confirm every few seconds that they are ready."""
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
                self.members.pop(self.bots()[-1])   # the human replaces an AI
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
            if any(h != pid for h in self.humans()):
                # Leaves mid-match (quits, closes the game, loses the connection...) while other people are
                # still playing: the loss goes on their profile and an AI plays their role until the end
                await self.replace_with_ai(sess)
                return
            # Leaves mid-match (closes the game, loses the connection...) and nobody else is left: it counts
            # as surrendering. Their side loses and the other one wins.
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

    async def replace_with_ai(self, sess):
        """A player leaves mid-match while other people are still playing. The loss is recorded for them now
        and an AI plays their role until the match ends. The game keeps them in its player list (removing
        someone mid-match would shift everyone's place in it); they are taken out back in the lobby."""
        pid = sess.player_id
        m = self.members[pid]
        log.info("Sala %s: %s se va a mitad de partida; una IA lleva su papel", self.id, m["name"])
        self.record_quitter(pid)
        tag = ai.BOT_NAMES.get(str(self.owner_lang() or "").upper(), ai.BOT_NAMES["EN"])[0]
        m["human_name"] = m["name"]
        m["name"] = f"{m['human_name']} ({tag})"       # same word as the AI names in the room ("AI", "IA", "KI"...)
        # Hard, or Expert if another AI in the match is Expert or Nightmare (same rule as the solo partner AI)
        m.update({"bot": True, "replaced": True, "ready": True, "slot": None, "difficulty": self.support_level()})
        self.sessions.pop(pid, None)
        self.hub.unsubscribe(sess, self.topic)
        if sess.room is self:
            sess.room = None
        self.reference.pop(pid, None)       # their turn data would be out of date from now on
        for got in self.pending.values():   # the AI answers for them from now on
            if isinstance(got, dict):
                got.pop(pid, None)
        if self.owner == pid:
            self.owner = self.humans()[0]
        self.log_call("left", self.turn, pid)
        await self.control("CsrReplaced", {"PlayerId": pid, "PlayerName": m["human_name"], "NewName": m["name"]})
        if self.vote:
            if self.vote["from"] == pid:
                await self.end_vote("cancel", pid)
            elif pid in self.vote["waiting"]:
                self.vote["waiting"].discard(pid)
                if not self.vote["waiting"]:
                    await self.team_forfeit()
        if self.taking_orders and self.turn_ref:
            self.plan_bots(self.turn_ref, only=pid)     # it already gives orders this turn
        if not self.bot_task or self.bot_task.done():
            self.bot_task = asyncio.ensure_future(self._bot_heartbeat())
        self.refresh_vars()
        await self.start_if_prepared()      # if they left while the match was loading
        await self.check_phase_complete()

    def record_quitter(self, pid):
        """Loss for a player who left a match that goes on without them (no points, no action bonuses)."""
        m = self.members[pid]
        role = int(m["role"])
        u = self.hub.api.s.user(pid)
        pts = stats.record_match(u, role, "abandon", [], self.current_stage or self.settings.get("stage", ""),
                                 match_id=getattr(self, "match_id", None), level=self.level(), finish="abandon")
        log.info("Sala %s: %s (%s) ABANDONA, +%s puntos -> %s", self.id, m["name"], ROLE_KEY.get(role, role),
                 pts, stats.summary(u))
        self.log_call("awarded", pid, "abandon", [], pts)
        self.hub.api.s.save()

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
        # the game only lets the match start with a full room: while someone is awaited, "one missing"
        v["attendance"] = len(self.members) - (1 if wait else 0)
        v["detective_count"], v["criminal_count"] = self.side_counts()
        for pid in self.ordered_members():
            m = self.members[pid]
            v["player_" + pid] = f"{m['name']} ({wait[pid]})" if pid in wait else m["name"]
            v["role_" + pid] = int(m["role"])
            v["ready_" + pid] = bool(m.get("ready", False))
            v["match_count_" + pid] = int(m.get("match_count", 0))
        self.vars = v

    def detective_orders(self, pid):
        """Orders per turn for a Sherlock, as the game works them out (GameManager.GetInstructPawnCount online):
        total / detective_count, where total is 4 with two Sherlocks and 3 otherwise. Watson has his own count
        and isn't part of it: a Sherlock next to a Watson keeps his 3 orders."""
        d = max(1, len(self.players_by_role([ROLE_DETECTIVE])))
        return max(1, (4 if d == 2 else 3) // d)

    def side_counts(self):
        """(detectives, criminals) for the room variables. detective_count is the number of SHERLOCKS: the game
        gives each Sherlock total / detective_count orders (GameManager.UpdateInstructPawnCount/GetInstructPawnCount:
        total 4 with two Sherlocks, 3 otherwise) and Watson has his own fixed count. Counting Watson as a detective
        left Sherlock with 4 / 2 = 2 orders in a 2v2. In the lobby the AIs and the players on "Random" have no role
        yet, so the counts come from the seats assign_roles() hands out."""
        n = len(self.members)
        if self.phase == "lobby" and n >= 2:
            irene = int(self.settings.get("irene_count", 0) or 0)
            watson = int(self.settings.get("watson_count", 0) or 0)
            criminals = min(1 + irene, n - 1)
            return max(1, n - 1 - irene - watson), criminals
        return (max(1, sum(1 for m in self.members.values() if m["role"] == ROLE_DETECTIVE)),
                sum(1 for m in self.members.values() if m["role"] in (ROLE_CRIMINAL, ROLE_IRENE)))

    def apply_var_ops(self, ops):
        locked = self.counting_down()
        for op in ops:
            for k, val in (op.get("set") or {}).items():
                if k.startswith("role_") and k[5:] in self.members:
                    if locked:
                        # the roles are locked during the countdown (they were dealt when it started): the change
                        # is ignored and everyone gets the room's roles again; cancelling the countdown unlocks them
                        if self.members[k[5:]]["role"] != int(val):
                            log.info("Sala %s: cambio de rol durante la cuenta atras: ignorado", self.id)
                            self.redealt = True
                        continue
                    self.members[k[5:]]["role"] = int(val)
                elif k.startswith("ready_") and k[6:] in self.members:
                    self.members[k[6:]]["ready"] = bool(val)
                else:
                    self.vars[k] = val
            for k in op.get("unset") or op.get("delete") or []:
                self.vars.pop(k, None)
        self.refresh_vars()

    def counting_down(self):
        return self.phase == "lobby" and self.countdown_task is not None and not self.countdown_task.done()

    async def control(self, cmd, data=None):
        await self.hub.emit(self.topic, {"Control": {cmd: data}}, var=self.vars)

    async def control_to(self, pids, cmd, data=None):
        """Like control(), but only for those players."""
        await self.hub.emit(self.topic, {"Control": {cmd: data}}, var=self.vars, eligible=set(pids))

    def humans(self):
        return [pid for pid in self.members if pid in self.sessions and not self.sessions[pid].ws.closed]

    def stage_wait(self, starting=False):
        """Players waited for before the match can start, because they don't have (yet) the chosen custom
        stage: {player: notice next to their name}. Empty if it can start."""
        stage = self.settings.get("stage") or ""
        if not starting and (self.phase != "lobby" or self.current_stage):
            return {}
        sync, missing = STAGE_WAIT.get(str(self.owner_lang() or "").upper(), STAGE_WAIT["EN"])
        humans = self.humans()
        if stage in EXTRA_STAGES:                    # "Test stage": everyone has their own
            return {p: missing for p in humans if p != self.owner}
        if not stage.startswith(CUSTOM_STAGE_PREFIX):
            return {}
        room_stages = getattr(self.hub.api, "stages", None)
        if room_stages is None:
            return {p: missing for p in humans}
        states = {p: room_stages.state(stage, p) for p in humans}
        return {p: sync if st == "sync" else missing for p, st in states.items() if st != "ok"}

    def clamp_turns(self):
        """Maximum turns: from 1 to 99 (the original game allowed 6 to 15; 10 by default).
        Time per turn: from 60 to 999 seconds."""
        try:
            self.settings["max_turn"] = max(1, min(99, int(self.settings.get("max_turn", 10))))
        except (TypeError, ValueError):
            self.settings["max_turn"] = 10
        # Time per turn: from 60 to 999 seconds (the original: 10-999 in private rooms, 60-180 in public ones)
        try:
            self.settings["time_limit"] = max(60, min(999, int(self.settings.get("time_limit", 180))))
        except (TypeError, ValueError):
            self.settings["time_limit"] = 180

    def match_state(self, pid):
        """For a guest's launcher: if they are in the middle of a match, with which role."""
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
        await self.send_partner_icons()

    async def send_partner_icons(self, pids=None):
        """Room setting "Reveal Partner (Detective Team)" (off by default, as in the original game): the plugin shows it in
        the Match Settings window and, when it is on, adds Watson's icon for Sherlock and Sherlock's for Watson in
        the player list. Games without the plugin ignore it."""
        on = self.settings.get("partner_icons")
        on = on.strip().lower() in ("1", "true") if isinstance(on, str) else bool(on)
        data = {"Show": "1" if on else "0"}       # as text: the plugin reads every value as text
        if pids is None:
            await self.control("CsrPartnerIcons", data)
        else:
            await self.control_to(pids, "CsrPartnerIcons", data)

    # ---- room procedures
    async def p_CreateRoom(self, sess, p):
        for k, v in p.items():
            self.settings[k] = v
        self.pick_quick_mode()
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
            # The game's solo room (the training): right after creating it, the game starts the
            # match with the room's player list. If that list arrives after the
            # answer, it is empty and the game closes. So here it goes before.
            await self.hub.emit_now(self.topic, {"Control": {"Enter": {
                "PlayerId": sess.player_id, "PlayerName": sess.name, "RandomSeed": "random_seed"}}}, var=self.vars)
        else:
            await self.announce_enter(sess)
        return rc(self.settings_result())

    def pick_quick_mode(self):
        """Quick Match "No preference" asks for a room of any size (capacity 0): the original server put you in
        whatever room was waiting. Here one of the Quick Match modes is drawn, and the AIs fill its free seats."""
        try:
            cap = int(self.settings.get("capacity", 1))
        except (TypeError, ValueError):
            cap = 0
        if not self.settings.get("quick") or cap >= 1:
            return
        cap, irene, watson = random.choice(QUICK_MODES)
        self.settings.update({"capacity": cap, "irene_count": irene, "watson_count": watson})
        log.info("Sala %s: partida rapida sin preferencia -> %s jugadores (Irene %s, Watson %s)",
                 self.id, cap, irene, watson)

    async def p_ChangeCapacity(self, sess, p):
        self.settings["capacity"] = max(len(self.humans()), min(4, int(p.get("capacity", self.settings["capacity"]))))
        self.open_seats = 0     # when the number of players changes, the AIs take the free seats again
        self.fill_bots()
        self.refresh_vars()
        await self.control("ChangeCapacity", None)
        return rc({"changed": True})

    async def p_ChangeSettings(self, sess, p):
        self.settings.update(p)
        self.clamp_turns()
        self.refresh_vars()
        await self.control("ChangeSettings", None)
        await self.send_partner_icons()
        return rc({})

    async def p_Kick(self, sess, p):
        pid = str(p.get("player_id") or "")
        if "#" in pid:
            # The plugin picks the difficulty with its window: "bot0001#expert", "bot0001#expert#all", "bot0001#free"
            pid, _, choice = pid.partition("#")
            return await self.set_bot_difficulty(sess, pid, choice)
        bot = self.members.get(pid, {})
        if sess.player_id == self.owner and bot.get("bot"):
            # Kicking an AI changes its difficulty: Normal -> Hard -> Easy -> free seat
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
        """The plugin's AI window: difficulty of one AI (or of all of them) or leaving its seat free."""
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
        if self.counting_down():
            # roles locked during the countdown: everyone gets the room's roles again
            self.refresh_vars()
            await self.control("ChangeSettings", None)
            return rc({})
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
        self.assign_roles()
        self.boost_support()
        self.current_stage = self.pick_stage()
        want = self.forced()
        self.draw_roster([c for c in (want or {}).values() if c])
        self.apply_forced(want)
        self.refresh_vars()
        await self.control("StartCountDown", {"CountDownTimer": COUNTDOWN_SECONDS})
        self.countdown_task = asyncio.ensure_future(self._countdown())
        return rc({})

    def forced(self):
        """Killer/target picked in the launcher's developer mode (None if none)."""
        try:
            f = forced_roles() if callable(forced_roles) else None
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(f, dict):
            return None
        f = {k: (str(f.get(k)) if f.get(k) else None) for k in ("killer", "target")}
        return f if any(f.values()) else None

    def apply_forced(self, want):
        """Makes the picked characters the killer/target (in whatever place the draw gave them)."""
        if not want:
            return
        positions = (getattr(self, "roster", None) or {}).get("positions") or {}

        def index(cid):
            if not cid:
                return None
            if cid.startswith("orig:"):
                key = cid[5:]
                if key in modelpack.PAWNS and not positions.get(key):
                    return modelpack.PAWNS.index(key)
                return None
            for key, v in positions.items():
                if v == cid and key in modelpack.PAWNS:
                    return modelpack.PAWNS.index(key)
            return None
        k, t = index(want.get("killer")), index(want.get("target"))
        k = k if k is not None and k < self.pawn_count else None
        t = t if t is not None and t < self.pawn_count and t != k else None
        if k is None and t is None:
            log.info("Sala %s: [dev] no pude poner el asesino/objetivo elegido (%s)", self.id, want)
            return
        killer = k if k is not None else self.killer
        target = t if t is not None else self.target
        if killer == target or killer < 0 or target < 0:
            others = [i for i in range(self.pawn_count) if i != (k if k is not None else t)]
            if k is None:
                killer = random.choice(others)
            else:
                target = random.choice(others)
        self.killer, self.target = killer, target
        log.info("Sala %s: [dev] asesino %s, objetivo %s (elegidos: %s)", self.id, self.killer, self.target, want)

    def draw_roster(self, must=()):
        """Which character is seen in each place in this match (the room's new characters, at random among the
        ticked ones). Each player's launcher checks it (GET /revival/roster) and passes it to the plugin."""
        mr = getattr(self.hub, "model_room", None)
        if mr is None:
            return
        try:
            before = getattr(mr, "before_draw", None)
            if before is not None:
                before()            # the host's latest Character Selection (set by the launcher)
        except Exception:  # noqa: BLE001
            log.exception("No pude leer el Selector de personajes")
        try:
            r = mr.draw(self.disabled, must)
            self.hub.roster_seq = getattr(self.hub, "roster_seq", 0) + 1
            r["id"] = "%s-%d" % (self.id, self.hub.roster_seq)
            self.roster = r
            if any(r["positions"].values()) or r["traitor"]:
                log.info("Sala %s: reparto de personajes %s, traidor %s", self.id, r["positions"], r["traitor"])
        except Exception:  # noqa: BLE001  (the draw must never stop a match)
            log.exception("No pude sortear los personajes")

    def pick_stage(self):
        """Real stage of this match: the chosen one, or a random one if it is "Random" (or unknown).
        A creator stage only counts if every player in the room has the same one (each one's launcher
        says so). The room doesn't let the match start while someone lacks it; if the order still
        arrives, a normal stage is played and nobody stays on a black screen."""
        stage = self.settings.get("stage") or ""
        if stage in STAGES:
            return stage
        if stage.startswith("Stage_Tutorial"):
            # Solo training: its scripted characters are placed for the original mansion. On another map one of them
            # ended up inside a wall and the first turn never started ("Case 01: The First Killer").
            return "Stage_Yokn"
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
            self.countdown_task = None          # roles unlocked right away
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
        self.match_order = self.ordered_members()
        self.match_id = f"{self.id}-{int(time.time())}-{secrets.token_hex(3)}"
        try:
            self.mlog = matchlog.MatchLog(os.path.dirname(self.hub.api.s.path), self.match_id,
                                          self.current_stage or self.settings.get("stage", ""), self.settings,
                                          self.members, self.killer, self.target, ROLE_KEY)
        except Exception:  # noqa: BLE001  (the log must never stop a match)
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
        """Solo with Irene or Watson, the AI on your side plays on Hard, and that is its name in the
        match (before it still said "Normal" and it made no sense). Back in the room it gets its own back."""
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
        """Level of the partner AI when solo: Hard, or Expert if the rivals are experts."""
        rivals = [m.get("lobby_difficulty") or m.get("difficulty") for m in self.members.values() if m.get("bot")]
        return "expert" if {"expert", "nightmare"} & set(rivals) else "hard"

    def restore_support(self):
        for m in self.members.values():
            if m.get("bot") and m.get("lobby_difficulty"):
                m["difficulty"] = m.pop("lobby_difficulty")
                m["name"] = ai.bot_name(m["slot"], m["difficulty"], self.owner_lang())

    def assign_roles(self):
        """Hands out the roles with the match's seats: 1 Moriarty, the Irenes/Watsons the room asks for
        and the rest Sherlock. What each one picked is respected; if more people ask for a role than
        there are seats, it is drawn among them (people before AIs) and those left
        out, like the "random" ones, get one of the remaining seats at random."""
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
            asking.sort(key=lambda pid: bool(self.members[pid].get("bot")))   # people first
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
        """Each client sends its stage's data; when everyone has, RoleData starts the match."""
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
        await self.start_if_prepared()
        return rc({})

    async def start_if_prepared(self):
        if "prepare" in self.pending and self._complete("prepare"):
            self.pending.pop("prepare", None)
            self.phase = "playing"
            await self.send_partner_icons(self.humans())     # before the roles, so the player list is right at once
            # Each player gets what their role knows (GameManager.SelectOpenWeapon/SelectOpenFood)
            for pid in self.humans():
                await self.control_to([pid], "RoleData", self.role_data(pid))

    def deal_items(self):
        """Deals the match's items among the furniture, like the original server.
        The indices follow ItemManager.CreateMatchItemList online: first the food, then
        the weapons and then the rest (boards, sketches, notes, potions, sprays). There is one piece of furniture
        per item (MatchSettings.GetNeedSearchObjectCount)."""
        md = self.match_data or {}
        n = int(md.get("matchItemCount", 42) or 42)
        food = int(md.get("foodCount", 17) or 0)
        weapons = int(md.get("weaponCount", 15) or 0)
        items = list(range(n))
        random.shuffle(items)
        self.object_items = dict(enumerate(items))
        self.item_types = []       # Item.Type of each item, from the plugin ("itemTypes" in the turn data)
        self.ai_mem = ai.new_memory()
        self.watson_food, self.watson_done = set(), False
        self.bot_food = {}
        self.bot_food_turn = {}     # Watson AI -> turn in which it already discovered its furniture with food
        self.furniture, self.furniture_at = {}, {}
        self.irene_cmds, self.watson_suspect = [], None
        self.food_items = set(range(food))
        self.weapon_items = set(range(food, food + weapons))
        # Switchboards (plans): right after the weapons, one per switchboard in the settings. Checked
        # with the saved matches: every switchboard Moriarty broke was in the furniture of item 32, 33 or 34
        # (17 food + 15 weapons = 32), never in the last ones of the list
        sw = int(self.settings.get("switchboard_count", 0) or 0)
        self.switch_items = set(range(food + weapons, min(n, food + weapons + sw)))
        self.events = {}
        self.switch_found = set()
        self.turn_attacks = {}
        self.turn_potions = set()
        self.turn_spray_rooms = set()
        self.candidates = {}
        self.critical = {}
        self.pending_success = []
        self.clashed = set()
        log.info("Sala %s: %s objetos repartidos (%s comida, %s armas)", self.id, n, food, weapons)

    def bot_knowledge(self, pid):
        """Where an AI knows there are weapons and food: the same as a person in its role (role_data).
        Moriarty, everything; the rest, no weapons and FOOD_OPEN_COUNT random pieces of furniture with food; Watson,
        also, a new one each turn (like watson_reveal). Called once per turn for each AI."""
        role = self.members.get(pid, {}).get("role")
        if role == ROLE_CRIMINAL:
            return set(self.objects_with(self.weapon_items)), set(self.objects_with(self.food_items))
        foods = self.objects_with(self.food_items)
        known = self.bot_food.get(pid)
        if known is None:
            known = self.bot_food[pid] = set(random.sample(foods, min(FOOD_OPEN_COUNT, len(foods))))
        revealed = self.__dict__.setdefault("bot_food_turn", {})
        if role == ROLE_WATSON and revealed.get(pid) != self.turn:
            # one new furniture per turn: this also runs again when the AI changes plan mid-turn (someone takes
            # one of its characters), and that used to reveal and ping another one each time
            revealed[pid] = self.turn
            hidden = [o for o in foods if o not in known]
            if hidden:
                # better one that can be pointed at with a ping (on a square of the turn's data)
                o = random.choice([x for x in hidden if self.object_grid(x) is not None] or hidden)
                known.add(o)
                self.bot_new_food[pid] = o      # bot_announce tells Sherlock with a "Search" ping
        return set(), known - set(self.searched)

    def object_grid(self, obj):
        """Square where a piece of furniture is: from the full map the plugin sends or, if there is none, from the
        turn's data (squares within the characters' reach)."""
        if obj in self.furniture:
            return self.furniture[obj]
        ref = self.turn_ref or {}
        lists = [r.get("gridList") for r in ref.get("roomList") or [] if isinstance(r, dict)]
        lists += [p.get("gridList") for p in ref.get("pawns") or [] if isinstance(p, dict)]
        for grids in lists:
            for g in grids or []:
                if isinstance(g, dict) and any(isinstance(o, dict) and o.get("id") == obj
                                               for o in g.get("searchObjects") or []):
                    return g.get("gridId")
        return None

    def objects_with(self, items):
        """Furniture not searched yet that holds any of those items."""
        return sorted(o for o, i in self.object_items.items() if i in items and o not in self.searched)

    def role_data(self, pid):
        """What each role knows at the start: Moriarty, every weapon and all the food; the rest (Irene
        too), no weapons and only a few places with food (MatchSettings.foodOpenCount), picked
        at random for each player. Irene knows the same as Sherlock: "what she knows about what happens in the
        mansion is the same as us" (Sherlock's tip about Irene); her "green light" is the one that
        marks the known food, the same one Sherlock sees."""
        foods = self.objects_with(self.food_items)
        if self.members.get(pid, {}).get("role") != ROLE_CRIMINAL:
            foods = sorted(random.sample(foods, min(FOOD_OPEN_COUNT, len(foods))))
            if self.members.get(pid, {}).get("role") == ROLE_WATSON:
                self.watson_food |= set(foods)
            return {"weaponList": [], "foodList": foods}
        return {"weaponList": self.objects_with(self.weapon_items), "foodList": foods}

    # ---- turn phases
    def _store(self, phase, sess, p):
        self.pending.setdefault(phase, {})[sess.player_id] = p
        ref = p.get("reference_data")
        if isinstance(ref, str):
            try:
                ref = json.loads(ref)
            except ValueError:
                ref = self.read_reference(ref)
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
            # The plugin adds all the stage's furniture with its square (SearchMap in CrimeSightRevivalPartner.cs)
            for row in ref.get("searchMap") or []:      # [furniture, square, x, y, z]
                try:
                    self.furniture[int(row[0])] = int(row[1])
                    if len(row) >= 5:
                        self.furniture_at[int(row[0])] = (int(row[2]), int(row[3]), int(row[4]))
                except (TypeError, ValueError, IndexError):
                    continue
            if isinstance(ref.get("pawns"), list) and ref["pawns"]:
                self.pawn_count = len(ref["pawns"])
            # The plugin also sends the type of each item of the match list (Item.Type), so the server knows which
            # ones are notes (memos)
            types = ref.get("itemTypes")
            if isinstance(types, list) and types:
                try:
                    first = not self.item_types
                    self.item_types = [int(t) for t in types]
                    if first:
                        # what the match list holds and how much furniture the stage has (to check empty furniture:
                        # the game has lines and a sound for searching and finding nothing)
                        kinds = {}
                        for t in self.item_types:
                            kinds[t] = kinds.get(t, 0) + 1
                        log.info("Sala %s: lista de objetos %s (tipo: cuantos; 0 = vacio, 9 = nota), %s muebles en el "
                                 "escenario", self.id, dict(sorted(kinds.items())), len(self.furniture))
                except (TypeError, ValueError):
                    pass

    def read_reference(self, text):
        """Unreadable turn summary: the furniture map the plugin adds ("searchMap") is removed and it is
        tried again, so that a broken map never leaves the match without data (the AI would stop playing)."""
        log.warning("Sala %s: resumen del turno ilegible, se intenta sin el mapa de muebles", self.id)
        key = text.find('"searchMap"')
        if key < 0:
            return None
        start = text.find("[", key)
        depth, end = 0, -1
        for i in range(start, len(text)) if start >= 0 else ():
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end < 0:
            return None
        rest = text[:key] + text[end:]
        for a, b in ((",,", ","), ("{,", "{"), (",}", "}")):
            rest = rest.replace(a, b, 1)
        ref = None
        for cand in (rest, rest.rstrip(", ") + "}"):
            try:
                ref = json.JSONDecoder().raw_decode(cand)[0]   # whatever is left at the end doesn't matter
                break
            except ValueError:
                continue
        if not isinstance(ref, dict):
            return None
        try:
            ref["searchMap"] = json.loads(text[start:end])
        except ValueError:
            pass
        return ref

    def _complete(self, phase):
        got = self.pending.get(phase, {})
        who = self.humans()
        if phase == "answer":  # only Sherlock's side accuses
            who = [p for p in who if self.members[p]["role"] in (ROLE_DETECTIVE, ROLE_WATSON)]
        return all(pid in got for pid in who)

    def detect_kill(self, ref):
        """The client's GameManager.CheckKill: armed killer on the victim's square and no
        witness awake in the room. In a blackout only those in a lit room
        or on the same square see. Some threats also count as witnesses."""
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
        """GameManager.ResultPhaseCallback: the final result of the online match.
        isKill True -> KILL_SUCCESS (Moriarty wins); False -> ARREST_SUCCESS (the killer arrested).
        Without this message the client keeps waiting (black screen)."""
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
            try:
                self.score_ruled_out(self.turn_ref)   # what is dropped between one turn and the next
                self.score_critical(self.turn_ref)
                self.score_success(None, self.turn_ref, final=True)
            except Exception:  # noqa: BLE001 - action points must never stop the match
                log.exception("Sala %s turno %s: fallo mirando los descartes", self.id, self.turn)
            self.claims = {"sherlock": set(), "moriarty": set()}
            self.irene_cmds = []
            self.plan_bots(self.turn_ref)
            self.taking_orders = True
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
            try:
                self.score_turn_end(ref)
            except Exception:  # noqa: BLE001 - action points must never stop the match
                log.exception("Sala %s turno %s: fallo mirando las acciones del final del turno", self.id, self.turn)
            self.log_call("turn_end", self.turn, ref)
            if self.detect_kill(ref):
                # Online, the server decides the murder (the client doesn't check it on its own)
                await self.end_by_kill()
            else:
                if int(ref.get("isLastTurn", 0) or 0):
                    # It was the final turn after the killer was found out (failed Assault or deduction) and the
                    # victim is still alive: result ARREST_SUCCESS, Sherlock's side wins.
                    log.info("Sala %s turno %s: fin del turno final sin asesinato, detenido el asesino", self.id, self.turn)
                    await self.send_result(False)
                    self.conclude("sherlock", {ROLE_DETECTIVE: [ACT_DEDUCED], ROLE_WATSON: [ACT_DEDUCED]})
                else:
                    await self.control("StartTransitionPhase", {"Turn": self.turn, "Data": {"isDanger": self.is_danger()}})
        if "selection" in self.pending and self._complete("selection"):
            await self.start_selection()
        if "answer" in self.pending and self._complete("answer"):
            await self.finish_answers()

    def watson_reveal(self):
        """Watson's ability: at the start of each turn she discovers a piece of furniture with food she didn't know yet
        (the game highlights it, adds it to her list and Watson comments on it). When there is none left, she is told once.
        GameManager.CommandPhaseCallback reads it from the "watson" data (only in Watson's game)."""
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

    def plan_bots(self, ref, only=None):
        """The AI decides its orders with the state of the turn the client sends.
        only: plan just this AI and keep the others' orders (an AI that takes over a player mid-turn)."""
        if only is None:
            self.bot_orders = {}
            self.bot_new_food = {}     # Watson AI -> furniture with food it has just discovered this turn
        bots = [only] if only else self.bots()
        if not bots or not ref.get("pawns"):
            return
        gone = set(self.searched) | self.disabled_objects
        # One view per side (so teammates don't search the same furniture); what each AI knows about
        # where the weapons and the food are is set before it decides (bot_knowledge)
        views = {"moriarty": ai.View(ref, gone), "sherlock": ai.View(ref, gone)}
        for v in views.values():
            v.max_turn = int(self.settings.get("max_turn") or 0) or None
        prof = getattr(self, "profiles", None) or {}
        self.ai_mem["prof_moriarty"] = prof.get("moriarty")     # what was learned from people (Nightmare)
        self.ai_mem["prof_sherlock"] = prof.get("sherlock")
        self.last_view = view = views["sherlock"]
        rng = random.Random()
        cri_players = self.players_by_role([ROLE_CRIMINAL])
        # Each side only knows which characters its own team has ordered (and the ones its
        # humans have claimed with a ping this turn)
        taken = {team: set(c) for team, c in self.claims.items()}
        for b, given in self.bot_orders.items():      # orders other AIs already have this turn
            taken[self.side(b)] |= {o["pawnId"] for o in given}
        prio = {ROLE_CRIMINAL: 0, ROLE_IRENE: 1, ROLE_DETECTIVE: 2, ROLE_WATSON: 3}
        for pid in sorted(bots, key=lambda b: prio.get(self.members[b]["role"], 9)):
            m = self.members[pid]
            idx = self.member_index(pid)
            role, diff = m["role"], m["difficulty"]
            team = "moriarty" if role in (ROLE_CRIMINAL, ROLE_IRENE) else "sherlock"
            if self.solo_support(team):
                diff = self.support_level()  # solo, Irene's/Watson's partner plays seriously
            views[team].weapon_objects, views[team].food_objects = self.bot_knowledge(pid)
            if role == ROLE_CRIMINAL:
                n = max(1, 2 // max(1, len(cri_players)))
                own, _ = ai.plan_moriarty(views[team], idx, self.killer, self.target, n, diff, rng, taken[team],
                                          memory=self.ai_mem)
                if self.solo_support(team) and self.irene_cmds:
                    # What Irene asks for goes first, except an assault: if Moriarty can kill this turn, it kills
                    # (before, Irene's orders took up both of its characters and it never attacked)
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
                n = self.detective_orders(pid)
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
        """Gathers everyone's orders. If several order the same character: Moriarty beats everyone,
        Irene beats Sherlock/Watson and among the rest it is drawn. If Moriarty overrides a different order from
        Sherlock/Watson, the order is marked (isBatting) and Sherlock's side notices it.
        The characters nobody ordered act on their own (online the server decides)."""
        by_pawn, from_criminal, from_detective, kill, owner = {}, set(), {}, False, {}
        criminals = set(self.players_by_role([ROLE_CRIMINAL]))
        payloads = dict(payloads)
        # What a human orders is not overridden by the AI on their own side (e.g. Irene with an AI Moriarty)
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
        self.taking_orders = False
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
        try:
            self.score_actions(commands, owner)
        except Exception:  # noqa: BLE001 - action points must never stop the match
            log.exception("Sala %s turno %s: fallo mirando las acciones del turno", self.id, self.turn)
        commands += self.npc_orders(by_pawn)
        self.remember(commands, set(from_detective))
        sides = {p: ("M" if o == GHOST_CRIMINAL or self.side(o) == "moriarty" else "S") for p, o in owner.items()}
        who = {p: ("criminal" if o == GHOST_CRIMINAL else ROLE_KEY.get(self.members.get(o, {}).get("role")), o)
               for p, o in owner.items()}
        self.log_call("turn_orders", self.turn, commands, sides, kill, who)
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
            got = self.events.setdefault(pid, set())
            if action not in got:
                got.add(action)
                self.log_call("action", self.turn, pid, action)

    def score_actions(self, commands, owner):
        """Actions with points seen in this turn's orders (for whoever gave them)."""
        ref = self.turn_ref or {}
        pawns = {int(x["pawnId"]): x for x in ref.get("pawns", []) if isinstance(x, dict) and "pawnId" in x}
        room_of_grid = {}
        for r in ref.get("roomList") or []:
            for g in r.get("gridList") or []:
                room_of_grid[g.get("gridId")] = r.get("roomId")
        self.turn_attacks, self.turn_potions, self.turn_spray_rooms = {}, set(), set()

        def injured(x):
            try:
                return bool(int(x.get("injureCount", 0) or 0) or int(x.get("isInjure", 0) or 0))
            except (TypeError, ValueError):
                return False
        # Where each character goes this turn, with any order (the heal one points at that square)
        dest = {int(c["pawnId"]): c.get("grid") for c in commands if c.get("grid") is not None}
        try:
            dark0 = bool(int(ref.get("isBlack", 0) or 0))   # to know whether the blackout (or the light) is new
        except (TypeError, ValueError):
            dark0 = False
        # Switchboard plans: Sherlock's side first, for "before Sherlock" in the same turn
        for c in sorted(commands, key=lambda c: self.side(owner.get(int(c["pawnId"]), "")) != "sherlock"):
            pid = owner.get(int(c["pawnId"]))
            if pid is None:
                continue
            kind, side = int(c.get("type", 0)), self.side(pid)
            item = c.get("itemId", -1)
            if kind == INSTRUCT_BYWAY:          # counts if the character reaches the passage (to open it)
                self.pending_success.append((pid, ACT_BYWAY, "byway", int(c["pawnId"]), c.get("grid"), dark0))
            elif kind == INSTRUCT_GASPIPE:      # counts if the leak has gone at the end of the turn
                self.pending_success.append((pid, ACT_GAS_REPAIR, "gas", int(c.get("targetId", -1)),
                                             room_of_grid.get(c.get("grid")), dark0))
            elif kind == INSTRUCT_ATTACK:
                self.turn_attacks[int(c.get("targetId", -1))] = pid     # dogs: checked at the end of the turn
            elif kind == INSTRUCT_SEARCH and item in self.switch_items:
                if side == "sherlock":
                    self.note(pid, ACT_FOUND_SWITCH)
                    if "moriarty" not in self.switch_found:
                        self.note(pid, ACT_FOUND_SWITCH_BEFORE_MORIARTY)
                elif "sherlock" not in self.switch_found:
                    self.note(pid, ACT_FOUND_SWITCH_FIRST)
                self.switch_found.add(side)
            if kind == INSTRUCT_POTION:
                # The order goes to a square (where the injured one is or reaches), not to a character. It only counts
                # if someone injured is there: hunger is not healed (in one match, healing someone with two
                # hunger did nothing)
                patients = [q for q, x in pawns.items() if injured(x)
                            and c.get("grid") is not None and dest.get(q, x.get("gridId")) == c.get("grid")]
                if side == "moriarty" and self.killer in patients:
                    self.note(pid, ACT_TREAT_KILLER)    # if the killer is one of them, the medicine is for them
                elif patients:
                    self.note(pid, ACT_TREAT)
                self.turn_potions.add(pid)     # and just in case, at the end of the turn: if someone has healed
            if side == "sherlock":
                if kind == INSTRUCT_REPAIR:     # counts if the light comes back (at the end of the turn or at the start of the next one)
                    self.pending_success.append((pid, ACT_REPAIR, "light", None, None, dark0))
                elif kind == INSTRUCT_SEARCH and item in self.food_items:
                    self.note(pid, ACT_FOOD)
            if kind == INSTRUCT_SPRAY:
                room = room_of_grid.get(c.get("grid"))
                if room is not None:
                    self.turn_spray_rooms.add(room)
                inside = [q for q, x in pawns.items() if room is not None and x.get("roomId") == room]
                if side == "sherlock" and self.killer in inside:
                    self.note(pid, ACT_SPRAY_KILLER)
                elif side == "moriarty" and any(q != self.killer for q in inside):
                    self.note(pid, ACT_SPRAY_OTHER)
            if c.get("isBatting"):          # Moriarty order that clashes with Sherlock's (only their own are seen)
                pawn = int(c["pawnId"])
                self.note(pid, ACT_CLASH_AGAIN if pawn in self.clashed else ACT_FIRST_CLASH)
                self.clashed.add(pawn)
            if side == "moriarty" and kind == INSTRUCT_BOARD:  # counts if the light goes out (at the end of the turn or at the start of the next one)
                self.pending_success.append((pid, ACT_BLACKOUT, "dark", None, None, dark0))

    def score_turn_end(self, end):
        """Actions with points that are only seen comparing the snapshot of the start of the turn with the end one
        (reference_data, GameManager.CreateServerReferenceData): characters ruled out as killer or
        victim, dogs (and other threats) that die, and people injured by a dog or by a gas leak."""
        start = self.turn_ref or {}

        def by(ref, key, ident):
            return {int(x[ident]): x for x in ref.get(key) or [] if isinstance(x, dict) and ident in x}

        def flag(x, key, default=0):
            try:
                return int(x.get(key, default) or 0)
            except (TypeError, ValueError):
                return default

        humans = [p for p, m in self.members.items() if not m.get("bot")]
        moriartys = [p for p in humans if self.side(p) == "moriarty"]
        s_pawns, e_pawns = by(start, "pawns", "pawnId"), by(end, "pawns", "pawnId")
        s_threats, e_threats = by(start, "threatList", "uniqId"), by(end, "threatList", "uniqId")

        def injuries(x):
            return flag(x, "injureCount") or flag(x, "isInjure")

        # Someone was injured and isn't any more (or less), and a heal order was given. For Moriarty's side, healing
        # the killer is its own action; for Sherlock's it is "Heal a character" like any other
        k0, k1 = s_pawns.get(self.killer), e_pawns.get(self.killer)
        killer_healed = k0 is not None and k1 is not None and injuries(k1) < injuries(k0)
        other_healed = any(q != self.killer and q in s_pawns and injuries(p) < injuries(s_pawns[q])
                           for q, p in e_pawns.items())
        for pid in self.turn_potions:
            if self.side(pid) == "moriarty":
                if killer_healed:
                    self.note(pid, ACT_TREAT_KILLER)
                if other_healed:
                    self.note(pid, ACT_TREAT)
            elif killer_healed or other_healed:
                self.note(pid, ACT_TREAT)
        self.score_ruled_out(end)
        self.score_critical(end)
        self.score_success(start, end)
        # Dog (or traitor) that dies this turn: for whoever ordered to attack it
        for uid, t in e_threats.items():
            if flag(t, "isDie") and not flag(s_threats.get(uid, {}), "isDie") and uid in self.turn_attacks:
                self.note(self.turn_attacks[uid], ACT_DOG_KILL)
        # Injured without anyone attacking or gassing them with the spray: in the room of a live dog
        # or of a gas leak
        dog_rooms = {t.get("roomId") for t in list(s_threats.values()) + list(e_threats.values())
                     if not flag(s_threats.get(int(t.get("uniqId", -1)), t), "isDie")}
        gas_rooms = {g.get("roomId") for g in (start.get("gaspipeList") or []) + (end.get("gaspipeList") or [])
                     if isinstance(g, dict)}
        for q, p in e_pawns.items():
            before = s_pawns.get(q, {})
            hurt = flag(p, "injureCount") > flag(before, "injureCount") or (flag(p, "isInjure")
                                                                           and not flag(before, "isInjure"))
            if q == self.killer or not hurt or int(p.get("uniqId", -1)) in self.turn_attacks:
                continue
            rooms = {p.get("roomId"), before.get("roomId")} - {None}
            if rooms & self.turn_spray_rooms:
                continue
            if rooms & dog_rooms:
                for pid in moriartys:
                    self.note(pid, ACT_DOG_HIT)
            elif rooms & gas_rooms:
                for pid in moriartys:
                    self.note(pid, ACT_GAS_HIT)

    def score_success(self, start, end, final=False):
        """Fixing a gas leak, breaking the switchboard (blackout), fixing it (the light comes back) and opening a passage
        only count if they succeed, not when giving the order. At the end of the turn it is compared with the start; whatever
        still isn't seen is checked again at the start of the next turn (final=True) and forgotten there."""
        def dark(ref):
            try:
                return bool(int((ref or {}).get("isBlack", 0) or 0))
            except (TypeError, ValueError):
                return False

        def leaks(ref):
            return [g for g in (ref or {}).get("gaspipeList") or [] if isinstance(g, dict)]

        keep = []
        for item in self.pending_success:
            pid, action, kind, tid, room, dark0 = item
            if kind == "gas":
                if final:
                    continue
                if any("uniqId" in g for g in leaks(start)):   # the leak that was ordered to be fixed is gone
                    fixed = any(int(g.get("uniqId", -2)) == tid for g in leaks(start)) and \
                        not any(int(g.get("uniqId", -2)) == tid for g in leaks(end))
                else:                                            # no id: there are fewer leaks in that room
                    fixed = room is not None and sum(g.get("roomId") == room for g in leaks(end)) < \
                        sum(g.get("roomId") == room for g in leaks(start))
                if fixed:
                    self.note(pid, action)
            elif kind == "byway":
                # The game sends no data about the passages: it counts if the character reached the passage's
                # square (it goes there to open it)
                at = {int(p["pawnId"]): p.get("gridId") for p in (end or {}).get("pawns") or []
                      if isinstance(p, dict) and "pawnId" in p}
                if room is not None and at.get(tid) == room:
                    self.note(pid, action)
                elif not final:
                    keep.append(item)
            elif kind == "dark" and dark(end) and not dark0:
                self.note(pid, action)
            elif kind == "light" and not dark(end) and dark0:
                self.note(pid, action)
            elif not final:
                keep.append(item)
        self.pending_success = keep

    def score_critical(self, ref):
        """Action "A character who is not the killer became critical" (for Moriarty's side): with 2 or more
        ailments (hunger, injuries...) a character becomes critical and can barely see (Sherlock's tutorial); the game marks it
        with isBlind. Checked at the end of each turn and at the start of the next one, like the rule-outs."""
        now = {int(x["pawnId"]): bool(x.get("isBlind")) for x in ref.get("pawns") or []
               if isinstance(x, dict) and "pawnId" in x}
        moriartys = [p for p, m in self.members.items() if not m.get("bot") and self.side(p) == "moriarty"]
        for q, crit in now.items():
            if crit and self.critical.get(q) is False and q != self.killer:
                for pid in moriartys:
                    self.note(pid, ACT_KNOCKOUT)
        self.critical.update(now)

    def score_ruled_out(self, ref):
        """Characters ruled out as killer or victim since the last check. Checked at the end
        of each turn and at the start of the next one: sometimes they are ruled out between the two (it happened in an online
        match: 6 possible killers at the end of turn 3 and 4 at the start of turn 4)."""
        def flag(x, key):
            try:
                return int(x.get(key, 1) if x.get(key) is not None else 1)
            except (TypeError, ValueError):
                return 1
        now = {int(x["pawnId"]): (flag(x, "isKillerCandidate"), flag(x, "isTargetCandidate"))
               for x in ref.get("pawns") or [] if isinstance(x, dict) and "pawnId" in x}
        sherlocks = [p for p, m in self.members.items() if not m.get("bot") and self.side(p) == "sherlock"]
        for q, (killer, target) in now.items():
            before = self.candidates.get(q)
            if before is None:
                continue
            if before[0] and not killer:
                for pid in sherlocks:
                    self.note(pid, ACT_NOT_KILLER)
            if before[1] and not target:
                for pid in sherlocks:
                    self.note(pid, ACT_NOT_TARGET)
        self.candidates.update(now)

    def level(self):
        """Level of the match for the points: against people "online"; otherwise, the AI's."""
        if len([p for p, m in self.members.items() if not m.get("bot") or m.get("replaced")]) >= 2:
            return "online"
        order = ai.RANK
        diffs = [m.get("difficulty", "normal") for m in self.members.values() if m.get("bot") and not m.get("replaced")]
        return max(diffs, key=lambda d: order.get(d, 1)) if diffs else "normal"

    def remember(self, commands, ordered_by_sherlock):
        """What Sherlock's side sees this turn: who acted without them ordering it and on
        whom Moriarty's hand was noticed (overridden order)."""
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
            # What draws attention: running (nobody runs on their own) or getting close to a possible victim
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
        """The game's solo training: the room has a single person and nobody plays
        Moriarty. The official server moved the killer on its own; without this nothing happened during the whole
        match. Here a Moriarty AI plays that isn't in the room (it doesn't show in the list)."""
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
        """Pawn.RunNpcAction: whoever gets no orders searches something nearby or takes a walk."""
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
        """Spawning of dogs/threats and gas leaks, with the same rules as the offline client:
        between the start and end turn, while the room's maximum hasn't been reached, a
        die is rolled against a probability that starts low and doubles every time it misses."""
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
        start, end, growth = hazard_window(start, end, base, int(self.settings.get("max_turn") or DEFAULT_TURNS))
        if not (start <= turn <= end) or maxc <= 0 or locates < maxc or len(alive) >= maxc:
            return -1
        if turn == start or kind not in self.hazard_prob:
            self.hazard_prob[kind] = base
        if random.randrange(100) >= self.hazard_prob[kind]:
            self.hazard_prob[kind] *= growth
            return -1
        self.hazard_prob[kind] = base
        used = {int(x.get("spawnLocateIndex", -1)) for x in active}
        free = [i for i in range(locates) if i not in used] or list(range(locates))
        idx = random.choice(free)
        log.info("Sala %s turno %s: aparece %s en el punto %s", self.id, turn,
                 "una amenaza" if kind == "threat" else "un escape de gas", idx)
        return idx

    def memo_reveal(self, c, found_at):
        """A note (memo) points to a piece of furniture that still holds a weapon or food: the game turns the camera
        to it, marks it with a ping and Sherlock says where it is ("memoTargetId" and "memoItemId" in the search
        order, read by Pawn.InstructData.Deserialize). Which items are notes comes from the plugin ("itemTypes")."""
        item = c.get("itemId", -1)
        types = getattr(self, "item_types", None) or []
        if not (isinstance(item, int) and 0 <= item < len(types) and types[item] == ITEM_MEMO):
            return
        wanted = self.weapon_items | self.food_items
        cands = [o for o, i in self.object_items.items()
                 if i in wanted and o not in self.searched and o != found_at and o not in self.disabled_objects]
        if not cands:
            log.info("Sala %s: nota en el mueble %s, pero no queda ningun mueble con arma o comida", self.id, found_at)
            return
        o = random.choice(cands)
        c["memoTargetId"], c["memoItemId"] = o, self.object_items[o]
        log.info("Sala %s: nota en el mueble %s: senala el mueble %s (%s)", self.id, found_at, o,
                 "arma" if self.object_items[o] in self.weapon_items else "comida")

    def resolve_item(self, c):
        """Search/pick up: the server says which item the character gets (the same for everyone)."""
        c = dict(c)
        kind = int(c.get("type", 0))
        target = int(c.get("targetId", -1))
        if kind == INSTRUCT_SEARCH and target >= 0:
            if target not in self.searched:
                self.searched[target] = self.object_items.get(target, -1)
                log.info("Sala %s: mueble %s -> objeto %s (%s)", self.id, target, self.searched[target],
                         "arma" if self.searched[target] in self.weapon_items else
                         "comida" if self.searched[target] in self.food_items else "otro")
                item = self.searched[target]
                self.log_call("found", self.turn, target, item,
                              "weapon" if item in self.weapon_items else "food" if item in self.food_items
                              else "plan" if item in self.switch_items else "other")
                c["itemId"] = self.searched[target]
                self.memo_reveal(c, target)
                self.searched_now[target] = (self.turn, {k: c[k] for k in ("memoTargetId", "memoItemId") if k in c})
            elif self.searched_now.get(target, (None,))[0] == self.turn:
                # Another character searches the same furniture this turn: it gets the same item. The game plays
                # the searches in its own order: whoever gets there first takes it (with its dialogue) and the rest
                # find it already searched and just walk there. Giving "nothing" to all but one made the item
                # vanish when the game played that one first (silent search, then the other only walked).
                c["itemId"] = self.searched[target]
                c.update(self.searched_now[target][1])
            else:
                c["itemId"] = -1   # searched in an earlier turn: nothing left
        elif kind == INSTRUCT_PICK and target >= 0:
            if target in self.drops:
                c["itemId"] = self.drops.pop(target)
                self.picked_now[target] = (self.turn, c["itemId"])
            elif self.picked_now.get(target, (None,))[0] == self.turn:
                c["itemId"] = self.picked_now[target][1]     # same item on the floor this turn: same rule as searches
            else:
                c["itemId"] = -1
        return c

    def is_danger(self):
        """Night hint: killer and victim 3 squares apart or less (data the client itself works out)."""
        for ref in self.reference.values():
            for pawn in ref.get("pawns", []) if isinstance(ref, dict) else []:
                if int(pawn.get("pawnId", -1)) != self.killer:
                    continue
                for other in pawn.get("pawnList", []) or []:
                    if int(other.get("pawnId", -1)) == self.target:
                        return int(other.get("distance", 99)) <= 3
        return False

    async def p_SetSelectionPhase(self, sess, p):
        """Each game says when it reaches the final deduction. Everyone is waited for before starting it: if
        it started with the first one, the game that hadn't arrived yet didn't get it and didn't show the
        voting screen (in a 1 vs 1, the Sherlock who was a few seconds behind)."""
        if self.phase in ("selection", "ended"):
            return rc({})
        self.pending.setdefault("selection", {})[sess.player_id] = True
        if self._complete("selection"):
            await self.start_selection()
        elif getattr(self, "selection_wait", None) is None or self.selection_wait.done():
            self.selection_wait = asyncio.ensure_future(self._selection_wait())
        return rc({})

    async def _selection_wait(self):
        """If some game doesn't arrive (it froze or left), the deduction starts anyway."""
        await asyncio.sleep(SELECTION_WAIT)
        if "selection" in self.pending and self.phase not in ("selection", "ended"):
            log.info("Sala %s: no todos han llegado a la deduccion final; empieza igual", self.id)
            await self.start_selection()

    async def start_selection(self):
        self.pending.pop("selection", None)
        wait, self.selection_wait = getattr(self, "selection_wait", None), None
        if wait and wait is not asyncio.current_task():
            wait.cancel()
        if self.phase in ("selection", "ended"):
            return
        self.phase = "selection"
        self.pending["answer"] = {}
        await self.control("StartSelectionPhase", {"CountDownTimer": SELECTION_SECONDS})
        if not any(self.members[x]["role"] in (ROLE_DETECTIVE, ROLE_WATSON) for x in self.humans()):
            # Sherlock is played by the AI: it "thinks" for a few seconds and accuses
            self.selection_task = asyncio.ensure_future(self._ai_answer())
        else:
            self.selection_task = asyncio.ensure_future(self._selection_timeout())

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
            # The game stores the answers per player and closes if it gets the same one twice
            # (it happened with an AI Sherlock and a human Watson/Irene: the deduction had already closed and
            # another answer arrived). Late or repeated ones are not forwarded.
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
        # The AI Sherlocks/Watsons accuse according to their difficulty
        for bot in self.bots():
            m = self.members[bot]
            if m["role"] in (ROLE_DETECTIVE, ROLE_WATSON):
                guess = ai.accuse(self.last_view, self.killer, m["difficulty"], random.Random(), self.pawn_count,
                                  self.ai_mem)
                # solo with Watson, the Sherlock AI accuses whoever Watson told it (if they still can be)
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
        """Writes something in the match log (matchlog); if it fails, the match goes on the same."""
        ml = getattr(self, "mlog", None)
        if ml is None:
            return
        try:
            getattr(ml, name)(*args)
        except Exception:  # noqa: BLE001
            log.exception("Fallo apuntando la partida (%s)", name)

    def record_result(self, selections):
        """End by deduction: if someone on Sherlock's side (Sherlock or Watson) is right, their side wins and Moriarty
        loses; if nobody is right, it is a draw (there was no murder). Each of them gets their own result, as the
        game's end screen shows it: whoever accused the villain wins, a teammate who accused someone else draws (seen
        in a 4-player match). Accusing right also gives the action's points to whoever got it."""
        self.log_call("accusations", [(s["player_id"], s["killer"], self.members.get(s["player_id"], {}).get("bot"))
                                      for s in selections])
        right = [s["player_id"] for s in selections if s["killer"] == self.killer
                 and self.members.get(s["player_id"], {}).get("role") in (ROLE_DETECTIVE, ROLE_WATSON)]
        extra = {pid: [ACT_DEDUCED] for pid in right}
        wrong = {pid for pid, m in self.members.items()
                 if m.get("role") in (ROLE_DETECTIVE, ROLE_WATSON) and pid not in right} if right else set()
        self.conclude("sherlock" if right else "draw", extra, draws=wrong)

    def conclude(self, winner, extra=None, quitter=None, draws=None):
        """winner: "sherlock", "moriarty" or "draw". extra: actions with points, per role or per player.
        quitter: the player who forfeited or left, or a set of them (a team that voted to forfeit).
        draws: players on the winning side who still only draw (Sherlock or Watson who accused the wrong person)."""
        if self.recorded:
            return
        self.recorded = True
        ml = getattr(self, "mlog", None)
        reason = "abandon" if quitter else ("kill" if ml is not None and ml.rec.get("kill") else "deduction")
        try:
            self._record_players(winner, extra or {}, quitter, reason, draws or set())
        finally:
            self.log_call("finish", winner, reason)     # the log is saved with what was written in the profiles
        self.hub.api.s.save()

    def _record_players(self, winner, extra, quitter, reason, draws=frozenset()):
        quitters = {quitter} if isinstance(quitter, str) else set(quitter or ())
        for pid, m in self.members.items():
            if m.get("bot"):
                continue
            role = int(m["role"])
            side = "sherlock" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "moriarty"
            outcome = "draw" if winner == "draw" else ("win" if side == winner else "lose")
            if pid in draws:
                outcome = "draw"
            if pid in quitters:
                outcome = "abandon"
            acts = list(extra.get(role, [])) + list(extra.get(pid, [])) + sorted(self.events.get(pid, ()))
            u = self.hub.api.s.user(pid)
            pts = stats.record_match(u, role, outcome, acts, self.current_stage or self.settings.get("stage", ""),
                                     match_id=getattr(self, "match_id", None), level=self.level(), finish=reason)
            log.info("Sala %s: %s (%s) %s, +%s puntos -> %s", self.id, m["name"], ROLE_KEY.get(role, role),
                     {"win": "GANA", "lose": "PIERDE", "draw": "EMPATA", "abandon": "ABANDONA"}[outcome],
                     pts, stats.summary(u))
            given = [] if outcome == "abandon" else list(dict.fromkeys(a for a in acts if a in stats.ACTIONS))
            self.log_call("awarded", pid, outcome, given, pts)

    async def p_Sync(self, sess, p):
        await self.control("Sync", {"Data": p.get("payload") if isinstance(p.get("payload"), dict) else {}})
        return rc({})

    async def p_Abandon(self, sess, p):
        message = p.get("message", "")
        try:
            data = json.loads(message) if message else {}
        except ValueError:
            data = {}
        if isinstance(data, dict) and "csr_vote" in data:       # a teammate answers the surrender vote
            await self.vote_answer(sess.player_id, data.get("csr_vote") == "yes")
            return rc({})
        if self.phase in ("lobby", "ended") or self.recorded:
            return rc({})
        mates = self.teammates(sess.player_id)
        if mates:
            await self.start_vote(sess.player_id, mates, message)
        else:
            await self.forfeit(sess.player_id, message=message, reason="se rinde")
        return rc({})

    # ---- surrender vote: with a person on your team, they must agree before your side forfeits
    def teammates(self, pid):
        return [h for h in self.humans() if h != pid and self.side(h) == self.side(pid)]

    async def start_vote(self, pid, mates, message):
        if self.vote:
            return
        self.vote = {"from": pid, "waiting": set(mates), "message": message or "{}",
                     "task": asyncio.ensure_future(self._vote_timeout())}
        log.info("Sala %s: %s quiere rendirse; se pregunta a %s", self.id, self.members[pid]["name"],
                 [self.members[x]["name"] for x in mates])
        await self.control_to(mates, "CsrSurrenderVote", {"PlayerId": pid, "PlayerName": self.members[pid]["name"],
                                                          "Seconds": SURRENDER_VOTE_SECONDS})
        await self.control_to([pid], "CsrSurrenderWait", {"Seconds": SURRENDER_VOTE_SECONDS})

    async def vote_answer(self, pid, yes):
        v = self.vote
        if not v or pid not in v["waiting"]:
            return
        log.info("Sala %s: %s %s rendirse", self.id, self.members[pid]["name"], "acepta" if yes else "no quiere")
        if not yes:
            await self.end_vote("no", pid)
            return
        v["waiting"].discard(pid)
        if not v["waiting"]:
            await self.team_forfeit()

    async def _vote_timeout(self):
        try:
            await asyncio.sleep(SURRENDER_VOTE_SECONDS + 3)     # a little longer than the window, for the network
        except asyncio.CancelledError:
            return
        v = self.vote
        if v and self.phase not in ("lobby", "ended"):
            v["task"] = None
            await self.end_vote("timeout", next(iter(v["waiting"]), v["from"]))

    def cancel_vote(self):
        v, self.vote = self.vote, None
        if v and v.get("task") and v["task"] is not asyncio.current_task():
            v["task"].cancel()
        return v

    async def end_vote(self, result, who):
        """The match goes on: result "no" (who said no), "timeout" (who didn't answer) or "cancel"."""
        v = self.cancel_vote()
        if not v:
            return
        team = [h for h in self.humans() if self.side(h) == self.side(v["from"])]
        name = self.members.get(who, {}).get("human_name") or self.members.get(who, {}).get("name", "")
        await self.control_to(team, "CsrSurrenderVoteEnd", {"Result": result, "PlayerName": name})

    async def team_forfeit(self):
        """Everyone asked agreed: the team forfeits (all its people get the loss, as if each had surrendered)."""
        v = self.cancel_vote()
        if not v:
            return
        team = [h for h in self.humans() if self.side(h) == self.side(v["from"])]
        await self.forfeit(v["from"], message=v["message"], reason="se rinde (votacion del equipo)",
                           quitters=set(team) | {v["from"]})

    async def forfeit(self, pid, message="", reason="", quitters=None):
        """pid surrenders or leaves: their side loses, the other one wins, and the match ends for everyone.
        quitters: everyone who forfeits with them (a team vote); by default only pid."""
        self.cancel_vote()
        self.phase = "ended"
        role = self.members.get(pid, {}).get("role")
        log.info("Sala %s: %s %s", self.id, self.members.get(pid, {}).get("name", pid), reason)
        winner = "moriarty" if role in (ROLE_DETECTIVE, ROLE_WATSON) else "sherlock"
        self.conclude(winner, quitter=quitters or pid)
        crim = self.players_by_role([ROLE_CRIMINAL])
        det = self.players_by_role([ROLE_DETECTIVE])
        await self.control("Abandon", {"Data": {
            "killer": self.killer, "target": self.target,
            "criminal_player": crim[0] if crim else "", "criminal_name": self.members[crim[0]]["name"] if crim else "",
            "detective_player": det[0] if det else "", "detective_name": self.members[det[0]]["name"] if det else "",
            "message": message,       # "Surrender" sends here who surrenders (surrenderPlayerId)
            # The game assumes whoever surrenders is Moriarty: the plugin uses this to show
            # victory or defeat correctly when another role surrenders (or leaves)
            "csr_winner": winner,
            # and who it was (role) and whether they surrendered or left, for the notice's text
            "csr_quitter_role": ROLE_KEY.get(role, ""), "csr_reason": "surrender" if message else "left"}})

    async def p_Rematch(self, sess, p):
        gone = {pid: m.get("human_name", m["name"]) for pid, m in self.members.items() if m.get("replaced")}
        for pid in gone:                   # left mid-match: out of the room now (an AI took their place)
            self.members.pop(pid)
        self.match_order = []
        self.taking_orders = False
        self.cancel_vote()
        self.phase = "lobby"
        self.restore_support()
        self.current_stage = None          # with "Random", the next match draws another stage
        self.refresh_vars()
        self.killer = self.target = -1
        self.object_items, self.searched, self.drops = {}, {}, {}
        self.searched_now, self.picked_now = {}, {}
        self.disabled_objects = set()
        self.recorded, self.hazard_prob = False, {}
        self.vars["random_seed"] = random.randint(1, 2**31 - 1)
        await self.control("Rematch", {"RandomSeed": "random_seed"})
        if gone:
            self.fill_bots()
            self.refresh_vars()
            owner = self.members[self.owner]
            for pid, name in gone.items():
                await self.control("Leave", {"PlayerId": pid, "PlayerName": name,
                                             "OwnerId": self.owner, "OwnerName": owner["name"]})
        return rc({})

    async def p_PingLog(self, sess, p):
        return rc({})

    async def p_StampLog(self, sess, p):
        return rc({})
