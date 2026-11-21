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
import copy, random

MOVE, SEARCH, TARGET = 2, 3, 5
NO_TARGET = 130              # valor que manda el cliente cuando la orden no apunta a una casilla
WALK_RANGE = 2
GRID_W = 10                  # GridManager: id = x*10 + z (z con el signo de x)

DIFFICULTIES = ["normal", "hard", "expert", "nightmare", "easy"]     # orden del ciclo al "expulsar" a una IA
RANK = {"easy": 0, "normal": 1, "hard": 2, "expert": 3, "nightmare": 4}
LABEL = {"easy": "Fácil", "normal": "Normal", "hard": "Difícil", "expert": "Experto", "nightmare": "Pesadilla"}
# Nombre de las IA en el idioma del anfitrion (codigos de idioma del juego)
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
        self.max_turn = None            # lo pone la sala: turnos de la partida (para saber cuanto queda)

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
def plan_moriarty(view, idx, killer, target, n_orders, difficulty, rng, taken=(), memory=None):
    """Ordenes para el bando de Moriarty. Devuelve (ordenes, asalto?)."""
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
def plan_irene(view, idx, killer, target, difficulty, rng, taken=(), memory=None):
    """Irene (bando Moriarty): 1 orden, sin asalto y nunca sobre la victima.
    Prioridad: apartar a un testigo de la victima; si no, ayudar al asesino sin arma;
    si no, despistar como un Watson cualquiera."""
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
    if difficulty in ("expert", "nightmare"):
        mem = memory or new_memory()
        fn = suspicion_nightmare if difficulty == "nightmare" else suspicion_expert
        best = max(fn(view, mem, q) for q in cands)
        top = [q for q in cands if fn(view, mem, q) == best]
        return min(top, key=lambda q: (-mem["moved"].get(q, 0), rng.random()))
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
    """Lo que se ha visto durante la partida (sin trampas: lo ve cualquier jugador):
    moved: veces que un personaje hizo algo llamativo sin que lo ordenara el bando de Sherlock;
    moriarty: personajes en los que se detecto la mano de Moriarty (orden pisada);
    ran: veces que corrio sin orden de Sherlock (quien va por su cuenta nunca corre: alguien se lo mando);
    approach: veces que se acerco a una posible victima sin orden de Sherlock;
    search: veces que registro un mueble sin orden de Sherlock;
    acts: acciones sin orden de Sherlock (para comparar).
    La sala anade prof_moriarty / prof_sherlock: lo aprendido de las personas de la partida (Pesadilla)."""
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
def plan_moriarty_hard(view, idx, killer, target, n_orders, rng, taken=(), memory=None):
    """Moriarty dificil: lo de abajo (_moriarty_hard_core) y, sin asalto, las ordenes que le sobran no se
    pierden (fill_free_orders)."""
    orders, assault = _moriarty_hard_core(view, idx, killer, target, n_orders, rng, taken)
    if assault:
        return orders, True
    pred = predict_sherlock(view, memory or new_memory(), rng)
    return fill_free_orders(view, idx, killer, target, orders, n_orders, rng, taken, pred), False


