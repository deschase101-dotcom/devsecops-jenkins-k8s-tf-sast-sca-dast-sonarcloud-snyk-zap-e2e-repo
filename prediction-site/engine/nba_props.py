"""
NBA player projections (points, rebounds, assists, threes, PRA) from every box score of the current season.

Source: basketball-reference.com box-score pages (allowed by robots.txt; we respect its 3 s crawl-delay
and cache every finished game forever, so after the first build only the new games are downloaded).

Method per player:
  * weighted average of his recent games (a game's weight halves every 6 games), minutes-aware
  * points scaled by the opponent's defensive rating from the team model
  * spread estimated from his own game-to-game variation (with a floor), normal approximation
  * "safe line" = the highest .5 line he clears with >= 75 % probability
Players who missed their team's last two games are treated as out (no injury feed is available).
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import math
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

BOX = "https://www.basketball-reference.com/boxscores/{id}.html"
UA = "Mozilla/5.0 (compatible; ProScoreBot/1.0)"
STATS = ("pts", "trb", "ast", "fg3")
HALF_LIFE_GAMES = 6
SAFE_P = 0.75
SD_FLOOR = {"pts": 4.0, "trb": 1.8, "ast": 1.5, "fg3": 0.9, "pra": 5.0}


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob_over(stat: str, mu: float, sd: float, line: float, recent: list[float]) -> float:
    """50/50 blend of the model distribution and the player's own recent hit rate (smoothed)."""
    if stat == "fg3":  # small whole numbers -> Poisson
        k = int(math.floor(line))
        model = 1 - sum(math.exp(-mu) * mu ** i / math.factorial(i) for i in range(k + 1))
    else:
        model = 1 - _phi((line + 0.5 - 0.5 - mu) / sd)
    hits = sum(v > line for v in recent)
    emp = (hits + 1) / (len(recent) + 2)
    return 0.5 * model + 0.5 * emp


