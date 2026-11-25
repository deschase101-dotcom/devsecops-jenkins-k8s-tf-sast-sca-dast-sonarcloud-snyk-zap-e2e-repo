"""
Faster football results from football-data.org (free plan: results arrive about a day after the match).

football-data.co.uk (our main history source) only publishes new results every few days, so recent
tips would stay "pending". This module pulls the last few days of FINISHED matches from football-data.org
and maps them onto our team names (league + date + name similarity), so they can be settled and shown.

Needs a token: env FOOTBALL_DATA_TOKEN (GitHub secret). Without it, the module does nothing.
"""
from __future__ import annotations

import datetime as dt
import difflib
import json
import os
import re
import sys
import unicodedata
import urllib.request

API = "https://api.football-data.org/v4/matches?dateFrom={a}&dateTo={b}&status=FINISHED"
CODE_MAP = {"PL": "E0", "ELC": "E1", "PD": "SP1", "SA": "I1", "BL1": "D1", "FL1": "F1", "DED": "N1", "PPL": "P1"}
STOP = {"fc", "cf", "ac", "afc", "sc", "sv", "as", "ss", "us", "rc", "cd", "ud", "sd", "rcd", "club", "de", "the",
        "1", "real", "calcio", "football", "ssc", "acf", "es", "ogc", "losc", "stade", "vfl", "vfb", "tsg", "fsv"}


def _norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = s.replace("münchen", "munich").replace("munchen", "munich").replace("koln", "koln")
    words = [w for w in re.split(r"[^a-z0-9]+", s) if w and w not in STOP]
    out = " ".join(words)
    for k, v in ALIASES.items():
        if out == k:
            return v
    return out


# football-data.co.uk short names -> names used by the APIs (after normalisation)
ALIASES = {"ath bilbao": "athletic", "athletic club": "athletic", "ath madrid": "atletico madrid",
           "espanol": "espanyol", "espanyol barcelona": "espanyol", "sociedad": "real sociedad", "betis": "real betis",
           "man united": "manchester united", "man city": "manchester city", "nott m forest": "nottingham forest",
           "sheffield weds": "sheffield wednesday", "qpr": "queens park rangers", "wolves": "wolverhampton",
           "paris sg": "paris saint germain", "psg": "paris saint germain", "inter": "inter milan", "milan": "ac milan",
           "dortmund": "borussia dortmund", "m gladbach": "borussia monchengladbach", "ein frankfurt": "eintracht frankfurt",
           "leverkusen": "bayer leverkusen", "sp lisbon": "sporting cp", "sporting": "sporting cp"}