def fill_free_orders(view, idx, killer, target, orders, n_orders, rng, taken, predicted):
    """Dificil y superiores: Moriarty no desperdicia ordenes, pero tampoco se arriesga sin motivo. Las que le
    sobran van a personajes que Sherlock no va a ordenar (predicted: asi no chocan y no le delatan) y siempre
    andando, como haria el personaje por su cuenta:
    1. alejar a un posible testigo de la victima (alguien que podria llegar a su habitacion);
    2. si no, registrar o moverse sin coger comida, sin acercarse a la victima (no estropea su asesinato).
    Nunca ordena al asesino (lo decide el plan) ni a la victima."""
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
    """Moriarty dificil:
    - Asalto solo cuando es seguro: la victima no puede escapar del alcance del asesino y ningun
      testigo puede acabar en su habitacion (calculando hasta donde puede andar cada uno). Con
      apagon solo cuenta quien acabe en la misma casilla, asi que aprovecha la oscuridad.
    - Su asesino siempre armado y alimentado: si no tiene arma va a por la que sabe donde esta (o
      se acerca a ella) y si tiene hambre o no lleva comida, coge la que conoce.
    - Con arma prefiere plantarse en la casilla de la victima cuando nadie puede verlo: si la
      victima no se mueve, cae al final del turno sin revelarse.
    - Da las menos ordenes posibles: cada orden que choca con una de Sherlock le delata. Solo usa
      la segunda orden si con ella consigue matar (apartar al unico testigo); a veces ni mueve a su
      asesino y deja que actue por su cuenta, como uno mas.
    - Nunca hace correr a nadie (Sherlock sospecha de quien corre) y no deja que los demas cojan
      comida."""
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
    if killer in used or not view.grids(killer):
        return [], False
    kwalk = walk(view, killer)
    dark = view.dark and not view.pawns[target].get("isNoBlack")

    def with_one_lure(test):
        """Prueba sin ordenes extra y, si no basta, apartando a un unico testigo."""
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
        """Registrar un mueble conocido (arma o comida) al alcance andando."""
        opts = [(g, o) for g in kwalk for o in view.searchable(g) if o in kinds]
        if not opts:
            return None
        g, o = min(opts, key=lambda go: (view.danger(go[0]), view.dist(go[0], prefer) if prefer is not None else 0,
                                          rng.random()))
        return order(view, idx, killer, SEARCH, g, o)

    def toward(kinds):
        """Acercarse a un mueble conocido que aun no esta a su alcance: algun personaje lo tiene cerca."""
        holders = [q for q in view.ids() if q != killer and
                   any(o in kinds for g in view.grids(q) for o in view.searchable(g))]
        if not holders:
            return None
        q = min(holders, key=lambda q: view.pair_distance(killer, q))
        g = min(kwalk, key=lambda g: (view.dist(g, q), view.danger(g), rng.random()))
        return order(view, idx, killer, MOVE, g)

    if armed:
        # 1. Asalto seguro
        extra = with_one_lure(lambda ws: assault_is_certain(view, killer, target, ws))
        if extra is not None:
            return [assault_order(view, idx, killer, target)] + extra, True
    food = grab(view.food_objects, prefer=target) if not has_food(view, killer) or k.get("isHungry") else None
    # 2. Con hambre, comer primero (con hambre llega menos lejos)
    if food and k.get("isHungry"):
        return [food], False
    if not armed:
        # 3. Armarse: el arma que conoce; si no la tiene a mano, coger comida de reserva o acercarse al arma
        o = grab(view.weapon_objects, prefer=target) or food or toward(view.weapon_objects) or \
            search_no_food(view, idx, killer, kwalk, rng, prefer=target)
        return ([o] if o else []), False
    # 3b. Armado y sin comida encima: hacerse con comida de reserva (a veces, para no ser predecible)
    if food and rng.random() < 0.5:
        return [food], False
    # 4. Plantarse en la casilla de la victima sin que nadie lo vea
    here = next((g for g in kwalk if view.dist(g, target) == 0), None)
    if here is not None:
        extra = with_one_lure(lambda ws: not watched(view, here, dark, ws))
        if extra is not None:
            return [order(view, idx, killer, MOVE, here)] + extra, False
    # 5. Sin ocasion: a veces deja que su asesino actue por su cuenta (no da pistas)...
    if view.pair_distance(killer, target) <= 3 and rng.random() < 0.4:
        return [], False
    # ...y si no, la acecha a 2 casillas, andando
    g = min(kwalk, key=lambda g: (abs(view.dist(g, target) - 2), view.danger(g), rng.random()))
    return [order(view, idx, killer, MOVE, g)], False


# ------------------------------------------------------------------ dificil: Sherlock
def plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=None, probes=1, avoid_sus=None):
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
    sus = {q: (sus_fn or suspicion)(view, memory, q) for q in ids}
    cleared = [q for q in ids if not pw[q].get("isKillerCandidate", 1)]
    cleared_both = [q for q in cleared if not pw[q].get("isTargetCandidate", 1)]
    victims = [q for q in ids if pw[q].get("isTargetCandidate", 1)]
    if avoid_sus is not None:      # a un sospechoso claro no se le protege como posible victima
        victims = [q for q in victims if sus[q] < avoid_sus] or victims
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

    def push_away(q):
        far = max(view.grids(q), key=lambda g: (min((view.dist(g, v) for v in victims if v != q), default=0),
                                                  -view.danger(g), rng.random()))
        add(q, MOVE, far)

    # 0. (experto) El sospechoso claro, lo primero: alejarlo protege a todas las posibles victimas a la vez
    if avoid_sus is not None:
        top = max((q for q in ids if orderable(q)), key=lambda q: (sus[q], rng.random()), default=None)
        if top is not None and sus[top] >= avoid_sus and len(orders) < n_orders:
            push_away(top)

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

    # 2. Apartar al mas sospechoso de las posibles victimas (si Moriarty tambien lo mueve, se le nota)
    done = 0
    for q in sorted(ids, key=lambda q: -sus[q]):
        if len(orders) >= n_orders or sus[q] <= 0 or done >= probes:
            break
        if orderable(q):
            push_away(q)
            done += 1

    # 3. Resto: todos juntos (a 3 casillas o menos) y registrando si se puede (el experto no acerca a
    #    nadie a quien ya tiene por muy sospechoso)
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


