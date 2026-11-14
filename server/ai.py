"""
CRIMESIGHT Revival - IA de los jugadores bot.

Cada turno el cliente manda al servidor (reference_data) el estado de la mansion:
para cada personaje, las casillas a las que puede llegar este turno (gridList) con
su habitacion, los muebles registrables, los objetos en el suelo y la distancia
desde esa casilla a cada personaje (pawnDistance). Con eso la IA genera ordenes
validas sin conocer el mapa.

Reglas (guias de la comunidad + codigo del cliente):
- Sherlock da ordenes a 3 personajes (puede incluir a la victima); Moriarty a 2,
  nunca a la victima. Si ambos ordenan al mismo personaje, gana Moriarty.
- Andar llega a 2 casillas, correr a 3 (isRun). Hambrientos o heridos llegan menos.
- Para matar, el asesino necesita un arma, estar en la casilla de la victima y que
  no haya testigos en la habitacion. El "Asalto" (orden tipo 5) hace que el asesino
  actue el ultimo y vaya directo a por la victima; si falla, ambos quedan al
  descubierto.
- Watson (bando Sherlock) e Irene (bando Moriarty) dan 1 orden cada uno. Irene no puede
  asaltar ni dar ordenes a la victima. Irene gana a Sherlock/Watson sin dejar rastro; si
  Moriarty pisa una orden distinta de Sherlock/Watson, se nota (isBatting).
- El bando de Moriarty sabe en que muebles hay armas desde el principio.
- Los personajes sin ordenes actuan por su cuenta (en linea lo decide el servidor).
- Peligros: los escapes de gas hieren a quien acabe el turno en esa habitacion; los perros
  salvajes atacan a los personajes cercanos (algunas amenazas cuentan como testigo).
"""
import random

MOVE, SEARCH, TARGET = 2, 3, 5
NO_TARGET = 130              # valor que manda el cliente cuando la orden no apunta a una casilla
WALK_RANGE = 2
GRID_W = 10                  # GridManager: id = x*10 + z (z con el signo de x)

DIFFICULTIES = ["normal", "hard", "easy"]       # orden del ciclo al "expulsar" a una IA
LABEL = {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}
# Nombre de las IA en el idioma del anfitrion (codigos de idioma del juego)
BOT_NAMES = {
    "ES": ("IA", {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}),
    "EN": ("AI", {"easy": "Easy", "normal": "Normal", "hard": "Hard"}),
    "FR": ("IA", {"easy": "Facile", "normal": "Normal", "hard": "Difficile"}),
    "IT": ("IA", {"easy": "Facile", "normal": "Normale", "hard": "Difficile"}),
    "DE": ("KI", {"easy": "Leicht", "normal": "Normal", "hard": "Schwer"}),
    "PT": ("IA", {"easy": "Fácil", "normal": "Normal", "hard": "Difícil"}),
    "RU": ("ИИ", {"easy": "Легко", "normal": "Нормально", "hard": "Сложно"}),
    "JP": ("AI", {"easy": "かんたん", "normal": "ふつう", "hard": "むずかしい"}),
    "KO": ("AI", {"easy": "쉬움", "normal": "보통", "hard": "어려움"}),
    "CN": ("AI", {"easy": "简单", "normal": "普通", "hard": "困难"}),
    "TW": ("AI", {"easy": "簡單", "normal": "普通", "hard": "困難"}),
}


def bot_name(slot, difficulty, lang=None):
    prefix, labels = BOT_NAMES.get(str(lang or "").upper(), BOT_NAMES["EN"])
    return f"{prefix}_{slot} ({labels.get(difficulty, difficulty)})"


def turn_clock(turn):
    """turno -> (dia, momento del dia): 3 momentos por dia."""
    t = max(1, int(turn))
    return (t - 1) // 3 + 1, (t - 1) % 3


