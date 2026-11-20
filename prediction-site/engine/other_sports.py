"""
NBA, NHL and tennis analysis for ProScore (data: ESPN public scoreboard JSON, no key needed).

NBA   – offence/defence point ratings (time-weighted), margin ~ Normal(sd 12), total ~ Normal(sd 17.5).
        Markets: moneyline, point spread, total points.
NHL   – Poisson goal model on regulation scores (like soccer) + overtime handling.
        Markets: moneyline (incl. OT), puck line, total goals.
Tennis – Elo ratings from every ATP/WTA singles match of the last year.  Market: match winner.

When bookmaker odds exist, the model probability is blended with the market's no-vig probability
(60/40) so that thin-data team ratings don't produce fake "value".
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ESPN = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={d}&limit=500"
UA = "Mozilla/5.0 (compatible; ProScoreBot/1.0)"
MODEL_WEIGHT = 0.6

SPORTS = {
    "nba": {"path": "basketball/nba", "sport": "basketball", "name": "NBA", "country": "USA"},
    "nhl": {"path": "hockey/nhl", "sport": "hockey", "name": "NHL", "country": "USA / Canada"},
}
TENNIS = {"atp": "tennis/atp", "wta": "tennis/wta"}


# --------------------------------------------------------------------------- fetching
def _fetch(path: str, day: dt.date, today: dt.date, cache_dir: str) -> dict:
    d = day.strftime("%Y%m%d")
    folder = os.path.join(cache_dir, "espn", path.replace("/", "_"))
    os.makedirs(folder, exist_ok=True)
    fp = os.path.join(folder, d + ".json")
    final = (today - day).days > 3  # older days never change -> cache forever
    if final and os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            pass
    data = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(ESPN.format(path=path, d=d), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                print(f"  ! espn {path} {d}: {e}", file=sys.stderr)
                return {}
            time.sleep(1.5 * 2 ** attempt + random.random())
    if final:
        with open(fp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    return data


def fetch_days(path: str, days: list[dt.date], today: dt.date, cache_dir: str) -> dict[dt.date, dict]:
    with ThreadPoolExecutor(max_workers=3) as ex:
        res = list(ex.map(lambda d: _fetch(path, d, today, cache_dir), days))
    return dict(zip(days, res))


def american_to_decimal(s) -> float | None:
    try:
        v = float(str(s).replace("+", ""))
    except (TypeError, ValueError):
        return None
    if v == 0:
        return None
    return round(1 + (v / 100 if v > 0 else 100 / -v), 3)


def _f(x):
    try:
        return float(str(x).lstrip("ou"))
    except (TypeError, ValueError):
        return None


def parse_odds(comp: dict) -> dict:
    o = (comp.get("odds") or [None])[0]
    if not o:
        return {}
    ml = o.get("moneyline") or {}
    ps = o.get("pointSpread") or {}
    tot = o.get("total") or {}
    g = lambda d, side, k: ((d.get(side) or {}).get("close") or {}).get(k)  # noqa: E731
    out = {
        "provider": (o.get("provider") or {}).get("name"),
        "ml_h": american_to_decimal(g(ml, "home", "odds")),
        "ml_a": american_to_decimal(g(ml, "away", "odds")),
        "sp_h_line": _f(g(ps, "home", "line")),
        "sp_h": american_to_decimal(g(ps, "home", "odds")),
        "sp_a_line": _f(g(ps, "away", "line")),
        "sp_a": american_to_decimal(g(ps, "away", "odds")),
        "total": _f(o.get("overUnder")) or _f(g(tot, "over", "line")),
        "ov": american_to_decimal(g(tot, "over", "odds")),
        "un": american_to_decimal(g(tot, "under", "odds")),
    }
    return {k: v for k, v in out.items() if v is not None}


# --------------------------------------------------------------------------- team sports
def parse_team_games(days: dict[dt.date, dict], key: str) -> list[dict]:
    games = []
    seen = set()
    for day, data in days.items():
        for ev in data.get("events", []) or []:
            if ev.get("id") in seen:
                continue
            seen.add(ev.get("id"))
            comp = (ev.get("competitions") or [{}])[0]
            cs = {c.get("homeAway"): c for c in comp.get("competitors", [])}
            if "home" not in cs or "away" not in cs:
                continue
            st = ((comp.get("status") or {}).get("type") or {})
            g = {"id": ev["id"], "league": key, "date": day, "kickoff": ev.get("date", ""),
                 "home": cs["home"]["team"]["displayName"], "away": cs["away"]["team"]["displayName"],
                 "home_abbr": cs["home"]["team"].get("abbreviation", ""), "away_abbr": cs["away"]["team"].get("abbreviation", ""),
                 "final": st.get("name") == "STATUS_FINAL", "scheduled": st.get("state") == "pre",
                 "odds": parse_odds(comp)}
            if g["final"]:
                try:
                    g["hs"], g["as"] = int(cs["home"]["score"]), int(cs["away"]["score"])
                except (KeyError, ValueError):
                    continue
                # regulation score (first 3 periods) for hockey
                lh = [x.get("value", 0) for x in cs["home"].get("linescores", [])]
                la = [x.get("value", 0) for x in cs["away"].get("linescores", [])]
                if len(lh) >= 3 and len(la) >= 3:
                    g["hr"], g["ar"] = int(sum(lh[:3])), int(sum(la[:3]))
            games.append(g)
    games.sort(key=lambda g: g["kickoff"])
    return games


class Ratings:
    """Multiplicative attack/defence ratings fitted by weighted Poisson likelihood (works for goals or points)."""

    def __init__(self, games: list[dict], ref: dt.date, hk: str, ak: str, half_life: float):
        xi = math.log(2) / half_life
        self.games = [g for g in games if g["date"] < ref and hk in g]
        self.teams = sorted({g["home"] for g in self.games} | {g["away"] for g in self.games})
        self.n = defaultdict(int)
        for g in self.games:
            self.n[g["home"]] += 1
            self.n[g["away"]] += 1
        self.att = {t: 1.0 for t in self.teams}
        self.dfn = {t: 1.0 for t in self.teams}
        self.base, self.ha = 1.0, 1.0
        if len(self.games) < 40:
            self.ok = False
            return
        self.ok = True
        w = [math.exp(-xi * (ref - g["date"]).days) for g in self.games]
        sw = sum(w)
        H = sum(wi * g[hk] for wi, g in zip(w, self.games))
        A = sum(wi * g[ak] for wi, g in zip(w, self.games))
        self.base = (H + A) / (2 * sw)
        self.ha = math.sqrt(H / A)
        prior = self.base * 2  # shrink new teams towards average (≈ 2 games of average output)
        for _ in range(40):
            na, da = defaultdict(float), defaultdict(float)
            for wi, g in zip(w, self.games):
                h, a = g["home"], g["away"]
                na[h] += wi * g[hk]; da[h] += wi * self.base * self.ha * self.dfn[a]
                na[a] += wi * g[ak]; da[a] += wi * self.base / self.ha * self.dfn[h]
            for t in self.teams:
                self.att[t] = (na[t] + prior) / (da[t] + prior)
            nd, dd = defaultdict(float), defaultdict(float)
            for wi, g in zip(w, self.games):
                h, a = g["home"], g["away"]
                nd[a] += wi * g[hk]; dd[a] += wi * self.base * self.ha * self.att[h]
                nd[h] += wi * g[ak]; dd[h] += wi * self.base / self.ha * self.att[a]
            for t in self.teams:
                self.dfn[t] = (nd[t] + prior) / (dd[t] + prior)
            ma = sum(self.att.values()) / len(self.att)
            md = sum(self.dfn.values()) / len(self.dfn)
            for t in self.teams:
                self.att[t] /= ma
                self.dfn[t] /= md

    def can(self, h: str, a: str, min_games: int = 5) -> bool:
        return self.ok and self.n.get(h, 0) >= min_games and self.n.get(a, 0) >= min_games

    def expect(self, h: str, a: str) -> tuple[float, float]:
        return (self.base * self.ha * self.att[h] * self.dfn[a],
                self.base / self.ha * self.att[a] * self.dfn[h])


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def no_vig(a: float | None, b: float | None) -> tuple[float, float] | None:
    if not a or not b:
        return None
    pa, pb = 1 / a, 1 / b
    s = pa + pb
    return pa / s, pb / s


def blend(model: float, market: float | None) -> float:
    return model if market is None else MODEL_WEIGHT * model + (1 - MODEL_WEIGHT) * market


def nba_markets(mh: float, ma: float, odds: dict) -> list[dict]:
    m, tot = mh - ma, mh + ma
    sd_m, sd_t = 12.0, 17.5
    out = []
    ph = phi(m / sd_m)
    mk = no_vig(odds.get("ml_h"), odds.get("ml_a"))
    out.append(_mkt("ML_H", None, ph, mk[0] if mk else None, odds.get("ml_h")))
    out.append(_mkt("ML_A", None, 1 - ph, mk[1] if mk else None, odds.get("ml_a")))
    L = odds.get("sp_h_line")
    if L is not None:
        p = phi((m + L) / sd_m)
        mk = no_vig(odds.get("sp_h"), odds.get("sp_a"))
        out.append(_mkt("SP_H", L, p, mk[0] if mk else None, odds.get("sp_h")))
        out.append(_mkt("SP_A", -L, 1 - p, mk[1] if mk else None, odds.get("sp_a")))
    T = odds.get("total")
    if T is not None:
        p = 1 - phi((T - tot) / sd_t)
        mk = no_vig(odds.get("ov"), odds.get("un"))
        out.append(_mkt("OV", T, p, mk[0] if mk else None, odds.get("ov")))
        out.append(_mkt("UN", T, 1 - p, mk[1] if mk else None, odds.get("un")))
    return out


def nhl_markets(lh: float, la: float, odds: dict) -> tuple[list[dict], list[dict]]:
    N = 12
    M = [[pois(i, lh) * pois(j, la) for j in range(N)] for i in range(N)]
    p_reg_h = sum(M[i][j] for i in range(N) for j in range(N) if i > j)
    p_tie = sum(M[i][i] for i in range(N))
    ot_home = 0.52
    ph = p_reg_h + p_tie * ot_home
    out = []
    mk = no_vig(odds.get("ml_h"), odds.get("ml_a"))
    out.append(_mkt("ML_H", None, ph, mk[0] if mk else None, odds.get("ml_h")))
    out.append(_mkt("ML_A", None, 1 - ph, mk[1] if mk else None, odds.get("ml_a")))
    # final margin: regulation margin, ties become ±1 after OT/SO
    def p_final_margin_gt(x: float) -> float:  # P(home final - away final > x)
        s = sum(M[i][j] for i in range(N) for j in range(N) if i != j and i - j > x)
        s += p_tie * (ot_home if 1 > x else 0) + p_tie * ((1 - ot_home) if -1 > x else 0)
        return s
    L = odds.get("sp_h_line")
    if L is None:
        L = -1.5 if ph >= 0.5 else 1.5
    p = p_final_margin_gt(-L)
    mk = no_vig(odds.get("sp_h"), odds.get("sp_a"))
    out.append(_mkt("SP_H", L, p, mk[0] if mk else None, odds.get("sp_h")))
    out.append(_mkt("SP_A", -L, 1 - p, mk[1] if mk else None, odds.get("sp_a")))
    T = odds.get("total") or 6.5
    p_over = sum(M[i][j] for i in range(N) for j in range(N) if (i + j + (1 if i == j else 0)) > T)
    mk = no_vig(odds.get("ov"), odds.get("un"))
    out.append(_mkt("OV", T, p_over, mk[0] if mk else None, odds.get("ov")))
    out.append(_mkt("UN", T, 1 - p_over, mk[1] if mk else None, odds.get("un")))
    scores = sorted(((M[i][j], f"{i}-{j}") for i in range(7) for j in range(7)), reverse=True)[:5]
    return out, [{"score": s, "prob": round(p, 4)} for p, s in scores]


def _mkt(code: str, line, model_p: float, market_p: float | None, odds: float | None) -> dict:
    p = blend(model_p, market_p)
    return {"code": code, "line": line, "prob": round(p, 4), "model_prob": round(model_p, 4),
            "market_prob": round(market_p, 4) if market_p is not None else None,
            "odds": odds, "fair_odds": round(1 / max(p, 1e-6), 2),
            "edge": round(p * odds - 1, 4) if odds else None}


def choose(markets: list[dict]) -> dict:
    """Value first (edge > 3% at a sensible probability), otherwise the most likely market."""
    value = [m for m in markets if m["edge"] is not None and m["edge"] > 0.03 and m["prob"] >= 0.45]
    if value:
        best = max(value, key=lambda m: m["edge"] * m["prob"])
    else:
        best = max(markets, key=lambda m: (m["prob"], m["code"].startswith("ML")))
    conf = "high" if best["prob"] >= 0.72 else "medium" if best["prob"] >= 0.58 else "low"
    return {"market": best["code"], "line": best["line"], "prob": best["prob"],
            "fair_odds": best["fair_odds"], "book_odds": best["odds"], "edge": best["edge"],
            "value": bool(best["edge"] is not None and best["edge"] > 0.04), "confidence": conf}


def form(games: list[dict], team: str, before: dt.date, n: int = 5) -> list[str]:
    out = []
    for g in reversed(games):
        if g["date"] >= before or not g["final"] or team not in (g["home"], g["away"]):
            continue
        f, a = (g["hs"], g["as"]) if g["home"] == team else (g["as"], g["hs"])
        out.append("W" if f > a else "L")
        if len(out) == n:
            break
    return out


def team_stats(games: list[dict], team: str, before: dt.date, total_line: float | None, n: int = 10) -> dict:
    ms = [g for g in reversed(games) if g["final"] and g["date"] < before and team in (g["home"], g["away"])][:n]
    if not ms:
        return {}
    pf = sum(g["hs"] if g["home"] == team else g["as"] for g in ms) / len(ms)
    pa = sum(g["as"] if g["home"] == team else g["hs"] for g in ms) / len(ms)
    wins = sum((g["hs"] > g["as"]) == (g["home"] == team) for g in ms)
    out = {"games": len(ms), "pf": round(pf, 1), "pa": round(pa, 1), "win": round(wins / len(ms), 2)}
    if total_line:
        out["over"] = round(sum(g["hs"] + g["as"] > total_line for g in ms) / len(ms), 2)
    return out


def h2h(games: list[dict], h: str, a: str, before: dt.date, n: int = 5) -> list[dict]:
    ms = [g for g in reversed(games) if g["final"] and g["date"] < before and {g["home"], g["away"]} == {h, a}][:n]
    return [{"date": g["date"].isoformat(), "home": g["home"], "away": g["away"], "score": f'{g["hs"]}-{g["as"]}'} for g in ms]


def season_start(today: dt.date) -> dt.date:
    return dt.date(today.year if today.month >= 9 else today.year - 1, 10, 1)


def run_team_sport(key: str, today: dt.date, cache_dir: str) -> tuple:
    cfg = SPORTS[key]
    start = season_start(today) - dt.timedelta(days=365)  # current + previous season
    days = [start + dt.timedelta(days=i) for i in range((today - start).days + 3)]
    print(f"  {cfg['name']}: fetching {len(days)} days")
    games = parse_team_games(fetch_days(cfg["path"], days, today, cache_dir), key)
    finals = [g for g in games if g["final"]]
    print(f"  {cfg['name']}: {len(finals)} results")
    if key == "nba":
        R = Ratings(games, today, "hs", "as", half_life=90)
    else:
        R = Ratings(games, today, "hr", "ar", half_life=150)
    preds = []
    for g in games:
        if not g["scheduled"] or not (today <= g["date"] <= today + dt.timedelta(days=1)):
            continue
        if not R.can(g["home"], g["away"]):
            continue
        eh, ea = R.expect(g["home"], g["away"])
        scores = []
        if key == "nba":
            mkts = nba_markets(eh, ea, g["odds"])
        else:
            mkts, scores = nhl_markets(eh, ea, g["odds"])
        tip = choose(mkts)
        tl = g["odds"].get("total")
        preds.append({
            "id": f"{key}|{g['id']}", "sport": cfg["sport"], "league": key.upper(), "country": cfg["country"],
            "league_name": cfg["name"], "date": g["date"].isoformat(), "time": g["kickoff"][11:16] + " UTC" if g["kickoff"] else "",
            "kickoff": g["kickoff"], "home": g["home"], "away": g["away"],
            "home_abbr": g["home_abbr"], "away_abbr": g["away_abbr"],
            "xg": [round(eh, 1 if key == "nba" else 2), round(ea, 1 if key == "nba" else 2)],
            "markets": mkts, "tip": tip, "odds": g["odds"], "correct_scores": scores,
            "form": {"home": form(games, g["home"], today), "away": form(games, g["away"], today)},
            "stats": {"home": team_stats(games, g["home"], today, tl), "away": team_stats(games, g["away"], today, tl)},
            "h2h": h2h(games, g["home"], g["away"], today),
            "strength": {"home_att": round(R.att[g["home"]], 2), "home_def": round(R.dfn[g["home"]], 2),
                         "away_att": round(R.att[g["away"]], 2), "away_def": round(R.dfn[g["away"]], 2)},
        })
    finished = {f"{key}|{g['id']}": (g["hs"], g["as"]) for g in finals}
    recent = [{"league": key.upper(), "league_name": cfg["name"], "sport": cfg["sport"], "date": g["date"].isoformat(),
               "home": g["home"], "away": g["away"], "score": f'{g["hs"]}-{g["as"]}'}
              for g in finals if (today - g["date"]).days <= 3]
    bt = backtest_team(games, key, today)
    return preds, finished, recent, len(finals), bt


def backtest_team(games: list[dict], key: str, today: dt.date) -> dict:
    """Refit weekly over the last 120 days, predict the following week (moneyline accuracy)."""
    hk, ak, hl = ("hs", "as", 90) if key == "nba" else ("hr", "ar", 150)
    n = c = 0
    brier = 0.0
    d = today - dt.timedelta(days=120)
    while d < today:
        R = Ratings(games, d, hk, ak, hl)
        for g in games:
            if g["final"] and d <= g["date"] < d + dt.timedelta(days=7) and R.can(g["home"], g["away"]):
                eh, ea = R.expect(g["home"], g["away"])
                if key == "nba":
                    ph = phi((eh - ea) / 12.0)
                else:
                    ph = nhl_markets(eh, ea, {})[0][0]["model_prob"]
                won = g["hs"] > g["as"]
                n += 1; c += (ph >= 0.5) == won
                brier += (ph - won) ** 2
        d += dt.timedelta(days=7)
    return {"matches": n, "acc": round(c / n, 4) if n else None, "brier": round(brier / n, 4) if n else None}


# --------------------------------------------------------------------------- tennis
def run_tennis(today: dt.date, cache_dir: str) -> tuple[list[dict], dict, list[dict], int, dict]:
    preds, finished, recent, total = [], {}, [], 0
    bt = {"matches": 0, "correct": 0, "brier": 0.0}
    for tour, path in TENNIS.items():
        # a scoreboard day returns every match of the tournaments running that day -> sample every 3 days
        days = [today - dt.timedelta(days=i) for i in range(0, 366, 3)] + [today + dt.timedelta(days=1)]
        print(f"  {tour.upper()}: fetching {len(days)} days")
        data = fetch_days(path, sorted(set(days)), today, cache_dir)
        matches, seen = [], set()
        for d in sorted(data):
            for ev in data[d].get("events", []) or []:
                for grp in ev.get("groupings", []) or []:
                    if "Singles" not in ((grp.get("grouping") or {}).get("displayName") or ""):
                        continue
                    for c in grp.get("competitions", []) or []:
                        if c.get("id") in seen:
                            continue
                        seen.add(c.get("id"))
                        ps = c.get("competitors", [])
                        if len(ps) != 2:
                            continue
                        names = [((p.get("athlete") or {}).get("displayName") or "").strip() for p in ps]
                        if not all(names) or any(n.upper() in ("TBD", "BYE") for n in names):
                            continue
                        st = ((c.get("status") or {}).get("type") or {})
                        sets = [sum(1 for a, b in zip(_ls(ps[i]), _ls(ps[1 - i])) if a > b) for i in (0, 1)]
                        matches.append({"id": c["id"], "tour": tour, "event": ev.get("name", ""),
                                        "round": (c.get("round") or {}).get("displayName", ""),
                                        "kickoff": c.get("date", ""), "p1": names[0], "p2": names[1],
                                        "winner": 0 if ps[0].get("winner") else 1 if ps[1].get("winner") else None,
                                        "final": st.get("name") == "STATUS_FINAL", "state": st.get("state"),
                                        "sets": sets, "odds": parse_odds(c)})
        matches.sort(key=lambda m: m["kickoff"])
        elo, cnt = defaultdict(lambda: 1500.0), defaultdict(int)
        for m in matches:
            if not (m["final"] and m["winner"] is not None):
                continue
            a, b = m["p1"], m["p2"]
            pa = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
            if cnt[a] >= 10 and cnt[b] >= 10 and m["kickoff"][:10] >= (today - dt.timedelta(days=120)).isoformat():
                bt["matches"] += 1
                bt["correct"] += (pa >= 0.5) == (m["winner"] == 0)
                bt["brier"] += (pa - (m["winner"] == 0)) ** 2
            s = 1.0 if m["winner"] == 0 else 0.0
            ka, kb = 250 / (cnt[a] + 5) ** 0.4, 250 / (cnt[b] + 5) ** 0.4
            elo[a] += ka * (s - pa); elo[b] -= kb * (s - pa)
            cnt[a] += 1; cnt[b] += 1
            total += 1
            mid = f"{tour}|{m['id']}"
            finished[mid] = tuple(m["sets"]) if sum(m["sets"]) else ((1, 0) if m["winner"] == 0 else (0, 1))
            if m["kickoff"][:10] >= (today - dt.timedelta(days=3)).isoformat():
                recent.append({"league": tour.upper(), "league_name": m["event"], "sport": "tennis",
                               "date": m["kickoff"][:10], "home": m["p1"], "away": m["p2"],
                               "score": "-".join(map(str, m["sets"]))})
        for m in matches:
            if m["state"] != "pre" or not m["kickoff"]:
                continue
            day = dt.date.fromisoformat(m["kickoff"][:10])
            if not (today <= day <= today + dt.timedelta(days=1)):
                continue
            a, b = m["p1"], m["p2"]
            if cnt[a] < 5 or cnt[b] < 5:
                continue
            p = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
            mk = no_vig(m["odds"].get("ml_h"), m["odds"].get("ml_a"))
            mkts = [_mkt("ML_H", None, p, mk[0] if mk else None, m["odds"].get("ml_h")),
                    _mkt("ML_A", None, 1 - p, mk[1] if mk else None, m["odds"].get("ml_a"))]
            preds.append({
                "id": f"{tour}|{m['id']}", "sport": "tennis", "league": tour.upper(), "country": tour.upper(),
                "league_name": m["event"], "round": m["round"], "date": day.isoformat(),
                "time": m["kickoff"][11:16] + " UTC", "kickoff": m["kickoff"], "home": a, "away": b,
                "elo": [round(elo[a]), round(elo[b])], "matches_played": [cnt[a], cnt[b]],
                "markets": mkts, "tip": choose(mkts), "odds": m["odds"],
                "form": {"home": _tform(matches, a), "away": _tform(matches, b)},
                "h2h": _th2h(matches, a, b),
            })
    btn = bt["matches"] or 1
    return preds, finished, recent, total, {"matches": bt["matches"], "acc": round(bt["correct"] / btn, 4),
                                            "brier": round(bt["brier"] / btn, 4)}


def _ls(p: dict) -> list[float]:
    return [x.get("value", 0) or 0 for x in p.get("linescores", [])]


def _tform(matches: list[dict], player: str, n: int = 5) -> list[str]:
    out = []
    for m in reversed(matches):
        if m["final"] and m["winner"] is not None and player in (m["p1"], m["p2"]):
            out.append("W" if (m["p1"] == player) == (m["winner"] == 0) else "L")
            if len(out) == n:
                break
    return out


def _th2h(matches: list[dict], a: str, b: str, n: int = 5) -> list[dict]:
    out = []
    for m in reversed(matches):
        if m["final"] and {m["p1"], m["p2"]} == {a, b}:
            out.append({"date": m["kickoff"][:10], "home": m["p1"], "away": m["p2"], "score": "-".join(map(str, m["sets"]))})
            if len(out) == n:
                break
    return out