# ------------------------------------------------------------------ experto
# Mismas reglas que todos: solo lo que veria una persona en ese papel. Lo que cambia es como se piensa.
def chase_order(view, idx, killer, target, pred, rng):
    """Ir a por la victima: lo mas cerca posible de donde estara (si se preve que Sherlock la mueve, de ahi), y
    mejor en su misma casilla, donde cae al final del turno si nadie lo ve. Corre si hace falta."""
    goal = pred.get(target)

    def gap(g):
        if goal is not None:
            return 0 if g.get("gridId") == goal.get("gridId") else (1 if g.get("roomId") == goal.get("roomId") else 2)
        return view.dist(g, target)
    g = min(view.grids(killer), key=lambda g: (gap(g), view.dist(g, target), view.danger(g), rng.random()))
    return order(view, idx, killer, MOVE, g)


def turns_left(view):
    """Turnos que quedan despues de este (None si no se sabe)."""
    if not view.max_turn:
        return None
    return int(view.max_turn) - int(view.turn)


def suspicion_expert(view, memory, q):
    """Sospecha del Sherlock experto. Lo mas fuerte: la mano de Moriarty (orden pisada) y correr sin que
    lo mande Sherlock (quien va por su cuenta nunca corre). Luego, acercarse a las posibles victimas y
    llevar arma. Quien ya esta descartado como asesino no cuenta."""
    p = view.pawns.get(q, {})
    if not p.get("isKillerCandidate", 1):
        return -99
    m = memory
    score = 6 * (q in m["moriarty"]) + 3 * m.get("ran", {}).get(q, 0) + 1.5 * m.get("approach", {}).get(q, 0)
    if p.get("isHaveWeapon"):
        score += 2
    # pegado ahora mismo a una posible victima que esta sola con el
    for v, pv in view.pawns.items():
        if v != q and pv.get("isTargetCandidate", 1) and view.pair_distance(q, v) <= 1:
            mates = [x for x in view.room_mates(v) if x != q]
            if not mates:
                score += 1
                break
    return score


def plan_sherlock_expert(view, idx, n_orders, rng, taken, memory):
    """Sherlock experto: como el dificil, pero
    - sospecha con mas criterio (suspicion_expert);
    - aparta y sondea hasta a dos sospechosos: ordenarles algo descubre si Moriarty los mueve (orden
      pisada), y de paso los aleja de las posibles victimas;
    - nunca acerca al grupo a quien ya tiene por muy sospechoso;
    - en los dos ultimos turnos, las ordenes que sobran van a alejar sospechosos (hasta tres)."""
    left = turns_left(view)
    end = left is not None and left <= 1
    return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=suspicion_expert,
                              probes=3 if end else 2, avoid_sus=3)


def predict_sherlock(view, memory, rng):
    """Que ordenaria Sherlock este turno con lo que se ve en la partida (se simula su forma de pensar).
    Devuelve {personaje: casilla prevista}. No mira nada oculto: ni armas en muebles ni nada del bando
    de Moriarty."""
    v = copy.copy(view)
    v.unavailable = set(view.unavailable)
    v.weapon_objects, v.food_objects = set(), set()
    try:
        orders = plan_sherlock_hard(v, -1, 3, random.Random(rng.random()), set(), memory)
    except Exception:  # noqa: BLE001  (una prediccion fallida no debe romper el turno)
        return {}
    out = {}
    for o in orders:
        g = next((x for x in view.grids(o["pawnId"]) if x.get("gridId") == o["grid"]), None)
        if g is not None:
            out[o["pawnId"]] = g
    return out


def killer_is_hot(view, memory, killer, threshold=3):
    """El asesino ya es el principal sospechoso a ojos de Sherlock."""
    mine = suspicion_expert(view, memory, killer)
    rest = [suspicion_expert(view, memory, q) for q in view.ids() if q != killer]
    return mine >= threshold and mine >= max(rest, default=-99)


