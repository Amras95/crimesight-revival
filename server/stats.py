"""
CRIMESIGHT Revival - victorias, derrotas, empates y puntos.

El cliente pide user.GetStats (perfil y nivel) y match.GetStats (puntos de la ultima partida).
Ambos devuelven {"stats": [{id, role, category, text_id, count, point}, ...]}:
- category "count": partidas ganadas/perdidas/empatadas por rol (el nivel sale de la suma).
- category "points": puntos totales de cada bando.
- cualquier otra categoria: filas de "Puntos de accion" (texto traducido por el propio juego).

Los ids salen de PlayerPointManager en el cliente.
"""
import time

DETECTIVE, CRIMINAL, IRENE, WATSON = 1, 2, 3, 4

# rol -> ids de victorias / derrotas / empates
COUNT_IDS = {
    DETECTIVE: {"win": 1, "lose": 2, "draw": 3},
    CRIMINAL: {"win": 4, "lose": 5, "draw": 6},
    IRENE: {"win": 7, "lose": 9, "draw": 8},
    WATSON: {"win": 41, "lose": 43, "draw": 42},
}
POINT_IDS = {DETECTIVE: 10, CRIMINAL: 20, IRENE: 30, WATSON: 40}

# Puntos por partida (sistema generoso: el juego ya no tiene comunidad, que desbloquear no sea un trabajo)
# Victoria segun el nivel: IA facil 200, normal 400, dificil 800; contra otras personas 1000 (ahora
# cuesta mucho encontrar partida). Empate o derrota: la mitad. Abandonar: 0.
WIN_POINTS = {"easy": 200, "normal": 400, "hard": 800, "online": 1000}
LEVELS = tuple(WIN_POINTS)
RESULT_POINTS = {"win": 400, "draw": 250, "lose": 250, "abandon": 0}   # tabla antigua (partidas viejas)
RECORD_VERSION = 2
RESULT_TEXT = "ctg_name_result_match_result_point"            # "Puntos por resultado de la partida"


