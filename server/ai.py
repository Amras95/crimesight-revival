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
  asaltar ni dar ordenes a la victima. Los conflictos entre ellos y Sherlock se sortean.
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


def away_from(view, pid, other):
    """Casilla alcanzable por pid lo mas lejos posible de 'other' (sin meterse en peligro si se puede)."""
    return max(view.grids(pid), key=lambda g: (view.dist(g, other) - 2 * view.danger(g), view.dist(g, other)))


# ------------------------------------------------------------------ Moriarty
def plan_moriarty(view, idx, killer, target, n_orders, difficulty, rng, taken=()):
    """Ordenes para el bando de Moriarty. Devuelve (ordenes, asalto?)."""
    orders, used = [], set(taken) | {target}
    if killer not in view.pawns or target not in view.pawns:
        return orders, False
    k, t = view.pawns[killer], view.pawns[target]
    kgrids = view.grids(killer)
    armed = bool(k.get("isHaveWeapon"))
    witnesses = [q for q in view.room_mates(target) if q != killer]
    reach = any(view.dist(g, target) == 0 for g in kgrids) and not view.threat_witness(t.get("roomId"))
    close = view.pair_distance(killer, target)

    assault = False
    if armed and killer not in used:
        if difficulty == "easy":
            assault = reach and not witnesses and rng.random() < 0.5
        elif difficulty == "normal":
            assault = reach and not witnesses
        else:  # hard: tambien si hay un unico testigo que podemos apartar este turno
            assault = reach and len(witnesses) <= (1 if n_orders >= 2 else 0)
    if assault:
        orders.append({**order(view, idx, killer, TARGET, {"gridId": t.get("gridId"), "pawnDistance": []}),
                       "targetId": int(t.get("uniqId", -1)), "isRun": 0})
        used.add(killer)
        if witnesses and len(orders) < n_orders:          # apartar al testigo
            w = witnesses[0]
            wg = view.grids(w)
            if wg:
                orders.append(order(view, idx, w, MOVE, away_from(view, w, target)))
                used.add(w)
        return orders, True

    # Mover al asesino: sin arma, a registrar muebles cerca de la victima; con arma, acercarse sin pegarse
    if killer not in used and kgrids:
        if difficulty == "easy":
            o = search_or_move(view, idx, killer, kgrids, rng)
        elif not armed:
            o = search_or_move(view, idx, killer, kgrids, rng, prefer=target)
        else:
            want = 2 if difficulty == "hard" else 1
            g = min(kgrids, key=lambda g: (abs(view.dist(g, target) - want), view.danger(g), rng.random()))
            o = order(view, idx, killer, MOVE, g)
        if o:
            orders.append(o)
            used.add(killer)

    # Segundo personaje: despejar a la victima (normal/dificil) o despistar (facil)
    while len(orders) < n_orders:
        candidates = [q for q in view.ids() if q not in used and view.grids(q)]
        if not candidates:
            break
        if difficulty != "easy" and witnesses:
            w = next((q for q in witnesses if q in candidates), None)
        else:
            w = None
        if w is not None:
            orders.append(order(view, idx, w, MOVE, away_from(view, w, target)))
            used.add(w)
            witnesses.remove(w)
            continue
        q = rng.choice(candidates)
        o = search_or_move(view, idx, q, view.grids(q), rng)   # comportarse como un sospechoso mas
        if o:
            orders.append(o)
        used.add(q)
    return orders, False


# ------------------------------------------------------------------ Sherlock
def plan_sherlock(view, idx, n_orders, difficulty, rng, taken=()):
    """Ordenes para el bando de Sherlock: buscar objetos y no dejar a nadie solo."""
    orders, used = [], set(taken)

    def lonely(q):
        return len(view.room_mates(q))

    pool = [q for q in view.ids() if q not in used and view.grids(q)]
    if difficulty == "easy":
        rng.shuffle(pool)
    else:
        # prioriza a los posibles victimas aisladas
        pool.sort(key=lambda q: (not view.pawns[q].get("isTargetCandidate", 1), lonely(q), rng.random()))
    for q in pool:
        if len(orders) >= n_orders:
            break
        grids = view.grids(q)
        if difficulty == "easy":
            o = search_or_move(view, idx, q, grids, rng)
        else:
            others = [x for x in view.ids() if x != q]

            def company(g):
                return sum(1 for x in others if view.dist(g, x) <= (1 if difficulty == "hard" else 2)) \
                    - view.danger(g)

            best = max(company(g) for g in grids)
            good = [g for g in grids if company(g) == best]
            if lonely(q) == 0 or difficulty == "hard":
                # registrar con compania aceptable antes que amontonarse sin hacer nada
                near_best = [g for g in grids if company(g) >= max(1, best - 1)]
                with_obj = [g for g in good if view.searchable(g)] or \
                           [g for g in near_best if view.searchable(g)]
                if with_obj:
                    g = rng.choice(with_obj)
                    o = order(view, idx, q, SEARCH, g, rng.choice(view.searchable(g)))
                else:
                    o = order(view, idx, q, MOVE, rng.choice(good))
            else:
                o = search_or_move(view, idx, q, grids, rng)
        if o:
            orders.append(o)
            used.add(q)
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
        o = search_or_move(view, idx, killer, view.grids(killer), rng, prefer=target)
        return [o] if o else []
    pool = [q for q in view.ids() if q not in used and q != killer and view.grids(q)]
    if not pool:
        return []
    q = rng.choice(pool)
    o = search_or_move(view, idx, q, view.grids(q), rng)
    return [o] if o else []


def plan_watson(view, idx, difficulty, rng, taken=()):
    """Watson (bando Sherlock): 1 orden con el mismo criterio que Sherlock."""
    return plan_sherlock(view, idx, 1, difficulty, rng, taken)


def accuse(view, killer, difficulty, rng, n_pawns):
    """Acusacion final de un Sherlock IA."""
    everyone = list(range(n_pawns))
    if view is None:
        return rng.choice(everyone)
    cands = [q for q, p in view.pawns.items() if p.get("isKillerCandidate")] or everyone
    if difficulty == "easy":
        return rng.choice(everyone)
    if difficulty == "hard" and killer in cands and (len(cands) <= 3 or rng.random() < 0.5):
        return killer
    return rng.choice(cands)