def frame_decoy(view, idx, killer, target, memory, used, rng):
    """Hacer que un inocente parezca el asesino: que corra hacia otra posible victima (no la de verdad,
    para no dejar un testigo junto a ella). Correr sin orden de Sherlock es lo que mas delata."""
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
    """Ultimos turnos: buscar el asesinato contando con lo que probablemente hara Sherlock. En el ultimo
    turno, si no hay nada seguro, se arriesga (si no mata, Moriarty no gana)."""
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
    """Moriarty experto: el dificil (asalto seguro, armado, sin correr, oscuridad...) y ademas
    - preve las ordenes de Sherlock: si Sherlock va a mover a su asesino, no le da una orden que no mate
      (chocarian y se notaria su mano);
    - si su asesino ya es el principal sospechoso, se esconde: no lo acerca a la victima y hace correr a
      un inocente hacia otra posible victima para que parezca el;
    - en los ultimos turnos busca el asesinato contando con lo previsto, y en el ultimo se arriesga;
    - en los ultimos kill_window + 2 turnos, si su asesino armado aun puede llegar a la victima en los turnos que
      quedan, deja de esconderse y va a por ella (corriendo si hace falta). Si no llega, sigue escondido y con
      senuelos: mejor un empate (Sherlock no acierta) que dejarse ver y perder."""
    mem = memory or new_memory()
    left = turns_left(view)
    pred = predict_sherlock(view, mem, rng)
    chase = left is not None and left <= kill_window + 2 and bool(view.pawns[killer].get("isHaveWeapon")) \
        and killer not in taken and bool(view.grids(killer)) \
        and view.pair_distance(killer, target) <= reach(view, killer) * (left + 1)   # le da tiempo a llegar
    if left is not None and left <= kill_window:
        kill = _kill_now(view, idx, killer, target, pred, n_orders, rng, set(taken) | {target}, desperate=left <= 0)
        if kill:
            return kill, True
    orders, assault = _moriarty_hard_core(view, idx, killer, target, n_orders, rng, taken)
    if assault:
        return orders, True
    tgrid = view.pawns[target].get("gridId")
    hot = killer_is_hot(view, mem, killer, hot_threshold)

    def kills(o):           # plantarse en la casilla de la victima, armado: si se queda, cae al final del turno
        return o["pawnId"] == killer and o["type"] == MOVE and o["grid"] == tgrid and \
            view.pawns[killer].get("isHaveWeapon")
    keep = []
    for o in orders:
        if o["pawnId"] == killer and not kills(o):
            if chase:
                continue                    # al final, la orden del asesino es ir a por la victima (abajo)
            if killer in pred and (left is None or left > 3):
                continue                    # chocaria con Sherlock y le delataria
            if hot and o["type"] == MOVE:
                continue                    # perfil bajo: ni acercarse ni acechar
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
    """Irene experta (gana a Sherlock sin dejar rastro): aparta al testigo de la victima hacia un
    peligro; si no hay, arma al asesino; si ya lo esta, hace parecer culpable a un inocente."""
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


# ------------------------------------------------------------------ pesadilla
# El experto, mas lo aprendido de las personas de la partida en sus partidas anteriores (profiles.py).
# Sin perfil (pocas partidas), juega como el experto pero mas agresivo.
def suspicion_nightmare(view, memory, q):
    """Sospecha del Sherlock Pesadilla: la del experto mas lo que delataba al asesino de esta persona
    en sus partidas (si su asesino solia correr, registrar, acercarse...)."""
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
    """Turno en el que el Moriarty de esta partida suele atacar (o uno antes/despues)."""
    prof = memory.get("prof_moriarty")
    if not prof or not prof.get("kill_turns"):
        return False
    return any(abs(int(view.turn) - t) <= 1 for t in prof["kill_turns"])


def plan_sherlock_nightmare(view, idx, n_orders, rng, taken, memory):
    """Sherlock Pesadilla: el experto con la sospecha aprendida. En los turnos en que esa persona suele
    atacar y en los dos ultimos, todo a proteger (solo aparta al sospechoso principal)."""
    left = turns_left(view)
    end = left is not None and left <= 1
    tense = danger_turn(view, memory)
    probes = 3 if end else (1 if tense else 2)
    return plan_sherlock_hard(view, idx, n_orders, rng, taken, memory, sus_fn=suspicion_nightmare,
                              probes=probes, avoid_sus=3)


def plan_moriarty_nightmare(view, idx, killer, target, n_orders, rng, taken=(), memory=None):
    """Moriarty Pesadilla: el experto ajustado al Sherlock de la partida.
    - Si esa persona se traga los senuelos (acusa al inocente que corrio), senuelos casi siempre; si no se
      los traga, pocos (solo delatarian a Moriarty).
    - Si suele vigilar al asesino con sus ordenes, esconde al suyo antes.
    - Busca el asesinato desde cuatro turnos antes del final (el experto, dos)."""
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
