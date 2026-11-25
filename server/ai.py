"""
CRIMESIGHT Revival - AI of the bot players.

Every turn the client sends the server (reference_data) the state of the mansion:
for each character, the squares it can reach this turn (gridList) with
their room, the searchable furniture, the items on the floor and the distance
from that square to each character (pawnDistance). With that the AI generates valid
orders without knowing the map.

Rules (community guides + client code):
- Sherlock gives orders to 3 characters (the victim can be one); Moriarty to 2,
  never to the victim. If both order the same character, Moriarty wins.
- Walking reaches 2 squares, running 3 (isRun). Hungry or injured ones reach less.
- To kill, the killer needs a weapon, to be on the victim's square and for there to be
  no witnesses in the room. The "Assault" (order type 5) makes the killer
  act last and go straight for the victim; if it fails, both are
  exposed.
- Watson (Sherlock's side) and Irene (Moriarty's side) give 1 order each. Irene can't
  assault or give orders to the victim. Irene beats Sherlock/Watson without leaving a trace; if
  Moriarty overrides a different order from Sherlock/Watson, it shows (isBatting).
- Moriarty's side knows which furniture has weapons from the start.
- Characters without orders act on their own (online the server decides).
- Hazards: gas leaks injure whoever ends the turn in that room; wild
  dogs attack nearby characters (some threats count as witnesses).
"""
import copy, random

MOVE, SEARCH, TARGET = 2, 3, 5
NO_TARGET = 130              # value the client sends when the order doesn't point at a square
WALK_RANGE = 2
GRID_W = 10                  # GridManager: id = x*10 + z (z with x's sign)

DIFFICULTIES = ["normal", "hard", "expert", "nightmare", "easy"]     # order of the cycle when "kicking" an AI
RANK = {"easy": 0, "normal": 1, "hard": 2, "expert": 3, "nightmare": 4}
LABEL = {"easy": "Fácil", "normal": "Normal", "hard": "Difícil", "expert": "Experto", "nightmare": "Pesadilla"}
# Names of the AIs in the host's language (the game's language codes)
BOT_NAMES = {
    "ES": ("IA", {"easy": "Fácil", "normal": "Normal", "hard": "Difícil", "expert": "Experto", "nightmare": "Pesadilla"}),
    "EN": ("AI", {"easy": "Easy", "normal": "Normal", "hard": "Hard", "expert": "Expert", "nightmare": "Nightmare"}),
    "FR": ("IA", {"easy": "Facile", "normal": "Normal", "hard": "Difficile", "expert": "Expert", "nightmare": "Cauchemar"}),
    "IT": ("IA", {"easy": "Facile", "normal": "Normale", "hard": "Difficile", "expert": "Esperto", "nightmare": "Incubo"}),
    "DE": ("KI", {"easy": "Leicht", "normal": "Normal", "hard": "Schwer", "expert": "Experte", "nightmare": "Albtraum"}),
    "PT": ("IA", {"easy": "Fácil", "normal": "Normal", "hard": "Difícil", "expert": "Especialista", "nightmare": "Pesadelo"}),
    "RU": ("ИИ", {"easy": "Легко", "normal": "Нормально", "hard": "Сложно", "expert": "Эксперт", "nightmare": "Кошмар"}),
    "JP": ("AI", {"easy": "かんたん", "normal": "ふつう", "hard": "むずかしい", "expert": "エキスパート", "nightmare": "ナイトメア"}),
    "KO": ("AI", {"easy": "쉬움", "normal": "보통", "hard": "어려움", "expert": "전문가", "nightmare": "악몽"}),
    "CN": ("AI", {"easy": "简单", "normal": "普通", "hard": "困难", "expert": "专家", "nightmare": "噩梦"}),
    "TW": ("AI", {"easy": "簡單", "normal": "普通", "hard": "困難", "expert": "專家", "nightmare": "噩夢"}),
}


def bot_name(slot, difficulty, lang=None):
    prefix, labels = BOT_NAMES.get(str(lang or "").upper(), BOT_NAMES["EN"])
    return f"{prefix}_{slot} ({labels.get(difficulty, difficulty)})"


def turn_clock(turn):
    """turn -> (day, time of day): 3 times per day."""
    t = max(1, int(turn))
    return (t - 1) // 3 + 1, (t - 1) % 3


class View:
    """Handy reading of a turn's reference_data."""

    def __init__(self, ref, unavailable_objects=()):
        self.turn = int(ref.get("turn", 1))
        self.pawns = {int(p["pawnId"]): p for p in ref.get("pawns", []) if isinstance(p, dict)}
        self.unavailable = set(unavailable_objects)
        self.weapon_objects = set()     # furniture with a weapon (only Moriarty's side knows it)
        self.food_objects = set()       # furniture with food (Moriarty knows all of it)
        self.dark = bool(int(ref.get("isBlack", 0) or 0))
        self.threats = [t for t in ref.get("threatList") or [] if isinstance(t, dict) and not t.get("isDie")]
        self.gas_rooms = {g.get("roomId") for g in ref.get("gaspipeList") or [] if isinstance(g, dict)}
        self.max_turn = None            # set by the room: the match's turns (to know how many are left)

    @staticmethod
    def xy(grid_id):
        g = int(grid_id)
        return int(g / GRID_W), abs(g) % GRID_W

    def danger(self, grid):
        """How risky it is to end the turn on that square (gas, dogs nearby)."""
        d = 2 if grid.get("roomId") in self.gas_rooms else 0
        if self.threats:
            x, z = self.xy(grid.get("gridId", 0))
            for t in self.threats:
                if t.get("gridId") is None:
                    continue
                tx, tz = self.xy(t["gridId"])
                if max(abs(tx - x), abs(tz - z)) <= 2:
                    d += 1
        return d

    def threat_witness(self, room):
        return any(t.get("isWitness") and t.get("roomId") == room for t in self.threats)

    def ids(self):
        return sorted(self.pawns)

    def grids(self, pid):
        return self.pawns[pid].get("gridList") or []

    def here(self, pid):
        p = self.pawns[pid]
        return {"gridId": p.get("gridId"), "roomId": p.get("roomId")}

    @staticmethod
    def dist(grid, pid):
        d = grid.get("pawnDistance") or []
        return d[pid] if 0 <= pid < len(d) else 99

    def self_dist(self, pid, grid):
        return self.dist(grid, pid)

    def searchable(self, grid):
        return [o["id"] for o in grid.get("searchObjects") or [] if o.get("id") not in self.unavailable]

    def room_mates(self, pid):
        room = self.pawns[pid].get("roomId")
        return [q for q, p in self.pawns.items() if q != pid and p.get("roomId") == room]

    def pair_distance(self, a, b):
        for other in self.pawns.get(a, {}).get("pawnList") or []:
            if int(other.get("pawnId", -1)) == b:
                return int(other.get("distance", 99))
        return 99