def fetch_boxes(games: list[dict], cache_dir: str, max_new: int | None = None) -> dict[str, str]:
    folder = os.path.join(cache_dir, "nba_box")
    os.makedirs(folder, exist_ok=True)
    out, new, last = {}, 0, 0.0
    todo = [g for g in games if g.get("final") and g.get("box")]
    for g in todo:
        fp = os.path.join(folder, g["box"] + ".html")
        if os.path.exists(fp):
            out[g["box"]] = fp
            continue
        if max_new is not None and new >= max_new:
            continue
        wait = 3.5 - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        last = time.time()
        try:
            req = urllib.request.Request(BOX.format(id=g["box"]), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            print(f"  ! box {g['box']}: {e}", file=sys.stderr)
            continue
        # keep only the two basic box tables to save disk
        keep = "\n".join(re.findall(r'<table[^>]*id="box-[A-Z]+-game-basic".*?</table>', text, re.S))
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(keep)
        out[g["box"]] = fp
        new += 1
        if new % 25 == 0:
            print(f"    … {new} new box scores downloaded")
    print(f"  NBA box scores: {len(out)} available ({new} new)")
    return out


def parse_box(path: str) -> list[list[dict]]:
    """Returns [away_players, home_players]; each player {id, name, min, pts, trb, ast, fg3}."""
    text = open(path, encoding="utf-8").read()
    teams = []
    for body in re.findall(r'id="box-[A-Z]+-game-basic".*?<tbody>(.*?)</tbody>', text, re.S):
        players = []
        for row in re.findall(r"<tr\s*>(.*?)</tr>", body, re.S):
            pid = re.search(r'data-append-csv="([^"]+)"', row)
            c = {k: htmllib.unescape(re.sub("<[^>]+>", "", v)).strip()
                 for k, v in re.findall(r'data-stat="(\w+)"[^>]*>(.*?)</t[hd]>', row, re.S)}
            if not pid or "player" not in c:
                continue
            p = {"id": pid.group(1), "name": c["player"], "min": 0.0}
            if "mp" in c and ":" in c["mp"]:
                mm, ss = c["mp"].split(":")
                p["min"] = int(mm) + int(ss) / 60
                for s in STATS:
                    p[s] = int(c.get(s) or 0)
            players.append(p)
        teams.append(players)
    return teams[:2]


def build_logs(games: list[dict], boxes: dict[str, str]) -> tuple[dict, dict]:
    """player_logs[team][player_id] = list of game lines (chronological); team_games[team] = list of dates."""
    logs: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    team_dates: dict[str, list] = defaultdict(list)
    names = {}
    for g in sorted((g for g in games if g.get("box") in boxes), key=lambda g: g["date"]):
        try:
            away, home = parse_box(boxes[g["box"]])
        except ValueError:
            continue
        for team, opp, players in ((g["away"], g["home"], away), (g["home"], g["away"], home)):
            team_dates[team].append(g["date"])
            for p in players:
                names[p["id"]] = p["name"]
                if p["min"] > 0:
                    logs[team][p["id"]].append({"date": g["date"], "opp": opp, **{k: p[k] for k in ("min",) + STATS}})
    return logs, team_dates, names


def project_team(team: str, opp: str, logs, team_dates, names, opp_def: float, top: int = 7) -> list[dict]:
    dates = team_dates.get(team, [])
    if len(dates) < 3:
        return []
    recent_two = set(dates[-2:])
    out = []
    for pid, lines in logs.get(team, {}).items():
        if not any(l["date"] in recent_two for l in lines):
            continue  # missed the last two games -> probably injured / out
        lines = lines[-15:]
        if len(lines) < 3:
            continue
        w = [0.5 ** ((len(lines) - 1 - i) / HALF_LIFE_GAMES) for i in range(len(lines))]
        sw = sum(w)
        mins = sum(wi * l["min"] for wi, l in zip(w, lines)) / sw
        if mins < 18:
            continue
        proj, sd = {}, {}
        for s in STATS + ("pra",):
            vals = [l["pts"] + l["trb"] + l["ast"] if s == "pra" else l[s] for l in lines]
            mu = sum(wi * v for wi, v in zip(w, vals)) / sw
            if s in ("pts", "pra"):
                mu *= opp_def ** 0.6  # opponent concedes more/less than average
            var = sum(wi * (v - mu) ** 2 for wi, v in zip(w, vals)) / sw
            proj[s] = round(mu, 1)
            sd[s] = max(math.sqrt(var), SD_FLOOR[s])
        safe = {}
        for s in STATS + ("pra",):
            vals = [l["pts"] + l["trb"] + l["ast"] if s == "pra" else l[s] for l in lines]
            if s == "fg3" and proj[s] < 1.2:
                continue
            best = None
            line = math.floor(proj[s]) + 0.5
            while line >= 0.5:  # highest .5 line he clears >= 75% of the time
                p = prob_over(s, proj[s], sd[s], line, vals)
                if p >= SAFE_P:
                    best = {"line": line, "prob": round(p, 3), "hit": f"{sum(v > line for v in vals)}/{len(vals)}"}
                    break
                line -= 1.0
            if best:
                safe[s] = best
        out.append({"id": pid, "name": names.get(pid, pid), "team": team, "opp": opp, "min": round(mins, 1),
                    "games": len(lines), "proj": proj, "sd": {k: round(v, 1) for k, v in sd.items()}, "safe": safe,
                    "last5": [{k: l[k] for k in ("pts", "trb", "ast", "fg3")} for l in lines[-5:]]})
    out.sort(key=lambda p: -p["min"])
    return out[:top]


def best_props(players: list[dict], home: str, away: str, n: int = 6) -> list[dict]:
    """Most reliable props of a game: high probability AND a line that is not trivially low."""
    cands = []
    for p in players:
        for s, v in p["safe"].items():
            if s == "pra":
                continue
            if v["line"] < {"pts": 9.5, "trb": 3.5, "ast": 2.5, "fg3": 1.5}[s]:
                continue
            cands.append({"player": p["name"], "team": p["team"], "stat": s, "line": v["line"], "hit": v["hit"],
                          "prob": v["prob"], "proj": p["proj"][s], "home": home, "away": away})
    # rank by probability, but prefer meaningful lines (points lines carry the most information)
    cands.sort(key=lambda c: -(c["prob"] + {"pts": 0.03, "trb": 0.01, "ast": 0.01, "fg3": 0.0}[c["stat"]]))
    return cands[:n]
