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
    return " ".join(words)


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