def order(view, player_index, pid, kind, grid, target_id=-1):
    days, tz = turn_clock(view.turn)
    if kind == SEARCH:
        view.unavailable.add(target_id)   # nobody else searches this furniture this turn
    return {"pawnId": pid, "playerId": player_index, "type": kind, "days": days, "timeZone": tz,
            "grid": int(grid["gridId"]), "target": NO_TARGET,
            "isRun": 1 if view.self_dist(pid, grid) > WALK_RANGE else 0, "targetId": int(target_id)}


def search_or_move(view, idx, pid, grids, rng, prefer=None):
    """Searches a piece of furniture if there is one at hand; otherwise, moves (optionally towards 'prefer')."""
    options = [(g, o) for g in grids for o in view.searchable(g)]
    if options:
        if prefer is not None:
            options.sort(key=lambda go: (view.danger(go[0]), view.dist(go[0], prefer), rng.random()))
            g, o = options[0]
        else:
            safe = min(view.danger(g) for g, _ in options)
            g, o = rng.choice([go for go in options if view.danger(go[0]) == safe])
        return order(view, idx, pid, SEARCH, g, o)
    if not grids:
        return None
    if prefer is not None:
        g = min(grids, key=lambda g: (view.danger(g), view.dist(g, prefer), rng.random()))
    else:
        safe = min(view.danger(g) for g in grids)
        g = rng.choice([g for g in grids if view.danger(g) == safe])
    return order(view, idx, pid, MOVE, g)


def seek_weapon(view, idx, pid, grids, rng, prefer=None):
    """Search a piece of furniture known to hold a weapon, if there is one at hand."""
    options = [(g, o) for g in grids for o in view.searchable(g) if o in view.weapon_objects]
    if not options:
        return None
    options.sort(key=lambda go: (view.danger(go[0]), view.dist(go[0], prefer) if prefer is not None else 0,
                                 rng.random()))
    g, o = options[0]
    return order(view, idx, pid, SEARCH, g, o)


NPC_SEARCH_PROB = 0.5


def npc_order(view, pid, rng):
    """Pawn.RunNpcAction: without orders, the character searches something within walking reach or
    moves to a nearby square (sometimes it stays where it is)."""
    grids = [g for g in view.grids(pid) if view.self_dist(pid, g) <= WALK_RANGE]
    if not grids:
        return None
    if rng.random() < NPC_SEARCH_PROB:
        options = [(g, o) for g in grids for o in view.searchable(g)]
        if options:
            g, o = rng.choice(options)
            return order(view, -1, pid, SEARCH, g, o)
    return order(view, -1, pid, MOVE, rng.choice(grids))


def away_from(view, pid, other):
    """Square reachable by pid as far as possible from 'other' (without walking into danger if possible)."""
    return max(view.grids(pid), key=lambda g: (view.dist(g, other) - 2 * view.danger(g), view.dist(g, other)))


# ------------------------------------------------------------------ Moriarty
def plan_moriarty(view, idx, killer, target, n_orders, difficulty, rng, taken=(), memory=None):
    """Orders for Moriarty's side. Returns (orders, assault?)."""
    orders, used = [], set(taken) | {target}
    if killer not in view.pawns or target not in view.pawns:
        return orders, False
    if difficulty == "nightmare":
        return plan_moriarty_nightmare(view, idx, killer, target, n_orders, rng, taken, memory)
    if difficulty == "expert":
        return plan_moriarty_expert(view, idx, killer, target, n_orders, rng, taken, memory)
    if difficulty == "hard":
        return plan_moriarty_hard(view, idx, killer, target, n_orders, rng, taken, memory)
    if difficulty == "easy":
        return plan_moriarty_easy(view, idx, killer, target, n_orders, rng, taken)
    return plan_moriarty_normal(view, idx, killer, target, n_orders, rng, taken)


def assault_order(view, idx, killer, target):
    t = view.pawns[target]
    return {**order(view, idx, killer, TARGET, {"gridId": t.get("gridId"), "pawnDistance": []}),
            "targetId": int(t.get("uniqId", -1)), "isRun": 0}


def plan_moriarty_normal(view, idx, killer, target, n_orders, rng, taken=()):
    """Normal Moriarty: takes three things from the hard one, without being relentless.
    - It never makes anyone run (it would draw Sherlock's attention).
    - It only assaults if nobody can reach the victim's room this turn (although it doesn't
      check whether she can escape, so it sometimes fails).
    - With a weapon, it stands on the victim's square if she is alone in her room right now.
    Its other order moves, walking, whoever is with the victim away."""
    orders, used = [], set(taken) | {target}
    k, t = view.pawns[killer], view.pawns[target]
    armed = bool(k.get("isHaveWeapon"))
    kwalk = walk(view, killer) if view.grids(killer) else []
    troom = t.get("roomId")
    witnesses = [q for q in view.room_mates(target) if q != killer and awake(view, q)]
    others = [q for q in view.ids() if q not in (killer, target) and awake(view, q)]
    nobody_can_come = not any(g.get("roomId") == troom for q in others for g in view.grids(q))
    reach = any(view.dist(g, target) == 0 for g in view.grids(killer)) and not view.threat_witness(troom)

    if armed and killer not in used and reach and nobody_can_come:
        return [assault_order(view, idx, killer, target)], True

    if killer not in used and kwalk:
        if not armed:
            o = seek_weapon(view, idx, killer, kwalk, rng, prefer=target) or \
                search_or_move(view, idx, killer, kwalk, rng, prefer=target)
        else:
            here = next((g for g in kwalk if view.dist(g, target) == 0), None)
            if here is not None and not witnesses:
                o = order(view, idx, killer, MOVE, here)
            else:
                g = min(kwalk, key=lambda g: (abs(view.dist(g, target) - 1), view.danger(g), rng.random()))
                o = order(view, idx, killer, MOVE, g)
        if o:
            orders.append(o)
            used.add(killer)

    while len(orders) < n_orders:
        candidates = [q for q in view.ids() if q not in used and view.grids(q)]
        if not candidates:
            break
        w = next((q for q in witnesses if q in candidates), None)
        if w is not None:
            g = max(walk(view, w), key=lambda g: (view.dist(g, target) - 2 * view.danger(g), rng.random()))
            orders.append(order(view, idx, w, MOVE, g))
            used.add(w)
            witnesses.remove(w)
            continue
        q = rng.choice(candidates)
        o = search_or_move(view, idx, q, walk(view, q), rng)   # behave like one more suspect
        if o:
            orders.append(o)
        used.add(q)
    return orders, False


