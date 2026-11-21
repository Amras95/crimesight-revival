"""
CRIMESIGHT Revival - registro detallado de cada partida (base para la IA "Pesadilla").

Por cada partida se guarda una linea JSON en <datos>/match_logs/AAAA-MM.jsonl con lo que se ha visto
en ella: quien jugaba cada papel (y contra que dificultad), donde estaba cada personaje al empezar cada
turno, todas las ordenes del turno (de que bando venian o si el personaje iba por su cuenta), si alguien
corrio, las ordenes pisadas, el asesinato y las acusaciones del final. Desde la version 2, tambien lo
necesario para comprobar los puntos de accion: los ajustes (planos, perros, gas), que salio al registrar
cada mueble, como acaba cada turno y que acciones con puntos se dieron. Solo lo que pasa en la partida:
nada del PC ni de la cuenta de nadie, y se queda en el ordenador de quien hace de servidor.

Con esto, mas adelante, la IA puede aprender las costumbres de cada jugador (a quien suele elegir de
asesino, en que turno ataca, a quien vigila...). Si algo falla al escribir, la partida sigue igual.
"""
import json, logging, os, time

log = logging.getLogger("crimesight")
MAX_FILE_BYTES = 30 * 1024 * 1024         # por mes; si se pasa, se deja de apuntar ese mes


