"""
CRIMESIGHT Revival - player profiles for the "Nightmare" AI.

From the saved matches (matchlog) each person's habits are worked out, as a human
rival who has already played against them would:

As Moriarty (for the Nightmare Sherlock):
- What gives their killer away: how their killer moved is compared to how the innocents moved in
  their matches (running, searching, getting close to possible victims, overridden orders). Only what
  Sherlock's side sees counts: what the characters did without its order.
- On which turns they usually attack.

As Sherlock / Watson (for the Nightmare Moriarty):
- Whether they fall for decoys: when the one who ran the most was innocent, whether they accused them anyway.
- Whether they order the killer more than anyone else (they watch suspects: hide earlier).
- How many matches they win.

Everything is worked out on the PC of whoever acts as the server, with their own matches. With fewer than MIN_MATCHES
matches in that role there is no profile and the AI plays as Expert.
"""
import math

MIN_MATCHES = 3
FEATURES = ("run", "search", "approach", "batting")


def _xy(g):
    try:
        g = int(g)
    except (TypeError, ValueError):
        return None
    return int(g / 10), abs(g) % 10


def _dist(a, b):
    pa, pb = _xy(a), _xy(b)
    if pa is None or pb is None:
        return 99
    return max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]))


def visible_features(rec):
    """For each character, what Sherlock's side saw in that match: times it ran, searched or got
    close to a possible victim without a Sherlock order, and overridden orders."""
    out = {}
    for t in rec.get("turns") or []:
        pos = {p[0]: p[1] for p in t.get("pawns") or [] if len(p) >= 2}
        victims = {p[0] for p in t.get("pawns") or [] if len(p) >= 6 and p[5]}
        for o in t.get("orders") or []:
            if len(o) < 7:
                continue
            pawn, kind, grid, run, _tid, side, bat = o[:7]
            f = out.setdefault(pawn, dict.fromkeys(FEATURES, 0))
            if bat:
                f["batting"] += 1
            if side == "S":
                continue
            if run or kind in (4, 5):
                f["run"] += 1
            if kind == 3:
                f["search"] += 1
            start = pos.get(pawn)
            for v in victims:
                if v == pawn or v not in pos:
                    continue
                if _dist(grid, pos[v]) <= 2 and _dist(grid, pos[v]) < _dist(start, pos[v]):
                    f["approach"] += 1
                    break
    return out


def _role_of(rec, pid):
    for p in rec.get("players") or []:
        if p.get("id") == pid and not p.get("bot"):
            return p.get("role")
    return None


def build(records, pid):
    """A player's profile (by their server player id)."""
    prof = {"as_moriarty": None, "as_sherlock": None}
    mor = [r for r in records if _role_of(r, pid) == "criminal" and r.get("killer", -1) >= 0]
    det = [r for r in records if _role_of(r, pid) in ("detective", "watson") and r.get("killer", -1) >= 0]

    if len(mor) >= MIN_MATCHES:
        k_sum = dict.fromkeys(FEATURES, 0)
        i_sum = dict.fromkeys(FEATURES, 0)
        k_n = i_n = 0
        kill_turns = []
        for r in mor:
            feats = visible_features(r)
            killer = r["killer"]
            for pawn, f in feats.items():
                if pawn == r.get("target"):
                    continue
                if pawn == killer:
                    k_n += 1
                    for x in FEATURES:
                        k_sum[x] += f[x]
                else:
                    i_n += 1
                    for x in FEATURES:
                        i_sum[x] += f[x]
            if r.get("kill"):
                kill_turns.append(int(r["kill"].get("turn", 0)))
        # How many times per match their killer does each thing compared to an innocent. It is smoothed towards the
        # overall average, so without data on something (it never happened) the weight stays at 0.
        weights = {}
        for x in FEATURES:
            if not k_sum[x] + i_sum[x]:
                weights[x] = 0.0                  # never happened: it says nothing
                continue
            prior = (k_sum[x] + i_sum[x]) / max(1, k_n + i_n)
            rk = (k_sum[x] + 2 * prior + 0.05) / (k_n + 2)
            ri = (i_sum[x] + 2 * prior + 0.05) / (i_n + 2)
            weights[x] = max(-1.0, min(3.0, math.log(rk / ri)))
        prof["as_moriarty"] = {"matches": len(mor), "weights": weights, "kill_turns": kill_turns}

    if len(det) >= MIN_MATCHES:
        fooled = fooled_n = 0
        ordered_killer = ordered_any = turns_n = wins = 0
        for r in det:
            feats = visible_features(r)
            killer = r["killer"]
            runner = max(feats, key=lambda q: (feats[q]["run"], -q), default=None) if feats else None
            mine = [a for a in r.get("accusations") or [] if a.get("player") == pid]
            # Do they fall for it? Only counts when the one who ran the most was a decoy (not the killer)
            if runner is not None and feats[runner]["run"] > 0 and runner != killer and mine:
                fooled_n += 1
                fooled += mine[0].get("accused") == runner
            n_pawns = max(1, len({p[0] for t in r.get("turns") or [] for p in t.get("pawns") or []}))
            for t in r.get("turns") or []:
                s_orders = {o[0] for o in t.get("orders") or [] if len(o) >= 7 and o[5] == "S"}
                turns_n += 1
                ordered_killer += killer in s_orders
                ordered_any += len(s_orders) / n_pawns
            wins += r.get("winner") == "sherlock"
        prof["as_sherlock"] = {"matches": len(det),
                               "fooled_by_runner": fooled / fooled_n if fooled_n else None,
                               # >1: orders the killer more than any character (watches them)
                               "tracks_killer": (ordered_killer / ordered_any) if ordered_any else 1.0,
                               "win_rate": wins / len(det)}
    return prof


def for_room(records, members, role_names):
    """Profiles of a room's humans: {"moriarty": profile of the human Moriarty (or None),
    "sherlock": profile of the human Sherlock or Watson (or None)}."""
    out = {"moriarty": None, "sherlock": None}
    for pid, m in members.items():
        if m.get("bot"):
            continue
        role = role_names.get(m.get("role"), m.get("role"))
        p = build(records, pid)
        if role == "criminal" and p["as_moriarty"]:
            out["moriarty"] = p["as_moriarty"]
        if role in ("detective", "watson") and p["as_sherlock"] and not out["sherlock"]:
            out["sherlock"] = p["as_sherlock"]
    return out