def plan_moriarty_easy(view, idx, killer, target, n_orders, rng, taken=()):
    """Easy Moriarty: makes mistakes an attentive Sherlock can catch.
    - It makes its killer run often and sticks it to the victim turn after turn.
    - It sometimes assaults even with witnesses (and then usually fails and gets exposed).
    - Its other order is almost always a random move."""
    orders, used = [], set(taken) | {target}
    k, t = view.pawns[killer], view.pawns[target]
    armed = bool(k.get("isHaveWeapon"))
    kgrids = view.grids(killer)
    witnesses = [q for q in view.room_mates(target) if q != killer and awake(view, q)]
    reach = any(view.dist(g, target) == 0 for g in kgrids)

    if armed and killer not in used and reach and rng.random() < (0.6 if not witnesses else 0.35):
        return [assault_order(view, idx, killer, target)], True

    if killer not in used and kgrids:
        if armed or rng.random() < 0.5:
            # stick to the victim, running if needed: very obvious
            g = min(kgrids, key=lambda g: (view.dist(g, target), -view.self_dist(killer, g), rng.random()))
            o = order(view, idx, killer, MOVE, g)
        else:
            o = search_or_move(view, idx, killer, kgrids, rng)
        if o:
            orders.append(o)
            used.add(killer)

    while len(orders) < n_orders:
        candidates = [q for q in view.ids() if q not in used and view.grids(q)]
        if not candidates:
            break
        q = rng.choice(candidates)
        orders.append(order(view, idx, q, MOVE, rng.choice(view.grids(q))))
        used.add(q)
    return orders, False


# ------------------------------------------------------------------ Sherlock
def plan_sherlock(view, idx, n_orders, difficulty, rng, taken=(), memory=None):
    """Orders for Sherlock's side: search for items and leave nobody alone."""
    if difficulty == "nightmare":
        return plan_sherlock_nightmare(view, idx, n_orders, rng, taken, memory or new_memory())
    if difficulty == "expert":
        return plan_sherlock_expert(view, idx, n_orders, rng, taken, memory or new_memory())
    if difficulty == "hard":
        return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory or new_memory())
    orders, used = [], set(taken)
    pool = [q for q in view.ids() if q not in used and view.grids(q)]
    if difficulty == "easy":
        return plan_sherlock_easy(view, idx, n_orders, rng, pool)
    return plan_sherlock_normal(view, idx, n_orders, rng, pool, memory or new_memory())


def plan_sherlock_normal(view, idx, n_orders, rng, pool, memory):
    """Normal Sherlock: takes three things from the hard one.
    - It doesn't spend orders on characters Moriarty already controls (overridden order) if there are others.
    - It keeps people together, 3 squares apart or less, starting with the isolated possible victims.
    - At the end it almost always accuses the most suspicious one from what it has seen (see accuse)."""
    orders = []

    def lonely(q):
        return len(view.room_mates(q))

    pool = [q for q in pool if q not in memory["moriarty"]] or pool
    pool.sort(key=lambda q: (not view.pawns[q].get("isTargetCandidate", 1), lonely(q), rng.random()))
    for q in pool:
        if len(orders) >= n_orders:
            break
        grids = view.grids(q)
        others = [x for x in view.ids() if x != q]

        def company(g):
            return sum(1 for x in others if view.dist(g, x) <= 3) - view.danger(g)

        best = max(company(g) for g in grids)
        good = [g for g in grids if company(g) == best]
        if lonely(q) == 0:
            near_best = [g for g in grids if company(g) >= max(1, best - 1)]
            with_obj = [g for g in good if view.searchable(g)] or [g for g in near_best if view.searchable(g)]
            if with_obj:
                g = rng.choice(with_obj)
                o = order(view, idx, q, SEARCH, g, rng.choice(view.searchable(g)))
            else:
                o = order(view, idx, q, MOVE, rng.choice(good))
        else:
            o = search_or_move(view, idx, q, grids, rng)
        if o:
            orders.append(o)
    return orders


# ------------------------------------------------------------------ Irene and Watson
def plan_irene(view, idx, killer, target, difficulty, rng, taken=(), memory=None):
    """Irene (Moriarty's side): 1 order, no assault and never on the victim.
    Priority: move a witness away from the victim; otherwise, help the unarmed killer;
    otherwise, mislead like any Watson would."""
    used = set(taken) | {target}
    if target not in view.pawns:
        return []
    if difficulty in ("expert", "nightmare"):
        mem = memory or new_memory()
        prof = mem.get("prof_sherlock") if difficulty == "nightmare" else None
        return plan_irene_expert(view, idx, killer, target, rng, taken, mem,
                                 frame_first=bool(prof and (prof.get("fooled_by_runner") or 0) >= 0.5))
    witnesses = [q for q in view.room_mates(target) if q not in used and q != killer and view.grids(q)]
    if witnesses and difficulty != "easy":
        w = min(witnesses, key=lambda q: view.pair_distance(q, target))
        return [order(view, idx, w, MOVE, away_from(view, w, target))]
    k = view.pawns.get(killer, {})
    if killer not in used and view.grids(killer) and not k.get("isHaveWeapon"):
        o = (seek_weapon(view, idx, killer, view.grids(killer), rng, prefer=target) if difficulty != "easy" else None) \
            or search_or_move(view, idx, killer, view.grids(killer), rng, prefer=target)
        return [o] if o else []
    pool = [q for q in view.ids() if q not in used and q != killer and view.grids(q)]
    if not pool:
        return []
    q = rng.choice(pool)
    o = search_or_move(view, idx, q, view.grids(q), rng)
    return [o] if o else []