def result_points(outcome, level=None):
    """Puntos por el resultado. Sin nivel (partidas antiguas), la tabla de antes."""
    if level not in WIN_POINTS:
        return RESULT_POINTS.get(outcome, 0)
    win = WIN_POINTS[level]
    return {"win": win, "draw": win // 2, "lose": win // 2}.get(outcome, 0)


# Acciones que el servidor detecta -> (id, puntos). Los textos son los del propio juego.
ACTIONS = {
    # Bando de Sherlock
    "ctg_name_result_repair_switchboard": (104, 50),                    # arreglar el cuadro electrico
    "ctg_name_result_action_treated_pawnForInjuries": (105, 50),        # curar a alguien
    "ctg_name_result_arrest_succeed": (106, 100),                       # frustrar el ataque principal
    "ctg_name_result_apply_tearSpray_to_killer": (107, 100),            # gas lacrimogeno al asesino
    "ctg_name_result_identified_killer_by_deduction": (108, 100),       # acusar al asesino correcto
    # Bando de Moriarty
    "ctg_name_result_action_targetKilledByAssail": (101, 50),           # ganar matando con el Asalto
    "ctg_name_result_blackOut_by_switchboard": (109, 50),               # romper el cuadro (apagon)
    "ctg_name_result_action_blockedSherlockWithSpray": (110, 50),       # gasear a alguien
    "ctg_name_result_action_beCriticalNoKiller": (111, 100),            # atacar a la victima y dejarla K.O.
    # Antiguas (solo para recalcular partidas viejas)
    "ctg_name_result_action_kill_succeed_not_identified_killer": (102, 30),
    "ctg_name_result_pattern_arrest_success": (103, 50),
}


def _record(user):
    rec = user.get("record")
    if not isinstance(rec, dict) or rec.get("v") != RECORD_VERSION:
        # (Re)calcular con la tabla de puntos actual a partir del historial de partidas
        rec = {"v": RECORD_VERSION, "counts": {}, "points": {}, "actions": {}}
        for h in user.get("history", []) or []:
            role = int(h.get("role", 0))
            if role not in COUNT_IDS:
                continue
            outcome = h.get("outcome") or ("win" if h.get("win") else "lose")
            if outcome not in RESULT_POINTS:
                continue
            if "base" in h:      # partidas nuevas: cada una guarda sus propios puntos
                h["points"] = _add(rec, role, outcome, h.get("actions") or [], h.get("base"), h.get("acts"))
            else:
                h["points"] = _add(rec, role, outcome, h.get("actions") or [])
        user["record"] = rec
    return rec


def _add(rec, role, outcome, actions, base=None, acts=None):
    if outcome == "abandon":                     # cuenta como derrota, sin puntos ni extras
        actions, base, acts = [], 0, {}
    cid = str(COUNT_IDS[role]["lose" if outcome == "abandon" else outcome])
    rec["counts"][cid] = rec["counts"].get(cid, 0) + 1
    if base is None:
        base = RESULT_POINTS[outcome]
    if acts is None:
        acts = {a: ACTIONS[a][1] for a in actions if a in ACTIONS}
    pts = int(base) + sum(int(acts.get(a, 0)) for a in actions)
    pid = str(POINT_IDS[role])
    rec["points"][pid] = rec["points"].get(pid, 0) + pts
    for a in actions:
        if a in ACTIONS:
            k = f"{role}:{a}"
            rec["actions"][k] = rec["actions"].get(k, 0) + 1
    return pts


HISTORY_MAX = 20000          # unas cuantas vidas de partidas; el registro se recalcula desde aqui


def record_match(user, role, outcome, actions=(), stage="", match_id=None, level=None):
    """Anota una partida terminada. Devuelve los puntos ganados.
    match_id identifica la partida en cualquier servidor: al juntar perfiles no se duplica.
    level: "easy"/"normal"/"hard" (contra la IA) u "online" (contra personas)."""
    if role not in COUNT_IDS or outcome not in RESULT_POINTS:
        return 0
    hist = user.setdefault("history", [])
    now = int(time.time())
    mid = match_id or f"{now}-{role}-{len(hist)}"
    if any(h.get("mid") == mid for h in hist):
        return 0
    rec = _record(user)
    actions = [] if outcome == "abandon" else list(dict.fromkeys(a for a in actions if a in ACTIONS))
    base = result_points(outcome, level)
    acts = {a: ACTIONS[a][1] for a in actions}
    pts = _add(rec, role, outcome, actions, base, acts)
    hist.append({"mid": mid, "time": now, "role": role, "outcome": outcome, "win": outcome == "win",
                 "points": pts, "actions": actions, "stage": stage, "level": level, "base": base, "acts": acts})
    del hist[:-HISTORY_MAX]
    user["match_count"] = int(user.get("match_count", 0)) + 1
    # Lo que se ve en la pantalla de resultados
    items = [{"id": 100, "role": role, "category": "result", "text_id": RESULT_TEXT,
              "count": 1, "point": base}]
    for a in actions:
        aid, p = ACTIONS[a]
        items.append({"id": aid, "role": role, "category": "action", "text_id": a, "count": 1, "point": acts[a]})
    user["last_result"] = items
    return pts


def user_stats(user):
    rec = _record(user)
    out = []
    for role, ids in COUNT_IDS.items():
        for outcome, cid in ids.items():
            out.append({"id": cid, "role": role, "category": "count", "text_id": "",
                        "count": int(rec["counts"].get(str(cid), 0)), "point": 0})
        played = sum(int(rec["counts"].get(str(c), 0)) for c in ids.values())
        pid = POINT_IDS[role]
        out.append({"id": pid, "role": role, "category": "points", "text_id": "",
                    "count": played, "point": int(rec["points"].get(str(pid), 0))})
    for key, n in sorted(rec["actions"].items()):
        role, text = key.split(":", 1)
        aid, p = ACTIONS.get(text, (0, 0))
        if aid:
            out.append({"id": aid * 10 + int(role), "role": int(role), "category": "action", "text_id": text,
                        "count": int(n), "point": p})
    return out


def summary(user):
    """Texto corto para el log del servidor."""
    rec = _record(user)
    c = rec["counts"]
    w = sum(int(c.get(str(ids["win"]), 0)) for ids in COUNT_IDS.values())
    l = sum(int(c.get(str(ids["lose"]), 0)) for ids in COUNT_IDS.values())
    d = sum(int(c.get(str(ids["draw"]), 0)) for ids in COUNT_IDS.values())
    return f"{w}V {d}E {l}D, {sum(rec['points'].values())} puntos"


# ------------------------------------------------------------------ perfiles portables
PROFILE_KEYS = ("name", "progress", "tutorial_step", "config", "config_time", "history", "last_result", "updated",
                "lang", "lang_time")


def _mid(h):
    return h.get("mid") or f"legacy-{h.get('time', 0)}-{h.get('role', 0)}"


def export_profile(user):
    """Lo que viaja entre servidores y el PC de cada jugador."""
    out = {k: user[k] for k in PROFILE_KEYS if k in user}
    out["history"] = [dict(h, mid=_mid(h)) for h in user.get("history", []) or []]
    return out


def merge_into(user, other):
    """Junta 'other' (perfil exportado) dentro de 'user'. Solo suma: partidas por id unico,
    tutorial/progreso el mas avanzado, ajustes y nombre el cambio mas reciente."""
    if not isinstance(other, dict):
        return user
    seen = {}
    for h in (user.get("history") or []) + (other.get("history") or []):
        if isinstance(h, dict):
            seen.setdefault(_mid(h), dict(h, mid=_mid(h)))
    user["history"] = sorted(seen.values(), key=lambda h: (h.get("time", 0), h["mid"]))[-HISTORY_MAX:]
    for k in ("progress", "tutorial_step"):
        user[k] = max(int(user.get(k, 0) or 0), int(other.get(k, 0) or 0))
    cfg, ct = dict(user.get("config") or {}), dict(user.get("config_time") or {})
    for key, val in (other.get("config") or {}).items():
        t = (other.get("config_time") or {}).get(key, 0)
        if key not in cfg or t > ct.get(key, 0):
            cfg[key], ct[key] = val, t
    user["config"], user["config_time"] = cfg, ct
    if other.get("name") and (not user.get("name") or other.get("updated", 0) > user.get("updated", 0)):
        user["name"] = other["name"]
    if other.get("last_result") and other.get("updated", 0) > user.get("updated", 0):
        user["last_result"] = other["last_result"]
    if other.get("lang") and other.get("lang_time", 0) > user.get("lang_time", 0):
        user["lang"], user["lang_time"] = other["lang"], other["lang_time"]
    user["updated"] = max(user.get("updated", 0), other.get("updated", 0))
    user["match_count"] = len(user["history"])
    user.pop("record", None)            # se recalcula con el historial completo
    _record(user)
    return user
