"""
Official NBA injury report (the league's own PDF, published every 15 minutes on game days).

fetch() finds the newest report for today (US Eastern), reads it and returns
{normalised player name: {"name", "status", "reason", "matchup"}}.
Statuses: Out, Doubtful, Questionable, Probable, Available.

Needs the `pypdf` package (installed by the workflow); without it the module returns {} and the
engine falls back to its "missed the last two games" heuristic.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import sys
import unicodedata
import urllib.request

URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d}_{t}.pdf"
STATUSES = ("Out", "Doubtful", "Questionable", "Probable", "Available")
ROW = re.compile(
    r"([A-Z][^\s,]*(?: [A-Z][^\s,]*){0,2}), "                 # last name(s)
    r"([A-Z][^\s,]*(?: (?:Jr\.|Sr\.|II|III|IV|V))?) "          # first name (+ suffix)
    r"(Out|Doubtful|Questionable|Probable|Available)\b")
MATCHUP = re.compile(r"\b([A-Z]{2,3}@[A-Z]{2,3})\b")


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return " ".join(re.split(r"[^a-z0-9]+", s)).strip()


def _get(url: str) -> bytes | None:
    try:
        # the NBA's file server stalls requests that announce a crawler name, so use urllib's own default
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.read()
    except Exception:  # noqa: BLE001  404 = no report at that time
        return None


def fetch(today: dt.date, now_et: dt.datetime | None = None) -> dict:
    try:
        import pypdf
    except ImportError:
        print("  NBA injury report: pypdf not installed, skipping", file=sys.stderr)
        return {}
    if now_et is None:
        from zoneinfo import ZoneInfo
        now_et = dt.datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    if now_et.date() != today:  # running for another day: start from the end of that day
        now_et = dt.datetime.combine(today, dt.time(23, 45))
    t = now_et.replace(minute=now_et.minute - now_et.minute % 15, second=0, microsecond=0)
    pdf, used = None, None
    for _ in range(4 * 24):  # walk back up to 24 h in 15-minute steps
        if t.date() < today - dt.timedelta(days=1):
            break
        stamp = t.strftime("%I_%M%p")
        pdf = _get(URL.format(d=t.date().isoformat(), t=stamp))
        if pdf and pdf.startswith(b"%PDF"):
            used = f"{t.date()} {stamp}"
            break
        pdf = None
        t -= dt.timedelta(minutes=15)
    if not pdf:
        print("  NBA injury report: none found", file=sys.stderr)
        return {}
    text = " ".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\w)- (\w)", r"\1-\2", text)  # names hyphenated across a line break ("Karl- Anthony")
    out = {}
    marks = [(m.start(), m.group(1)) for m in MATCHUP.finditer(text)]
    rows = []
    for m in ROW.finditer(text):
        words = m.group(1).split(" ")
        # the team name / previous reason can run into the last name ("Trail Blazers Avdija"): keep the
        # final word, or the final two for particles like "Van Vleet"
        keep = 2 if len(words) > 1 and words[-2].lower() in ("van", "de", "da", "del", "le", "di") else 1
        last = " ".join(words[-keep:])
        name_start = m.start(1) + len(m.group(1)) - len(last)
        rows.append((name_start, m.end(), last, m.group(2), m.group(3)))
    for i, (start, end, last, first, status) in enumerate(rows):
        matchup = ""
        for pos, mu in marks:
            if pos < start:
                matchup = mu
            else:
                break
        nxt = rows[i + 1][0] if i + 1 < len(rows) else len(text)
        reason = text[end:nxt].strip()
        reason = re.split(r" \d\d/\d\d/\d{4}| \d\d:\d\d \(ET\)| [A-Z]{2,3}@[A-Z]{2,3}", reason)[0]
        reason = reason.replace("Injury/Illness - ", "").strip()[:60]
        name = f"{first} {last}"
        out[norm(name)] = {"name": name, "status": status, "reason": reason, "matchup": matchup}
    print(f"  NBA injury report {used}: {len(out)} players listed")
    return out
