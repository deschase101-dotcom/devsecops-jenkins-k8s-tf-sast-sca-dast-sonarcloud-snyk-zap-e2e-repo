# ProScore — daily football predictions

A prediction website that re-analyses every recorded result each morning and publishes
probabilities, tips, accumulators ("coupons") and a public, auto-settled track record.

```
engine/predict.py   ← data download + model + tips + coupons + settlement + backtest (pure Python, no deps)
site/               ← static website (HTML/CSS/JS), reads site/data/*.json
.github/workflows/daily-predictions.yml  ← runs the engine daily and deploys to GitHub Pages
```

## How the analysis works

1. **Collect** – downloads every result from the current + 2 previous seasons for 11 leagues
   (Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga,
   Belgian Pro League, Süper Lig, Scottish Premiership) and the upcoming fixtures with bookmaker odds,
   from the free CSVs at football-data.co.uk.
2. **Rate** – fits a time-weighted Poisson model with Dixon–Coles low-score correction per league:
   attack and defence strength for every team plus home advantage. Matches lose half their weight
   each year, so current form matters most.
3. **Predict** – builds the full scoreline matrix (0-0 … 10-10) for each fixture in the next 7 days and
   derives 1X2, double chance, over/under 1.5/2.5/3.5, BTTS and the most likely correct scores.
4. **Tip** – picks one tip per match (markets must beat a minimum probability), flags **value bets**
   where model probability × bookmaker odds > 1.04, and builds three daily coupons:
   *Safe* (top 3 picks ≥70%), *Value* (best edges), *Mega* (8 picks ≥55%).
5. **Settle** – every published tip is stored in `site/data/history.json` and graded against the real
   score the next day → hit-rate and ROI by market, all-time and last 30 days.
6. **Backtest** – walk-forward test on the most recent third of the data (the model only sees games
   played before each match) → 1X2 accuracy, Brier score, tip hit-rate per league.

## Run locally

```bash
cd prediction-site
python3 engine/predict.py          # live data (needs internet access to football-data.co.uk)
python3 engine/predict.py --demo   # fictional teams, synthetic data — for testing offline
cd site && python3 -m http.server 8000   # open http://localhost:8000
```

The data committed now is **demo data** (a yellow banner says so). The first live run replaces it,
and demo tips are never mixed into the real track record.

## Go live (free, on GitHub Pages)

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. **Actions → Daily predictions → Run workflow** (it also runs every day at 06:17 UTC).
3. The site is published at `https://<user>.github.io/<repo>/`. Point a custom domain at it in the
   Pages settings if you want one.

## Ideas for next steps

- User accounts / VIP area (e.g. Supabase or Firebase auth) and payments (Stripe, mobile money).
- More leagues/sports via an API such as API-Football (needs a key; add it as a repo secret).
- Telegram/WhatsApp bot that posts the daily coupons.

> Predictions are statistical estimates, not guarantees. Gambling laws vary by country — check
> yours before running a paid tipping service. 18+ only.
