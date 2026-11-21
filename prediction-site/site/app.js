/* ProScore front-end — static, reads JSON produced daily by engine/predict.py */
(() => {
  "use strict";

  // ------------------------------------------------------------------ i18n
  const I18N = {
    en: {
      nav_home: "Home", nav_today: "Matches", nav_coupons: "Coupons", nav_record: "Record", nav_tables: "Tables",
      live: "LIVE DATA & ALGORITHMS",
      hero1: "Stop guessing,", hero2: "bet with data.",
      hero_p: "Every day our model re-reads every recorded result, rates every team and player, and turns it into probabilities for today's football, NBA, NHL and tennis games.",
      cta_today: "Today's predictions", cta_coupons: "Daily coupons",
      st_matches: "results analysed", st_hit: "tip hit-rate (settled)", st_today: "matches predicted", st_bt: "backtest tip hit-rate",
      top_picks: "Top picks today", see_all: "See all →", coupons_today: "Today's coupons",
      how: "How the analysis works",
      how1t: "1 · Collect", how1: "All results from the last 3 seasons of 11 leagues are downloaded every morning.",
      how2t: "2 · Rate", how2: "A time-weighted Poisson / Dixon–Coles model rates each team's attack, defence and home advantage. Recent games count more.",
      how3t: "3 · Simulate", how3: "Each fixture gets a full scoreline matrix → 1X2, double chance, over/under, BTTS, correct score.",
      how4t: "4 · Verify", how4: "Every tip is settled against the real score and published in the track record. Nothing is deleted.",
      all: "All", today: "Today", tomorrow: "Tomorrow", week: "Next 7 days", month: "Next 30 days", value_only: "Value bets", high_conf: "High confidence",
      no_matches: "No predictions for this filter yet. New fixtures are analysed every morning.",
      tip: "Tip", fair: "fair", value: "VALUE", conf_high: "High", conf_medium: "Medium", conf_low: "Low",
      coupon: "Accumulator", events: "Events", total_odds: "Total odds", model_prob: "Model probability", status: "Status",
      k_safe: "Safe", k_value: "Value", k_mega: "Mega",
      pending: "Pending", won: "Won", lost: "Lost",
      record: "Track record", record_sub: "Every published tip, settled against the final score.",
      overall: "All time", last30: "Last 30 days", tips: "tips", hit: "hit-rate", roi: "ROI (1 unit flat)",
      by_market: "By market", market: "Market", n: "Tips", recent_tips: "Latest settled tips", coupons_won: "Coupons won",
      backtest: "Model backtest", backtest_sub: "Walk-forward test: the model only sees games played before each match it predicts.",
      acc: "1X2 accuracy", brier: "Brier score", matches: "Matches",
      tables: "League tables", results: "Latest results",
      back: "← Back", xg: "Expected goals", markets: "All markets", form: "Form (last 5)", compare: "Last 10 games",
      gf: "Goals for / game", ga: "Goals against / game", btts_r: "BTTS rate", o25_r: "Over 2.5 rate", cs_r: "Clean sheets",
      h2h: "Head to head", no_h2h: "No previous meetings in the data.", scores: "Most likely scores",
      why: "Why this tip", strength: "Team ratings",
      att: "Attack", def: "Defence (lower = better)",
      demo: "Demo mode — fictional teams and synthetic data. Deploy with the daily workflow to show real fixtures.",
      updated: "Updated",
      disclaimer: "Predictions are statistical estimates, not guarantees. 18+ only. Never bet more than you can afford to lose. If gambling stops being fun, seek help.",
      m_1: "Home win", m_X: "Draw", m_2: "Away win", m_1X: "Home or draw", m_X2: "Draw or away", m_12: "No draw",
      "m_O1.5": "Over 1.5 goals", "m_O2.5": "Over 2.5 goals", "m_O3.5": "Over 3.5 goals",
      "m_U1.5": "Under 1.5 goals", "m_U2.5": "Under 2.5 goals", "m_U3.5": "Under 3.5 goals",
      m_BTTS: "Both teams score", m_NO_BTTS: "Not both score", m_H_SCORES: "Home scores", m_A_SCORES: "Away scores",
      m_ML_H: "Home win", m_ML_A: "Away win", m_SP_H: "Home spread", m_SP_A: "Away spread", m_OV: "Over", m_UN: "Under",
      s_all: "All sports", s_soccer: "Football", s_basketball: "Basketball", s_hockey: "Ice hockey", s_tennis: "Tennis",
      win: "to win", over: "Over", under: "Under", proj: "Projected", elo: "Elo rating", points: "pts", goals: "goals",
      pf: "Scored / game", pa: "Conceded / game", winr: "Win rate", overr: "Over the line", played: "Matches rated",
      model: "Model", market_p: "Market", book: "Odds", by_sport: "By sport", sport: "Sport",
      no_sport: "No games to analyse for this sport today or tomorrow.",
      projections: "Projections", g_total: "Game total", t_total: "team total", margin: "Margin",
      props: "Player props", props_top: "Top player props", props_sub: "Most reliable lines from each player's games this season: projection blended with his real hit rate (12/12 = cleared in each of his last 12 games). No bookmaker lines yet.",
      player: "Player", min: "Min", safe_line: "Safe line", st_pts: "pts", st_trb: "reb", st_ast: "ast", st_fg3: "3PM", st_pra: "PRA",
      over_short: "Over", proj_short: "Proj.", record_short: "Hit",
      tab_lines: "Game lines", tab_props: "Player props", players_n: "players", yes: "Yes", no: "No",
      c_pts: "Player points", c_ast: "Player assists", c_trb: "Player rebounds", c_fg3: "Player threes",
      c_stl: "Player steals", c_blk: "Player blocks", c_dd: "Double double", c_td: "Triple double",
      dd_sub: "Players to record a double double", td_sub: "Players to record a triple double",
      board_sub: "Chance of each line from ProScore's model (projection blended with the player's real record this season). Tap a category to open it.",
      did: "did it", of: "of", past_results: "Past results", no_past: "No settled coupons yet.",
      yesterday: "Yesterday", final: "Final", live_now: "LIVE", yesterday_sub: "Yesterday's published tips and how they finished.",
      no_yesterday: "No settled tips for yesterday yet. Results are added on the next update.",
      c_game: "Game total points", c_team: "Team total points", lines_n: "lines",
      out_title: "Probably out", out_sub: "Missed the team's last two games (no official injury report is used). The projection is lowered for this.",
      ppg: "pts/game", lineup_adj: "lineup-adjusted from", last5: "Last 5",
    },
    fr: {
      nav_home: "Accueil", nav_today: "Matchs", nav_coupons: "Coupons", nav_record: "Bilan", nav_tables: "Classements",
      live: "DONNÉES & ALGORITHMES",
      hero1: "Arrêtez de deviner,", hero2: "pariez avec les données.",
      hero_p: "Chaque jour notre modèle relit tous les résultats enregistrés, note chaque équipe et chaque joueur, et en tire des probabilités pour le football, la NBA, la NHL et le tennis du jour.",
      cta_today: "Pronostics du jour", cta_coupons: "Coupons du jour",
      st_matches: "résultats analysés", st_hit: "réussite des pronos", st_today: "matchs analysés", st_bt: "réussite en backtest",
      top_picks: "Meilleurs pronos du jour", see_all: "Tout voir →", coupons_today: "Coupons du jour",
      how: "Comment fonctionne l'analyse",
      how1t: "1 · Collecte", how1: "Tous les résultats des 3 dernières saisons de 11 championnats sont téléchargés chaque matin.",
      how2t: "2 · Notation", how2: "Un modèle Poisson / Dixon–Coles pondéré dans le temps note l'attaque, la défense et l'avantage du terrain. Les matchs récents comptent plus.",
      how3t: "3 · Simulation", how3: "Chaque match reçoit une matrice complète de scores → 1X2, double chance, plus/moins, les deux marquent, score exact.",
      how4t: "4 · Vérification", how4: "Chaque prono est validé avec le score réel et publié dans le bilan. Rien n'est supprimé.",
      all: "Tous", today: "Aujourd'hui", tomorrow: "Demain", week: "7 jours", month: "30 jours", value_only: "Value bets", high_conf: "Haute confiance",
      no_matches: "Aucun pronostic pour ce filtre. Les nouveaux matchs sont analysés chaque matin.",
      tip: "Prono", fair: "juste", value: "VALUE", conf_high: "Haute", conf_medium: "Moyenne", conf_low: "Faible",
      coupon: "Combiné", events: "Événements", total_odds: "Cote totale", model_prob: "Probabilité modèle", status: "Statut",
      k_safe: "Sûr", k_value: "Value", k_mega: "Méga",
      pending: "En attente", won: "Gagné", lost: "Perdu",
      record: "Bilan", record_sub: "Chaque prono publié, validé avec le score final.",
      overall: "Depuis le début", last30: "30 derniers jours", tips: "pronos", hit: "réussite", roi: "ROI (mise fixe)",
      by_market: "Par marché", market: "Marché", n: "Pronos", recent_tips: "Derniers pronos validés", coupons_won: "Coupons gagnés",
      backtest: "Backtest du modèle", backtest_sub: "Test glissant : le modèle ne voit que les matchs joués avant chaque match prédit.",
      acc: "Précision 1X2", brier: "Score de Brier", matches: "Matchs",
      tables: "Classements", results: "Derniers résultats",
      back: "← Retour", xg: "Buts attendus", markets: "Tous les marchés", form: "Forme (5 derniers)", compare: "10 derniers matchs",
      gf: "Buts marqués / match", ga: "Buts encaissés / match", btts_r: "Les deux marquent", o25_r: "Plus de 2,5", cs_r: "Clean sheets",
      h2h: "Confrontations", no_h2h: "Aucune confrontation dans les données.", scores: "Scores les plus probables",
      why: "Pourquoi ce prono", strength: "Notes des équipes",
      att: "Attaque", def: "Défense (bas = mieux)",
      demo: "Mode démo — équipes fictives et données synthétiques. Déployez le workflow quotidien pour afficher les vrais matchs.",
      updated: "Mis à jour",
      disclaimer: "Les pronostics sont des estimations statistiques, pas des garanties. Réservé aux 18 ans et plus. Ne misez jamais plus que ce que vous pouvez perdre.",
      m_1: "Victoire domicile", m_X: "Match nul", m_2: "Victoire extérieur", m_1X: "Domicile ou nul", m_X2: "Nul ou extérieur", m_12: "Pas de nul",
      "m_O1.5": "Plus de 1,5 buts", "m_O2.5": "Plus de 2,5 buts", "m_O3.5": "Plus de 3,5 buts",
      "m_U1.5": "Moins de 1,5 buts", "m_U2.5": "Moins de 2,5 buts", "m_U3.5": "Moins de 3,5 buts",
      m_BTTS: "Les deux marquent", m_NO_BTTS: "Pas les deux", m_H_SCORES: "Domicile marque", m_A_SCORES: "Extérieur marque",
      m_ML_H: "Victoire domicile", m_ML_A: "Victoire extérieur", m_SP_H: "Handicap domicile", m_SP_A: "Handicap extérieur", m_OV: "Plus de", m_UN: "Moins de",
      s_all: "Tous les sports", s_soccer: "Football", s_basketball: "Basket", s_hockey: "Hockey sur glace", s_tennis: "Tennis",
      win: "gagne", over: "Plus de", under: "Moins de", proj: "Projection", elo: "Classement Elo", points: "pts", goals: "buts",
      pf: "Marqués / match", pa: "Encaissés / match", winr: "Victoires", overr: "Au-dessus de la ligne", played: "Matchs notés",
      model: "Modèle", market_p: "Marché", book: "Cote", by_sport: "Par sport", sport: "Sport",
      no_sport: "Aucun match à analyser pour ce sport aujourd'hui ou demain.",
      projections: "Projections", g_total: "Total du match", t_total: "total équipe", margin: "Écart",
      props: "Props joueurs", props_top: "Meilleurs props joueurs", props_sub: "Lignes les plus fiables d'après les matchs de la saison : projection mélangée avec son taux de réussite réel (12/12 = dépassée lors de ses 12 derniers matchs). Pas encore de lignes bookmaker.",
      player: "Joueur", min: "Min", safe_line: "Ligne sûre", st_pts: "pts", st_trb: "reb", st_ast: "pd", st_fg3: "3PTS", st_pra: "PRA",
      over_short: "Plus de", proj_short: "Proj.", record_short: "Réussi",
      tab_lines: "Lignes du match", tab_props: "Props joueurs", players_n: "joueurs", yes: "Oui", no: "Non",
      c_pts: "Points joueur", c_ast: "Passes joueur", c_trb: "Rebonds joueur", c_fg3: "Paniers à 3 pts",
      c_stl: "Interceptions", c_blk: "Contres", c_dd: "Double-double", c_td: "Triple-double",
      dd_sub: "Joueurs qui feront un double-double", td_sub: "Joueurs qui feront un triple-double",
      board_sub: "Probabilité de chaque ligne selon le modèle ProScore (projection mélangée avec le bilan réel du joueur cette saison). Touchez une catégorie pour l'ouvrir.",
      did: "réussi", of: "sur", past_results: "Résultats passés", no_past: "Pas encore de coupons validés.",
      yesterday: "Hier", final: "Terminé", live_now: "EN DIRECT", yesterday_sub: "Les pronos publiés hier et leur résultat.",
      no_yesterday: "Pas encore de pronos validés pour hier. Les résultats sont ajoutés à la prochaine mise à jour.",
      c_game: "Total de points du match", c_team: "Total de points par équipe", lines_n: "lignes",
      out_title: "Probablement absents", out_sub: "Absents lors des deux derniers matchs de l'équipe (pas de rapport officiel des blessures). La projection est réduite en conséquence.",
      ppg: "pts/match", lineup_adj: "ajusté selon l'effectif, base", last5: "5 derniers",
    },
  };
  let lang = (() => { try { return localStorage.getItem("ps_lang") || (navigator.language || "en").slice(0, 2); } catch { return "en"; } })();
  if (!I18N[lang]) lang = "en";
  const t = (k) => (I18N[lang][k] ?? I18N.en[k] ?? k);
  const mk = (m) => t("m_" + m);
  const signed = (x) => (x > 0 ? "+" : "") + x;
  // full label for a market on a specific game, e.g. "Lakers -5.5", "Over 219.5", "Sinner to win"
  function mkLabel(code, line, home, away) {
    switch (code) {
      case "ML_H": return `${home} ${t("win")}`;
      case "ML_A": return `${away} ${t("win")}`;
      case "SP_H": return `${home} ${signed(line)}`;
      case "SP_A": return `${away} ${signed(line)}`;
      case "OV": return `${t("over")} ${line}`;
      case "UN": return `${t("under")} ${line}`;
      default: return mk(code);
    }
  }
  const SPORTS = ["soccer", "basketball", "hockey", "tennis"];
  const SPORT_ICON = { soccer: "⚽", basketball: "🏀", hockey: "🏒", tennis: "🎾" };
  const sportOf = (m) => m.sport || "soccer";

  // ------------------------------------------------------------------ utils
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x, d = 0) => (x == null ? "–" : (x * 100).toFixed(d) + "%");
  const fmtOdds = (x) => (x == null ? "–" : Number(x).toFixed(2));
  const fmtDate = (iso, opts = { weekday: "short", day: "numeric", month: "short" }) =>
    new Date(iso + "T12:00:00").toLocaleDateString(lang === "fr" ? "fr-FR" : "en-GB", opts);
  const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };

  function crest(name) {
    let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const hue = h % 360;
    const initials = name.replace(/[^\p{L}\s]/gu, "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
    return `<span class="crest" style="background:linear-gradient(135deg,hsl(${hue} 60% 45%),hsl(${(hue + 40) % 360} 55% 30%))">${esc(initials)}</span>`;
  }
  const formChips = (f = []) => `<span class="form">${f.map((r) => `<i class="${r}">${r}</i>`).join("")}</span>`;

  // ------------------------------------------------------------------ data
  const DATA = {};
  async function load(name, fallback) {
    try { const r = await fetch(`data/${name}.json`, { cache: "no-cache" }); if (!r.ok) throw 0; return await r.json(); }
    catch { return fallback; }
  }

  // ------------------------------------------------------------------ components
  function matchCard(m) {
    if (sportOf(m) !== "soccer") return otherCard(m);
    const p = m.probs, tip = m.tip;
    return `<a class="match" href="#match-${DATA.pred.matches.indexOf(m)}">
      <div class="match-top"><span>${esc(m.country)} · ${esc(m.league_name)}</span><span>${fmtDate(m.date)}${m.time ? " · " + esc(m.time) : ""}</span></div>
      <div class="teams">
        <div class="team">${crest(m.home)}<span>${esc(m.home)}</span></div>
        <div class="vs">${m.result ? centerInfo(m) : `xG<b>${m.xg[0].toFixed(1)} – ${m.xg[1].toFixed(1)}</b>`}</div>
        <div class="team">${crest(m.away)}<span>${esc(m.away)}</span></div>
      </div>
      <div class="probbar"><i class="h" style="width:${p["1"] * 100}%"></i><i class="d" style="width:${p.X * 100}%"></i><i class="a" style="width:${p["2"] * 100}%"></i></div>
      <div class="problabels"><span>1 · ${pct(p["1"])}</span><span>X · ${pct(p.X)}</span><span>2 · ${pct(p["2"])}</span></div>
      <div class="tip-row">
        <span class="tip"><span class="tag">${esc(tip.market)}</span>${esc(mk(tip.market))}</span>
        <span style="display:flex;gap:6px;align-items:center">
          ${tip.value ? `<span class="value">${t("value")}</span>` : ""}
          ${resultBadge(m)}<span class="conf ${tip.confidence}">${pct(tip.prob)}</span>
          <span class="odds">@${fmtOdds(tip.book_odds || tip.fair_odds)}</span>
        </span>
      </div>
    </a>`;
  }

  function twoWay(m) {
    const ph = (m.markets.find((x) => x.code === "ML_H") || {}).prob || 0.5;
    return { ph, pa: 1 - ph };
  }
  // did the tip win, given a final score [home, away]?
  function tipWon(market, line, h, a) {
    const tot = h + a;
    switch (market) {
      case "1": case "ML_H": return h > a;
      case "2": case "ML_A": return a > h;
      case "X": return h === a;
      case "1X": return h >= a;
      case "X2": return a >= h;
      case "12": return h !== a;
      case "SP_H": return h + line > a;
      case "SP_A": return a + line > h;
      case "OV": return tot > line;
      case "UN": return tot < line;
      case "BTTS": return h > 0 && a > 0;
      case "NO_BTTS": return !(h > 0 && a > 0);
      default: {
        const mm = /^([OU])(\d+\.5)$/.exec(market);
        if (mm) return mm[1] === "O" ? tot > +mm[2] : tot < +mm[2];
        return null;
      }
    }
  }
  function resultBadge(m) {
    if (m.result) {
      const w = tipWon(m.tip.market, m.tip.line, m.result[0], m.result[1]);
      return w == null ? "" : `<span class="badge ${w ? "won" : "lost"}">${w ? "✅ " + t("won") : "❌ " + t("lost")}</span>`;
    }
    return m.live ? `<span class="badge live">● ${t("live_now")}</span>` : "";
  }
  function centerInfo(m) {
    const sp = sportOf(m);
    if (m.result) return `${t("final")}<b class="final">${m.result[0]} – ${m.result[1]}</b>`;
    if (sp === "tennis") return `${t("elo")}<b>${m.elo[0]} – ${m.elo[1]}</b>`;
    const d = sp === "basketball" ? 0 : 1;
    return `${t("proj")}<b>${m.xg[0].toFixed(d)} – ${m.xg[1].toFixed(d)}</b>`;
  }
  function otherCard(m) {
    const tip = m.tip, { ph, pa } = twoWay(m), sp = sportOf(m);
    const sub = sp === "tennis" ? `${esc(m.league_name)}${m.round ? " · " + esc(m.round) : ""}` : `${esc(m.country)} · ${esc(m.league_name)}`;
    return `<a class="match" href="#match-${DATA.pred.matches.indexOf(m)}">
      <div class="match-top"><span>${SPORT_ICON[sp]} ${sub}</span><span>${fmtDate(m.date)}${m.time ? " · " + esc(m.time) : ""}</span></div>
      <div class="teams">
        <div class="team">${crest(m.home)}<span>${esc(m.home)}</span></div>
        <div class="vs">${centerInfo(m)}</div>
        <div class="team">${crest(m.away)}<span>${esc(m.away)}</span></div>
      </div>
      <div class="probbar"><i class="h" style="width:${ph * 100}%"></i><i class="a" style="width:${pa * 100}%"></i></div>
      <div class="problabels"><span>${pct(ph)}${m.odds.ml_h ? " @" + fmtOdds(m.odds.ml_h) : ""}</span><span>${pct(pa)}${m.odds.ml_a ? " @" + fmtOdds(m.odds.ml_a) : ""}</span></div>
      <div class="tip-row">
        <span class="tip"><span class="tag">${esc(tip.market.replace("_", " "))}</span>${esc(mkLabel(tip.market, tip.line, m.home_abbr || m.home, m.away_abbr || m.away))}</span>
        <span style="display:flex;gap:6px;align-items:center">
          ${tip.value ? `<span class="value">${t("value")}</span>` : ""}
          ${resultBadge(m)}<span class="conf ${tip.confidence}">${pct(tip.prob)}</span>
          <span class="odds">@${fmtOdds(tip.book_odds || tip.fair_odds)}</span>
        </span>
      </div>
    </a>`;
  }

  function propsList(list) {
    return `<div class="table-wrap"><table class="std"><thead><tr><th>${t("player")}</th><th></th><th>${t("proj_short")}</th><th>${t("record_short")}</th><th>%</th></tr></thead><tbody>
      ${list.map((c) => `<tr><td><b>${esc(c.player)}</b><div class="sub">${esc(c.team)}</div></td><td>${t("over_short")} <b>${c.line}</b> ${t("st_" + c.stat)}</td><td class="mono">${c.proj}</td><td class="mono">${esc(c.hit || "")}</td><td class="mono status-won">${pct(c.prob)}</td></tr>`).join("")}
    </tbody></table></div>`;
  }
  function playersTable(team, ps) {
    if (!ps || !ps.length) return "";
    const cell = (p, s) => p.safe[s] ? `<b>${p.proj[s]}</b><div class="sub">${t("over_short")} ${p.safe[s].line} · ${pct(p.safe[s].prob)}</div>` : `<b>${p.proj[s]}</b>`;
    return `<h3 style="margin:14px 0 8px">${esc(team)}</h3><div class="table-wrap"><table class="std" style="min-width:560px"><thead><tr><th>${t("player")}</th><th>${t("min")}</th><th>PTS</th><th>REB</th><th>AST</th><th>3PM</th><th>PRA</th></tr></thead><tbody>
      ${ps.map((p) => `<tr><td><b>${esc(p.name)}</b><div class="sub">${t("last5")}: ${p.last5.map((l) => l.pts).join(" · ")} pts</div></td><td>${p.min}</td><td>${cell(p, "pts")}</td><td>${cell(p, "trb")}</td><td>${cell(p, "ast")}</td><td>${cell(p, "fg3")}</td><td>${cell(p, "pra")}</td></tr>`).join("")}
    </tbody></table></div>`;
  }

  const short = (name) => name.split(" ").slice(-1)[0];
  const heat = (p) => `--heat:${Math.round(p * 100)}%`;
  function marketBoard(m) {
    const all = [...(m.players.home || []), ...(m.players.away || [])];
    const abbr = (team) => (team === m.home ? m.home_abbr || short(m.home) : m.away_abbr || short(m.away));
    const ph = (m.markets.find((x) => x.code === "ML_H") || {}).prob || 0.5;
    const teamRow = (name, p) => `<div class="mrow">${crest(name)}<span class="mname">${esc(name)}</span>
      <span class="pill yes">${t("yes")} ${pct(p)}</span><span class="pill no">${t("no")} ${pct(1 - p)}</span></div>`;
    const cat = (key, rowsHtml, n, sub) => `<details class="acc">
      <summary><span><b>${t("c_" + key)}</b>${sub ? `<small>${sub}</small>` : ""}</span><span class="cnt">${n} ${t("players_n")}</span></summary>
      <div class="acc-body">${rowsHtml}</div></details>`;
    const ladderCat = (s) => {
      const ps = all.filter((p) => p.ladder && p.ladder[s]).sort((a, b) => b.proj[s] - a.proj[s]);
      if (!ps.length) return "";
      const rows = ps.map((p) => `<div class="lrow"><div class="lwho"><b>${esc(p.name)}</b><small>${esc(abbr(p.team))} · ${t("proj_short")} ${p.proj[s]}</small></div>
        <div class="rungs">${p.ladder[s].map((r) => `<span class="rung" style="${heat(r.p)}" title="${r.hit} ${t("of")} ${p.games}"><b>${r.k}+</b>${pct(r.p)}</span>`).join("")}</div></div>`).join("");
      return cat(s, rows, ps.length);
    };
    const multiCat = (key, field, realField) => {
      const ps = all.filter((p) => p[field] >= 0.03).sort((a, b) => b[field] - a[field]);
      if (!ps.length) return "";
      const rows = ps.map((p) => `<div class="lrow"><div class="lwho"><b>${esc(p.name)}</b><small>${esc(abbr(p.team))} · ${t("did")} ${p[realField]} ${t("of")} ${p.games}</small></div>
        <div class="rungs"><span class="rung" style="${heat(p[field])}"><b>${t("yes")}</b>${pct(p[field])}</span></div></div>`).join("");
      return cat(key, rows, ps.length, t(key + "_sub"));
    };
    const tot = m.totals;
    const totRow = (label, sub, rows) => `<div class="lrow"><div class="lwho"><b>${esc(label)}</b><small>${sub}</small></div>
      <div class="rungs">${rows.map((r) => `<span class="rung" style="${heat(r.p)}"><b>${r.line}+</b>${pct(r.p)}</span>`).join("")}</div></div>`;
    const totals = tot ? `<details class="acc" open><summary><span><b>${t("c_game")}</b></span><span class="cnt">${tot.game.length} ${t("lines_n")}</span></summary>
        <div class="acc-body">${totRow(`${abbr(m.home)} + ${abbr(m.away)}`, `${t("proj_short")} ${(m.xg[0] + m.xg[1]).toFixed(1)}`, tot.game)}</div></details>
      <details class="acc" open><summary><span><b>${t("c_team")}</b></span><span class="cnt">2 ${lang === "fr" ? "équipes" : "teams"}</span></summary>
        <div class="acc-body">${totRow(m.home, `${t("proj_short")} ${m.xg[0].toFixed(1)}`, tot.home)}${totRow(m.away, `${t("proj_short")} ${m.xg[1].toFixed(1)}`, tot.away)}</div></details>` : "";
    const miss = m.missing ? [...m.missing.home.map((x) => ({ ...x, team: m.home })), ...m.missing.away.map((x) => ({ ...x, team: m.away }))] : [];
    const missing = miss.length ? `<div class="panel out"><b>⚠️ ${t("out_title")}</b>
        <ul>${miss.map((x) => `<li><b>${esc(x.name)}</b> <span class="sub">${esc(abbr(x.team))} · ${x.pts} ${t("ppg")} · ${x.min} min</span></li>`).join("")}</ul>
        <small class="sub">${t("out_sub")}${m.xg_base ? ` (${t("lineup_adj")} ${m.xg_base[0].toFixed(1)} – ${m.xg_base[1].toFixed(1)})` : ""}</small></div>` : "";
    return `<div class="board">
      <div class="board-teams">${teamRow(m.home, ph)}${teamRow(m.away, 1 - ph)}</div>
      ${missing}
      <p class="sub" style="margin:4px 2px 10px">${t("board_sub")}</p>
      ${totals}
      ${["pts", "ast", "trb", "fg3", "stl", "blk"].map(ladderCat).join("")}
      ${multiCat("dd", "dd", "dd_real")}${multiCat("td", "td", "td_real")}
    </div>`;
  }

  function sportTabs(counts) {
    const f = (v, label) => `<button class="filter ${state.sport === v ? "on" : ""}" data-f="sport" data-v="${v}">${label}</button>`;
    return `<div class="filters">${f("all", t("s_all"))}${SPORTS.map((s) => f(s, `${SPORT_ICON[s]} ${t("s_" + s)}${counts && counts[s] != null ? ` · ${counts[s]}` : ""}`)).join("")}</div>`;
  }
  const bySport = (arr) => (state.sport === "all" ? arr : arr.filter((x) => (x.sport || "soccer") === state.sport));
  const countBy = (arr) => SPORTS.reduce((o, s) => ((o[s] = arr.filter((x) => (x.sport || "soccer") === s).length), o), {});

  function couponCard(c) {
    const status = c.status || "pending";
    const legs = c.picks.map((p) => `<div class="leg">
        <div class="leg-top"><span>${esc(p.country || "")} · ${esc(p.league_name)}</span><span>${fmtDate(p.date, { day: "2-digit", month: "2-digit" })}${p.time ? " " + esc(p.time) : ""}</span></div>
        <div class="leg-teams">${esc(p.home)} <span class="sub">vs</span> ${esc(p.away)}${p.score ? ` <span class="mono">(${esc(p.score)})</span>` : ""}</div>
        <div class="leg-bottom"><span>${esc(mkLabel(p.market, p.line, p.home, p.away))}</span><span class="mono ${p.status ? "status-" + p.status : ""}">${fmtOdds(p.odds)}</span></div>
      </div>`).join("");
    const done = c.picks.filter((p) => p.status && p.status !== "pending").length;
    return `<article class="coupon">
      <div class="coupon-head">
        <span class="coupon-icon"><svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/></svg></span>
        <div><small>${fmtDate(c.date)}</small><h3>${SPORT_ICON[c.sport || "soccer"]} ${t("coupon")} · ${t("s_" + (c.sport || "soccer"))}</h3><small class="mono">N° ${esc(c.id.replace(/\D/g, "").slice(0, 10))}</small></div>
        <span class="coupon-kind kind-${c.kind}">${t("k_" + c.kind)}${c.n ? " #" + c.n : ""}</span>
      </div>
      <dl class="kv">
        <dt>${t("events")}: ${c.picks.length}</dt><dd>${status === "pending" && !done ? "" : `${done}/${c.picks.length}`}</dd>
        <dt>${t("total_odds")}</dt><dd>${fmtOdds(c.total_odds)}</dd>
        <dt>${t("model_prob")}</dt><dd>${pct(c.prob, 1)}</dd>
        <dt>${t("status")}</dt><dd class="status-${status}">${t(status)}</dd>
      </dl>
      ${legs}
    </article>`;
  }

  // ------------------------------------------------------------------ views
  function viewHome() {
    const { meta, matches, coupons } = DATA.pred;
    const bt = DATA.backtest;
    const today = meta.date;
    const soon = matches.filter((m) => m.date === today || m.date === addDays(today, 1));
    const top = bySport(soon).sort((a, b) => b.tip.prob - a.tip.prob).slice(0, 6);
    const rec = meta.record?.overall || {};
    return `
      <section class="hero">
        <span class="chip-live">${t("live")}</span>
        <h1>${t("hero1")}<em>${t("hero2")}</em></h1>
        <p>${t("hero_p")}</p>
        <div class="cta-row"><a class="btn primary" href="#today">${t("cta_today")}</a><a class="btn" href="#coupons">${t("cta_coupons")}</a></div>
      </section>
      <div class="stats">
        <div class="stat"><b>${(meta.matches_analysed || 0).toLocaleString()}</b><span>${t("st_matches")}</span></div>
        <div class="stat"><b>${matches.length}</b><span>${t("st_today")}</span></div>
        <div class="stat"><b class="good">${pct(rec.rate, 1)}</b><span>${t("st_hit")} · ${rec.n || 0}</span></div>
        <div class="stat"><b>${pct(bt?.tip_rate, 1)}</b><span>${t("st_bt")}</span></div>
      </div>
      <section>
        <div class="section-head"><h2>${t("top_picks")}</h2><a href="#today">${t("see_all")}</a></div>
        ${sportTabs(countBy(soon))}
        ${top.length ? `<div class="grid">${top.map(matchCard).join("")}</div>` : `<div class="empty">${t("no_matches")}</div>`}
      </section>
      ${coupons.length ? `<section>
        <div class="section-head"><h2>${t("coupons_today")}</h2><a href="#coupons">${t("see_all")}</a></div>
        <div class="grid">${bySport(coupons).filter((c) => c.date === today || c.date === addDays(today, 1)).slice(0, 3).map(couponCard).join("")}</div>
      </section>` : ""}
      <section>
        <div class="section-head"><h2>${t("how")}</h2></div>
        <div class="how">${[1, 2, 3, 4].map((i) => `<div class="panel"><b>${t("how" + i + "t")}</b><p>${t("how" + i)}</p></div>`).join("")}</div>
      </section>
      <p class="sub" style="text-align:center;margin-top:24px">${t("updated")}: ${new Date(meta.generated_at).toLocaleString(lang === "fr" ? "fr-FR" : "en-GB")}</p>`;
  }

  const state = { day: "today", league: "all", flag: "all", sport: "all", ptab: "props", cday: "today" };
  function viewToday() {
    const { meta, matches } = DATA.pred;
    const today = meta.date;
    let ms = bySport(matches);
    if (state.day === "today" || state.day === "yesterday") ms = ms.filter((m) => m.date === today);
    else if (state.day === "tomorrow") ms = ms.filter((m) => m.date === addDays(today, 1));
    else if (state.day === "week") ms = ms.filter((m) => m.date <= addDays(today, 7));
    if (state.league !== "all") ms = ms.filter((m) => m.league === state.league);
    if (state.flag === "value") ms = ms.filter((m) => m.tip.value);
    if (state.flag === "high") ms = ms.filter((m) => m.tip.confidence === "high");
    const leagues = [...new Set(bySport(matches).map((m) => m.league))];
    const f = (group, val, label) => `<button class="filter ${state[group] === val ? "on" : ""}" data-f="${group}" data-v="${esc(val)}">${esc(label)}</button>`;
    return `<section>
      <div class="section-head"><h2>${t("nav_today")}</h2><span class="sub">${ms.length}</span></div>
      <div class="filters">${f("day", "yesterday", t("yesterday"))}${f("day", "today", t("today"))}${f("day", "tomorrow", t("tomorrow"))}${f("day", "week", t("week"))}${f("day", "month", t("month"))}</div>
      ${sportTabs(countBy(matches))}
      <div class="filters">${f("league", "all", t("all"))}${leagues.map((l) => f("league", l, meta.leagues[l]?.name || l)).join("")}</div>
      <div class="filters">${f("flag", "all", t("all"))}${f("flag", "high", t("high_conf"))}${f("flag", "value", t("value_only"))}</div>
      ${state.day === "yesterday" ? yesterdayTable() : ms.length ? `<div class="grid">${ms.map(matchCard).join("")}</div>` : `<div class="empty">${t("no_matches")}</div>`}
    </section>`;
  }
  function yesterdayTable() {
    const y = addDays(DATA.pred.meta.date, -1);
    const tips = bySport(Object.values(DATA.history.tips || {}).filter((x) => x.date === y))
      .sort((a, b) => (a.sport || "").localeCompare(b.sport || "") || (a.league || "").localeCompare(b.league || ""));
    if (!tips.length) return `<div class="empty">${t("no_yesterday")}</div>`;
    const won = tips.filter((x) => x.status === "won").length, done = tips.filter((x) => x.status !== "pending").length;
    return `<p class="sub">${t("yesterday_sub")} <b>${won}/${done}</b> ${t("won").toLowerCase()}.</p>
      <div class="table-wrap"><table class="std"><thead><tr><th></th><th>${t("matches")}</th><th>${t("tip")}</th><th>Score</th><th>${t("status")}</th></tr></thead><tbody>
      ${tips.map((x) => `<tr><td>${SPORT_ICON[x.sport || "soccer"] || ""}</td><td>${esc(x.home)} – ${esc(x.away)}<div class="sub">${esc(x.league_name)}</div></td><td><b>${esc(mkLabel(x.market, x.line, x.home, x.away))}</b><div class="sub">${pct(x.prob)} · @${fmtOdds(x.odds)}</div></td><td class="mono">${esc(x.score || "–")}</td><td class="status-${x.status}">${t(x.status)}</td></tr>`).join("")}
      </tbody></table></div>`;
  }

  function viewCoupons() {
    const today = DATA.pred.meta.date;
    const day = state.cday || "today";
    let list;
    if (day === "past") {
      // settled coupons from earlier days (newest first), plus today's that are already decided
      const hist = Object.values(DATA.history.coupons || {}).filter((c) => c.status !== "pending" && c.date < today);
      const todayDone = DATA.pred.coupons.filter((c) => c.date === today && c.status && c.status !== "pending");
      list = [...todayDone, ...hist].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 30);
    } else {
      const d = day === "tomorrow" ? addDays(today, 1) : today;
      // only coupons still in play; decided ones move to "Past results"
      list = DATA.pred.coupons.filter((c) => c.date === d && (!c.status || c.status === "pending"));
    }
    const f = (v, label) => `<button class="filter ${day === v ? "on" : ""}" data-f="cday" data-v="${v}">${label}</button>`;
    const shown = bySport(list);
    return `<section>
        <div class="section-head"><h2>${t("nav_coupons")}</h2><span class="sub">${shown.length}</span></div>
        <div class="filters">${f("today", t("today"))}${f("tomorrow", t("tomorrow"))}${f("past", t("past_results"))}</div>
        ${sportTabs(countBy(list))}
        ${shown.length ? `<div class="grid">${shown.map(couponCard).join("")}</div>` : `<div class="empty">${day === "past" ? t("no_past") : t("no_sport")}</div>`}
      </section>
      ${(() => {
        if (day === "past" || !(state.sport === "all" || state.sport === "basketball")) return "";
        const d = day === "tomorrow" ? addDays(today, 1) : today;
        const props = DATA.pred.matches.filter((m) => m.props && m.date === d)
          .flatMap((m) => m.props.map((c) => ({ ...c, date: m.date }))).sort((a, b) => b.prob - a.prob).slice(0, 12);
        return props.length ? `<section><div class="section-head"><div><h2>🏀 ${t("props_top")}</h2><div class="sub">${t("props_sub")}</div></div></div>${propsList(props)}</section>` : "";
      })()}`;
  }


  function viewRecord() {
    const r = DATA.pred.meta.record || {};
    const bt = DATA.backtest;
    const tile = (label, a) => `<div class="panel"><h3>${label}</h3>
      <div class="stats" style="margin:0;grid-template-columns:repeat(3,1fr)">
        <div class="stat"><b>${a?.n ?? 0}</b><span>${t("tips")}</span></div>
        <div class="stat"><b class="good">${pct(a?.rate, 1)}</b><span>${t("hit")}</span></div>
        <div class="stat"><b style="color:${(a?.roi ?? 0) >= 0 ? "var(--win)" : "var(--lose)"}">${a?.roi == null ? "–" : (a.roi >= 0 ? "+" : "") + (a.roi * 100).toFixed(1) + "%"}</b><span>${t("roi")}</span></div>
      </div></div>`;
    const markets = Object.entries(r.by_market || {});
    const settled = Object.values(DATA.history.tips || {}).filter((x) => x.status !== "pending")
      .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 40);
    return `<section>
        <div class="section-head"><div><h2>${t("record")}</h2><div class="sub">${t("record_sub")}</div></div></div>
        <div class="panels">${tile(t("overall"), r.overall)}${tile(t("last30"), r.last30)}</div>
        <p class="sub">${t("coupons_won")}: <b>${r.coupons?.won ?? 0}</b> / ${r.coupons?.n ?? 0}</p>
      </section>
      ${Object.keys(r.by_sport || {}).length ? `<section><div class="section-head"><h2>${t("by_sport")}</h2></div>
        <div class="table-wrap"><table class="std"><thead><tr><th>${t("sport")}</th><th></th><th>${t("n")}</th><th>${t("hit")}</th><th>ROI</th></tr></thead><tbody>
        ${Object.entries(r.by_sport).map(([k, a]) => `<tr><td>${SPORT_ICON[k] || ""}</td><td>${esc(t("s_" + k))}</td><td>${a.n}</td><td>${pct(a.rate, 1)}</td><td class="${a.roi >= 0 ? "status-won" : "status-lost"}">${(a.roi * 100).toFixed(1)}%</td></tr>`).join("")}
        </tbody></table></div></section>` : ""}
      ${markets.length ? `<section><div class="section-head"><h2>${t("by_market")}</h2></div>
        <div class="table-wrap"><table class="std"><thead><tr><th>${t("market")}</th><th></th><th>${t("n")}</th><th>${t("hit")}</th><th>ROI</th></tr></thead><tbody>
        ${markets.map(([k, a]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(mk(k))}</td><td>${a.n}</td><td>${pct(a.rate, 1)}</td><td class="${a.roi >= 0 ? "status-won" : "status-lost"}">${(a.roi * 100).toFixed(1)}%</td></tr>`).join("")}
        </tbody></table></div></section>` : ""}
      ${bt && bt.matches ? `<section><div class="section-head"><div><h2>${t("backtest")}</h2><div class="sub">${t("backtest_sub")}</div></div></div>
        <div class="stats" style="margin-top:0">
          <div class="stat"><b>${bt.matches.toLocaleString()}</b><span>${t("matches")}</span></div>
          <div class="stat"><b>${pct(bt.acc_1x2, 1)}</b><span>${t("acc")}</span></div>
          <div class="stat"><b class="good">${pct(bt.tip_rate, 1)}</b><span>${t("st_bt")}</span></div>
          <div class="stat"><b>${bt.brier.toFixed(3)}</b><span>${t("brier")}</span></div>
        </div>
        <div class="table-wrap" style="margin-top:12px"><table class="std"><thead><tr><th>League</th><th></th><th>${t("matches")}</th><th>${t("acc")}</th><th>${t("hit")}</th></tr></thead><tbody>
        ${Object.entries(bt.leagues).map(([k, l]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(l.league_name)}</td><td>${l.matches}</td><td>${pct(l.acc_1x2, 1)}</td><td>${pct(l.tip_rate, 1)}</td></tr>`).join("")}
        ${Object.entries(bt.sports || {}).filter(([, v]) => v.matches).map(([k, v]) => `<tr><td>${SPORT_ICON[k]}</td><td>${esc(t("s_" + k))} (${lang === "fr" ? "vainqueur" : "winner"})</td><td>${v.matches}</td><td>${pct(v.acc, 1)}</td><td>–</td></tr>`).join("")}
        </tbody></table></div></section>` : ""}
      ${settled.length ? `<section><div class="section-head"><h2>${t("recent_tips")}</h2></div>
        <div class="table-wrap"><table class="std"><thead><tr><th>${t("matches")}</th><th></th><th>${t("tip")}</th><th>Score</th><th>${t("status")}</th></tr></thead><tbody>
        ${settled.map((x) => `<tr><td>${fmtDate(x.date, { day: "2-digit", month: "2-digit" })}</td><td>${esc(x.home)} – ${esc(x.away)}</td><td><b>${esc(mkLabel(x.market, x.line, x.home, x.away))}</b> @${fmtOdds(x.odds)}</td><td class="mono">${esc(x.score)}</td><td class="status-${x.status}">${t(x.status)}</td></tr>`).join("")}
        </tbody></table></div></section>` : ""}`;
  }

  function viewTables() {
    const tabs = Object.entries(DATA.tables || {});
    const sel = state.table && DATA.tables[state.table] ? state.table : tabs[0]?.[0];
    const tb = DATA.tables[sel];
    return `<section>
        <div class="section-head"><h2>${t("tables")}</h2></div>
        <div class="filters">${tabs.map(([k, v]) => `<button class="filter ${k === sel ? "on" : ""}" data-f="table" data-v="${esc(k)}">${esc(v.league_name)}</button>`).join("")}</div>
        ${tb ? `<div class="table-wrap"><table class="std"><thead><tr><th>#</th><th></th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>Pts</th></tr></thead><tbody>
          ${tb.rows.map((r) => `<tr><td>${r.pos}</td><td>${esc(r.team)}</td><td>${r.p}</td><td>${r.w}</td><td>${r.d}</td><td>${r.l}</td><td>${r.gd > 0 ? "+" : ""}${r.gd}</td><td><b>${r.pts}</b></td></tr>`).join("")}
        </tbody></table></div>` : `<div class="empty">–</div>`}
      </section>
      ${DATA.results.length ? `<section><div class="section-head"><h2>${t("results")}</h2></div>
        <div class="table-wrap"><table class="std"><tbody>
        ${DATA.results.slice(0, 40).map((r) => `<tr><td>${fmtDate(r.date, { day: "2-digit", month: "2-digit" })}</td><td>${esc(r.home)} – ${esc(r.away)}</td><td class="sub">${esc(r.league_name)}</td><td><b>${esc(r.score)}</b></td></tr>`).join("")}
        </tbody></table></div></section>` : ""}`;
  }

  function viewMatch(id) {
    const m = DATA.pred.matches.find((x) => x.id === id);
    if (!m) return `<a class="back" href="#today">${t("back")}</a><div class="empty" style="margin-top:16px">${t("no_matches")}</div>`;
    if (sportOf(m) !== "soccer") return viewOther(m);
    const p = m.probs;
    const row = (k) => `<div class="mk-row"><span>${esc(mk(k))}</span><span class="bar"><i style="width:${p[k] * 100}%"></i></span><span class="pct">${pct(p[k])}</span></div>`;
    const hs = m.stats.home || {}, as = m.stats.away || {};
    const cmp = (label, key, f = (x) => x) => `<tr><td>${hs[key] != null ? f(hs[key]) : "–"}</td><td>${label}</td><td>${as[key] != null ? f(as[key]) : "–"}</td></tr>`;
    const tip = m.tip;
    const why = lang === "fr"
      ? `Le modèle attend <strong>${m.xg[0].toFixed(2)}</strong> buts pour ${esc(m.home)} et <strong>${m.xg[1].toFixed(2)}</strong> pour ${esc(m.away)}. La probabilité de <strong>${esc(mk(tip.market))}</strong> est de <strong>${pct(tip.prob, 1)}</strong>, soit une cote juste de ${fmtOdds(tip.fair_odds)}${tip.book_odds ? ` contre ${fmtOdds(tip.book_odds)} chez les bookmakers (avantage ${(tip.edge * 100).toFixed(1)}%)` : ""}.`
      : `The model expects <strong>${m.xg[0].toFixed(2)}</strong> goals for ${esc(m.home)} and <strong>${m.xg[1].toFixed(2)}</strong> for ${esc(m.away)}. That gives <strong>${esc(mk(tip.market))}</strong> a <strong>${pct(tip.prob, 1)}</strong> chance — fair odds ${fmtOdds(tip.fair_odds)}${tip.book_odds ? ` vs ${fmtOdds(tip.book_odds)} at the bookmakers (edge ${(tip.edge * 100).toFixed(1)}%)` : ""}.`;
    return `<a class="back" href="#today">${t("back")}</a>
      <div class="detail-hero">
        <div class="match-top"><span>${esc(m.country)} · ${esc(m.league_name)}</span><span>${fmtDate(m.date)}${m.time ? " · " + esc(m.time) : ""}</span></div>
        <div class="teams">
          <div class="team">${crest(m.home)}<span>${esc(m.home)}</span>${formChips(m.form.home)}</div>
          <div class="vs">${t("xg")}<b>${m.xg[0].toFixed(2)} – ${m.xg[1].toFixed(2)}</b></div>
          <div class="team">${crest(m.away)}<span>${esc(m.away)}</span>${formChips(m.form.away)}</div>
        </div>
        <div class="probbar"><i class="h" style="width:${p["1"] * 100}%"></i><i class="d" style="width:${p.X * 100}%"></i><i class="a" style="width:${p["2"] * 100}%"></i></div>
        <div class="problabels"><span>1 · ${pct(p["1"], 1)}${m.odds.H ? " @" + fmtOdds(m.odds.H) : ""}</span><span>X · ${pct(p.X, 1)}${m.odds.D ? " @" + fmtOdds(m.odds.D) : ""}</span><span>2 · ${pct(p["2"], 1)}${m.odds.A ? " @" + fmtOdds(m.odds.A) : ""}</span></div>
        <div class="tip-row">
          <span class="tip">${t("tip")}: <span class="tag">${esc(tip.market)}</span>${esc(mk(tip.market))}</span>
          <span style="display:flex;gap:6px;align-items:center">${tip.value ? `<span class="value">${t("value")}</span>` : ""}<span class="conf ${tip.confidence}">${t("conf_" + tip.confidence)}</span></span>
        </div>
      </div>
      <section class="panels">
        <div class="panel"><h3>${t("why")}</h3><p class="explain">${why}</p>
          <h3 style="margin-top:16px">${t("scores")}</h3>
          <div class="scores">${m.correct_scores.map((s) => `<div><b>${esc(s.score)}</b><span>${pct(s.prob, 1)}</span></div>`).join("")}</div>
        </div>
        <div class="panel"><h3>${t("markets")}</h3>${["1", "X", "2", "1X", "X2", "12", "O1.5", "O2.5", "U2.5", "O3.5", "BTTS", "NO_BTTS"].map(row).join("")}</div>
        <div class="panel"><h3>${t("compare")}</h3>
          <table class="cmp"><tbody>
            <tr><td><b>${esc(m.home)}</b></td><td></td><td><b>${esc(m.away)}</b></td></tr>
            ${cmp(t("gf"), "gf")}${cmp(t("ga"), "ga")}${cmp(t("btts_r"), "btts", pct)}${cmp(t("o25_r"), "o25", pct)}${cmp(t("cs_r"), "cs", pct)}
            <tr><td>${m.strength.home_att}</td><td>${t("att")}</td><td>${m.strength.away_att}</td></tr>
            <tr><td>${m.strength.home_def}</td><td>${t("def")}</td><td>${m.strength.away_def}</td></tr>
          </tbody></table>
        </div>
        <div class="panel"><h3>${t("h2h")}</h3>
          ${m.h2h.length ? `<table class="cmp"><tbody>${m.h2h.map((g) => `<tr><td>${fmtDate(g.date, { day: "2-digit", month: "2-digit", year: "2-digit" })}</td><td>${esc(g.home)} – ${esc(g.away)}</td><td class="mono"><b>${esc(g.score)}</b></td></tr>`).join("")}</tbody></table>` : `<p class="sub">${t("no_h2h")}</p>`}
        </div>
      </section>`;
  }

  function viewOther(m) {
    const sp = sportOf(m), tip = m.tip, { ph, pa } = twoWay(m);
    const unit = sp === "basketball" ? t("points") : t("goals");
    const lbl = (x) => mkLabel(x.code, x.line, m.home, m.away);
    const rows = m.markets.map((x) => `<tr><td>${esc(lbl(x))}</td><td class="mono">${pct(x.model_prob, 1)}</td><td class="mono">${x.market_prob != null ? pct(x.market_prob, 1) : "–"}</td><td class="mono"><b>${pct(x.prob, 1)}</b></td><td class="mono">${x.odds ? fmtOdds(x.odds) : "–"}</td><td class="mono ${x.edge > 0 ? "status-won" : ""}">${x.edge != null ? (x.edge * 100).toFixed(1) + "%" : "–"}</td></tr>`).join("");
    const tipTxt = esc(lbl({ code: tip.market, line: tip.line }));
    let why;
    if (sp === "tennis") {
      why = lang === "fr"
        ? `${esc(m.home)} a un Elo de <strong>${m.elo[0]}</strong> contre <strong>${m.elo[1]}</strong> pour ${esc(m.away)} (calculé sur ${m.matches_played[0]} et ${m.matches_played[1]} matchs). Probabilité pour <strong>${tipTxt}</strong> : <strong>${pct(tip.prob, 1)}</strong>, cote juste ${fmtOdds(tip.fair_odds)}.`
        : `${esc(m.home)} is rated <strong>${m.elo[0]}</strong> Elo against <strong>${m.elo[1]}</strong> for ${esc(m.away)} (from ${m.matches_played[0]} and ${m.matches_played[1]} rated matches). That makes <strong>${tipTxt}</strong> <strong>${pct(tip.prob, 1)}</strong> likely, fair odds ${fmtOdds(tip.fair_odds)}.`;
    } else {
      const d = sp === "basketball" ? 1 : 2;
      why = lang === "fr"
        ? `Projection : <strong>${m.xg[0].toFixed(d)}</strong> ${unit} pour ${esc(m.home)} et <strong>${m.xg[1].toFixed(d)}</strong> pour ${esc(m.away)}. Probabilité pour <strong>${tipTxt}</strong> : <strong>${pct(tip.prob, 1)}</strong> (cote juste ${fmtOdds(tip.fair_odds)}${tip.book_odds ? `, bookmaker ${fmtOdds(tip.book_odds)}, avantage ${(tip.edge * 100).toFixed(1)}%` : ""}).`
        : `Projected score: <strong>${m.xg[0].toFixed(d)}</strong> ${unit} for ${esc(m.home)}, <strong>${m.xg[1].toFixed(d)}</strong> for ${esc(m.away)}. <strong>${tipTxt}</strong> comes out at <strong>${pct(tip.prob, 1)}</strong> (fair odds ${fmtOdds(tip.fair_odds)}${tip.book_odds ? `, bookmaker ${fmtOdds(tip.book_odds)}, edge ${(tip.edge * 100).toFixed(1)}%` : ""}).`;
    }
    const hs = (m.stats || {}).home || {}, as = (m.stats || {}).away || {};
    const cmp = (label, key, f = (x) => x) => `<tr><td>${hs[key] != null ? f(hs[key]) : "–"}</td><td>${label}</td><td>${as[key] != null ? f(as[key]) : "–"}</td></tr>`;
    return `<a class="back" href="#today">${t("back")}</a>
      <div class="detail-hero">
        <div class="match-top"><span>${SPORT_ICON[sp]} ${esc(m.league_name)}${m.round ? " · " + esc(m.round) : ""}</span><span>${fmtDate(m.date)}${m.time ? " · " + esc(m.time) : ""}</span></div>
        <div class="teams">
          <div class="team">${crest(m.home)}<span>${esc(m.home)}</span>${formChips(m.form.home)}</div>
          <div class="vs">${centerInfo(m)}</div>
          <div class="team">${crest(m.away)}<span>${esc(m.away)}</span>${formChips(m.form.away)}</div>
        </div>
        <div class="probbar"><i class="h" style="width:${ph * 100}%"></i><i class="a" style="width:${pa * 100}%"></i></div>
        <div class="problabels"><span>${pct(ph, 1)}${m.odds.ml_h ? " @" + fmtOdds(m.odds.ml_h) : ""}</span><span>${pct(pa, 1)}${m.odds.ml_a ? " @" + fmtOdds(m.odds.ml_a) : ""}</span></div>
        <div class="tip-row">
          <span class="tip">${t("tip")}: <span class="tag">${esc(tip.market.replace("_", " "))}</span>${tipTxt}</span>
          <span style="display:flex;gap:6px;align-items:center">${tip.value ? `<span class="value">${t("value")}</span>` : ""}<span class="conf ${tip.confidence}">${t("conf_" + tip.confidence)}</span></span>
        </div>
      </div>
      ${m.players ? `<div class="mtabs"><button class="mtab ${state.ptab === "lines" ? "on" : ""}" data-f="ptab" data-v="lines">${t("tab_lines")}</button><button class="mtab ${state.ptab === "props" ? "on" : ""}" data-f="ptab" data-v="props">${t("tab_props")}</button></div>` : ""}
      ${m.players && state.ptab === "props" ? `<section>${marketBoard(m)}
        ${m.props && m.props.length ? `<div class="section-head" style="margin-top:22px"><h2>${t("props_top")}</h2></div><div class="panel">${propsList(m.props)}</div>` : ""}
        <div class="panel" style="margin-top:12px">${playersTable(m.home, m.players.home)}${playersTable(m.away, m.players.away)}</div>
      </section>` : `<section class="panels">
        <div class="panel"><h3>${t("why")}</h3><p class="explain">${why}</p>
          ${m.correct_scores && m.correct_scores.length ? `<h3 style="margin-top:16px">${t("scores")}</h3><div class="scores">${m.correct_scores.map((s) => `<div><b>${esc(s.score)}</b><span>${pct(s.prob, 1)}</span></div>`).join("")}</div>` : ""}
        </div>
        ${sp !== "tennis" ? `<div class="panel"><h3>${t("projections")}</h3>
          <table class="cmp"><tbody>
            <tr><td><b>${(m.xg[0] + m.xg[1]).toFixed(1)}</b></td><td>${t("g_total")}</td><td>${m.odds.total ? "line " + m.odds.total : ""}</td></tr>
            <tr><td><b>${m.xg[0].toFixed(1)}</b></td><td>${esc(m.home_abbr || m.home)} ${t("t_total")}</td><td></td></tr>
            <tr><td><b>${m.xg[1].toFixed(1)}</b></td><td>${esc(m.away_abbr || m.away)} ${t("t_total")}</td><td></td></tr>
            <tr><td><b>${signed(+(m.xg[0] - m.xg[1]).toFixed(1))}</b></td><td>${t("margin")} (${esc(m.home_abbr || m.home)})</td><td></td></tr>
          </tbody></table></div>` : ""}
        <div class="panel" style="min-width:0"><h3>${t("markets")}</h3>
          <div class="table-wrap" style="border:0"><table class="std" style="min-width:420px"><thead><tr><th>${t("market")}</th><th>${t("model")}</th><th>${t("market_p")}</th><th>ProScore</th><th>${t("book")}</th><th>Edge</th></tr></thead><tbody>${rows}</tbody></table></div>
        </div>
        ${sp !== "tennis" ? `<div class="panel"><h3>${t("compare")}</h3>
          <table class="cmp"><tbody>
            <tr><td><b>${esc(m.home)}</b></td><td></td><td><b>${esc(m.away)}</b></td></tr>
            ${cmp(t("pf"), "pf")}${cmp(t("pa"), "pa")}${cmp(t("winr"), "win", pct)}${hs.over != null ? cmp(t("overr") + ` (${m.odds.total})`, "over", pct) : ""}
            <tr><td>${m.strength.home_att}</td><td>${t("att")}</td><td>${m.strength.away_att}</td></tr>
            <tr><td>${m.strength.home_def}</td><td>${t("def")}</td><td>${m.strength.away_def}</td></tr>
          </tbody></table></div>` : ""}
        <div class="panel"><h3>${t("h2h")}</h3>
          ${m.h2h.length ? `<table class="cmp"><tbody>${m.h2h.map((g) => `<tr><td>${fmtDate(g.date, { day: "2-digit", month: "2-digit", year: "2-digit" })}</td><td>${esc(g.home)} – ${esc(g.away)}</td><td class="mono"><b>${esc(g.score)}</b></td></tr>`).join("")}</tbody></table>` : `<p class="sub">${t("no_h2h")}</p>`}
        </div>
      </section>`}`;
  }

  // Results already graded in the track record are shown on match cards and coupons too,
  // whichever source supplied the score (so a finished game never stays "pending" on the page).
  function applySettled() {
    const tips = (DATA.history && DATA.history.tips) || {};
    const hc = (DATA.history && DATA.history.coupons) || {};
    for (const m of DATA.pred.matches || []) {
      const t = tips[m.id];
      if (!m.result && t && t.status !== "pending" && t.score) {
        const sc = String(t.score).split("-").map(Number);
        if (sc.length === 2 && sc.every((x) => !isNaN(x))) { m.result = sc; m.live = false; }
      }
    }
    for (const c of DATA.pred.coupons || []) {
      const h = hc[c.id];
      for (const p of c.picks) {
        const t = tips[p.id];
        if (t && t.status !== "pending" && t.score) {  // grade the leg on its own market
          const sc = String(t.score).split("-").map(Number);
          const w = tipWon(p.market, p.line, sc[0], sc[1]);
          p.score = t.score;
          p.status = w == null ? t.status : w ? "won" : "lost";
        }
      }
      const st = c.picks.map((p) => p.status || "pending");
      c.status = h && h.status !== "pending" ? h.status : st.includes("lost") ? "lost" : st.every((x) => x === "won") ? "won" : "pending";
    }
  }

  // ------------------------------------------------------------------ router
  function render() {
    const route = location.hash.replace(/^#\/?/, "");
    const app = $("#app");
    let html, nav = route || "home";
    if (route.startsWith("match-")) {
      const m = DATA.pred.matches[parseInt(route.slice(6), 10)];
      html = viewMatch(m ? m.id : ""); nav = "today";
    } else switch (route) {
      case "today": html = viewToday(); break;
      case "coupons": html = viewCoupons(); break;
      case "record": html = viewRecord(); break;
      case "tables": html = viewTables(); break;
      default: html = viewHome(); nav = "home";
    }
    app.innerHTML = html;
    document.querySelectorAll(".bottom-nav a").forEach((a) => a.classList.toggle("on", a.dataset.route === nav));
    document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
    $("#langLabel").textContent = lang.toUpperCase();
    document.documentElement.lang = lang;
    const banner = $("#demoBanner");
    banner.hidden = !DATA.pred.meta.demo;
    banner.textContent = t("demo");
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-f]");
    if (!b) return;
    state[b.dataset.f] = b.dataset.v;
    render();
  });
  $("#langBtn").addEventListener("click", () => {
    lang = lang === "en" ? "fr" : "en";
    try { localStorage.setItem("ps_lang", lang); } catch {}
    render();
  });
  window.addEventListener("hashchange", () => { render(); window.scrollTo(0, 0); });

  (async () => {
    const empty = { meta: { date: new Date().toISOString().slice(0, 10), generated_at: new Date().toISOString(), leagues: {}, record: {} }, matches: [], coupons: [] };
    [DATA.pred, DATA.history, DATA.tables, DATA.results, DATA.backtest] = await Promise.all([
      load("predictions", empty), load("history", {}), load("tables", {}), load("results", []), load("backtest", null),
    ]);
    applySettled();
    render();
  })();
})();
