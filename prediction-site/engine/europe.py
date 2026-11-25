"""
European cup predictions (UEFA Champions League) for ProScore.

Data: football-data.org (free plan includes the Champions League; needs FOOTBALL_DATA_TOKEN).

Clubs are rated inside their own domestic league (the same time-weighted model as the league predictions),
then put on one European scale with a *league strength factor*:
    attack_eu  = league_base * attack * f_league
    defence_eu = defence / f_league
The factors start from a prior (roughly UEFA association strength) and are re-fitted every run on this
season's finished Champions League matches, so they follow how leagues actually perform in Europe.
Clubs from leagues ProScore does not follow get an average rating times their country's factor and are
flagged "low confidence".
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import urllib.request

API = "https://api.football-data.org/v4/competitions/{c}/{what}"
COMPETITIONS = {"CL": "Champions League"}

# country -> our league code
LEAGUE_OF = {"England": "E0", "Spain": "SP1", "Italy": "I1", "Germany": "D1", "France": "F1", "Netherlands": "N1",
             "Portugal": "P1", "Belgium": "B1", "Turkey": "T1", "Scotland": "SC0"}
# prior strength factors (1.00 = strongest league); re-fitted on this season's European results
PRIOR = {"England": 1.00, "Spain": 0.97, "Italy": 0.94, "Germany": 0.94, "France": 0.89, "Portugal": 0.85,
         "Netherlands": 0.84, "Belgium": 0.81, "Turkey": 0.79, "Scotland": 0.76, "Austria": 0.78,
         "Czech Republic": 0.78, "Norway": 0.76, "Denmark": 0.76, "Switzerland": 0.75, "Greece": 0.76,
         "Ukraine": 0.74, "Croatia": 0.72, "Serbia": 0.72, "Poland": 0.73, "Israel": 0.70, "Cyprus": 0.70,
         "Slovakia": 0.70, "Azerbaijan": 0.68, "Hungary": 0.70, "Sweden": 0.72, "Romania": 0.70}
DEFAULT_FACTOR = 0.68
HOME_ADV = 1.18     # smaller than in domestic leagues
RHO = -0.08


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _matrix(lh: float, la: float, n: int = 11) -> list[list[float]]:
    M = [[_pois(i, lh) * _pois(j, la) for j in range(n)] for i in range(n)]
    M[0][0] *= max(0.0, 1 - lh * la * RHO)
    M[0][1] *= max(0.0, 1 + lh * RHO)
    M[1][0] *= max(0.0, 1 + la * RHO)
    M[1][1] *= max(0.0, 1 - RHO)
    s = sum(map(sum, M))
    return [[x / s for x in row] for row in M]


def run(results: dict, models: dict, today: dt.date, markets_fn, choose_tip_fn, sim_fn,
        match_id_fn, horizon_days: int = 7) -> tuple[list[dict], dict, dict]:
    """Returns (predictions, finished {match_id: (hg, ag)}, league_names)."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        print("  Europe: no FOOTBALL_DATA_TOKEN set, skipping Champions League")
        COMPETITIONS_RUN = {}
    else:
        COMPETITIONS_RUN = COMPETITIONS
    preds, finished, names = [], {}, {}
    top = max(PRIOR.values())
    factors = {k: v / top for k, v in PRIOR.items()}
    for code, comp_name in COMPETITIONS_RUN.items():
        try:
            teams = _get(API.format(c=code, what="teams"), token).get("teams", [])
            matches = _get(API.format(c=code, what="matches"), token).get("matches", [])
        except Exception as e:  # noqa: BLE001
            print(f"  ! Europe {code}: {e}", file=sys.stderr)
            continue
        names[code] = comp_name
        # 1) map every club to (country, our league team or None)
        club = {}
        for t in teams:
            country = (t.get("area") or {}).get("name", "")
            lg = LEAGUE_OF.get(country)
            ours = None
            if lg and lg in models and models[lg].teams:
                cands = [t.get("shortName") or "", t.get("name") or "", t.get("tla") or ""]
                best = max(models[lg].teams, key=lambda x: max(sim_fn(x, c) for c in cands if c))
                if max(sim_fn(best, c) for c in cands if c) >= 0.6:
                    ours = best
            club[t["id"]] = {"country": country, "league": lg, "team": ours,
                             "name": t.get("shortName") or t.get("name")}

        def rating(cid: int, f: dict) -> tuple[float, float, bool]:
            c = club.get(cid, {"country": "", "league": None, "team": None})
            fac = f.get(c["country"], DEFAULT_FACTOR)
            if c["team"]:
                m = models[c["league"]]
                return m.base * m.att[c["team"]] * fac, m.dfn[c["team"]] / fac, True
            return 1.30 * fac, 1.0 / fac, False  # unknown league: average club of that country

        # 2) adjust league factors on this season's finished matches, cautiously: a league moves away from its
        #    prior only in proportion to how many European games its clubs have played (one club's hot streak
        #    must not re-rate a whole league)
        f = dict(PRIOR)
        done = [m for m in matches if m.get("status") == "FINISHED"
                and (m.get("score") or {}).get("fullTime", {}).get("home") is not None]
        gf, ef, ga, ea, n = {}, {}, {}, {}, {}
        for m in done:
            hid, aid = m["homeTeam"]["id"], m["awayTeam"]["id"]
            ah, dh, _ = rating(hid, f)
            aa, da, _ = rating(aid, f)
            lh, la = ah * da * HOME_ADV, aa * dh / HOME_ADV
            hg, ag = m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]
            for cid, g_for, e_for, g_ag, e_ag in ((hid, hg, lh, ag, la), (aid, ag, la, hg, lh)):
                k = club.get(cid, {}).get("country", "")
                gf[k] = gf.get(k, 0) + g_for; ef[k] = ef.get(k, 0) + e_for
                ga[k] = ga.get(k, 0) + g_ag; ea[k] = ea.get(k, 0) + e_ag
                n[k] = n.get(k, 0) + 1
        for k in gf:
            ratio = ((gf[k] + 3) / (ef[k] + 3)) ** 0.5 * ((ea[k] + 3) / (ga[k] + 3)) ** 0.5
            w = n[k] / (n[k] + 30)  # ~30 games of evidence to move halfway
            f[k] = f.get(k, DEFAULT_FACTOR) * ratio ** (0.5 * w)
        top = max(f[k] for k in f)
        f = {k: v / top for k, v in f.items()}
        factors = f

        # 3) results (for grading) and predictions
        for m in done:
            d = dt.date.fromisoformat(m["utcDate"][:10])
            h, a = club[m["homeTeam"]["id"]]["name"], club[m["awayTeam"]["id"]]["name"]
            finished[match_id_fn(code, d, h, a)] = (m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"])
        for m in matches:
            st = m.get("status")
            if st not in ("TIMED", "SCHEDULED", "IN_PLAY", "PAUSED", "FINISHED"):
                continue
            d = dt.date.fromisoformat(m["utcDate"][:10])
            if not (today <= d <= today + dt.timedelta(days=horizon_days)):
                continue
            # today's games stay listed while live and after the final whistle (their tip is locked in history)
            ft = (m.get("score") or {}).get("fullTime") or {}
            result = [ft["home"], ft["away"]] if st == "FINISHED" and ft.get("home") is not None else None
            live = st in ("IN_PLAY", "PAUSED")
            if st == "FINISHED" and result is None:
                continue
            hid, aid = m["homeTeam"]["id"], m["awayTeam"]["id"]
            ah, dh, kh = rating(hid, f)
            aa, da, ka = rating(aid, f)
            lh, la = ah * da * HOME_ADV, aa * dh / HOME_ADV
            M = _matrix(lh, la)
            p = markets_fn(M)
            scores = sorted(((M[i][j], f"{i}-{j}") for i in range(6) for j in range(6)), reverse=True)[:5]
            h, a = club[hid]["name"], club[aid]["name"]
            tip = choose_tip_fn(p, {})
            if not (kh and ka):
                tip["confidence"] = "low"
            preds.append({
                "id": match_id_fn(code, d, h, a), "sport": "soccer", "league": code, "result": result, "live": live,
                "country": "Europe", "league_name": comp_name, "date": d.isoformat(),
                "time": m["utcDate"][11:16], "home": h, "away": a,
                "xg": [round(lh, 2), round(la, 2)], "probs": p,
                "correct_scores": [{"score": s, "prob": round(pr, 4)} for pr, s in scores], "odds": {}, "tip": tip,
                "form": {"home": [], "away": []}, "stats": {"home": {}, "away": {}}, "h2h": [],
                "strength": {"home_att": round(ah, 2), "home_def": round(dh, 2), "away_att": round(aa, 2),
                             "away_def": round(da, 2)},
                "europe": {"home_league": club[hid]["country"], "away_league": club[aid]["country"],
                           "home_factor": round(f.get(club[hid]["country"], DEFAULT_FACTOR), 3),
                           "away_factor": round(f.get(club[aid]["country"], DEFAULT_FACTOR), 3),
                           "rated_home": kh, "rated_away": ka},
            })
        print(f"  Europe {code}: {len(done)} results, {len(preds)} upcoming predicted; league factors "
              + ", ".join(f"{k} {v:.2f}" for k, v in sorted(f.items(), key=lambda kv: -kv[1])
                          if k in {c['country'] for c in club.values()}))
    try:
        p2, f2, n2 = run_af_cups(models, today, factors, markets_fn, choose_tip_fn, sim_fn, match_id_fn, horizon_days)
        preds += p2; finished.update(f2); names.update(n2)
    except Exception as e:  # noqa: BLE001
        print(f"  ! Europa/Conference League: {e}", file=sys.stderr)
    return preds, finished, names


# --------------------------------------------------------------------------- Europa / Conference League
# API-Football (APISPORTS_KEY). Free plan serves only yesterday..tomorrow, so cups appear the day before.
AF_CUPS = {3: ("EL", "Europa League"), 848: ("ECL", "Conference League")}
COUNTRY_OF = {v: k for k, v in LEAGUE_OF.items()}
LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
DONE = {"FT", "AET", "PEN"}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache", "af_team_country.json")


def run_af_cups(models, today, f, markets_fn, choose_tip_fn, sim_fn, match_id_fn, horizon_days):
    import fd_results as fr
    if not os.environ.get("APISPORTS_KEY"):
        return [], {}, {}
    utc = dt.datetime.now(dt.timezone.utc).date()
    games = []
    for d in (utc - dt.timedelta(days=1), utc, utc + dt.timedelta(days=1)):
        for x in fr.af_day(d) or []:
            if (x.get("league") or {}).get("id") in AF_CUPS:
                games.append(x)
    if not games:
        print("  Europa/Conference League: no games yesterday..tomorrow")
        return [], {}, {}
    try:
        countries = json.load(open(CACHE))
    except Exception:  # noqa: BLE001
        countries = {}
    pool = [(lg, t) for lg, m in models.items() if lg in COUNTRY_OF for t in m.teams]
    looked = 0

    def club(team: dict) -> tuple[str, str | None, str | None]:
        """(country, our league, our team) for an API team."""
        nonlocal looked
        name = team.get("name") or ""
        best = max(pool, key=lambda lt: sim_fn(lt[1], name), default=None)
        if best and sim_fn(best[1], name) >= 0.8:
            return COUNTRY_OF[best[0]], best[0], best[1]
        tid = str(team.get("id"))
        if tid not in countries and looked < 15 and (fr.AF_QUOTA["remaining"] is None or fr.AF_QUOTA["remaining"] > 30):
            looked += 1
            data = fr.af_get(f"https://v3.football.api-sports.io/teams?id={tid}")
            resp = (data or {}).get("response") or []
            if resp:
                countries[tid] = (resp[0].get("team") or {}).get("country") or ""
        return countries.get(tid, ""), None, None

    def rating(c):
        country, lg, t = c
        fac = f.get(country, DEFAULT_FACTOR)
        if t:
            m = models[lg]
            return m.base * m.att[t] * fac, m.dfn[t] / fac, True
        return 1.30 * fac, 1.0 / fac, False

    preds, finished, names = [], {}, {}
    for x in games:
        code, comp_name = AF_CUPS[x["league"]["id"]]
        names[code] = comp_name
        fx, g = x.get("fixture") or {}, x.get("goals") or {}
        st = (fx.get("status") or {}).get("short", "")
        d = dt.date.fromisoformat(fx["date"][:10])
        th, ta = x["teams"]["home"], x["teams"]["away"]
        h, a = th.get("name"), ta.get("name")
        mid = match_id_fn(code, d, h, a)
        result = [int(g["home"]), int(g["away"])] if st in DONE and g.get("home") is not None else None
        if result:
            finished[mid] = tuple(result)
        if not (today <= d <= today + dt.timedelta(days=horizon_days)):
            continue
        if st not in DONE and st not in LIVE and st not in ("NS", "TBD"):
            continue  # postponed / cancelled
        ch, ca = club(th), club(ta)
        ah, dh, kh = rating(ch)
        aa, da, ka = rating(ca)
        lh, la = ah * da * HOME_ADV, aa * dh / HOME_ADV
        M = _matrix(lh, la)
        p = markets_fn(M)
        scores = sorted(((M[i][j], f"{i}-{j}") for i in range(6) for j in range(6)), reverse=True)[:5]
        tip = choose_tip_fn(p, {})
        if not (kh and ka):
            tip["confidence"] = "low"
        preds.append({
            "id": mid, "sport": "soccer", "league": code, "result": result, "live": st in LIVE,
            "country": "Europe", "league_name": comp_name, "date": d.isoformat(), "time": fx["date"][11:16],
            "home": h, "away": a, "xg": [round(lh, 2), round(la, 2)], "probs": p,
            "correct_scores": [{"score": s, "prob": round(pr, 4)} for pr, s in scores], "odds": {}, "tip": tip,
            "form": {"home": [], "away": []}, "stats": {"home": {}, "away": {}}, "h2h": [],
            "strength": {"home_att": round(ah, 2), "home_def": round(dh, 2), "away_att": round(aa, 2),
                         "away_def": round(da, 2)},
            "europe": {"home_league": ch[0], "away_league": ca[0],
                       "home_factor": round(f.get(ch[0], DEFAULT_FACTOR), 3),
                       "away_factor": round(f.get(ca[0], DEFAULT_FACTOR), 3), "rated_home": kh, "rated_away": ka},
        })
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(countries, open(CACHE, "w"))
    except Exception:  # noqa: BLE001
        pass
    print(f"  Europa/Conference League: {len(preds)} games predicted, {len(finished)} results, "
          f"{looked} team lookups, API quota left {fr.AF_QUOTA['remaining']}")
    return preds, finished, names