def plan_sherlock_easy(view, idx, n_orders, rng, pool):
    """Easy Sherlock: almost random orders, without looking at hazards or who is armed; it sometimes leaves
    a possible victim alone or brings her closer to a suspect."""
    orders = []
    rng.shuffle(pool)
    for q in pool[:n_orders]:
        grids = view.grids(q)
        objs = [(g, o) for g in grids for o in view.searchable(g)]
        if objs and rng.random() < 0.5:
            g, o = rng.choice(objs)
            orders.append(order(view, idx, q, SEARCH, g, o))
        else:
            orders.append(order(view, idx, q, MOVE, rng.choice(grids)))
    return orders


def plan_watson(view, idx, difficulty, rng, taken=(), memory=None):
    """Watson (Sherlock's side): 1 order with the same criteria as Sherlock."""
    return plan_sherlock(view, idx, 1, difficulty, rng, taken, memory)


def accuse(view, killer, difficulty, rng, n_pawns, memory=None):
    """Acusacion final de un Sherlock IA."""
    everyone = list(range(n_pawns))
    if view is None:
        return rng.choice(everyone)
    cands = [q for q, p in view.pawns.items() if p.get("isKillerCandidate")] or everyone
    if difficulty == "easy":
        return rng.choice(everyone)
    if difficulty in ("expert", "nightmare"):
        mem = memory or new_memory()
        fn = suspicion_nightmare if difficulty == "nightmare" else suspicion_expert
        best = max(fn(view, mem, q) for q in cands)
        top = [q for q in cands if fn(view, mem, q) == best]
        return min(top, key=lambda q: (-mem["moved"].get(q, 0), rng.random()))
    if difficulty == "hard":
        # Only with what it has seen: the most suspicious of those who can still be the killer
        mem = memory or new_memory()
        best = max(suspicion(view, mem, q) for q in cands)
        return rng.choice([q for q in cands if suspicion(view, mem, q) == best])
    # normal: it usually accuses the most suspicious one from what it has seen, but not always
    mem = memory or new_memory()
    if rng.random() < 0.6:
        best = max(suspicion(view, mem, q) for q in cands)
        return rng.choice([q for q in cands if suspicion(view, mem, q) == best])
    return rng.choice(cands)


# ------------------------------------------------------------------ hard: helpers
def new_memory():
    """What was seen during the match (no cheating: any player sees it):
    moved: times a character did something striking without Sherlock's side ordering it;
    moriarty: characters where Moriarty's hand was detected (overridden order);
    ran: times it ran without a Sherlock order (whoever acts on their own never runs: someone told them to);
    approach: times it got close to a possible victim without a Sherlock order;
    search: times it searched a piece of furniture without a Sherlock order;
    acts: actions without a Sherlock order (to compare).
    The room adds prof_moriarty / prof_sherlock: what was learned from the match's people (Nightmare)."""
    return {"moved": {}, "moriarty": set(), "ran": {}, "approach": {}, "search": {}, "acts": {}}


def suspicion(view, memory, q):
    p = view.pawns.get(q, {})
    if not p.get("isKillerCandidate", 1):
        return -99
    score = memory["moved"].get(q, 0) + (4 if q in memory["moriarty"] else 0)
    if p.get("isHaveWeapon"):
        score += 2
    return score


def reach(view, pid):
    return max((view.dist(g, pid) for g in view.grids(pid)), default=0)


def awake(view, q):
    return not view.pawns.get(q, {}).get("isBlind")


def watched(view, grid, dark, watchers, room_of_target=None):
    """Could anyone see what happens on that square at the end of the turn?
    watchers: {character: list of squares where it can end}. In a blackout only whoever
    ends on the same square counts; with light, anyone in the room. Witness dogs too."""
    room, gid = grid.get("roomId"), grid.get("gridId")
    for ends in watchers.values():
        for g in ends:
            if (g.get("gridId") == gid) if dark else (g.get("roomId") == room):
                return True
    return view.threat_witness(room)


def assault_is_certain(view, killer, target, watchers):
    """Assault only if it is safe: wherever the victim goes, the killer gets there and nobody sees it."""
    kr = reach(view, killer)
    tg = view.grids(target)
    if not tg or kr <= 0:
        return False
    dark = view.dark and not view.pawns[target].get("isNoBlack")
    for g in tg:
        if view.dist(g, killer) > kr or watched(view, g, dark, watchers):
            return False
    return True


def walk(view, pid):
    """Squares reached walking: making someone run draws Sherlock's attention."""
    return [g for g in view.grids(pid) if view.self_dist(pid, g) <= WALK_RANGE] or view.grids(pid)


def lure(view, idx, w, target, rng):
    """Move a witness away from the victim, better towards a hazard (gas, dogs), always walking
    (if it runs, Sherlock gets suspicious)."""
    troom = view.pawns[target].get("roomId")

    def value(g):
        return (3 * view.danger(g) + view.dist(g, target) - (5 if g.get("roomId") == troom else 0), rng.random())
    g = max(walk(view, w), key=value)
    return order(view, idx, w, MOVE, g), g


def has_food(view, pid):
    return any(int(i.get("itemType", -1)) == 1 for i in view.pawns.get(pid, {}).get("itemList") or [])


def search_no_food(view, idx, pid, grids, rng, prefer=None):
    """Search or move without taking food: the others are better off staying hungry."""
    saved = set(view.unavailable)
    view.unavailable |= view.food_objects
    try:
        o = search_or_move(view, idx, pid, grids, rng, prefer)
    finally:
        added = view.unavailable - saved - view.food_objects
        view.unavailable = saved | added
    return o


# ------------------------------------------------------------------ hard: Moriarty
def plan_moriarty_hard(view, idx, killer, target, n_orders, rng, taken=(), memory=None):
    """Hard Moriarty: the one below (_moriarty_hard_core) and, without an assault, its spare orders are not
    wasted (fill_free_orders)."""
    orders, assault = _moriarty_hard_core(view, idx, killer, target, n_orders, rng, taken)
    if assault:
        return orders, True
    pred = predict_sherlock(view, memory or new_memory(), rng)
    return fill_free_orders(view, idx, killer, target, orders, n_orders, rng, taken, pred), False