class View:
    """Lectura comoda del reference_data de un turno."""

    def __init__(self, ref, unavailable_objects=()):
        self.turn = int(ref.get("turn", 1))
        self.pawns = {int(p["pawnId"]): p for p in ref.get("pawns", []) if isinstance(p, dict)}
        self.unavailable = set(unavailable_objects)
        self.weapon_objects = set()     # muebles con arma (solo lo sabe el bando de Moriarty)
        self.food_objects = set()       # muebles con comida (Moriarty los conoce todos)
        self.dark = bool(int(ref.get("isBlack", 0) or 0))
        self.threats = [t for t in ref.get("threatList") or [] if isinstance(t, dict) and not t.get("isDie")]
        self.gas_rooms = {g.get("roomId") for g in ref.get("gaspipeList") or [] if isinstance(g, dict)}

    @staticmethod
    def xy(grid_id):
        g = int(grid_id)
        return int(g / GRID_W), abs(g) % GRID_W

    def danger(self, grid):
        """Cuanto riesgo tiene acabar el turno en esa casilla (gas, perros cerca)."""
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
        view.unavailable.add(target_id)   # nadie mas registra este mueble este turno
    return {"pawnId": pid, "playerId": player_index, "type": kind, "days": days, "timeZone": tz,
            "grid": int(grid["gridId"]), "target": NO_TARGET,
            "isRun": 1 if view.self_dist(pid, grid) > WALK_RANGE else 0, "targetId": int(target_id)}


def search_or_move(view, idx, pid, grids, rng, prefer=None):
    """Registra un mueble si hay alguno a mano; si no, se mueve (opcionalmente hacia 'prefer')."""
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
    """Registrar un mueble que se sabe que tiene un arma, si hay alguno a mano."""
    options = [(g, o) for g in grids for o in view.searchable(g) if o in view.weapon_objects]
    if not options:
        return None
    options.sort(key=lambda go: (view.danger(go[0]), view.dist(go[0], prefer) if prefer is not None else 0,
                                 rng.random()))
    g, o = options[0]
    return order(view, idx, pid, SEARCH, g, o)


NPC_SEARCH_PROB = 0.5


def npc_order(view, pid, rng):
    """Pawn.RunNpcAction: sin ordenes, el personaje registra algo a su alcance andando o se
    mueve a una casilla cercana (a veces se queda donde esta)."""
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
    """Casilla alcanzable por pid lo mas lejos posible de 'other' (sin meterse en peligro si se puede)."""
    return max(view.grids(pid), key=lambda g: (view.dist(g, other) - 2 * view.danger(g), view.dist(g, other)))


# ------------------------------------------------------------------ Moriarty
def plan_moriarty(view, idx, killer, target, n_orders, difficulty, rng, taken=()):
    """Ordenes para el bando de Moriarty. Devuelve (ordenes, asalto?)."""
    orders, used = [], set(taken) | {target}
    if killer not in view.pawns or target not in view.pawns:
        return orders, False
    if difficulty == "hard":
        return plan_moriarty_hard(view, idx, killer, target, n_orders, rng, taken)
    if difficulty == "easy":
        return plan_moriarty_easy(view, idx, killer, target, n_orders, rng, taken)
    return plan_moriarty_normal(view, idx, killer, target, n_orders, rng, taken)


def assault_order(view, idx, killer, target):
    t = view.pawns[target]
    return {**order(view, idx, killer, TARGET, {"gridId": t.get("gridId"), "pawnDistance": []}),
            "targetId": int(t.get("uniqId", -1)), "isRun": 0}


def plan_moriarty_normal(view, idx, killer, target, n_orders, rng, taken=()):
    """Moriarty normal: toma tres cosas del dificil, sin ser implacable.
    - Nunca hace correr a nadie (llamaria la atencion de Sherlock).
    - Asalta solo si nadie puede llegar este turno a la habitacion de la victima (aunque no
      comprueba si ella puede escaparse, asi que a veces falla).
    - Con arma, se planta en la casilla de la victima si ahora mismo esta sola en su habitacion.
    Su otra orden aparta, andando, a quien acompana a la victima."""
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
        o = search_or_move(view, idx, q, walk(view, q), rng)   # comportarse como un sospechoso mas
        if o:
            orders.append(o)
        used.add(q)
    return orders, False


def plan_moriarty_easy(view, idx, killer, target, n_orders, rng, taken=()):
    """Moriarty facil: comete errores que un Sherlock atento puede pillar.
    - Hace correr a su asesino a menudo y lo pega a la victima turno tras turno.
    - A veces asalta aunque haya testigos (y entonces suele fallar y quedar al descubierto).
    - Su otra orden es casi siempre un movimiento al azar."""
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
            # pegarse a la victima, corriendo si hace falta: muy evidente
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
    """Ordenes para el bando de Sherlock: buscar objetos y no dejar a nadie solo."""
    if difficulty == "hard":
        return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory or new_memory())
    orders, used = [], set(taken)
    pool = [q for q in view.ids() if q not in used and view.grids(q)]
    if difficulty == "easy":
        return plan_sherlock_easy(view, idx, n_orders, rng, pool)
    return plan_sherlock_normal(view, idx, n_orders, rng, pool, memory or new_memory())