class MatchLog:
    def __init__(self, data_dir, match_id, stage, settings, members, killer, target, role_names):
        self.dir = os.path.join(data_dir, "match_logs") if data_dir else None
        self.rec = {
            "v": 2, "match_id": match_id, "date": int(time.time()), "stage": stage,
            "max_turn": settings.get("max_turn"), "time_limit": settings.get("time_limit"),
            "killer": killer, "target": target,
            "players": [{"id": pid, "name": m.get("name", ""), "role": role_names.get(m.get("role"), m.get("role")),
                         "bot": bool(m.get("bot")), "difficulty": m.get("difficulty") if m.get("bot") else None}
                        for pid, m in members.items()],
            "turns": [], "kill": None, "accusations": [], "winner": None, "end": None,
            "settings": {k: settings.get(k) for k in ("switchboard_count", "wild_dog_count", "gaspipe_count",
                                                       "secret_passage", "fast_action")},
            "actions": [], "awarded": [],
        }
        self.done = False

    def turn_state(self, turn, ref):
        """Donde empieza cada personaje el turno (lo que ve cualquiera en la partida)."""
        pawns = []
        for p in ref.get("pawns") or []:
            if not isinstance(p, dict) or "pawnId" not in p:
                continue
            pawns.append([int(p["pawnId"]), p.get("gridId"), p.get("roomId"), int(bool(p.get("isHaveWeapon"))),
                          int(bool(p.get("isKillerCandidate", 1))), int(bool(p.get("isTargetCandidate", 1))),
                          int(bool(p.get("isBlind")))])        # critico (version 2: al final, no cambia lo anterior)
        self._turn(turn)["pawns"] = pawns
        self._turn(turn)["dark"] = int(bool(int(ref.get("isBlack", 0) or 0)))

    def turn_orders(self, turn, commands, owner_side, kill, owner_who=None):
        """Las ordenes que se ejecutan: [personaje, tipo, casilla, corre, mueble, bando, pisada, papel, jugador].
        bando: "S" Sherlock/Watson, "M" Moriarty/Irene, "N" nadie (va por su cuenta).
        papel y jugador (desde la version 2): quien dio la orden ("detective", "criminal", "irene" o "watson"
        y su id); None si nadie. Van al final para que lo que ya lee las 7 primeras no cambie."""
        owner_who = owner_who or {}
        out = []
        for c in commands:
            try:
                p = int(c["pawnId"])
            except (KeyError, TypeError, ValueError):
                continue
            role, player = owner_who.get(p, (None, None))
            out.append([p, int(c.get("type", 0) or 0), c.get("grid"), int(bool(int(c.get("isRun", 0) or 0))),
                        c.get("targetId"), owner_side.get(p, "N"), int(bool(c.get("isBatting"))), role, player])
        t = self._turn(turn)
        t["orders"] = out
        if kill:
            t["assault"] = 1

    def found(self, turn, furniture, item, kind):
        """Lo que sale al registrar un mueble: [mueble, objeto, tipo] (food, weapon, plan u other).
        Quien lo registro se ve en las ordenes del turno (la orden de buscar en ese mueble)."""
        self._turn(turn).setdefault("found", []).append([furniture, item, kind])

    def turn_end(self, turn, ref):
        """Como acaba el turno: personajes [id, habitacion, puede ser asesino, puede ser victima, heridas,
        herido, critico, hambre], amenazas (perros...) [id, habitacion, muerta] y habitaciones con escape de gas."""
        def num(x, key, default=0):
            try:
                return int(x.get(key, default) or 0)
            except (TypeError, ValueError):
                return default
        t = self._turn(turn)
        t["end"] = [[int(p["pawnId"]), p.get("roomId"), int(bool(p.get("isKillerCandidate", 1))),
                     int(bool(p.get("isTargetCandidate", 1))), num(p, "injureCount"), num(p, "isInjure"),
                     int(bool(p.get("isBlind"))), int(bool(p.get("isHungry")))]
                    for p in ref.get("pawns") or [] if isinstance(p, dict) and "pawnId" in p]
        t["end_threats"] = [[num(x, "uniqId", -1), x.get("roomId"), num(x, "isDie")]
                            for x in ref.get("threatList") or [] if isinstance(x, dict)]
        t["end_gas"] = [g.get("roomId") for g in ref.get("gaspipeList") or [] if isinstance(g, dict)]
        t["end_gas_ids"] = [g.get("uniqId") for g in ref.get("gaspipeList") or [] if isinstance(g, dict)]
        t["end_dark"] = num(ref, "isBlack")
        for key in ("bywayList", "byways", "bywayLocateDatas"):          # pasadizos, si el juego los manda
            if key in ref:
                t["end_byways"] = ref[key]
        if "ref_keys" not in self.rec:                                    # que datos manda el juego (una vez)
            self.rec["ref_keys"] = sorted(ref)

    def action(self, turn, player, action):
        """Una accion con puntos, la primera vez que la consigue un jugador en la partida."""
        self.rec["actions"].append([turn, player, action.replace("ctg_name_result_", "")])

    def awarded(self, player, outcome, actions, points):
        """Lo que se anoto en el perfil de cada jugador al acabar (acciones y puntos totales)."""
        self.rec["awarded"].append({"player": player, "outcome": outcome, "points": points,
                                    "actions": [a.replace("ctg_name_result_", "") for a in actions]})

    def killed(self, turn, assault):
        self.rec["kill"] = {"turn": turn, "assault": bool(assault)}

    def accusations(self, items):
        """[(jugador, personaje acusado, es_bot)]"""
        self.rec["accusations"] = [{"player": p, "accused": k, "bot": bool(b)} for p, k, b in items]

    def finish(self, winner, reason=""):
        if self.done:
            return
        self.done = True
        self.rec["winner"] = winner
        self.rec["end"] = reason or None
        self.rec["turn_count"] = len(self.rec["turns"])
        if not self.dir:
            return
        try:
            os.makedirs(self.dir, exist_ok=True)
            path = os.path.join(self.dir, time.strftime("%Y-%m") + ".jsonl")
            if os.path.exists(path) and os.path.getsize(path) > MAX_FILE_BYTES:
                return
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.rec, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError as e:
            log.warning("No pude guardar el registro de la partida: %s", e)

    def _turn(self, turn):
        turns = self.rec["turns"]
        if not turns or turns[-1]["turn"] != turn:
            turns.append({"turn": turn})
        return turns[-1]


def read_all(data_dir):
    """Todas las partidas guardadas (para la IA que aprende), de la mas antigua a la mas nueva."""
    d = os.path.join(data_dir, "match_logs")
    out = []
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith(".jsonl"))
    except OSError:
        return out
    for n in names:
        try:
            with open(os.path.join(d, n), encoding="utf-8") as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
        except OSError:
            pass
    return out