def fill_free_orders(view, idx, killer, target, orders, n_orders, rng, taken, predicted):
    """Hard and above: Moriarty doesn't waste orders, but doesn't take risks without a reason either. Its
    spare ones go to characters Sherlock isn't going to order (predicted: so they don't clash and give it away) and always
    walking, like the character would on its own:
    1. move a possible witness away from the victim (someone who could reach her room);
    2. otherwise, search or move without taking food, without getting close to the victim (it doesn't spoil its murder).
    It never orders the killer (the plan decides that) or the victim."""
    out = list(orders)
    used = set(taken) | {killer, target} | {o["pawnId"] for o in out}
    free = [q for q in view.ids() if q not in used and q not in predicted and awake(view, q) and view.grids(q)]
    troom = view.pawns[target].get("roomId")
    rooms = {g.get("roomId") for g in view.grids(target)} | {troom}
    witnesses = sorted([q for q in free if any(g.get("roomId") in rooms for g in view.grids(q))],
                       key=lambda q: (view.pawns[q].get("roomId") != troom, view.pair_distance(q, target)))
    for q in witnesses:
        if len(out) >= n_orders:
            return out
        o, g = lure(view, idx, q, target, rng)
        if g.get("roomId") not in rooms:
            out.append(o)
            used.add(q)
    rest = [q for q in free if q not in used]
    rng.shuffle(rest)
    for q in rest:
        if len(out) >= n_orders:
            break
        away = [g for g in walk(view, q) if g.get("roomId") not in rooms]
        o = search_no_food(view, idx, q, away, rng) if away else None
        if o:
            out.append(o)
    return out


def _moriarty_hard_core(view, idx, killer, target, n_orders, rng, taken=()):
    """Hard Moriarty:
    - Assault only when it is safe: the victim can't escape the killer's reach and no
      witness can end in her room (working out how far each one can walk). In a
      blackout only whoever ends on the same square counts, so it takes advantage of the dark.
    - Its killer always armed and fed: if it has no weapon it goes for the one it knows about (or
      gets closer to it) and if it is hungry or carries no food, it takes the one it knows.
    - With a weapon it prefers to stand on the victim's square when nobody can see it: if the
      victim doesn't move, she falls at the end of the turn without it being revealed.
    - It gives as few orders as possible: each order that clashes with a Sherlock one gives it away. It only uses
      the second order if it gets the kill with it (moving the only witness away); sometimes it doesn't even move its
      killer and lets it act on its own, like everyone else.
    - It never makes anyone run (Sherlock suspects whoever runs) and doesn't let the others take
      food."""
    used = set(taken) | {target}
    orders = []
    k = view.pawns[killer]
    armed = bool(k.get("isHaveWeapon"))
    others = [q for q in view.ids() if q not in (killer, target) and awake(view, q)]
    watchers = {q: view.grids(q) or [view.here(q)] for q in others}
    tgrids = view.grids(target)
    troom = view.pawns[target].get("roomId")

    def threatens(q):     # can end in some room the victim can go to
        rooms = {g.get("roomId") for g in tgrids} | {troom}
        return any(g.get("roomId") in rooms for g in watchers[q])

    blockers = sorted([q for q in others if q not in used and view.grids(q) and threatens(q)],
                      key=lambda q: (view.pawns[q].get("roomId") != troom, view.pair_distance(q, target)))
    if killer in used or not view.grids(killer):
        return [], False
    kwalk = walk(view, killer)
    dark = view.dark and not view.pawns[target].get("isNoBlack")

    def with_one_lure(test):
        """Tries without extra orders and, if that isn't enough, moving a single witness away."""
        if test(watchers):
            return []
        if n_orders < 2:
            return None
        for w in blockers[:3]:
            extra, g = lure(view, idx, w, target, rng)
            ws = dict(watchers)
            ws[w] = [g]
            if test(ws):
                return [extra]
        return None

    def grab(kinds, prefer=None):
        """Search a known piece of furniture (weapon or food) within walking reach."""
        opts = [(g, o) for g in kwalk for o in view.searchable(g) if o in kinds]
        if not opts:
            return None
        g, o = min(opts, key=lambda go: (view.danger(go[0]), view.dist(go[0], prefer) if prefer is not None else 0,
                                          rng.random()))
        return order(view, idx, killer, SEARCH, g, o)

    def toward(kinds):
        """Get closer to a known piece of furniture that isn't within reach yet: some character has it close."""
        holders = [q for q in view.ids() if q != killer and
                   any(o in kinds for g in view.grids(q) for o in view.searchable(g))]
        if not holders:
            return None
        q = min(holders, key=lambda q: view.pair_distance(killer, q))
        g = min(kwalk, key=lambda g: (view.dist(g, q), view.danger(g), rng.random()))
        return order(view, idx, killer, MOVE, g)

    if armed:
        # 1. Safe assault
        extra = with_one_lure(lambda ws: assault_is_certain(view, killer, target, ws))
        if extra is not None:
            return [assault_order(view, idx, killer, target)] + extra, True
    food = grab(view.food_objects, prefer=target) if not has_food(view, killer) or k.get("isHungry") else None
    # 2. When hungry, eat first (hungry, it reaches less far)
    if food and k.get("isHungry"):
        return [food], False
    if not armed:
        # 3. Arm itself: the weapon it knows about; if it isn't at hand, take spare food or get closer to the weapon
        o = grab(view.weapon_objects, prefer=target) or food or toward(view.weapon_objects) or \
            search_no_food(view, idx, killer, kwalk, rng, prefer=target)
        return ([o] if o else []), False
    # 3b. Armed and without food on it: get spare food (sometimes, so as not to be predictable)
    if food and rng.random() < 0.5:
        return [food], False
    # 4. Stand on the victim's square without anyone seeing it
    here = next((g for g in kwalk if view.dist(g, target) == 0), None)
    if here is not None:
        extra = with_one_lure(lambda ws: not watched(view, here, dark, ws))
        if extra is not None:
            return [order(view, idx, killer, MOVE, here)] + extra, False
    # 5. No chance: sometimes it lets its killer act on its own (it gives no clues)...
    if view.pair_distance(killer, target) <= 3 and rng.random() < 0.4:
        return [], False
    # ...and otherwise it stalks her 2 squares away, walking
    g = min(kwalk, key=lambda g: (abs(view.dist(g, target) - 2), view.danger(g), rng.random()))
    return [order(view, idx, killer, MOVE, g)], False