def plan_sherlock_normal(view, idx, n_orders, rng, pool, memory):
    """Sherlock normal: toma tres cosas del dificil.
    - No gasta ordenes en personajes que Moriarty ya controla (orden pisada) si hay otros.
    - Mantiene a la gente junta, a 3 casillas o menos, empezando por las posibles victimas aisladas.
    - Al final acusa casi siempre al mas sospechoso de lo que ha visto (ver accuse)."""
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


# ------------------------------------------------------------------ Irene y Watson
def plan_irene(view, idx, killer, target, difficulty, rng, taken=()):
    """Irene (bando Moriarty): 1 orden, sin asalto y nunca sobre la victima.
    Prioridad: apartar a un testigo de la victima; si no, ayudar al asesino sin arma;
    si no, despistar como un Watson cualquiera."""
    used = set(taken) | {target}
    if target not in view.pawns:
        return []
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
    """Sherlock facil: ordenes casi al azar, sin mirar peligros ni quien va armado; a veces deja
    sola a una posible victima o la acerca a un sospechoso."""
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
    """Watson (bando Sherlock): 1 orden con el mismo criterio que Sherlock."""
    return plan_sherlock(view, idx, 1, difficulty, rng, taken, memory)


def accuse(view, killer, difficulty, rng, n_pawns, memory=None):
    """Acusacion final de un Sherlock IA."""
    everyone = list(range(n_pawns))
    if view is None:
        return rng.choice(everyone)
    cands = [q for q, p in view.pawns.items() if p.get("isKillerCandidate")] or everyone
    if difficulty == "easy":
        return rng.choice(everyone)
    if difficulty == "hard":
        # Solo con lo que ha visto: el mas sospechoso de los que aun pueden ser el asesino
        mem = memory or new_memory()
        best = max(suspicion(view, mem, q) for q in cands)
        return rng.choice([q for q in cands if suspicion(view, mem, q) == best])
    # normal: suele acusar al mas sospechoso de lo que ha visto, pero no siempre
    mem = memory or new_memory()
    if rng.random() < 0.6:
        best = max(suspicion(view, mem, q) for q in cands)
        return rng.choice([q for q in cands if suspicion(view, mem, q) == best])
    return rng.choice(cands)


# ------------------------------------------------------------------ dificil: utilidades
def new_memory():
    """Lo que el bando de Sherlock ha ido viendo durante la partida (sin trampas):
    moved: veces que un personaje actuo sin que lo ordenara su equipo;
    moriarty: personajes en los que se detecto la mano de Moriarty (orden pisada)."""
    return {"moved": {}, "moriarty": set()}


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
    """Podria alguien ver lo que pasa en esa casilla al final del turno?
    watchers: {personaje: lista de casillas donde puede acabar}. Con apagon solo cuenta quien
    acabe en la misma casilla; con luz, cualquiera en la habitacion. Los perros testigo tambien."""
    room, gid = grid.get("roomId"), grid.get("gridId")
    for ends in watchers.values():
        for g in ends:
            if (g.get("gridId") == gid) if dark else (g.get("roomId") == room):
                return True
    return view.threat_witness(room)


def assault_is_certain(view, killer, target, watchers):
    """Asalto solo si es seguro: vaya donde vaya la victima, el asesino llega y nadie lo ve."""
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
    """Casillas a las que se llega andando: hacer correr a alguien llama la atencion de Sherlock."""
    return [g for g in view.grids(pid) if view.self_dist(pid, g) <= WALK_RANGE] or view.grids(pid)


def lure(view, idx, w, target, rng):
    """Alejar a un testigo de la victima, mejor hacia un peligro (gas, perros), siempre andando
    (si corre, Sherlock sospecha)."""
    troom = view.pawns[target].get("roomId")

    def value(g):
        return (3 * view.danger(g) + view.dist(g, target) - (5 if g.get("roomId") == troom else 0), rng.random())
    g = max(walk(view, w), key=value)
    return order(view, idx, w, MOVE, g), g


def has_food(view, pid):
    return any(int(i.get("itemType", -1)) == 1 for i in view.pawns.get(pid, {}).get("itemList") or [])


