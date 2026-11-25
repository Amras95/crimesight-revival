"""
CRIMESIGHT Revival - wins, losses, draws and points.

The client asks for user.GetStats (profile and level) and match.GetStats (points of the last match).
Both return {"stats": [{id, role, category, text_id, count, point}, ...]}:
- category "count": matches won/lost/drawn per role (the level comes from the sum).
- category "points": total points of each side.
- category "result": rows of "Match result points". In the profile, as in the original game, two
  per role: how many times each result was achieved and the points it gave (RESULT_ROWS).
- any other category: rows of "Action points" (text translated by the game itself).

The ids come from PlayerPointManager in the client.
"""
import time

DETECTIVE, CRIMINAL, IRENE, WATSON = 1, 2, 3, 4

# role -> ids of wins / losses / draws
COUNT_IDS = {
    DETECTIVE: {"win": 1, "lose": 2, "draw": 3},
    CRIMINAL: {"win": 4, "lose": 5, "draw": 6},
    IRENE: {"win": 7, "lose": 9, "draw": 8},
    WATSON: {"win": 41, "lose": 43, "draw": 42},
}
POINT_IDS = {DETECTIVE: 10, CRIMINAL: 20, IRENE: 30, WATSON: 40}

# Points per match (generous system: the game no longer has a community, unlocking shouldn't be a chore)
# Win by level: easy AI 200, normal 400, hard 800; against other people 1000 (finding a match is
# very hard now). Draw or loss: half. Quitting: 0.
WIN_POINTS = {"easy": 200, "normal": 400, "hard": 800, "expert": 1000, "nightmare": 1200, "online": 1000}
LEVELS = tuple(WIN_POINTS)
RESULT_POINTS = {"win": 400, "draw": 250, "lose": 250, "abandon": 0}   # old table (old matches)
RECORD_VERSION = 3
RESULT_TEXT = "ctg_name_result_match_result_point"            # "Match result points"

# Rows of "Match result points" in the profile (the same ones the original game showed):
# match result -> game text. Losses have no row.
SIDE_SHERLOCK = (("win", "ctg_name_result_arrest_succeed"),                # "Villain identified and Moriarty's..."
                 ("draw", "ctg_name_result_pattern_sherlock_arrest_failed"))  # "Foiled Moriarty's plan, but failed..."
SIDE_MORIARTY = (("win", "ctg_name_result_kill_succeed"),                 # "Killed a target."
                 ("draw", "ctg_name_result_pattern_moriarty_arrest_failed"))  # "Failure. But Sherlock failed..."
RESULT_ROWS = {DETECTIVE: SIDE_SHERLOCK, WATSON: SIDE_SHERLOCK, CRIMINAL: SIDE_MORIARTY, IRENE: SIDE_MORIARTY}