# ------------------------------------------------------------------ hard: Sherlock
def plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=None, probes=1, avoid_sus=None):
    """Hard Sherlock (only with what a player sees):
    - It protects the most exposed possible victim first, bringing her close to trusted people and away from
      armed suspects.
    - It uses as an escort whoever is already ruled out as the killer; if they are also ruled out as the
      victim, they can share a square with her.
    - It doesn't waste orders on characters Moriarty already controls and moves the most suspicious away.
    - The rest, together 3 squares apart or less so nobody is left alone."""
    orders, used = [], set(taken)
    ids = view.ids()
    pw = view.pawns
    sus = {q: (sus_fn or suspicion)(view, memory, q) for q in ids}
    cleared = [q for q in ids if not pw[q].get("isKillerCandidate", 1)]
    cleared_both = [q for q in cleared if not pw[q].get("isTargetCandidate", 1)]
    victims = [q for q in ids if pw[q].get("isTargetCandidate", 1)]
    if avoid_sus is not None:      # a clear suspect isn't protected as a possible victim
        victims = [q for q in victims if sus[q] < avoid_sus] or victims
    armed_sus = [q for q in ids if pw[q].get("isHaveWeapon") and sus[q] > -99]
    planned = {}          # character -> square we send it to

    def orderable(q):
        return q not in used and view.grids(q) and q not in memory["moriarty"]

    def risk(g, who):
        """Risk of ending on that square for a possible victim: armed suspects who get there."""
        return sum(1 for a in armed_sus if a != who and any(x.get("gridId") == g.get("gridId") for x in view.grids(a)))

    def add(q, kind, g, target_id=-1):
        orders.append(order(view, idx, q, kind, g, target_id))
        used.add(q)
        planned[q] = g

    def exposure(v):
        room = pw[v].get("roomId")
        guards = [q for q in cleared if q != v and pw[q].get("roomId") == room]
        near_armed = sum(1 for a in armed_sus if a != v and view.pair_distance(a, v) <= 3)
        return (len(guards) == 0) * 2 + near_armed + (len(view.room_mates(v)) == 0)

    def push_away(q):
        far = max(view.grids(q), key=lambda g: (min((view.dist(g, v) for v in victims if v != q), default=0),
                                                  -view.danger(g), rng.random()))
        add(q, MOVE, far)

    # 0. (expert) The clear suspect, first: moving them away protects every possible victim at once
    if avoid_sus is not None:
        top = max((q for q in ids if orderable(q)), key=lambda q: (sus[q], rng.random()), default=None)
        if top is not None and sus[top] >= avoid_sus and len(orders) < n_orders:
            push_away(top)

    # 1. Most exposed possible victim: with an escort and away from armed ones
    for v in sorted(victims, key=lambda v: (-exposure(v), rng.random())):
        if len(orders) >= n_orders:
            break
        if exposure(v) == 0:
            break
        if orderable(v):
            friends = [q for q in cleared if q != v] or [q for q in ids if q != v and sus[q] <= 0]

            def safety(g, v=v, friends=friends):
                return (-3 * risk(g, v) + sum(1 for f in friends if view.dist(g, f) <= 1)
                        - view.danger(g), rng.random())
            add(v, MOVE, max(view.grids(v), key=safety))
        # ruled-out escort
        dest = planned.get(v) or view.here(v)
        guard = next((q for q in sorted(cleared, key=lambda q: view.pair_distance(q, v))
                      if q != v and orderable(q)), None)
        if guard is not None and len(orders) < n_orders:
            same_ok = guard in cleared_both
            opts = view.grids(guard)

            def closeness(g, guard=guard, same_ok=same_ok, dest=dest):
                d = 0 if g.get("gridId") == dest.get("gridId") else (1 if g.get("roomId") == dest.get("roomId") else 3)
                if d == 0 and not same_ok and risk(g, guard):
                    d = 2            # don't share a square if an armed one can get there
                return (-d, -view.danger(g), rng.random())
            add(guard, MOVE, max(opts, key=closeness))

    # 2. Move the most suspicious away from the possible victims (if Moriarty also moves them, it shows)
    done = 0
    for q in sorted(ids, key=lambda q: -sus[q]):
        if len(orders) >= n_orders or sus[q] <= 0 or done >= probes:
            break
        if orderable(q):
            push_away(q)
            done += 1

    # 3. The rest: all together (3 squares apart or less) and searching if possible (the expert doesn't bring
    #    anyone close to someone it already finds very suspicious)
    rest = [q for q in ids if orderable(q) and (avoid_sus is None or sus[q] < avoid_sus)]
    for q in sorted(rest, key=lambda q: (len(view.room_mates(q)), rng.random())):
        if len(orders) >= n_orders:
            break
        others = [x for x in ids if x != q]

        def company(g):
            return sum(1 for x in others if view.dist(g, x) <= 3) - 2 * view.danger(g)
        best = max(company(g) for g in view.grids(q))
        good = [g for g in view.grids(q) if company(g) >= best - 1]
        with_obj = [g for g in good if view.searchable(g)]
        if with_obj:
            g = rng.choice(with_obj)
            add(q, SEARCH, g, rng.choice(view.searchable(g)))
        else:
            add(q, MOVE, rng.choice([g for g in good if company(g) == best]))
    return orders


# ------------------------------------------------------------------ expert
# The same rules as everyone: only what a person in that role would see. What changes is how it thinks.
def chase_order(view, idx, killer, target, pred, rng):
    """Go for the victim: as close as possible to where she will be (if Sherlock is expected to move her, from there), and
    better on her same square, where she falls at the end of the turn if nobody sees it. It runs if needed."""
    goal = pred.get(target)

    def gap(g):
        if goal is not None:
            return 0 if g.get("gridId") == goal.get("gridId") else (1 if g.get("roomId") == goal.get("roomId") else 2)
        return view.dist(g, target)
    g = min(view.grids(killer), key=lambda g: (gap(g), view.dist(g, target), view.danger(g), rng.random()))
    return order(view, idx, killer, MOVE, g)