def search_no_food(view, idx, pid, grids, rng, prefer=None):
    """Registrar o moverse sin coger comida: a los demas les conviene seguir hambrientos."""
    saved = set(view.unavailable)
    view.unavailable |= view.food_objects
    try:
        o = search_or_move(view, idx, pid, grids, rng, prefer)
    finally:
        added = view.unavailable - saved - view.food_objects
        view.unavailable = saved | added
    return o


# ------------------------------------------------------------------ dificil: Moriarty
def plan_moriarty_hard(view, idx, killer, target, n_orders, rng, taken=()):
    """Moriarty dificil:
    - Asalto solo cuando es seguro: la victima no puede escapar del alcance del asesino y ningun
      testigo puede acabar en su habitacion (calculando hasta donde puede andar cada uno). Con
      apagon solo cuenta quien acabe en la misma casilla, asi que aprovecha la oscuridad.
    - Si no, con arma prefiere plantarse en la casilla de la victima cuando nadie puede verlo:
      si la victima no se mueve, cae al final del turno sin revelarse.
    - Usa su otra orden para quitar testigos de en medio, llevandolos a peligros.
    - Nunca hace correr a nadie (Sherlock sospecha de quien corre) y no deja que los demas cojan
      comida, salvo su asesino si tiene hambre."""
    used = set(taken) | {target}
    orders = []
    k = view.pawns[killer]
    armed = bool(k.get("isHaveWeapon"))
    others = [q for q in view.ids() if q not in (killer, target) and awake(view, q)]
    watchers = {q: view.grids(q) or [view.here(q)] for q in others}
    tgrids = view.grids(target)
    troom = view.pawns[target].get("roomId")

    def threatens(q):     # puede acabar en alguna habitacion a la que pueda ir la victima
        rooms = {g.get("roomId") for g in tgrids} | {troom}
        return any(g.get("roomId") in rooms for g in watchers[q])

    blockers = sorted([q for q in others if q not in used and view.grids(q) and threatens(q)],
                      key=lambda q: (view.pawns[q].get("roomId") != troom, view.pair_distance(q, target)))
    can_order_killer = killer not in used and view.grids(killer)
    kwalk = walk(view, killer) if can_order_killer else []


    def feed_killer():
        """Su asesino si come: con hambre y sin comida, a por la comida que conoce (andando)."""
        if not (k.get("isHungry") and not has_food(view, killer)):
            return None
        food = [(g, o) for g in kwalk for o in view.searchable(g) if o in view.food_objects]
        if not food:
            return None
        g, o = min(food, key=lambda go: (view.danger(go[0]), view.dist(go[0], target), rng.random()))
        return order(view, idx, killer, SEARCH, g, o)

    if armed and can_order_killer:
        # 1. Asalto seguro (si hace falta, apartando antes a un testigo con la otra orden)
        plans = [None] + (blockers[:3] if n_orders >= 2 else [])
        for w in plans:
            ws = dict(watchers)
            extra = None
            if w is not None:
                extra, g = lure(view, idx, w, target, rng)
                ws[w] = [g]
            if assault_is_certain(view, killer, target, ws):
                t = view.pawns[target]
                orders.append({**order(view, idx, killer, TARGET, {"gridId": t.get("gridId"), "pawnDistance": []}),
                               "targetId": int(t.get("uniqId", -1)), "isRun": 0})
                if extra:
                    orders.append(extra)
                return orders, True
        # 2. Si tiene hambre, comer antes de seguir (con hambre llega menos lejos)
        o = feed_killer()
        if o:
            orders.append(o)
            return fill_moriarty(view, idx, killer, target, n_orders, rng, used | {killer}, orders, blockers), False
        # 3. Plantarse en la casilla de la victima si nadie puede verlo (sin revelarse)
        here = next((g for g in kwalk if view.dist(g, target) == 0), None)    # andando: sin llamar la atencion
        if here is not None:
            dark = view.dark and not view.pawns[target].get("isNoBlack")
            for w in [None] + (blockers[:3] if n_orders >= 2 else []):
                ws = dict(watchers)
                extra = None
                if w is not None:
                    extra, g = lure(view, idx, w, target, rng)
                    ws[w] = [g]
                if not watched(view, here, dark, ws):
                    orders.append(order(view, idx, killer, MOVE, here))
                    if extra:
                        orders.append(extra)
                    return fill_moriarty(view, idx, killer, target, n_orders, rng, used | {killer} |
                                         {o["pawnId"] for o in orders}, orders, blockers), False
        # 4. Acecharla a 2 casillas, sin peligro, a la espera de una ocasion
        g = min(kwalk, key=lambda g: (abs(view.dist(g, target) - 2), view.danger(g), rng.random()))
        orders.append(order(view, idx, killer, MOVE, g))
    elif can_order_killer:
        o = feed_killer() or seek_weapon(view, idx, killer, kwalk, rng, prefer=target) or \
            search_or_move(view, idx, killer, kwalk, rng, prefer=target)
        if o:
            orders.append(o)
    used |= {killer} | {o["pawnId"] for o in orders}
    return fill_moriarty(view, idx, killer, target, n_orders, rng, used, orders, blockers), False


