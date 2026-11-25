"""
CRIMESIGHT Revival - detailed log of each match (the base for the "Nightmare" AI).

For each match one JSON line is saved in <data>/match_logs/YYYY-MM.jsonl with what was seen in it: who
played each role (and against which difficulty), where each character was at the start of each turn, every
order of the turn (which side it came from, or whether the character acted on its own), whether someone ran,
the overridden orders, the murder and the final accusations. Since version 2, also what is needed to check
the action points: the settings (plans, dogs, gas), what came out when searching each piece of furniture, how
each turn ends and which actions with points happened. Only what happens in the match: nothing about anyone's
PC or account, and it stays on the computer of whoever runs the server.

With this, later on, the AI can learn each player's habits (who they usually pick as the killer, on which
turn they attack, who they watch...). If something fails while writing, the match goes on the same.
"""
import json, logging, os, time

log = logging.getLogger("crimesight")
MAX_FILE_BYTES = 30 * 1024 * 1024         # per month; past it, nothing more is written that month


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
        """Where each character starts the turn (what anyone in the match sees)."""
        pawns = []
        for p in ref.get("pawns") or []:
            if not isinstance(p, dict) or "pawnId" not in p:
                continue
            pawns.append([int(p["pawnId"]), p.get("gridId"), p.get("roomId"), int(bool(p.get("isHaveWeapon"))),
                          int(bool(p.get("isKillerCandidate", 1))), int(bool(p.get("isTargetCandidate", 1))),
                          int(bool(p.get("isBlind")))])        # critical (version 2: at the end, nothing before it changes)
        self._turn(turn)["pawns"] = pawns
        self._turn(turn)["dark"] = int(bool(int(ref.get("isBlack", 0) or 0)))

    def turn_orders(self, turn, commands, owner_side, kill, owner_who=None):
        """The orders that run: [character, type, square, runs, furniture, side, overridden, role, player].
        side: "S" Sherlock/Watson, "M" Moriarty/Irene, "N" nobody (acting on its own).
        role and player (since version 2): who gave the order ("detective", "criminal", "irene" or "watson"
        and their id); None if nobody. They go at the end so that whatever already reads the first 7 does not change."""
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
        """What comes out when searching a piece of furniture: [furniture, item, type] (food, weapon, plan or other).
        Who searched it shows in the turn's orders (the order to search that furniture)."""
        self._turn(turn).setdefault("found", []).append([furniture, item, kind])

    def turn_end(self, turn, ref):
        """How the turn ends: characters [id, room, can be the killer, can be the victim, injuries,
        injured, critical, hunger], threats (dogs...) [id, room, dead] and rooms with a gas leak."""
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

    def action(self, turn, player, action):
        """An action with points, the first time a player gets it in the match."""
        self.rec["actions"].append([turn, player, action.replace("ctg_name_result_", "")])

    def awarded(self, player, outcome, actions, points):
        """What was written in each player's profile at the end (actions and total points)."""
        self.rec["awarded"].append({"player": player, "outcome": outcome, "points": points,
                                    "actions": [a.replace("ctg_name_result_", "") for a in actions]})

    def left(self, turn, player):
        """A player left mid-match and an AI played their role from that turn on."""
        self.rec.setdefault("left", []).append({"turn": turn, "player": player})

    def killed(self, turn, assault):
        self.rec["kill"] = {"turn": turn, "assault": bool(assault)}

    def accusations(self, items):
        """[(player, accused character, is_bot)]"""
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
    """Every saved match (for the AI that learns), from the oldest to the newest."""
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