def turns_left(view):
    """Turns left after this one (None if not known)."""
    if not view.max_turn:
        return None
    return int(view.max_turn) - int(view.turn)


def suspicion_expert(view, memory, q):
    """The expert Sherlock's suspicion. The strongest: Moriarty's hand (overridden order) and running without
    Sherlock ordering it (whoever acts on their own never runs). Then, getting close to the possible victims and
    carrying a weapon. Whoever is already ruled out as the killer doesn't count."""
    p = view.pawns.get(q, {})
    if not p.get("isKillerCandidate", 1):
        return -99
    m = memory
    score = 6 * (q in m["moriarty"]) + 3 * m.get("ran", {}).get(q, 0) + 1.5 * m.get("approach", {}).get(q, 0)
    if p.get("isHaveWeapon"):
        score += 2
    # stuck right now to a possible victim who is alone with them
    for v, pv in view.pawns.items():
        if v != q and pv.get("isTargetCandidate", 1) and view.pair_distance(q, v) <= 1:
            mates = [x for x in view.room_mates(v) if x != q]
            if not mates:
                score += 1
                break
    return score


def plan_sherlock_expert(view, idx, n_orders, rng, taken, memory):
    """Expert Sherlock: like the hard one, but
    - it suspects with more judgement (suspicion_expert);
    - it moves away and probes up to two suspects: ordering them something reveals whether Moriarty moves them (overridden
      order), and moves them away from the possible victims along the way;
    - it never brings the group close to someone it already finds very suspicious;
    - in the last two turns, the spare orders go to moving suspects away (up to three)."""
    left = turns_left(view)
    end = left is not None and left <= 1
    return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=suspicion_expert,
                              probes=3 if end else 2, avoid_sus=3)


def predict_sherlock(view, memory, rng):
    """What Sherlock would order this turn with what is seen in the match (its way of thinking is simulated).
    Returns {character: expected square}. It looks at nothing hidden: no weapons in furniture or anything of
    Moriarty's side."""
    v = copy.copy(view)
    v.unavailable = set(view.unavailable)
    v.weapon_objects, v.food_objects = set(), set()
    try:
        orders = plan_sherlock_hard(v, -1, 3, random.Random(rng.random()), set(), memory)
    except Exception:  # noqa: BLE001  (a failed prediction must not break the turn)
        return {}
    out = {}
    for o in orders:
        g = next((x for x in view.grids(o["pawnId"]) if x.get("gridId") == o["grid"]), None)
        if g is not None:
            out[o["pawnId"]] = g
    return out


def killer_is_hot(view, memory, killer, threshold=3):
    """The killer is already the main suspect in Sherlock's eyes."""
    mine = suspicion_expert(view, memory, killer)
    rest = [suspicion_expert(view, memory, q) for q in view.ids() if q != killer]
    return mine >= threshold and mine >= max(rest, default=-99)


def frame_decoy(view, idx, killer, target, memory, used, rng):
    """Make an innocent look like the killer: make them run towards another possible victim (not the real one,
    so as not to leave a witness next to her). Running without a Sherlock order is what gives the most away."""
    cands = [q for q in view.ids() if q not in used and q not in (killer, target) and awake(view, q)
             and view.pawns[q].get("isKillerCandidate", 1) and view.grids(q)]
    if not cands:
        return None
    q = max(cands, key=lambda q: (suspicion_expert(view, memory, q), rng.random()))
    victims = [v for v in view.ids() if v not in (q, target, killer) and view.pawns[v].get("isTargetCandidate", 1)]
    grids = view.grids(q)
    runs = [g for g in grids if view.self_dist(q, g) > WALK_RANGE] or grids
    troom = view.pawns[target].get("roomId")
    runs = [g for g in runs if g.get("roomId") != troom] or runs
    if victims:
        g = min(runs, key=lambda g: (min(view.dist(g, v) for v in victims), view.danger(g), rng.random()))
    else:
        g = max(runs, key=lambda g: (view.dist(g, target), -view.danger(g), rng.random()))
    return order(view, idx, q, MOVE, g)


def _kill_now(view, idx, killer, target, pred, n_orders, rng, taken, desperate):
    """Last turns: look for the murder counting on what Sherlock will probably do. On the last
    turn, if nothing is safe, it takes the risk (if it doesn't kill, Moriarty doesn't win)."""
    k = view.pawns.get(killer, {})
    if not k.get("isHaveWeapon") or killer in taken or not view.grids(killer):
        return None
    others = [q for q in view.ids() if q not in (killer, target) and awake(view, q)]
    watchers = {q: ([pred[q]] if q in pred else (view.grids(q) or [view.here(q)])) for q in others}
    tgrids = [pred[target]] if target in pred else view.grids(target)
    kr = reach(view, killer)
    dark = view.dark and not view.pawns[target].get("isNoBlack")
    if tgrids and kr > 0 and all(view.dist(g, killer) <= kr and not watched(view, g, dark, watchers) for g in tgrids):
        return [assault_order(view, idx, killer, target)]
    if desperate:
        troom = view.pawns[target].get("roomId")
        now = [q for q in view.room_mates(target) if q != killer and awake(view, q)]
        if not now and not view.threat_witness(troom) and any(view.dist(g, target) == 0 for g in view.grids(killer)):
            return [assault_order(view, idx, killer, target)]
    return None