def fill_moriarty(view, idx, killer, target, n_orders, rng, used, orders, blockers):
    """Ordenes que sobran: debilitar y apartar a los acompanantes de la victima."""
    for w in blockers:
        if len(orders) >= n_orders:
            break
        if w in used or not view.grids(w):
            continue
        o, _ = lure(view, idx, w, target, rng)
        orders.append(o)
        used.add(w)
    while len(orders) < n_orders:
        pool = [q for q in view.ids() if q not in used and q != target and view.grids(q)]
        if not pool:
            break
        # Registrar muebles (asi tambien puede dar con el plano del cuadro electrico y provocar el
        # apagon), sin coger comida y andando, como haria cualquiera por su cuenta
        q = rng.choice(pool)
        o = search_no_food(view, idx, q, walk(view, q), rng)
        if o:
            orders.append(o)
        used.add(q)
    return orders


# ------------------------------------------------------------------ dificil: Sherlock
def plan_sherlock_hard(view, idx, n_orders, rng, taken, memory):
    """Sherlock dificil (solo con lo que ve un jugador):
    - Protege primero a la posible victima mas expuesta, acercandola a gente de confianza y lejos de
      sospechosos armados.
    - Usa como escolta a quien ya esta descartado como asesino; si ademas esta descartado como
      victima, puede compartir casilla con ella.
    - No malgasta ordenes en personajes que Moriarty ya controla y aparta al mas sospechoso.
    - El resto, juntos a 3 casillas o menos para que nadie se quede a solas."""
    orders, used = [], set(taken)
    ids = view.ids()
    pw = view.pawns
    sus = {q: suspicion(view, memory, q) for q in ids}
    cleared = [q for q in ids if not pw[q].get("isKillerCandidate", 1)]
    cleared_both = [q for q in cleared if not pw[q].get("isTargetCandidate", 1)]
    victims = [q for q in ids if pw[q].get("isTargetCandidate", 1)]
    armed_sus = [q for q in ids if pw[q].get("isHaveWeapon") and sus[q] > -99]
    planned = {}          # personaje -> casilla a la que lo mandamos

    def orderable(q):
        return q not in used and view.grids(q) and q not in memory["moriarty"]

    def risk(g, who):
        """Riesgo de acabar en esa casilla para una posible victima: sospechosos armados que llegan."""
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

    # 1. Posible victima mas expuesta: con escolta y lejos de armados
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
        # escolta descartado
        dest = planned.get(v) or view.here(v)
        guard = next((q for q in sorted(cleared, key=lambda q: view.pair_distance(q, v))
                      if q != v and orderable(q)), None)
        if guard is not None and len(orders) < n_orders:
            same_ok = guard in cleared_both
            opts = view.grids(guard)

            def closeness(g, guard=guard, same_ok=same_ok, dest=dest):
                d = 0 if g.get("gridId") == dest.get("gridId") else (1 if g.get("roomId") == dest.get("roomId") else 3)
                if d == 0 and not same_ok and risk(g, guard):
                    d = 2            # no compartir casilla si un armado puede llegar
                return (-d, -view.danger(g), rng.random())
            add(guard, MOVE, max(opts, key=closeness))

    # 2. Apartar al mas sospechoso de las posibles victimas
    for q in sorted(ids, key=lambda q: -sus[q]):
        if len(orders) >= n_orders or sus[q] <= 0:
            break
        if orderable(q):
            far = max(view.grids(q), key=lambda g: (min((view.dist(g, v) for v in victims if v != q), default=0),
                                                      -view.danger(g), rng.random()))
            add(q, MOVE, far)
            break

    # 3. Resto: todos juntos (a 3 casillas o menos) y registrando si se puede
    for q in sorted([q for q in ids if orderable(q)], key=lambda q: (len(view.room_mates(q)), rng.random())):
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
