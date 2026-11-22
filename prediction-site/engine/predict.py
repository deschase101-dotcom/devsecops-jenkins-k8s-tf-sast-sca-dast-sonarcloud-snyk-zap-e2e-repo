#!/usr/bin/env python3
"""
ProScore daily prediction engine.

Pipeline (runs once a day, e.g. from GitHub Actions):
  1. Download every match result for the last N seasons of each league
     (football-data.co.uk free CSVs) plus the upcoming fixtures list.
  2. Fit a time-weighted Dixon-Coles / Poisson model per league
     (attack + defence strength per team, home advantage).
  3. For every upcoming fixture compute the full score matrix and derive
     1X2, double chance, over/under, BTTS and correct-score probabilities.
  4. Pick a tip per match, flag value bets against bookmaker odds,
     and build daily accumulators ("coupons").
  5. Settle yesterday's tips against real results -> public track record.
  6. Walk-forward backtest on the last completed season -> model accuracy.

Outputs JSON files into site/data/ consumed by the static website.
Standard library only.

Usage:
  python engine/predict.py                # live data
  python engine/predict.py --demo         # offline synthetic data (for testing)
  python engine/predict.py --no-backtest  # skip the slower backtest step
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import os
import random
import sys
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "site", "data")
CACHE_DIR = os.path.join(ROOT, ".cache")

BASE_URL = "https://football-data.co.uk/mmz4281/{season}/{code}.csv"
FIXTURES_URL = "https://football-data.co.uk/fixtures.csv"

LEAGUES = {
    "E0": ("England", "Premier League"),
    "E1": ("England", "Championship"),
    "SP1": ("Spain", "La Liga"),
    "I1": ("Italy", "Serie A"),
    "D1": ("Germany", "Bundesliga"),
    "F1": ("France", "Ligue 1"),
    "N1": ("Netherlands", "Eredivisie"),
    "P1": ("Portugal", "Primeira Liga"),
    "B1": ("Belgium", "Pro League"),
    "T1": ("Turkey", "Süper Lig"),
    "SC0": ("Scotland", "Premiership"),
}

SEASONS_BACK = 3          # current season + 2 previous
HALF_LIFE_DAYS = 365      # weight of a match halves every year
XI = math.log(2) / HALF_LIFE_DAYS
RHO = -0.08               # Dixon-Coles low-score dependence
MAX_GOALS = 10
MIN_MATCHES_TEAM = 6      # need this much history to predict a team
FIXTURE_WINDOW_DAYS = 7

UA = "Mozilla/5.0 (compatible; ProScoreBot/1.0)"


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def season_codes(today: dt.date, n: int) -> list[str]:
    start = today.year if today.month >= 7 else today.year - 1
    out = []
    for i in range(n):
        y = start - i
        out.append(f"{y % 100:02d}{(y + 1) % 100:02d}")
    return out


def http_get(url: str) -> str | None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        return raw.decode("utf-8-sig", errors="replace")
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {e}", file=sys.stderr)
        return None


def parse_date(s: str) -> dt.date | None:
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def fnum(row: dict, *keys: str) -> float | None:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            try:
                f = float(v)
                if f > 1.0:
                    return f
            except ValueError:
                pass
    return None


def odds_from_row(row: dict) -> dict:
    o = {
        "H": fnum(row, "AvgH", "B365H", "PSH", "BWH"),
        "D": fnum(row, "AvgD", "B365D", "PSD", "BWD"),
        "A": fnum(row, "AvgA", "B365A", "PSA", "BWA"),
        "O25": fnum(row, "Avg>2.5", "B365>2.5", "P>2.5"),
        "U25": fnum(row, "Avg<2.5", "B365<2.5", "P<2.5"),
    }
    return {k: v for k, v in o.items() if v}


def rows_to_matches(text: str, code: str) -> list[dict]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        d = parse_date(row.get("Date", ""))
        h, a = (row.get("HomeTeam") or "").strip(), (row.get("AwayTeam") or "").strip()
        if not d or not h or not a:
            continue
        hg, ag = row.get("FTHG", ""), row.get("FTAG", "")
        m = {"league": row.get("Div", code) or code, "date": d, "time": row.get("Time", ""),
             "home": h, "away": a, "odds": odds_from_row(row)}
        if hg.strip().isdigit() and ag.strip().isdigit():
            m["hg"], m["ag"] = int(hg), int(ag)
        out.append(m)
    return out


def load_live(today: dt.date) -> tuple[dict[str, list[dict]], list[dict]]:
    results: dict[str, list[dict]] = defaultdict(list)
    for code in LEAGUES:
        for season in season_codes(today, SEASONS_BACK):
            url = BASE_URL.format(season=season, code=code)
            print(f"  fetching {code} {season}")
            txt = http_get(url)
            if txt:
                results[code].extend(m for m in rows_to_matches(txt, code) if "hg" in m)
    fixtures = []
    txt = http_get(FIXTURES_URL)
    if txt:
        fixtures = [m for m in rows_to_matches(txt, "") if m["league"] in LEAGUES]
    return results, fixtures


def load_demo(today: dt.date) -> tuple[dict[str, list[dict]], list[dict]]:
    """Synthetic but realistic data so the whole pipeline can run offline."""
    rnd = random.Random(42)
    names = {
        "E0": ["Northbridge", "Kingsport", "Ashford City", "Redhaven", "Millbrook", "Westvale",
               "Stonegate", "Harrowfield", "Clearwater", "Oakmont", "Bramley Utd", "Fenwick"],
        "SP1": ["Real Costa", "Atlético Sol", "Valdemar", "Sevilla Norte", "Bética", "Montaña CF",
                "Riazor", "Arenas", "Castellón Azul", "Toledo FC", "Mirador", "Pinar"],
        "I1": ["Lupi Roma", "Torre Milano", "Gemma", "Fiorenza", "Vesuvio", "Laguna",
               "Piave", "Etna", "Aquila", "Stella", "Dolomiti", "Marina"],
        "F1": ["Paris Étoile", "Olympique Sud", "Lumière", "Côte d'Azur", "Bretagne FC", "Alsace",
               "Rhône", "Loire", "Provence", "Normandie", "Garonne", "Jura"],
    }
    results: dict[str, list[dict]] = {}
    fixtures: list[dict] = []
    for code, teams in names.items():
        strength = {t: (rnd.uniform(0.7, 1.45), rnd.uniform(0.7, 1.35)) for t in teams}
        ms = []
        start = today - dt.timedelta(days=700)
        d = start
        while d < today:
            rnd.shuffle(teams)
            for i in range(0, len(teams), 2):
                h, a = teams[i], teams[i + 1]
                lh = 1.38 * strength[h][0] / strength[a][1]
                la = 1.08 * strength[a][0] / strength[h][1]
                ms.append({"league": code, "date": d, "time": "", "home": h, "away": a,
                           "hg": poisson_sample(rnd, lh), "ag": poisson_sample(rnd, la), "odds": {}})
            d += dt.timedelta(days=7)
        results[code] = ms
        for k in range(2):
            rnd.shuffle(teams)
            day = today + dt.timedelta(days=k)
            for i in range(0, len(teams), 2):
                h, a = teams[i], teams[i + 1]
                lh = 1.38 * strength[h][0] / strength[a][1]
                la = 1.08 * strength[a][0] / strength[h][1]
                ph = sum(pois(i_, lh) * sum(pois(j, la) for j in range(i_)) for i_ in range(10))
                pa = sum(pois(j, la) * sum(pois(i_, lh) for i_ in range(j)) for j in range(10))
                pd = max(0.05, 1 - ph - pa)
                mg = 1.06
                odds = {"H": round(1 / (ph * mg) * rnd.uniform(0.92, 1.08), 2),
                        "D": round(1 / (pd * mg) * rnd.uniform(0.92, 1.08), 2),
                        "A": round(1 / (pa * mg) * rnd.uniform(0.92, 1.08), 2)}
                fixtures.append({"league": code, "date": day, "time": f"{rnd.choice([15,17,19,21])}:00",
                                 "home": h, "away": a, "odds": odds})
    # pretend yesterday's predictions exist: add results for them
    return results, fixtures


def poisson_sample(rnd: random.Random, lam: float) -> int:
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= L:
            return k
        k += 1


def pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
class LeagueModel:
    def __init__(self, matches: list[dict], ref_date: dt.date):
        self.ref = ref_date
        self.matches = [m for m in matches if m["date"] < ref_date]
        self.teams = sorted({m["home"] for m in self.matches} | {m["away"] for m in self.matches})
        self.count = defaultdict(int)
        for m in self.matches:
            self.count[m["home"]] += 1
            self.count[m["away"]] += 1
        self.att = {t: 1.0 for t in self.teams}
        self.dfn = {t: 1.0 for t in self.teams}   # >1 = concedes more
        self.home_adv = 1.25
        self.base = 1.3
        self.fitted = len(self.matches) >= 60
        if self.fitted:
            self._fit()

    def _fit(self, iters: int = 40) -> None:
        w = [math.exp(-XI * (self.ref - m["date"]).days) for m in self.matches]
        # this season (from July) carries most of the weight: squads change a lot between seasons
        cur_start = dt.date(self.ref.year if self.ref.month >= 7 else self.ref.year - 1, 7, 1)
        cur = sum(wi for wi, m in zip(w, self.matches) if m["date"] >= cur_start)
        old = sum(wi for wi, m in zip(w, self.matches) if m["date"] < cur_start)
        if cur > 0 and old > 0:
            # sliding weight: ~50% at the start of the season, 95% by mid-season (about 19 games)
            cur_m = [m for m in self.matches if m["date"] >= cur_start]
            teams = {m["home"] for m in cur_m} | {m["away"] for m in cur_m}
            gpt = 2 * len(cur_m) / max(1, len(teams))
            share = min(0.95, 0.5 + 0.45 * gpt / 19)
            k = (1 - share) / share * cur / old
            w = [wi if m["date"] >= cur_start else wi * k for wi, m in zip(w, self.matches)]
        sw = sum(w)
        self.base = sum(wi * (m["hg"] + m["ag"]) for wi, m in zip(w, self.matches)) / (2 * sw)
        hg = sum(wi * m["hg"] for wi, m in zip(w, self.matches))
        ag = sum(wi * m["ag"] for wi, m in zip(w, self.matches))
        self.home_adv = math.sqrt(max(hg, 1e-9) / max(ag, 1e-9))
        for _ in range(iters):
            num_a, den_a = defaultdict(float), defaultdict(float)
            for wi, m in zip(w, self.matches):
                h, a = m["home"], m["away"]
                num_a[h] += wi * m["hg"]
                den_a[h] += wi * self.base * self.home_adv * self.dfn[a]
                num_a[a] += wi * m["ag"]
                den_a[a] += wi * self.base / self.home_adv * self.dfn[h]
            for t in self.teams:
                self.att[t] = (num_a[t] + 1.0) / (den_a[t] + 1.0)  # +1 shrinks towards average
            num_d, den_d = defaultdict(float), defaultdict(float)
            for wi, m in zip(w, self.matches):
                h, a = m["home"], m["away"]
                num_d[a] += wi * m["hg"]
                den_d[a] += wi * self.base * self.home_adv * self.att[h]
                num_d[h] += wi * m["ag"]
                den_d[h] += wi * self.base / self.home_adv * self.att[a]
            for t in self.teams:
                self.dfn[t] = (num_d[t] + 1.0) / (den_d[t] + 1.0)
            ma = sum(self.att.values()) / len(self.att)
            md = sum(self.dfn.values()) / len(self.dfn)
            for t in self.teams:
                self.att[t] /= ma
                self.dfn[t] /= md

    def can_predict(self, h: str, a: str) -> bool:
        return (self.fitted and self.count.get(h, 0) >= MIN_MATCHES_TEAM
                and self.count.get(a, 0) >= MIN_MATCHES_TEAM)

    def expected_goals(self, h: str, a: str) -> tuple[float, float]:
        lh = self.base * self.home_adv * self.att[h] * self.dfn[a]
        la = self.base / self.home_adv * self.att[a] * self.dfn[h]
        return lh, la

    def score_matrix(self, h: str, a: str) -> tuple[list[list[float]], float, float]:
        lh, la = self.expected_goals(h, a)
        ph = [pois(i, lh) for i in range(MAX_GOALS + 1)]
        pa = [pois(j, la) for j in range(MAX_GOALS + 1)]
        M = [[ph[i] * pa[j] for j in range(MAX_GOALS + 1)] for i in range(MAX_GOALS + 1)]
        # Dixon-Coles adjustment for 0-0, 1-0, 0-1, 1-1
        M[0][0] *= max(0.0, 1 - lh * la * RHO)
        M[0][1] *= max(0.0, 1 + lh * RHO)
        M[1][0] *= max(0.0, 1 + la * RHO)
        M[1][1] *= max(0.0, 1 - RHO)
        s = sum(map(sum, M))
        M = [[x / s for x in row] for row in M]
        return M, lh, la


def markets(M: list[list[float]]) -> dict[str, float]:
    n = len(M)
    p = defaultdict(float)
    for i in range(n):
        for j in range(n):
            x = M[i][j]
            if i > j:
                p["1"] += x
            elif i == j:
                p["X"] += x
            else:
                p["2"] += x
            t = i + j
            if t > 1.5: p["O1.5"] += x
            if t > 2.5: p["O2.5"] += x
            if t > 3.5: p["O3.5"] += x
            if i > 0 and j > 0: p["BTTS"] += x
            if i > 0: p["H_SCORES"] += x
            if j > 0: p["A_SCORES"] += x
    p["1X"] = p["1"] + p["X"]
    p["X2"] = p["X"] + p["2"]
    p["12"] = p["1"] + p["2"]
    p["U1.5"] = 1 - p["O1.5"]
    p["U2.5"] = 1 - p["O2.5"]
    p["U3.5"] = 1 - p["O3.5"]
    p["NO_BTTS"] = 1 - p["BTTS"]
    return {k: round(v, 4) for k, v in p.items()}


# Markets eligible to be "the tip". Order = tie-break preference.
TIP_MARKETS = ["1", "2", "X", "O2.5", "U2.5", "BTTS", "NO_BTTS", "1X", "X2", "O1.5"]
ODDS_KEY = {"1": "H", "X": "D", "2": "A", "O2.5": "O25", "U2.5": "U25"}
# A tip has to beat these probabilities to be worth publishing.
TIP_FLOOR = {"1": 0.55, "2": 0.50, "X": 0.34, "O2.5": 0.62, "U2.5": 0.62, "BTTS": 0.62,
             "NO_BTTS": 0.62, "1X": 0.78, "X2": 0.76, "O1.5": 0.82}


# "Safe" low-odds markets only win the tip when nothing more useful is strong enough.
TIP_WEIGHT = {"1X": 0.55, "X2": 0.55, "O1.5": 0.55}


def choose_tip(p: dict[str, float], odds: dict) -> dict:
    best, best_score = None, -1e9
    for mk in TIP_MARKETS:
        prob = p[mk]
        if prob < TIP_FLOOR[mk]:
            continue
        # prefer informative tips: reward probability above floor, penalise "safe" low-odds markets
        score = (prob - TIP_FLOOR[mk]) / (1 - TIP_FLOOR[mk])
        score *= TIP_WEIGHT.get(mk, 1.0)
        o = odds.get(ODDS_KEY.get(mk, ""), None)
        if o:
            score += max(0.0, prob * o - 1) * 2
        if score > best_score:
            best, best_score = mk, score
    if best is None:  # nothing strong: fall back to the double chance with the best probability
        best = max(["1X", "X2", "12"], key=lambda k: p[k])
    prob = p[best]
    o = odds.get(ODDS_KEY.get(best, ""), None)
    edge = round(prob * o - 1, 4) if o else None
    conf = "high" if prob >= 0.72 else "medium" if prob >= 0.58 else "low"
    return {"market": best, "prob": prob, "fair_odds": round(1 / max(prob, 1e-6), 2),
            "book_odds": o, "edge": edge, "value": bool(edge is not None and edge > 0.04),
            "confidence": conf}


def team_form(matches: list[dict], team: str, before: dt.date, n: int = 5) -> list[str]:
    out = []
    for m in sorted((m for m in matches if m["date"] < before and team in (m["home"], m["away"])),
                    key=lambda m: m["date"], reverse=True)[:n]:
        gf, ga = (m["hg"], m["ag"]) if m["home"] == team else (m["ag"], m["hg"])
        out.append("W" if gf > ga else "D" if gf == ga else "L")
    return out


def team_stats(matches: list[dict], team: str, before: dt.date, n: int = 10) -> dict:
    ms = sorted((m for m in matches if m["date"] < before and team in (m["home"], m["away"])),
                key=lambda m: m["date"], reverse=True)[:n]
    if not ms:
        return {}
    gf = ga = btts = o25 = cs = 0
    for m in ms:
        f, a = (m["hg"], m["ag"]) if m["home"] == team else (m["ag"], m["hg"])
        gf += f; ga += a
        btts += f > 0 and a > 0
        o25 += f + a > 2
        cs += a == 0
    k = len(ms)
    return {"games": k, "gf": round(gf / k, 2), "ga": round(ga / k, 2),
            "btts": round(btts / k, 2), "o25": round(o25 / k, 2), "cs": round(cs / k, 2)}


def head_to_head(matches: list[dict], h: str, a: str, before: dt.date, n: int = 5) -> list[dict]:
    ms = sorted((m for m in matches if m["date"] < before and {m["home"], m["away"]} == {h, a}),
                key=lambda m: m["date"], reverse=True)[:n]
    return [{"date": m["date"].isoformat(), "home": m["home"], "away": m["away"],
             "score": f'{m["hg"]}-{m["ag"]}'} for m in ms]


def standings(matches: list[dict], season_start: dt.date, before: dt.date) -> list[dict]:
    t = defaultdict(lambda: {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
    for m in matches:
        if not (season_start <= m["date"] < before):
            continue
        for team, f, a in ((m["home"], m["hg"], m["ag"]), (m["away"], m["ag"], m["hg"])):
            r = t[team]
            r["p"] += 1; r["gf"] += f; r["ga"] += a
            if f > a: r["w"] += 1; r["pts"] += 3
            elif f == a: r["d"] += 1; r["pts"] += 1
            else: r["l"] += 1
    rows = [{"team": k, **v, "gd": v["gf"] - v["ga"]} for k, v in t.items()]
    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    return rows


# --------------------------------------------------------------------------- #
# Predictions, coupons, settlement
# --------------------------------------------------------------------------- #
def match_id(league: str, d: dt.date | str, h: str, a: str) -> str:
    ds = d if isinstance(d, str) else d.isoformat()
    return f"{league}|{ds}|{h}|{a}"


def predict_fixtures(results: dict[str, list[dict]], fixtures: list[dict], today: dt.date) -> list[dict]:
    models = {code: LeagueModel(ms, today) for code, ms in results.items() if ms}
    out = []
    for f in fixtures:
        if not (today <= f["date"] <= today + dt.timedelta(days=FIXTURE_WINDOW_DAYS)):
            continue
        code = f["league"]
        model = models.get(code)
        if not model or not model.can_predict(f["home"], f["away"]):
            continue
        M, lh, la = model.score_matrix(f["home"], f["away"])
        p = markets(M)
        scores = sorted(((M[i][j], f"{i}-{j}") for i in range(6) for j in range(6)), reverse=True)[:5]
        ms = results[code]
        country, name = LEAGUES.get(code, ("", code))
        out.append({
            "id": match_id(code, f["date"], f["home"], f["away"]),
            "sport": "soccer", "league": code, "result": f.get("result"), "country": country, "league_name": name,
            "date": f["date"].isoformat(), "time": f.get("time", ""),
            "home": f["home"], "away": f["away"],
            "xg": [round(lh, 2), round(la, 2)],
            "probs": p,
            "correct_scores": [{"score": s, "prob": round(pr, 4)} for pr, s in scores],
            "odds": f.get("odds", {}),
            "tip": choose_tip(p, f.get("odds", {})),
            "form": {"home": team_form(ms, f["home"], today), "away": team_form(ms, f["away"], today)},
            "stats": {"home": team_stats(ms, f["home"], today), "away": team_stats(ms, f["away"], today)},
            "h2h": head_to_head(ms, f["home"], f["away"], today),
            "strength": {"home_att": round(model.att[f["home"]], 2), "home_def": round(model.dfn[f["home"]], 2),
                         "away_att": round(model.att[f["away"]], 2), "away_def": round(model.dfn[f["away"]], 2)},
        })
    out.sort(key=lambda m: (m["date"], m["time"] or "99:99", m["league"]))
    return out


SAFE_COUPONS = 5
SAFE_MIN = 0.75
SAFE_SOCCER_MARKETS = ["1X", "X2", "12", "O1.5", "U3.5", "1", "2"]


def safe_pick(m: dict, sport: str) -> dict | None:
    """The single most likely market of a match (a 'banker' leg), if it is at least SAFE_MIN."""
    if m.get("result"):
        return None  # already played
    if sport == "soccer":
        mk_, p = max(((k, m["probs"][k]) for k in SAFE_SOCCER_MARKETS), key=lambda kv: kv[1])
        line = None
    else:
        best = max(m["markets"], key=lambda x: x["prob"])
        mk_, p, line = best["code"], best["prob"], best.get("line")
    if p < SAFE_MIN:
        return None
    t = m["tip"]
    book = t["book_odds"] if t["market"] == mk_ else None
    return {"id": m["id"], "league": m["league"], "league_name": m["league_name"], "country": m["country"],
            "date": m["date"], "time": m["time"], "home": m["home"], "away": m["away"], "sport": sport,
            "market": mk_, "line": line, "prob": round(p, 4), "odds": book or round(1 / p, 2)}


def build_coupons(preds: list[dict], today: dt.date, sport: str = "soccer") -> list[dict]:
    coupons = []
    for day_offset in range(2):
        day = (today + dt.timedelta(days=day_offset)).isoformat()
        todays = [m for m in preds if m["date"] == day]
        if not todays:
            continue

        def pick(m: dict) -> dict:
            t = m["tip"]
            return {"id": m["id"], "league": m["league"], "league_name": m["league_name"], "country": m["country"],
                    "date": m["date"], "time": m["time"], "home": m["home"], "away": m["away"],
                    "sport": sport, "market": t["market"], "line": t.get("line"), "prob": t["prob"],
                    "odds": t["book_odds"] or t["fair_odds"]}

        def mk(kind: str, picks: list[dict]) -> dict | None:
            if len(picks) < 2:
                return None
            prob = math.prod(p["prob"] for p in picks)
            odds = math.prod(p["odds"] for p in picks)
            return {"id": f"{day}|{sport}|{kind}", "sport": sport, "date": day, "kind": kind, "picks": picks,
                    "total_odds": round(odds, 2), "prob": round(prob, 4)}

        # Safe coupons: up to SAFE_COUPONS different 3-leg coupons (no match repeated), each leg on the
        # match's safest market (>= 75%), best legs first.
        legs = sorted((sp for m in todays if (sp := safe_pick(m, sport))), key=lambda p: -p["prob"])
        n_safe = min(SAFE_COUPONS, len(legs) // 3)
        for i in range(n_safe):
            c = mk("safe" if i == 0 else f"safe{i + 1}", legs[i * 3:(i + 1) * 3])
            if c:
                c["kind"], c["n"] = "safe", i + 1
                coupons.append(c)
        value = sorted((m for m in todays if m["tip"]["value"]), key=lambda m: -(m["tip"]["edge"] or 0))[:4]
        big = sorted((m for m in todays if m["tip"]["prob"] >= 0.55), key=lambda m: -m["tip"]["prob"])[:8]
        for kind, ms in (("value", value), ("mega", big)):
            c = mk(kind, [pick(m) for m in ms])
            if c:
                coupons.append(c)
    return coupons


def tip_won(market: str, hg: int, ag: int, line: float | None = None) -> bool:
    t = hg + ag
    if market in ("ML_H", "ML_A", "SP_H", "SP_A", "OV", "UN"):
        return {"ML_H": hg > ag, "ML_A": ag > hg,
                "SP_H": line is not None and hg + line > ag, "SP_A": line is not None and ag + line > hg,
                "OV": line is not None and t > line, "UN": line is not None and t < line}[market]
    return {
        "1": hg > ag, "X": hg == ag, "2": hg < ag,
        "1X": hg >= ag, "X2": hg <= ag, "12": hg != ag,
        "O1.5": t > 1.5, "O2.5": t > 2.5, "O3.5": t > 3.5,
        "U1.5": t < 1.5, "U2.5": t < 2.5, "U3.5": t < 3.5,
        "BTTS": hg > 0 and ag > 0, "NO_BTTS": not (hg > 0 and ag > 0),
    }[market]


def soccer_finished(results: dict[str, list[dict]]) -> dict:
    return {match_id(code, m["date"], m["home"], m["away"]): (m["hg"], m["ag"])
            for code, ms in results.items() for m in ms}


def settle_history(history: dict, finished: dict, preds: list[dict], coupons: list[dict]) -> dict:
    """history = {"tips": {id: {...}}, "coupons": {id: {...}}} — append new, settle finished."""
    tips, cps = history.setdefault("tips", {}), history.setdefault("coupons", {})
    for m in preds:
        if m["id"] not in tips or tips[m["id"]]["status"] == "pending":
            t = m["tip"]
            tips[m["id"]] = {"id": m["id"], "sport": m.get("sport", "soccer"), "line": t.get("line"),
                             "league": m["league"], "league_name": m["league_name"],
                             "date": m["date"], "home": m["home"], "away": m["away"],
                             "market": t["market"], "prob": t["prob"], "odds": t["book_odds"] or t["fair_odds"],
                             "status": "pending", "score": None}
    for c in coupons:
        if c["id"] not in cps or cps[c["id"]]["status"] == "pending":
            cps[c["id"]] = {**c, "status": "pending"}

    for t in tips.values():
        if t["status"] == "pending" and t["id"] in finished:
            hg, ag = finished[t["id"]]
            t["score"] = f"{hg}-{ag}"
            t["status"] = "won" if tip_won(t["market"], hg, ag, t.get("line")) else "lost"
    for c in cps.values():
        if c["status"] != "pending":
            continue
        states = []
        for p in c["picks"]:
            if p["id"] in finished:
                hg, ag = finished[p["id"]]
                p["score"] = f"{hg}-{ag}"
                p["status"] = "won" if tip_won(p["market"], hg, ag, p.get("line")) else "lost"
            states.append(p.get("status", "pending"))
        if "lost" in states:
            c["status"] = "lost"
        elif all(s == "won" for s in states):
            c["status"] = "won"
    return history


def summarize_history(history: dict, today: dt.date) -> dict:
    tips = [t for t in history.get("tips", {}).values() if t["status"] != "pending"]
    def agg(ts):
        n = len(ts); w = sum(t["status"] == "won" for t in ts)
        profit = sum((t["odds"] - 1) if t["status"] == "won" else -1 for t in ts)
        return {"n": n, "won": w, "rate": round(w / n, 4) if n else None,
                "roi": round(profit / n, 4) if n else None}
    by_market = defaultdict(list)
    for t in tips:
        by_market[t["market"]].append(t)
    last30 = [t for t in tips if (today - dt.date.fromisoformat(t["date"])).days <= 30]
    cps = [c for c in history.get("coupons", {}).values() if c["status"] != "pending"]
    by_sport = defaultdict(list)
    for t in tips:
        by_sport[t.get("sport", "soccer")].append(t)
    return {"overall": agg(tips), "last30": agg(last30), "by_sport": {k: agg(v) for k, v in by_sport.items()},
            "by_market": {k: agg(v) for k, v in sorted(by_market.items())},
            "coupons": {"n": len(cps), "won": sum(c["status"] == "won" for c in cps)}}


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #
def backtest(results: dict[str, list[dict]], today: dt.date) -> dict:
    """Walk-forward: refit every 14 days on data before that point, predict the next 14 days."""
    per_league, tot = {}, {"n": 0, "correct_1x2": 0, "brier": 0.0, "tips": 0, "tips_won": 0, "logloss": 0.0}
    for code, ms in results.items():
        ms = sorted(ms, key=lambda m: m["date"])
        if len(ms) < 400:
            continue
        test_start = ms[len(ms) * 2 // 3]["date"]
        n = c = tw = tn = 0
        brier = ll = 0.0
        d = test_start
        while d <= ms[-1]["date"]:
            model = LeagueModel(ms, d)
            window = [m for m in ms if d <= m["date"] < d + dt.timedelta(days=14)]
            for m in window:
                if not model.can_predict(m["home"], m["away"]):
                    continue
                M, _, _ = model.score_matrix(m["home"], m["away"])
                p = markets(M)
                actual = "1" if m["hg"] > m["ag"] else "X" if m["hg"] == m["ag"] else "2"
                pred = max(("1", "X", "2"), key=lambda k: p[k])
                n += 1; c += pred == actual
                brier += sum((p[k] - (k == actual)) ** 2 for k in ("1", "X", "2"))
                ll += -math.log(max(p[actual], 1e-9))
                tip = choose_tip(p, m.get("odds", {}))
                tn += 1; tw += tip_won(tip["market"], m["hg"], m["ag"])
            d += dt.timedelta(days=14)
        if n:
            per_league[code] = {"league_name": LEAGUES.get(code, ("", code))[1], "matches": n,
                                "acc_1x2": round(c / n, 4), "brier": round(brier / n, 4),
                                "tip_rate": round(tw / tn, 4) if tn else None}
            tot["n"] += n; tot["correct_1x2"] += c; tot["brier"] += brier; tot["logloss"] += ll
            tot["tips"] += tn; tot["tips_won"] += tw
    N = tot["n"] or 1
    return {"generated": today.isoformat(), "matches": tot["n"],
            "acc_1x2": round(tot["correct_1x2"] / N, 4), "brier": round(tot["brier"] / N, 4),
            "logloss": round(tot["logloss"] / N, 4),
            "tip_rate": round(tot["tips_won"] / (tot["tips"] or 1), 4), "leagues": per_league}


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use offline synthetic data")
    ap.add_argument("--no-backtest", action="store_true")
    ap.add_argument("--date", help="override today (YYYY-MM-DD)")
    args = ap.parse_args()

    # "today" follows US Eastern time so an evening NBA/NHL slate stays on the site until the night is over
    from zoneinfo import ZoneInfo
    today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(ZoneInfo("America/New_York")).date()
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"ProScore engine — {today} — {'DEMO' if args.demo else 'LIVE'} data")

    results, fixtures = (load_demo if args.demo else load_live)(today)
    n_res = sum(len(v) for v in results.values())
    print(f"  {n_res} historical results, {len(fixtures)} fixtures")
    if n_res == 0:
        sys.exit("No data downloaded — aborting so the previous site data is kept.")

    if not args.demo:  # faster results (about a day after the match) so recent tips can be settled
        import fd_results
        n_af = fd_results.merge(results, fixtures, fd_results.fetch_api_football(today))
        print(f"  API-Football: {n_af} recent results added")
        n_fd = fd_results.merge(results, fixtures, fd_results.fetch(today))  # backup source
        print(f"  football-data.org: {n_fd} recent results added")
    # attach final scores to fixtures that have been played (fixtures.csv can still list them)
    finals = {match_id(c, m["date"], m["home"], m["away"]): (m["hg"], m["ag"]) for c, ms in results.items() for m in ms}
    for f in fixtures:
        r = finals.get(match_id(f["league"], f["date"], f["home"], f["away"]))
        if r:
            f["result"] = list(r)
    # keep today's already-played matches on the site, with their final score
    known = {match_id(f["league"], f["date"], f["home"], f["away"]) for f in fixtures}
    for code, ms in results.items():
        for m in ms:
            if m["date"] == today and match_id(code, m["date"], m["home"], m["away"]) not in known:
                fixtures.append({**{k: v for k, v in m.items() if k not in ("hg", "ag")}, "result": [m["hg"], m["ag"]]})
    preds = predict_fixtures(results, fixtures, today)
    coupons = build_coupons(preds, today, "soccer")
    print(f"  soccer: {len(preds)} predictions, {len(coupons)} coupons")
    finished = soccer_finished(results)
    sport_counts = {"soccer": n_res}
    extra_recent, sport_bt = [], {}
    if not args.demo:
        import other_sports as osp
        # Tennis is off until a data source that allows automated access is set up.
        jobs = [("basketball", lambda: osp.run_team_sport("nba", today, CACHE_DIR)),
                ("hockey", lambda: osp.run_team_sport("nhl", today, CACHE_DIR))]
        if os.environ.get("ENABLE_TENNIS"):
            jobs.append(("tennis", lambda: osp.run_tennis(today, CACHE_DIR)))
        for sport, job in jobs:
            try:
                sp_preds, sp_fin, sp_recent, sp_n, sp_bt = job()
            except Exception as e:  # noqa: BLE001  one sport failing must not kill the others
                print(f"  ! {sport} failed: {e}", file=sys.stderr)
                continue
            sp_coupons = build_coupons(sp_preds, today, sport)
            print(f"  {sport}: {sp_n} results, {len(sp_preds)} predictions, {len(sp_coupons)} coupons, backtest {sp_bt}")
            preds += sp_preds; coupons += sp_coupons; finished.update(sp_fin)
            extra_recent += sp_recent; sport_counts[sport] = sp_n; sport_bt[sport] = sp_bt

    hist_path = os.path.join(DATA_DIR, "history.json")
    history = {}
    if os.path.exists(hist_path) and not args.demo:
        with open(hist_path, encoding="utf-8") as fh:
            history = json.load(fh)
        if history.get("demo"):  # never mix synthetic tips into the real track record
            history = {}
    if args.demo:  # replay the last 4 weeks so the track record isn't empty
        played_days = sorted({m["date"] for ms in results.values() for m in ms
                              if 0 < (today - m["date"]).days <= 28})
        for d in played_days:
            past_fx = [{k: v for k, v in m.items() if k not in ("hg", "ag")}
                       for ms in results.values() for m in ms if m["date"] == d]
            past_preds = predict_fixtures(results, past_fx, d)
            history = settle_history(history, soccer_finished(results), past_preds, build_coupons(past_preds, d))
    history = settle_history(history, finished, preds, coupons)
    history["demo"] = args.demo

    season_start = dt.date(today.year if today.month >= 7 else today.year - 1, 7, 1)
    tables = {code: {"league_name": LEAGUES.get(code, ("", code))[1], "country": LEAGUES.get(code, ("", ""))[0],
                     "rows": standings(ms, season_start, today)} for code, ms in results.items() if ms}
    recent = []
    for code, ms in results.items():
        for m in ms:
            if (today - m["date"]).days <= 7:
                recent.append({"league": code, "sport": "soccer", "league_name": LEAGUES.get(code, ("", code))[1],
                               "date": m["date"].isoformat(), "home": m["home"], "away": m["away"],
                               "score": f'{m["hg"]}-{m["ag"]}'})
    recent += extra_recent
    recent.sort(key=lambda r: r["date"], reverse=True)

    meta = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "date": today.isoformat(), "demo": args.demo, "matches_analysed": sum(sport_counts.values()),
            "sports": sport_counts,
            "leagues": {c: {"country": LEAGUES[c][0], "name": LEAGUES[c][1]} for c in results if c in LEAGUES},
            "record": summarize_history(history, today)}

    def dump(name: str, obj) -> None:
        with open(os.path.join(DATA_DIR, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))

    dump("predictions.json", {"meta": meta, "matches": preds, "coupons": coupons})
    dump("history.json", history)
    dump("tables.json", tables)
    dump("results.json", recent[:200])

    if not args.no_backtest:
        print("  running walk-forward backtest…")
        bt = backtest(results, today)
        bt["sports"] = sport_bt
        dump("backtest.json", bt)
        print(f"  backtest: {bt['matches']} matches, 1X2 accuracy {bt['acc_1x2']:.1%}, tip hit-rate {bt['tip_rate']:.1%}")
    print("done.")


if __name__ == "__main__":
    main()