def result_points(outcome, level=None):
    """Points for the result. Without a level (old matches), the earlier table."""
    if level not in WIN_POINTS:
        return RESULT_POINTS.get(outcome, 0)
    win = WIN_POINTS[level]
    return {"win": win, "draw": win // 2, "lose": win // 2}.get(outcome, 0)


# Actions the server detects -> (id, points). The texts are the game's own.
ACTIONS = {
    # Bando de Sherlock
    "ctg_name_result_repair_switchboard": (104, 50),                    # fix the fuse box
    "ctg_name_result_action_treated_pawnForInjuries": (105, 50),        # heal someone
    "ctg_name_result_apply_tearSpray_to_killer": (107, 100),            # tear gas on the killer
    "ctg_name_result_identified_killer_by_deduction": (108, 100),       # accuse the right killer
    "ctg_name_result_discover_switchboard_before_moriarty": (123, 50),  # fuse box plan before Moriarty
    # Bando de Moriarty
    "ctg_name_result_action_targetKilledByAssail": (101, 50),           # win by killing with the Assault
    "ctg_name_result_blackOut_by_switchboard": (109, 50),               # break the fuse box (blackout)
    "ctg_name_result_action_blockedSherlockWithSpray": (110, 50),       # gas someone
    "ctg_name_result_action_beCriticalNoKiller": (111, 100),            # someone who isn't the killer ends up critical
    "ctg_name_result_first_batting": (124, 50),                         # first clash with Sherlock on a character
    "ctg_name_result_after_the_first_batting": (125, 50),               # another clash on an already clashed character
    "ctg_name_result_action_activateSecretPassage": (112, 50),        # use a secret passage
    "ctg_name_result_action_repair_gasPipe": (113, 50),               # fix a gas leak
    "ctg_name_result_action_exterminateWildDog": (114, 50),           # kill a dog (or a traitor)
    "ctg_name_result_action_foundSwitchboard": (115, 50),             # find a fuse box plan
    "ctg_name_result_action_obtainFoodFromFoodPoint": (116, 50),      # find food
    "ctg_name_result_action_proven_pawnNotKiller": (117, 50),         # rule someone out as the killer
    "ctg_name_result_action_proven_pawnNotTarget": (118, 50),         # rule someone out as the victim
    "ctg_name_result_action_foundSwitchboardBeforeSherlock": (119, 50),   # fuse box plan before Sherlock
    "ctg_name_result_action_treated_killerForInjuries": (120, 50),    # heal the killer
    "ctg_name_result_action_wildDogAttackedEveryoneButKiller": (121, 50),  # a dog injures someone who isn't the killer
    "ctg_name_result_action_injured_noKillerWithGasLeak": (122, 50),  # the gas injures someone who isn't the killer
    # Old ones (only to recalculate old matches)
    # "Villain identified and Moriarty's devious plot foiled": it is the game's text for the win of
    # Sherlock's side (RESULT_ROWS), not an action. It used to be given as an action when surviving an Assault; not
    # anymore.
    "ctg_name_result_arrest_succeed": (106, 100),
    "ctg_name_result_action_kill_succeed_not_identified_killer": (102, 30),
    "ctg_name_result_pattern_arrest_success": (103, 50),
}

# List of "Action points" in the profile: as in the original game, all of them show, also the ones at 0.
# The game sorts them by id, highest to lowest; these ids reproduce the original game's order (the
# first four of each side show in a video from back then). The ones the server doesn't detect yet
# always stay at 0. Text -> id in the profile.
PROFILE_ACTIONS_SHERLOCK = {
    "ctg_name_result_action_activateSecretPassage": 150,         # "Activated a secret passage."
    "ctg_name_result_action_exterminateWildDog": 149,            # "Defeated a wild dog..."
    "ctg_name_result_action_repair_gasPipe": 148,                # "Repaired a gas leak."
    "ctg_name_result_action_treated_pawnForInjuries": 147,       # "Treated a pawn's injury."
    "ctg_name_result_action_proven_pawnNotKiller": 146,
    "ctg_name_result_action_proven_pawnNotTarget": 145,
    "ctg_name_result_action_foundSwitchboard": 144,
    "ctg_name_result_repair_switchboard": 143,
    "ctg_name_result_action_obtainFoodFromFoodPoint": 142,
    "ctg_name_result_apply_tearSpray_to_killer": 141,
    "ctg_name_result_discover_switchboard_before_moriarty": 140,  # "Found a fuse box before Moriarty."
    "ctg_name_result_identified_killer_by_deduction": 139,
}
PROFILE_ACTIONS_MORIARTY = {
    "ctg_name_result_action_beCriticalNoKiller": 160,            # "A pawn other than the villain was in..."
    "ctg_name_result_action_activateSecretPassage": 150,         # "Activated a secret passage."
    "ctg_name_result_action_injured_noKillerWithGasLeak": 130,   # "Injured a pawn other than the villain..."
    "ctg_name_result_action_treated_killerForInjuries": 129,     # "Treated the villain's injury."
    "ctg_name_result_action_wildDogAttackedEveryoneButKiller": 128,
    "ctg_name_result_action_foundSwitchboardBeforeSherlock": 127,
    "ctg_name_result_blackOut_by_switchboard": 126,
    "ctg_name_result_action_blockedSherlockWithSpray": 125,
    "ctg_name_result_action_targetKilledByAssail": 124,
    "ctg_name_result_action_exterminateWildDog": 123,            # both sides can kill dogs
    "ctg_name_result_action_repair_gasPipe": 122,                # and fix gas leaks
    "ctg_name_result_action_treated_pawnForInjuries": 121,       # and heal anyone
    "ctg_name_result_first_batting": 120,                        # "Initial command conflict detected with each pawn."
    "ctg_name_result_after_the_first_batting": 119,              # "Interfered with Sherlock's command."
}
# Irene: Moriarty's minus what she can't do. Sherlock's tip about Irene: "she has no access to the
# 'Assault' nor can she sabotage the fuse box". And her clashes with Sherlock aren't detected (they are her
# advantage).
PROFILE_ACTIONS_IRENE = {k: v for k, v in PROFILE_ACTIONS_MORIARTY.items()
                         if k not in ("ctg_name_result_action_targetKilledByAssail",
                                      "ctg_name_result_blackOut_by_switchboard",
                                      "ctg_name_result_first_batting", "ctg_name_result_after_the_first_batting")}
PROFILE_ACTIONS = {DETECTIVE: PROFILE_ACTIONS_SHERLOCK, WATSON: PROFILE_ACTIONS_SHERLOCK,
                   CRIMINAL: PROFILE_ACTIONS_MORIARTY, IRENE: PROFILE_ACTIONS_IRENE}


def _record(user):
    rec = user.get("record")
    if not isinstance(rec, dict) or rec.get("v") != RECORD_VERSION or "outcomes" not in rec:
        # (Re)calculate with the current points table from the match history
        rec = {"v": RECORD_VERSION, "counts": {}, "points": {}, "outcomes": {}, "actions": {}}
        for h in user.get("history", []) or []:
            role = int(h.get("role", 0))
            if role not in COUNT_IDS:
                continue
            outcome = h.get("outcome") or ("win" if h.get("win") else "lose")
            if outcome not in RESULT_POINTS:
                continue
            if "base" in h:      # new matches: each one stores its own points
                h["points"] = _add(rec, role, outcome, h.get("actions") or [], h.get("base"), h.get("acts"),
                                   h.get("finish"))
            else:
                h["points"] = _add(rec, role, outcome, h.get("actions") or [])
        user["record"] = rec
    return rec


def _add(rec, role, outcome, actions, base=None, acts=None, finish=None):
    if outcome == "abandon":                     # counts as a loss, without points or extras
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
    # A real win or draw (not because the other side gave up): counts in "Match result points"
    if outcome in ("win", "draw") and finish != "abandon":
        o = rec.setdefault("outcomes", {}).setdefault(f"{role}:{outcome}", [0, 0])
        o[0] += 1
        o[1] += int(base)
    for a in actions:
        if a in ACTIONS:
            k = f"{role}:{a}"
            rec["actions"][k] = rec["actions"].get(k, 0) + 1
    return pts


HISTORY_MAX = 20000          # quite a few lifetimes of matches; the log is recalculated from here


def record_match(user, role, outcome, actions=(), stage="", match_id=None, level=None, finish=None):
    """Records a finished match. Returns the points earned.
    match_id identifies the match on any server: merging profiles doesn't duplicate it.
    level: "easy"/"normal"/"hard"/"expert"/"nightmare" (against the AI) or "online" (against people).
    finish: how the match ended: "kill", "deduction" or "abandon" (someone gave up or left)."""
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
    pts = _add(rec, role, outcome, actions, base, acts, finish)
    hist.append({"mid": mid, "time": now, "role": role, "outcome": outcome, "win": outcome == "win",
                 "points": pts, "actions": actions, "stage": stage, "level": level, "base": base, "acts": acts,
                 "finish": finish})
    del hist[:-HISTORY_MAX]
    user["match_count"] = int(user.get("match_count", 0)) + 1
    # What shows on the results screen
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
        # "Match result points": times each result was achieved and its points
        for i, (outcome, text) in enumerate(RESULT_ROWS[role]):
            n, p = rec["outcomes"].get(f"{role}:{outcome}", (0, 0))
            out.append({"id": 9000 + i * 10 + role, "role": role, "category": "result", "text_id": text,
                        "count": int(n), "point": int(p)})
    # "Action points": the whole list for each role (times and points earned with each action)
    for role, actions in PROFILE_ACTIONS.items():
        for text, aid in actions.items():
            n = int(rec["actions"].get(f"{role}:{text}", 0))
            out.append({"id": aid * 10 + role, "role": role, "category": "action", "text_id": text,
                        "count": n, "point": n * ACTIONS.get(text, (0, 0))[1]})
    # Actions from old matches no longer in the list: they still show, at the end
    for key, n in sorted(rec["actions"].items()):
        role, text = key.split(":", 1)
        aid, p = ACTIONS.get(text, (0, 0))
        if aid and text not in PROFILE_ACTIONS.get(int(role), {}):
            out.append({"id": aid * 10 + int(role), "role": int(role), "category": "action", "text_id": text,
                        "count": int(n), "point": int(n) * p})
    return out


def summary(user):
    """Short text for the server log."""
    rec = _record(user)
    c = rec["counts"]
    w = sum(int(c.get(str(ids["win"]), 0)) for ids in COUNT_IDS.values())
    l = sum(int(c.get(str(ids["lose"]), 0)) for ids in COUNT_IDS.values())
    d = sum(int(c.get(str(ids["draw"]), 0)) for ids in COUNT_IDS.values())
    return f"{w}V {d}E {l}D, {sum(rec['points'].values())} puntos"


# ------------------------------------------------------------------ portable profiles
PROFILE_KEYS = ("name", "progress", "tutorial_step", "config", "config_time", "history", "last_result", "updated",
                "lang", "lang_time")


def _mid(h):
    return h.get("mid") or f"legacy-{h.get('time', 0)}-{h.get('role', 0)}"


def export_profile(user):
    """What travels between servers and each player's PC."""
    out = {k: user[k] for k in PROFILE_KEYS if k in user}
    out["history"] = [dict(h, mid=_mid(h)) for h in user.get("history", []) or []]
    return out


def merge_into(user, other, prefer_other=False):
    """Merges 'other' (exported profile) into 'user'. It only adds: matches by unique id,
    tutorial/progress the most advanced, settings and name the most recent change.
    If a match is in both, 'user''s stays; with prefer_other, 'other''s (the server uses it
    when a player syncs: their copy of their own matches rules, so a correction reaches everywhere)."""
    if not isinstance(other, dict):
        return user
    seen = {}
    mine, theirs = user.get("history") or [], other.get("history") or []
    for h in (theirs + mine) if prefer_other else (mine + theirs):
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
    user.pop("record", None)            # recalculated with the full history
    _record(user)
    return user