def _sim(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return 0.95
    return difflib.SequenceMatcher(None, na, nb).ratio()


def fetch(today: dt.date, days: int = 5) -> list[dict]:
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        print("  football-data.org: no FOOTBALL_DATA_TOKEN set, skipping fast results")
        return []
    url = API.format(a=(today - dt.timedelta(days=days)).isoformat(), b=(today + dt.timedelta(days=1)).isoformat())
    try:
        req = urllib.request.Request(url, headers={"X-Auth-Token": token, "User-Agent": "ProScore/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  ! football-data.org: {e}", file=sys.stderr)
        return []
    out = []
    for m in data.get("matches", []):
        code = CODE_MAP.get((m.get("competition") or {}).get("code"))
        ft = (m.get("score") or {}).get("fullTime") or {}
        if not code or ft.get("home") is None or ft.get("away") is None:
            continue
        h, a = m["homeTeam"], m["awayTeam"]
        out.append({"league": code, "utc": m["utcDate"],
                    "home_names": [h.get("shortName") or "", h.get("name") or "", h.get("tla") or ""],
                    "away_names": [a.get("shortName") or "", a.get("name") or "", a.get("tla") or ""],
                    "hg": int(ft["home"]), "ag": int(ft["away"])})
    return out


def merge(results: dict[str, list[dict]], fixtures: list[dict], fd: list[dict]) -> int:
    """Add football-data.org finals to `results` (our team names), matching against our fixtures/teams."""
    added = 0
    for x in fd:
        code = x["league"]
        day = dt.date.fromisoformat(x["utc"][:10])
        # candidates: our fixtures of that league within a day of the match, or any pair of known teams
        cands = [f for f in fixtures if f["league"] == code and abs((f["date"] - day).days) <= 1]
        teams = sorted({m["home"] for m in results.get(code, [])} | {m["away"] for m in results.get(code, [])})
        best, score = None, 0.0
        for f in cands:
            s = min(max(_sim(f["home"], n) for n in x["home_names"]), max(_sim(f["away"], n) for n in x["away_names"]))
            if s > score:
                best, score = (f["home"], f["away"], f["date"]), s
        if score < 0.6 and teams:  # no fixture listed: map each side to the closest known team
            th = max(teams, key=lambda t: max(_sim(t, n) for n in x["home_names"]))
            ta = max(teams, key=lambda t: max(_sim(t, n) for n in x["away_names"]))
            s = min(max(_sim(th, n) for n in x["home_names"]), max(_sim(ta, n) for n in x["away_names"]))
            if s > score and th != ta:
                best, score = (th, ta, day), s
        if not best or score < 0.6:
            continue
        home, away, d = best
        if any(m["home"] == home and m["away"] == away and abs((m["date"] - d).days) <= 1 for m in results.get(code, [])):
            continue
        results.setdefault(code, []).append({"league": code, "date": d, "time": "", "home": home, "away": away,
                                             "hg": x["hg"], "ag": x["ag"], "odds": {}, "source": "football-data.org"})
        added += 1
    return added


UPCOMING_API = "https://api.football-data.org/v4/matches?dateFrom={a}&dateTo={b}"


def fetch_upcoming(today: dt.date, days: int = 7) -> list[dict]:
    """Scheduled league matches for the next days (football-data.co.uk posts weekend fixtures late in the week)."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        return []
    url = UPCOMING_API.format(a=today.isoformat(), b=(today + dt.timedelta(days=min(days, 9))).isoformat())
    try:
        req = urllib.request.Request(url, headers={"X-Auth-Token": token, "User-Agent": "ProScore/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  ! football-data.org fixtures: {e}", file=sys.stderr)
        return []
    out = []
    for m in data.get("matches", []):
        code = CODE_MAP.get((m.get("competition") or {}).get("code"))
        if not code or m.get("status") not in ("SCHEDULED", "TIMED"):
            continue
        h, a = m["homeTeam"], m["awayTeam"]
        out.append({"league": code, "utc": m["utcDate"],
                    "home_names": [h.get("shortName") or "", h.get("name") or "", h.get("tla") or ""],
                    "away_names": [a.get("shortName") or "", a.get("name") or "", a.get("tla") or ""]})
    return out


def add_fixtures(results: dict[str, list[dict]], fixtures: list[dict], upcoming: list[dict]) -> int:
    """Add scheduled matches that our fixture list doesn't have yet, using our own team names."""
    added = 0
    for x in upcoming:
        code = x["league"]
        teams = sorted({m["home"] for m in results.get(code, [])} | {m["away"] for m in results.get(code, [])})
        if not teams:
            continue
        th = max(teams, key=lambda t: max(_sim(t, n) for n in x["home_names"] if n))
        ta = max(teams, key=lambda t: max(_sim(t, n) for n in x["away_names"] if n))
        s = min(max(_sim(th, n) for n in x["home_names"] if n), max(_sim(ta, n) for n in x["away_names"] if n))
        if s < 0.6 or th == ta:
            continue
        day = dt.date.fromisoformat(x["utc"][:10])
        if any(f["league"] == code and f["home"] == th and f["away"] == ta and abs((f["date"] - day).days) <= 1
               for f in fixtures):
            continue
        fixtures.append({"league": code, "date": day, "time": x["utc"][11:16], "home": th, "away": ta,
                         "odds": {}, "source": "football-data.org"})
        added += 1
    return added


# --------------------------------------------------------------------------- API-Football (api-sports.io)
AF_API = "https://v3.football.api-sports.io/fixtures?date={d}"
AF_MAP = {("England", "Premier League"): "E0", ("England", "Championship"): "E1", ("Spain", "La Liga"): "SP1",
          ("Italy", "Serie A"): "I1", ("Germany", "Bundesliga"): "D1", ("France", "Ligue 1"): "F1",
          ("Netherlands", "Eredivisie"): "N1", ("Portugal", "Primeira Liga"): "P1",
          ("Belgium", "Jupiler Pro League"): "B1", ("Turkey", "Süper Lig"): "T1", ("Scotland", "Premiership"): "SC0"}
FINAL = {"FT", "AET", "PEN"}


def fetch_api_football(today: dt.date, days: int = 2) -> list[dict]:  # noqa: ARG001
    """Same-night results for every league we cover (1 request per day; free plan = 100 requests/day)."""
    key = os.environ.get("APISPORTS_KEY")
    if not key:
        print("  API-Football: no APISPORTS_KEY set, skipping")
        return []
    out = []
    # free plan only serves yesterday..tomorrow (UTC), so ask for UTC-today and UTC-yesterday
    utc_today = dt.datetime.now(dt.timezone.utc).date()
    for i in range(days):
        d = utc_today - dt.timedelta(days=i)
        try:
            req = urllib.request.Request(AF_API.format(d=d.isoformat()), headers={"x-apisports-key": key})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  ! API-Football {d}: {e}", file=sys.stderr)
            continue
        if data.get("errors"):
            print(f"  ! API-Football {d}: {data['errors']}", file=sys.stderr)
            continue
        for f in data.get("response", []):
            lg = f.get("league") or {}
            code = AF_MAP.get((lg.get("country"), lg.get("name")))
            g = f.get("goals") or {}
            if not code or (f.get("fixture") or {}).get("status", {}).get("short") not in FINAL or g.get("home") is None:
                continue
            out.append({"league": code, "utc": f["fixture"]["date"][:19],
                        "home_names": [f["teams"]["home"]["name"]], "away_names": [f["teams"]["away"]["name"]],
                        "hg": int(g["home"]), "ag": int(g["away"])})
    return out