def plan_moriarty_expert(view, idx, killer, target, n_orders, rng, taken=(), memory=None,
                         kill_window=2, frame_p=0.3, hot_threshold=3, decoy_when_hot=True):
    """Expert Moriarty: the hard one (safe assault, armed, no running, darkness...) and also
    - it foresees Sherlock's orders: if Sherlock is going to move its killer, it doesn't give it an order that doesn't kill
      (they would clash and its hand would show);
    - if its killer is already the main suspect, it hides: it doesn't bring it close to the victim and makes
      an innocent run towards another possible victim so they look like the killer;
    - in the last turns it looks for the murder counting on what is expected, and on the last one it takes the risk;
    - in the last kill_window + 2 turns, if its armed killer can still reach the victim in the turns
      left, it stops hiding and goes for her (running if needed). If it can't, it stays hidden with
      decoys: better a draw (Sherlock doesn't get it right) than being seen and losing."""
    mem = memory or new_memory()
    left = turns_left(view)
    pred = predict_sherlock(view, mem, rng)
    chase = left is not None and left <= kill_window + 2 and bool(view.pawns[killer].get("isHaveWeapon")) \
        and killer not in taken and bool(view.grids(killer)) \
        and view.pair_distance(killer, target) <= reach(view, killer) * (left + 1)   # there is time to get there
    if left is not None and left <= kill_window:
        kill = _kill_now(view, idx, killer, target, pred, n_orders, rng, set(taken) | {target}, desperate=left <= 0)
        if kill:
            return kill, True
    orders, assault = _moriarty_hard_core(view, idx, killer, target, n_orders, rng, taken)
    if assault:
        return orders, True
    tgrid = view.pawns[target].get("gridId")
    hot = killer_is_hot(view, mem, killer, hot_threshold)

    def kills(o):           # stand on the victim's square, armed: if she stays, she falls at the end of the turn
        return o["pawnId"] == killer and o["type"] == MOVE and o["grid"] == tgrid and \
            view.pawns[killer].get("isHaveWeapon")
    keep = []
    for o in orders:
        if o["pawnId"] == killer and not kills(o):
            if chase:
                continue                    # at the end, the killer's order is to go for the victim (below)
            if killer in pred and (left is None or left > 3):
                continue                    # it would clash with Sherlock and give it away
            if hot and o["type"] == MOVE:
                continue                    # low profile: neither approach nor stalk
        keep.append(o)
    if chase and not any(o["pawnId"] == killer for o in keep):
        keep.insert(0, chase_order(view, idx, killer, target, pred, rng))
    used = set(taken) | {target} | {o["pawnId"] for o in keep}
    if len(keep) < n_orders and ((hot and decoy_when_hot) or rng.random() < frame_p):
        d = frame_decoy(view, idx, killer, target, mem, used, rng)
        if d:
            keep.append(d)
    return fill_free_orders(view, idx, killer, target, keep[:n_orders], n_orders, rng, taken, pred), False


def plan_irene_expert(view, idx, killer, target, rng, taken, memory, frame_first=False):
    """Expert Irene (beats Sherlock without leaving a trace): moves the victim's witness towards a
    hazard; if there is none, arms the killer; if it already is, makes an innocent look guilty."""
    used = set(taken) | {target}
    witnesses = [q for q in view.room_mates(target) if q not in used and q != killer and view.grids(q)]
    if witnesses:
        w = min(witnesses, key=lambda q: view.pair_distance(q, target))
        o, _ = lure(view, idx, w, target, rng)
        return [o]
    k = view.pawns.get(killer, {})
    if killer not in used and view.grids(killer) and not k.get("isHaveWeapon") and not frame_first:
        o = seek_weapon(view, idx, killer, walk(view, killer), rng, prefer=target)
        if o:
            return [o]
    d = frame_decoy(view, idx, killer, target, memory, used | {killer}, rng)
    if d:
        return [d]
    pool = [q for q in view.ids() if q not in used and q != killer and view.grids(q)]
    if not pool:
        return []
    q = rng.choice(pool)
    o = search_or_move(view, idx, q, view.grids(q), rng)
    return [o] if o else []


# ------------------------------------------------------------------ nightmare
# The expert, plus what it learned from the match's people in their earlier matches (profiles.py).
# Without a profile (few matches), it plays like the expert but more aggressive.
def suspicion_nightmare(view, memory, q):
    """The Nightmare Sherlock's suspicion: the expert's plus what gave away this person's killer
    in their matches (if their killer used to run, search, get close...)."""
    base = suspicion_expert(view, memory, q)
    prof = memory.get("prof_moriarty")
    if base == -99 or not prof:
        return base
    w = prof.get("weights") or {}
    learned = (w.get("run", 0) * memory.get("ran", {}).get(q, 0)
               + w.get("search", 0) * memory.get("search", {}).get(q, 0)
               + w.get("approach", 0) * memory.get("approach", {}).get(q, 0)
               + w.get("batting", 0) * (q in memory.get("moriarty", ())))
    return base + 2 * learned


def danger_turn(view, memory):
    """Turn on which this match's Moriarty usually attacks (or one before/after)."""
    prof = memory.get("prof_moriarty")
    if not prof or not prof.get("kill_turns"):
        return False
    return any(abs(int(view.turn) - t) <= 1 for t in prof["kill_turns"])


def plan_sherlock_nightmare(view, idx, n_orders, rng, taken, memory):
    """Nightmare Sherlock: the expert with the learned suspicion. On the turns that person usually
    attacks and on the last two, everything goes to protecting (it only moves the main suspect away)."""
    left = turns_left(view)
    end = left is not None and left <= 1
    tense = danger_turn(view, memory)
    probes = 3 if end else (1 if tense else 2)
    return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=suspicion_nightmare,
                              probes=probes, avoid_sus=3)


def plan_moriarty_nightmare(view, idx, killer, target, n_orders, rng, taken=(), memory=None):
    """Nightmare Moriarty: the expert adjusted to the match's Sherlock.
    - If that person falls for the decoys (accuses the innocent who ran), decoys almost always; if they don't
      fall for them, few (they would only give Moriarty away).
    - If they usually watch the killer with their orders, it hides its own earlier.
    - It looks for the murder from four turns before the end (the expert, two)."""
    mem = memory or new_memory()
    prof = mem.get("prof_sherlock")
    frame_p, hot = 0.45, 3
    if prof:
        fooled = prof.get("fooled_by_runner")
        if fooled is not None:
            frame_p = 0.9 if fooled >= 0.5 else (0.15 if fooled < 0.25 else 0.45)
        if prof.get("tracks_killer", 1.0) >= 1.4:
            hot = 1.5
    return plan_moriarty_expert(view, idx, killer, target, n_orders, rng, taken, mem,
                                kill_window=4, frame_p=frame_p, hot_threshold=hot,
                                decoy_when_hot=frame_p >= 0.45)
