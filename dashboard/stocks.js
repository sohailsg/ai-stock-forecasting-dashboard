/**
 * stocks.js — S10 core UI + S11 utilities (what-if horizon, CSV/PNG export, dark mode).
 * Lazy-loads per-ticker JSON, checks schema_version, persists state in URL hash.
 */
const DATA_DIR = "../output/stocks/";
const EXPECTED_SCHEMA = 1;

let chart = null;
let cmpChart = null;
const insightCharts = [];
const state = { ticker: "", range: 365, showMA20: true, showMA50: true, showFc: true, showAn: true, fcDays: 30, cmp: [], sector: "", q: "" };
let cache = {};
let indexData = null;

function nameOf(t) { return (typeof COMPANY_NAMES !== "undefined" && COMPANY_NAMES[t]) || t; }
// Chart-friendly name: full company name without legal suffix / bracketed note.
function chartName(t, short) {
  const n = short ? nameOf(t).replace(/\s*\(.*?\)\s*/g, " ") : nameOf(t);
  return n.replace(/,?\s+(Inc\.?|Corporation|Corp\.?|Limited|Ltd\.?|plc|N\.V\.|Incorporated|Company|Co\.)$/i, "").trim();
}
function labelOf(t) { return nameOf(t); }

// Replace ticker codes inside free text (e.g. build-time AI summaries) with full names.
let _tickerRe = null;
function expandTickers(text) {
  if (!text || typeof COMPANY_NAMES === "undefined") return text;
  if (!_tickerRe) {
    const codes = Object.keys(COMPANY_NAMES).map((t) => t.replace(/\.NS$/, ""))
      .filter((c) => c.length >= 3 && /^[A-Z0-9&-]+$/.test(c)).sort((a, b) => b.length - a.length)
      .map((c) => c.replace(/[&-]/g, "\\$&"));
    _tickerRe = new RegExp("\\b(" + codes.join("|") + ")(?:\\.NS)?(?![A-Za-z0-9])", "g");
  }
  const byCode = {};
  Object.keys(COMPANY_NAMES).forEach((t) => { byCode[t.replace(/\.NS$/, "")] = COMPANY_NAMES[t]; });
  return text.replace(_tickerRe, (m, c) => byCode[c] || m);
}

function symOf(t) {
  const code = (indexData.snapshot && indexData.snapshot[t] && indexData.snapshot[t].currency)
    || (cache[t] && cache[t].currency) || "USD";
  return code === "INR" ? "₹" : "$";
}

function fmtMoney(v, t) {
  if (v == null) return "—";
  return symOf(t) + Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Could not load ${path} (HTTP ${r.status})`);
  return r.json();
}

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("t")) state.ticker = h.get("t");
  if (h.get("r")) state.range = parseInt(h.get("r"), 10) || state.range;
  if (h.get("f")) state.fcDays = Math.max(5, Math.min(30, parseInt(h.get("f"), 10) || 30));
  if (h.get("c")) state.cmp = h.get("c").split(",").filter(Boolean).slice(0, 3);
}
function writeHash() {
  location.hash = `t=${state.ticker}&r=${state.range}&f=${state.fcDays}&c=${state.cmp.join(",")}`;
}

function setControls() {
  document.getElementById("t-ma20").checked = state.showMA20;
  document.getElementById("t-ma50").checked = state.showMA50;
  document.getElementById("t-fc").checked = state.showFc;
  document.getElementById("t-an").checked = state.showAn;
  document.querySelectorAll(".range-btn").forEach((b) =>
    b.setAttribute("aria-pressed", parseInt(b.dataset.range, 10) === state.range ? "true" : "false"));
  const hz = document.getElementById("horizon");
  hz.value = state.fcDays;
  document.getElementById("horizon-out").textContent = `${state.fcDays} days`;
}

function windowStats(closes) {
  // Metrics over the visible window only — null when too few points.
  const xs = closes.filter((v) => v != null);
  if (xs.length < 2) return null;
  const rets = [];
  for (let i = 1; i < xs.length; i++) rets.push(xs[i] / xs[i - 1] - 1);
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const sd = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / rets.length);
  let peak = xs[0], dd = 0;
  xs.forEach((v) => { peak = Math.max(peak, v); dd = Math.min(dd, v / peak - 1); });
  return {
    n: xs.length,
    change: (xs[xs.length - 1] / xs[0] - 1) * 100,
    volatility: rets.length >= 10 ? sd * Math.sqrt(252) : null,
    sharpe: rets.length >= 10 && sd > 0 ? (mean / sd) * Math.sqrt(252) : null,
    drawdown: dd * 100,
    last: xs[xs.length - 1],
  };
}

function rangeName() {
  return { 30: "1M", 180: "6M", 365: "1Y", 1825: "5Y" }[state.range] || `${state.range}d`;
}

function sliceRange(payload) {
  const n = Math.min(state.range, payload.dates.length);
  const cut = payload.dates.length - n;
  return {
    dates: payload.dates.slice(cut),
    close: payload.close.slice(cut),
    ma20: payload.ma20.slice(cut),
    ma50: payload.ma50.slice(cut),
  };
}

function palette() {
  const dark = document.documentElement.dataset.theme === "dark";
  return {
    close: dark ? "#8fa6ff" : "#4361ee",
    ma20: dark ? "#ffa76b" : "#f3722c",
    ma50: dark ? "#5fd6b5" : "#43aa8b",
    fc: dark ? "#d0a2ff" : "#7209b7",
    anomaly: "#e63946",
  };
}

function render(payload) {
  const s = sliceRange(payload);
  const fc = payload.forecast;
  const c = palette();
  const fd = state.showFc ? Math.min(state.fcDays, fc.dates.length) : 0;
  const fcDates = fc.dates.slice(0, fd);
  const labels = [...s.dates, ...fcDates];
  const histN = s.dates.length;

  const datasets = [{
    label: "Close",
    data: [...s.close, ...Array(fd).fill(null)],
    borderColor: c.close, backgroundColor: c.close + "22",
    fill: false, pointRadius: 0, tension: 0.2, spanGaps: true, borderWidth: 2,
  }];
  if (state.showMA20) datasets.push({ label: "MA20", data: [...s.ma20, ...Array(fd).fill(null)], borderColor: c.ma20, pointRadius: 0, tension: 0.2, spanGaps: true, borderWidth: 1.5 });
  if (state.showMA50) datasets.push({ label: "MA50", data: [...s.ma50, ...Array(fd).fill(null)], borderColor: c.ma50, pointRadius: 0, tension: 0.2, spanGaps: true, borderWidth: 1.5 });
  if (fd > 0) {
    const mean = fc.mean.slice(0, fd), lo = fc.lower.slice(0, fd), hi = fc.upper.slice(0, fd);
    datasets.push({ label: "Forecast", data: [...Array(histN - 1).fill(null), s.close[s.close.length - 1], ...mean], borderColor: c.fc, borderDash: [6, 4], pointRadius: 0, tension: 0.2, spanGaps: true, borderWidth: 2 });
    datasets.push({ label: "Upper 95%", data: [...Array(histN).fill(null), ...hi], borderColor: c.fc + "33", backgroundColor: c.fc + "26", fill: "+1", pointRadius: 0, borderWidth: 1 });
    datasets.push({ label: "Lower 95%", data: [...Array(histN).fill(null), ...lo], borderColor: c.fc + "33", fill: false, pointRadius: 0, borderWidth: 1 });
  }
  if (state.showAn) {
    const idx = new Map(s.dates.map((d, i) => [d, i]));
    const markers = Array(labels.length).fill(null);
    (payload.anomalies || []).forEach((a) => {
      if (idx.has(a.date)) markers[idx.get(a.date)] = s.close[idx.get(a.date)];
    });
    datasets.push({ label: "Anomaly", data: markers, type: "scatter", backgroundColor: c.anomaly, pointRadius: 5, pointHoverRadius: 7 });
  }

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById("chart-main"), {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: labels.length > 800 ? false : undefined,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 14, padding: 14, filter: (l) => !/Upper|Lower/.test(l.text) } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed.y;
              if (v == null) return null;
              const s = symOf(payload.ticker);
              if (ctx.dataset.label === "Anomaly") return ` Anomaly: ${s}${v.toFixed(2)}`;
              return ` ${ctx.dataset.label}: ${s}${v.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 10, maxRotation: 0 }, title: { display: true, text: "Date" } },
        y: { beginAtZero: false, ticks: { callback: (v) => `${symOf(payload.ticker)}${v.toLocaleString()}` }, title: { display: true, text: `Price (${symOf(payload.ticker) === "₹" ? "INR" : "USD"})` } },
      },
    },
  });

  const st = payload.stats, bt = payload.backtest;
  const set = (id, txt) => {
    const el = document.getElementById(id);
    el.classList.remove("loading");
    el.textContent = txt;
  };
  // Window-aware metrics: everything follows the selected history range.
  // "Last close" is always the latest price (every window ends today).
  const w = windowStats(s.close) || {};
  const rn = rangeName();
  const setLabel = (id, txt) => { document.getElementById(id).textContent = txt; };
  set("kpi-close", fmtMoney(st.last_close, payload.ticker));
  set("kpi-chg", w.change == null ? "—" : `${w.change > 0 ? "+" : ""}${w.change.toFixed(2)}%`);
  setLabel("kpi-chg-label", `Change · ${rn}`);
  set("kpi-vol", w.volatility == null ? "—" : w.volatility.toFixed(4));
  setLabel("kpi-vol-label", `Volatility · ${rn}`);
  set("kpi-sharpe", w.sharpe == null ? "—" : w.sharpe.toFixed(3));
  setLabel("kpi-sharpe-label", `Sharpe · ${rn}`);
  set("kpi-dd", w.drawdown == null ? "—" : `${w.drawdown.toFixed(2)}%`);
  setLabel("kpi-dd-label", `Drawdown · ${rn}`);
  const conf = confidence(bt);
  set("kpi-bt", bt && bt.model_mape != null ? `${conf.level} · ±${bt.model_mape}%` : "—");
  document.getElementById("chart-title").textContent =
    `${nameOf(payload.ticker)} · ${payload.forecast.method} · next ${fd}d`;
  document.getElementById("ai-insight").textContent =
    expandTickers(liveInsight(payload, s, windowStats(s.close))) || "No insight available.";
  document.getElementById("ai-tag").textContent = `Forecast confidence: ${conf.level} — ${conf.text}`;
  document.getElementById("live-insight").textContent = liveNarrative(payload, s);
  {
    const inWin = new Set(s.dates);
    const nAn = (payload.anomalies || []).filter((a) => inWin.has(a.date)).length;
    const fd = state.showFc ? Math.min(state.fcDays, payload.forecast.mean.length) : 0;
    document.getElementById("ai-live").textContent =
      `In this ${rangeName()} view: ${w.change == null ? "—" : `${w.change > 0 ? "+" : ""}${w.change.toFixed(1)}%`} ` +
      `with ${nAn} anomal${nAn === 1 ? "y" : "ies"}${state.showFc ? `; showing ${fd} of ${payload.forecast.mean.length} forecast days` : "; forecast hidden"}. ` +
      ``;
  }
  renderNews(payload);
  const ul = document.getElementById("anomaly-list");
  ul.innerHTML = "";
  const anomalies = payload.anomalies || [];
  if (!anomalies.length) ul.innerHTML = "<li>No anomalies flagged in this window.</li>";
  anomalies.slice(0, 10).forEach((a) => {
    const li = document.createElement("li");
    const s = symOf(payload.ticker);
    li.textContent = `${a.date}: ${s}${a.price} (${a.return_pct > 0 ? "+" : ""}${a.return_pct}%, z=${a.z})`;
    ul.appendChild(li);
  });
  if (indexData.snapshot) {
    renderMarket();
    if (state._chartSector !== activeSector()) { state._chartSector = activeSector(); renderInsightCharts(); }
  }
}

function renderNews(payload) {
  const box = document.getElementById("news-box");
  const items = payload.news || [];
  const ai = (indexData.news_insights || {})[payload.ticker];
  if (!items.length && !ai) { box.hidden = true; return; }
  box.hidden = false;
  document.getElementById("news-insight").textContent = ai
    ? expandTickers(ai.text)
    : "Recent headlines are listed below; the AI reading will appear after the next scheduled refresh.";
  document.getElementById("news-tag").textContent = ai
    ? `(AI reading of recent headlines, ${ai.as_of || "latest refresh"} — educational only)`
    : "(recent headlines)";
  const ol = document.getElementById("news-list");
  ol.innerHTML = "";
  const cited = new Set(ai ? ai.cites : []);
  items.forEach((h, i) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = h.link; a.target = "_blank"; a.rel = "noopener noreferrer";
    a.textContent = h.title;
    li.appendChild(a);
    li.appendChild(document.createTextNode(` — ${h.source}${h.date ? ", " + h.date : ""}`));
    if (cited.has(i + 1)) li.style.fontWeight = "600";
    ol.appendChild(li);
  });
}

function currentCSV() {
  const p = cache[state.ticker];
  if (!p) return;
  const s = sliceRange(p);
  const rows = ["date,close,ma20,ma50"];
  s.dates.forEach((d, i) => rows.push(`${d},${s.close[i] ?? ""},${s.ma20[i] ?? ""},${s.ma50[i] ?? ""}`));
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${state.ticker}_${state.range}d.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function currentPNG() {
  if (!chart) return;
  const a = document.createElement("a");
  const bg = document.documentElement.dataset.theme === "dark" ? "#1a2233" : "#ffffff";
  const tmp = document.createElement("canvas");
  tmp.width = chart.canvas.width; tmp.height = chart.canvas.height;
  const ctx = tmp.getContext("2d");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, tmp.width, tmp.height);
  ctx.drawImage(chart.canvas, 0, 0);
  a.href = tmp.toDataURL("image/png");
  a.download = `${state.ticker}_chart.png`;
  a.click();
}

/* ── Live narrative: recomputed on every state change ────────────────────
   Plain-language, data-driven commentary. Moves with ticker, range,
   horizon and compare picks — nothing hardcoded. */

function confidence(bt) {
  if (!bt || bt.model_mape == null) return { level: "Unknown", text: "not enough history to judge" };
  const miss = `typically off by ~${bt.model_mape}% when replayed on the last 30 days`;
  if (bt.verdict === "beats naive") return { level: "High", text: `reasonably reliable (${miss})` };
  if (bt.verdict === "comparable") return { level: "Medium", text: `no better than assuming tomorrow equals today (${miss})` };
  return { level: "Low", text: `weak, treat the projection as decoration (${miss})` };
}

function plainVerdict(bt) { return confidence(bt).text; }

function liveInsight(payload, s, w) {
  if (!w || w.change == null) return "";
  const t = payload.ticker, nm = nameOf(t), rn = rangeName(), sym = symOf(t);
  const closes = s.close.filter((v) => v != null);
  const n = closes.length;
  if (n < 8) return `${nm}: too little history in this view to reason about.`;
  const pc = (a, b) => (a / b - 1) * 100;
  const f1 = (x) => `${x >= 0 ? "+" : ""}${x.toFixed(1)}%`;
  const last = w.last;
  const hi = Math.max(...closes);
  const ma20 = s.ma20[s.ma20.length - 1], ma50 = s.ma50[s.ma50.length - 1];
  const half = Math.floor(n / 2);
  const firstHalf = pc(closes[half], closes[0]), secondHalf = pc(last, closes[half]);
  const recentN = Math.min(10, n - 1);
  const recent = pc(last, closes[n - 1 - recentN]);
  const own1m = pc(last, closes[Math.max(0, n - 22)]);
  const up = w.change > 0;

  // Knowledge + peer context
  const sec = sectorOf(t);
  const ind = INDUSTRY[sec] || null;
  const co = companyFacts(t);
  const snap = indexData.snapshot || {};
  const mates = Object.entries(snap).filter(([k, v]) => k !== t && v.change_1m != null && (v.sector || sectorOf(k)) === sec);
  const indAvg = mates.length ? mates.reduce((a, [, v]) => a + v.change_1m, 0) / mates.length : null;
  const rank = mates.length ? 1 + mates.filter(([, v]) => v.change_1m > own1m).length : null;
  const matesUp = mates.filter(([, v]) => v.change_1m > 0).length;
  const volMates = mates.filter(([, v]) => v.volatility != null).map(([, v]) => v.volatility);
  const indVol = volMates.length ? volMates.reduce((a, b) => a + b, 0) / volMates.length : null;
  const inr = snap[t] && snap[t].currency === "INR";
  const mkt = snap[inr ? "^NSEI" : "^GSPC"];
  const mktName = inr ? "India's NIFTY 50" : "the S&P 500";
  const peers = ((indexData.peers || {})[t] || {}).high || [];
  const twin = peers.find(([b]) => snap[b] && snap[b].change_1m != null && !isBench(b));
  const gap = indAvg == null ? null : own1m - indAvg;
  const tide = gap != null && Math.abs(gap) < 2.5;

  const out = [];

  // 1. What the price is doing
  let regime, why;
  if (Math.abs(w.change) < 3) {
    regime = `${nm} has gone nowhere over the ${rn} (${f1(w.change)})`;
    why = w.volatility != null && w.volatility > 0.3
      ? "yet it swung hard on the way, so the flat result hides a real tug-of-war between buyers and sellers"
      : "and it did so quietly, a sign that little new information is reaching the price";
  } else if (up && recent >= 0 && (ma20 == null || last >= ma20)) {
    regime = `${nm} is climbing: ${f1(w.change)} over the ${rn}, still ${f1(recent)} in the last ${recentN} sessions`;
    why = secondHalf > firstHalf ? "and the pace is quickening, so buyers are still arriving" : "although the pace has cooled from the first half, the direction has not broken";
  } else if (up) {
    regime = `${nm} gained ${Math.abs(w.change).toFixed(1)}% over the ${rn}, but the rally is stalling (${f1(recent)} lately${ma20 != null && last < ma20 ? ", below its 20-day average" : ""})`;
    why = "gains that stall like this often mean early buyers are taking profit";
  } else if (recent > 2 && (ma20 == null || last >= ma20)) {
    regime = `${nm} fell ${Math.abs(w.change).toFixed(1)}% over the ${rn} but is bouncing (${f1(recent)} in ${recentN} sessions)`;
    why = ma50 != null && last < ma50 ? "it still has to clear the 50-day average, so for now this is a rebound inside a downtrend" : "holding above both averages would turn the bounce into a recovery";
  } else {
    regime = `${nm} is sliding: ${f1(w.change)} over the ${rn}${ma50 != null && last < ma50 ? ", under its 50-day average" : ""}`;
    why = recent < 0 ? `and it has not paused (${f1(recent)} in the last ${recentN} sessions)` : "though the latest sessions are steadier, the first hint that selling is easing";
  }
  out.push(`${regime} — ${why}.`);

  // 2. The business behind the chart + why this move makes sense for it
  if (co && ind) {
    const reason = up ? ind.up : ind.down;
    if (tide) {
      out.push(`${nm} ${co.what}. Its last month (${f1(own1m)}) matched the rest of ${sec} (${f1(indAvg)} on average; ${matesUp} of ${mates.length} peers rose), so the explanation is most likely industry-wide, since stocks in this industry tend to move on ${reason}. What sets ${nm} apart is that ${co.hinge}. Industry drivers to track: ${ind.watch}.`);
    } else if (gap > 0) {
      out.push(`${nm} ${co.what}, and ${co.hinge}. It beat its ${sec} peers by ${gap.toFixed(1)} points over the last month (${f1(own1m)} vs ${f1(indAvg)}, #${rank} of ${mates.length + 1}), which is company-specific strength rather than a rising tide; the most plausible source is whichever part of that story improved, since the wider industry only managed ${f1(indAvg)}.`);
    } else {
      out.push(`${nm} ${co.what}, and ${co.hinge}. It trailed its ${sec} peers by ${Math.abs(gap).toFixed(1)} points over the last month (${f1(own1m)} vs ${f1(indAvg)}, #${rank} of ${mates.length + 1}), so the problem is more likely inside the company than across the industry; the first place to look is the company-specific story above, not the industry-wide drivers.`);
    }
  } else if (ind) {
    out.push(`${sec} ${ind.engine}; moves in it usually trace to ${up ? ind.up : ind.down}.`);
  }

  // 3. Quality of the move relative to what is normal for this industry
  if (w.sharpe != null && w.volatility != null) {
    let q;
    const rel = indVol ? w.volatility / indVol : null;
    const relTxt = "";
    const relSent = rel == null ? "" : rel > 1.3 ? ` It is ${rel.toFixed(1)}x as jumpy as the typical ${sec} stock.` : rel < 0.75 ? ` It is calmer than the typical ${sec} stock.` : "";
    if (up && w.sharpe > 1) q = `The gain was efficient (Sharpe ${w.sharpe.toFixed(2)}${relTxt}), so holders were paid well for the risk.`;
    else if (up && w.sharpe > 0) q = `The gain was real but costly in nerves: volatility of ${w.volatility.toFixed(2)}${relTxt} absorbed most of the reward (Sharpe ${w.sharpe.toFixed(2)}).`;
    else if (!up && w.drawdown < -20) q = `The fall was deep: at its worst it sat ${Math.abs(w.drawdown).toFixed(0)}% below an earlier peak, which needs a ${(100 / (1 + w.drawdown / 100) - 100).toFixed(0)}% rise just to get back to even${relTxt}.`;
    else q = `Holders were not paid for the risk (Sharpe ${w.sharpe.toFixed(2)}${relTxt}).`;
    out.push(q + relSent);
  }

  // 4. Cross-checks: market and closest co-mover
  const cross = [];
  if (mkt && mkt.change_1m != null) {
    const rel = own1m - mkt.change_1m;
    cross.push(`against ${mktName} (${f1(mkt.change_1m)}), it ${rel >= 0 ? "outran" : "lagged"} the market by ${Math.abs(rel).toFixed(1)} points`);
  }
  if (twin) {
    const [b, c] = twin, bc = snap[b].change_1m;
    cross.push(`its closest co-mover, ${nameOf(b)} (correlation ${c.toFixed(2)}), ${Math.abs(bc) < 0.5 ? "was flat, so it neither confirms nor contradicts the move" : `${Math.sign(bc) === Math.sign(own1m) ? "confirms" : "contradicts"} it, ${bc >= 0 ? "up" : "down"} ${Math.abs(bc).toFixed(1)}%`}`);
  }
  if (cross.length) out.push(`${cross[0][0].toUpperCase()}${cross[0].slice(1)}${cross.length > 1 ? `; ${cross[1]}` : ""}.`);

  // 5. Levels, and the biggest shock in terms of what is normal for this stock
  const watch = [];
  if (ma50 != null) {
    const lv = `${sym}${ma50.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    watch.push(last >= ma50 ? `a close under the 50-day average (${lv}) would damage the trend` : `a close back above the 50-day average (${lv}) is the first sign of repair`);
  }
  const offHigh = pc(last, hi);
  if (offHigh > -2) watch.push(`it is pressing on its ${rn} high, where earlier buyers may sell`);
  else if (offHigh < -15) watch.push(`it is still ${Math.abs(offHigh).toFixed(0)}% under its ${rn} high, leaving plenty of trapped holders above`);
  const inWin = new Set(s.dates);
  const an = (payload.anomalies || []).filter((a) => inWin.has(a.date)).sort((a, b) => Math.abs(b.return_pct) - Math.abs(a.return_pct))[0];
  if (an && w.volatility) {
    const normal = (w.volatility / Math.sqrt(252)) * 100;
    const mult = Math.abs(an.return_pct) / normal;
    if (mult >= 3) watch.push(`its biggest single day (${an.return_pct > 0 ? "+" : ""}${an.return_pct}% on ${an.date}) was about ${mult.toFixed(0)}x a normal day for this stock${ind && ind.shock ? `; ${ind.shock}` : ""}`);
  }
  if (watch.length) out.push(`What to watch: ${watch.join("; ")}.`);

  // 6. How much to trust the projection
  const conf = confidence(payload.backtest);
  const fc = payload.forecast;
  if (fc && fc.mean && fc.mean.length && fc.upper && fc.lower) {
    const k = fc.mean.length - 1;
    const width = (fc.upper[k] - fc.lower[k]) / 2 / last * 100;
    out.push(`The statistical projection leans ${fc.mean[k] >= last ? "up" : "down"}, but its band is about ±${width.toFixed(0)}% and it earned ${conf.level.toLowerCase()} confidence when replayed on past data, so it cannot know how ${co ? co.hinge.replace(/^its stock hinges on /, "") : "company news"} will play out.`);
  }
  return out.join(" ");
}

function liveNarrative(payload, s) {
  const t = payload.ticker, sym = symOf(t);
  const closes = s.close.filter((v) => v != null);
  if (!closes.length) return "";
  const first = closes[0], last = closes[closes.length - 1];
  const pct = ((last / first - 1) * 100);
  const days = s.dates.length;
  const ma20 = s.ma20[s.ma20.length - 1], ma50 = s.ma50[s.ma50.length - 1];
  const maBits = [];
  if (ma20 != null) maBits.push(`its 20-day average (${sym}${ma20.toLocaleString()}) — roughly the last month's memory — price sits ${last >= ma20 ? "above it, buyers in charge lately" : "below it, sellers in charge lately"}`);
  if (ma50 != null) maBits.push(`its 50-day average (${sym}${ma50.toLocaleString()}) — the 2½-month trend — price sits ${last >= ma50 ? "above" : "below"} it`);
  let fcBit = "forecast hidden";
  if (state.showFc) {
    const fd = Math.min(state.fcDays, payload.forecast.mean.length);
    const fLast = payload.forecast.mean[fd - 1];
    const fPct = ((fLast / last - 1) * 100);
    fcBit = `the model stretches the trend ${fd} days to ${sym}${fLast.toLocaleString()} (${fPct >= 0 ? "+" : ""}${fPct.toFixed(1)}%), and its track record is ${plainVerdict(payload.backtest)}`;
  }
  return `You're looking at ${nameOf(t)} (${sectorOf(t)}) over the last ${days} trading days: ` +
    `${sym}${first.toLocaleString()} → ${sym}${last.toLocaleString()} (${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%). ` +
    (maBits.length ? `Against trend lines: ${maBits.join("; ")}.` : "") +
    ` Ahead: ${fcBit}.`;
}

function compareNarrative() {
  const el = document.getElementById("cmp-insight");
  if (!state.cmp.length) { el.textContent = ""; return; }
  const rows = state.cmp
    .filter((t) => cache[t])
    .map((t) => {
      const p = cache[t];
      const n = Math.min(state.range, p.dates.length);
      const closes = p.close.slice(-n).filter((v) => v != null);
      const chg = ((closes[closes.length - 1] / closes[0] - 1) * 100);
      const snap = (indexData.snapshot || {})[t] || {};
      return { t, chg, vol: snap.volatility, verdict: snap.verdict, sector: sectorOf(t) };
    });
  if (rows.length < 2) {
    el.textContent = rows.length
      ? `${nameOf(rows[0].t)}: ${rows[0].chg >= 0 ? "+" : ""}${rows[0].chg.toFixed(1)}% over this stretch. Pick a second stock to compare.`
      : "";
    return;
  }
  rows.sort((a, b) => b.chg - a.chg);
  const [win, ...rest] = rows;
  const lose = rest[rest.length - 1];
  const calm = [...rows].sort((a, b) => (a.vol ?? 9) - (b.vol ?? 9))[0];
  el.textContent =
    `${nameOf(win.t)} grew most here (${win.chg >= 0 ? "+" : ""}${win.chg.toFixed(1)}%) while ` +
    `${nameOf(lose.t)} trailed (${lose.chg >= 0 ? "+" : ""}${lose.chg.toFixed(1)}%). ` +
    `Calmest ride: ${nameOf(calm.t)} (volatility ${calm.vol ?? "—"}). ` +
    `On forecast honesty: ${rows.map((r) => `${nameOf(r.t)} is ${r.verdict || "unrated"}`).join("; ")}. ` +
    `Educational comparison only — not advice.`;
}

async function selectTicker(t) {
  state.ticker = t;
  state.fcDays = Math.min(state.fcDays, 30);
  writeHash();
  setControls();
  document.getElementById("ai-insight").textContent = "Loading…";
  if (!cache[t]) {
    const p = await loadJSON(`${DATA_DIR}${t}.json`);
    if (p.schema_version !== EXPECTED_SCHEMA) throw new Error(`Schema mismatch for ${t} (expected ${EXPECTED_SCHEMA})`);
    cache[t] = p;
  }
  // Clamp horizon slider to available forecast length
  const hz = document.getElementById("horizon");
  hz.max = Math.min(30, cache[t].forecast.dates.length);
  state.fcDays = Math.min(state.fcDays, parseInt(hz.max, 10));
  setControls();
  render(cache[t]);
}

/* ── Sectors, search, market overview, ranking ─────────────────────────── */

// Industry in focus: the one picked in the filter, else the inspected stock's own.
function activeSector() { return state.sector || (state.ticker ? sectorOf(state.ticker) : ""); }

function sectorOf(t) {
  return (indexData.sectors && indexData.sectors[t]) || "Other";
}

function buildTickerOptions() {
  const sel = document.getElementById("ticker");
  sel.innerHTML = "";
  const groups = {};
  indexData.tickers.forEach((t) => {
    if (state.sector && sectorOf(t) !== state.sector) return;
    if (state.q && !(t + " " + nameOf(t)).toLowerCase().includes(state.q)) return;
    (groups[sectorOf(t)] = groups[sectorOf(t)] || []).push(t);
  });
  Object.keys(groups).sort().forEach((g) => {
    const og = document.createElement("optgroup");
    og.label = g;
    groups[g].forEach((t) => {
      const o = document.createElement("option");
      o.value = t; o.textContent = labelOf(t);
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
  if (![...sel.options].some((o) => o.value === state.ticker)) {
    state.ticker = sel.options.length ? sel.options[0].value : "";
  }
  sel.value = state.ticker;
}

function verdictClass(v) {
  return v === "beats naive" ? "verdict-beats" : (v === "worse than naive" ? "verdict-worse" : "");
}

function industryInsight() {
  const rows = inView();
  const sec = activeSector();
  if (rows.length < 2) return `${sec}: not enough companies with data to read this industry.`;
  const by = [...rows].sort((a, b) => b[1].change_1m - a[1].change_1m);
  const avg = rows.reduce((a, [, v]) => a + v.change_1m, 0) / rows.length;
  const up = rows.filter(([, v]) => v.change_1m > 0).length;
  const volRows = rows.filter(([, v]) => v.volatility != null).sort((a, b) => b[1].volatility - a[1].volatility);
  const f = (x) => `${x > 0 ? "+" : ""}${x.toFixed(1)}%`;
  return `${sec} industry, last month: ${up} of ${rows.length} companies rose, average move ${f(avg)}. ` +
    `Best: ${nameOf(by[0][0])} (${f(by[0][1].change_1m)}); weakest: ${nameOf(by[by.length - 1][0])} (${f(by[by.length - 1][1].change_1m)}).` +
    (volRows.length ? ` Bumpiest ride: ${nameOf(volRows[0][0])} (volatility ${volRows[0][1].volatility}).` : "");
}

function renderMarket() {
  document.getElementById("market-insight").textContent = expandTickers(industryInsight());
  const mh = document.getElementById("market-tag");
  if (mh) mh.textContent = `(${activeSector() || "all"} industry — ${inView().length} companies)`;
  // Sector cards: average 1M change per sector
  const snap = indexData.snapshot || {};
  const bySec = {};
  Object.entries(snap).forEach(([t, v]) => {
    if (v.change_1m == null) return;
    const s = v.sector || sectorOf(t);
    (bySec[s] = bySec[s] || []).push(v.change_1m);
  });
  const wrap = document.getElementById("sector-cards");
  wrap.innerHTML = "";
  Object.keys(bySec).sort().forEach((s) => {
    const arr = bySec[s];
    const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
    const div = document.createElement("div");
    div.className = "card";
    div.style.cursor = "pointer";
    div.setAttribute("role", "button");
    div.tabIndex = 0;
    div.title = `Filter to ${s}`;
    div.innerHTML = `<h2></h2><p class="kpi-value" style="font-size:1.25rem"></p><p class="kpi-sub"></p>`;
    div.querySelector("h2").textContent = s;
    div.querySelector(".kpi-value").textContent = `${avg > 0 ? "+" : ""}${avg.toFixed(1)}%`;
    div.querySelector(".kpi-sub").textContent = `${arr.length} stock${arr.length > 1 ? "s" : ""} · avg 1M — click to filter`;
    const pick = () => {
      state.sector = state.sector === s ? "" : s;
      document.getElementById("sector").value = state.sector;
      buildTickerOptions();
      renderInsightCharts();
      renderMarket();
      resetCmpToIndustry();
      updateCompare().catch((e) => console.error(e));
      document.getElementById("sector").scrollIntoView({ behavior: "smooth", block: "center" });
    };
    div.addEventListener("click", pick);
    div.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    wrap.appendChild(div);
  });
  // Ranking table by 1M change
  const rows = Object.entries(snap)
    .filter(([, v]) => v.change_1m != null)
    .filter(([t, v]) => (v.sector || sectorOf(t)) === activeSector())
    .sort((a, b) => b[1].change_1m - a[1].change_1m);
  const tb = document.querySelector("#rank-table tbody");
  tb.innerHTML = "";
  rows.forEach(([t, v], i) => {
    const tr = document.createElement("tr");
    if (t === state.ticker) tr.className = "me";
    tr.innerHTML = `<td>${i + 1}</td><td><a href="#" data-goto="${t}"><strong>${nameOf(t)}</strong></a></td>` +
      `<td>${v.sector || sectorOf(t)}</td>` +
      `<td style="text-align:right">${v.change_1m > 0 ? "+" : ""}${v.change_1m}%</td>` +
      `<td style="text-align:right">${v.volatility ?? "—"}</td>` +
      `<td style="text-align:right">${v.sharpe ?? "—"}</td>` +
      `<td class="${verdictClass(v.verdict)}">${v.verdict ?? "—"}</td>`;
    tb.appendChild(tr);
  });
  tb.querySelectorAll("[data-goto]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    selectTicker(a.dataset.goto).catch((err) => showError(err));
    document.getElementById("chart-title").scrollIntoView({ behavior: "smooth", block: "center" });
  }));
}

/* ── Compare mode (rebased to 100, date-aligned) ─────────────────────────── */

const CMP_COLORS = ["#4361ee", "#e63946", "#43aa8b"];

function renderCmpPicks() {
  const wrap = document.getElementById("cmp-picks");
  wrap.innerHTML = "";
  indexData.tickers.filter((t) => sectorOf(t) === activeSector() || state.cmp.includes(t)).forEach((t) => {
    const lab = document.createElement("label");
    lab.className = "pill";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = state.cmp.includes(t);
    cb.disabled = !cb.checked && state.cmp.length >= 3;
    cb.addEventListener("change", () => {
      if (cb.checked) state.cmp.push(t);
      else state.cmp = state.cmp.filter((x) => x !== t);
      writeHash();
      updateCompare().catch((e) => console.error(e));
    });
    lab.append(cb, document.createTextNode(` ${labelOf(t)}`));
    wrap.appendChild(lab);
  });
}

async function ensureLoaded(t) {
  if (!cache[t]) {
    const p = await loadJSON(`${DATA_DIR}${t}.json`);
    if (p.schema_version !== EXPECTED_SCHEMA) throw new Error(`Schema mismatch for ${t}`);
    cache[t] = p;
  }
  return cache[t];
}

async function updateCompare() {
  renderCmpPicks();
  renderPairs();
  if (cmpChart) { cmpChart.destroy(); cmpChart = null; }
  compareNarrative();
  if (!state.cmp.length) return;
  const picks = state.cmp.slice(0, 3);
  await Promise.all(picks.map(ensureLoaded));
  // Intersect dates across markets, then take the selected range tail
  const maps = picks.map((t) => new Map(cache[t].dates.map((d, i) => [d, cache[t].close[i]])));
  const common = maps[0] instanceof Map
    ? [...maps[0].keys()].filter((d) => maps.every((m) => m.has(d))).sort()
    : [];
  const tail = common.slice(-Math.min(state.range, common.length));
  if (tail.length < 5) return;
  const datasets = picks.map((t, i) => {
    const base = maps[i].get(tail[0]);
    return {
      label: nameOf(t),
      data: tail.map((d) => {
        const v = maps[i].get(d);
        return v != null && base ? +(v / base * 100).toFixed(2) : null;
      }),
      borderColor: CMP_COLORS[i % CMP_COLORS.length],
      pointRadius: 0, tension: 0.2, spanGaps: true, borderWidth: 2,
    };
  });
  cmpChart = new Chart(document.getElementById("chart-cmp"), {
    type: "line",
    data: { labels: tail, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, maxRotation: 0 }, title: { display: true, text: "Date" } },
        y: { ticks: { callback: (v) => `${v}` }, title: { display: true, text: "Growth of 100 invested" } },
      },
    },
  });
}

function resetCmpToIndustry() {
  if (!state.sector) return;
  const own = indexData.tickers.filter((t) => sectorOf(t) === state.sector);
  const keep = state.cmp.filter((t) => sectorOf(t) === state.sector);
  state.cmp = [...new Set([...keep, ...own])].slice(0, Math.max(2, keep.length)).slice(0, 3);
  writeHash();
}

function comparePair(a, b) {
  state.cmp = [a, b];
  writeHash();
  updateCompare().catch((e) => console.error(e));
  document.getElementById("chart-cmp").scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ── Diversification pairs (heatmap replacement) ─────────────────────────
   Each list entry answers: "which two stocks move (least/most) together?" */

function renderPairs() {
  // Anchor = the companies being compared, else the stock being inspected.
  const anchors = state.cmp.length ? state.cmp.slice(0, 3) : (state.ticker ? [state.ticker] : []);
  const peers = indexData.peers || {};
  const fill = (elId, kind) => {
    const ul = document.getElementById(elId);
    ul.innerHTML = "";
    if (!anchors.length) { ul.innerHTML = "<li>Pick a company first.</li>"; return; }
    anchors.forEach((a) => {
      const list = (peers[a] && peers[a][kind]) || [];
      const li = document.createElement("li");
      const h = document.createElement("strong");
      h.textContent = nameOf(a);
      li.appendChild(h);
      if (!list.length) {
        li.appendChild(document.createTextNode(" — relations appear after the next data refresh."));
      }
      list.forEach(([b, v]) => {
        const btn = document.createElement("button");
        btn.className = "btn";
        btn.style.margin = "0.15rem 0.25rem 0.15rem 0";
        btn.textContent = `${nameOf(b)} (${v.toFixed(2)})`;
        btn.title = `Compare ${nameOf(a)} vs ${nameOf(b)} — ${sectorOf(b)}`;
        btn.addEventListener("click", () => comparePair(a, b));
        li.appendChild(document.createElement("br"));
        li.appendChild(btn);
      });
      ul.appendChild(li);
    });
  };
  const who = anchors.map(nameOf).join(", ");
  document.getElementById("pairs-title").textContent = who ? `Relation of ${who} with other companies` : "";
  fill("pairs-high", "high");
  fill("pairs-low", "low");
}

/* ── Analyst insight charts: one question per graph ─────────────────────── */

function inView() {
  // Stocks currently in view (sector filter applies; benchmarks marked ★)
  return Object.entries(indexData.snapshot || {})
    .filter(([, v]) => v.change_1m != null)
    .filter(([t]) => (indexData.snapshot[t].sector || sectorOf(t)) === activeSector());
}

function killInsights() {
  insightCharts.forEach((c) => c.destroy());
  insightCharts.length = 0;
}

function isBench(t) {
  return sectorOf(t) === "Benchmark";
}

function renderInsightCharts() {
  killInsights();
  const rows = inView();
  if (!rows.length) return;
  const dark = document.documentElement.dataset.theme === "dark";
  const up = dark ? "#5fd6b5" : "#1e9e6a";
  const down = "#e63946";
  const gray = "#9aa4b2";
  // Tall bars stay readable: ~30px per row for the horizontal bar charts
  const fitHeight = (id, n) => {
    document.getElementById(id).parentElement.style.height =
      `${Math.max(340, Math.min(n, 45) * 30)}px`;
  };

  // 1. Who's winning? — 1M return bars, sorted
  {
    const sorted = [...rows].sort((a, b) => a[1].change_1m - b[1].change_1m);
    fitHeight("chart-perf", sorted.length);
    const labels = sorted.map(([t]) => chartName(t) + (isBench(t) ? " ★" : ""));
    insightCharts.push(new Chart(document.getElementById("chart-perf"), {
      type: "bar",
      data: { labels, datasets: [{ data: sorted.map(([, v]) => v.change_1m),
        backgroundColor: sorted.map(([, v]) => (v.change_1m >= 0 ? up : down)), borderRadius: 4 } ] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` 1M return: ${c.parsed.x > 0 ? "+" : ""}${c.parsed.x}%` } } },
        scales: {
          x: { title: { display: true, text: "Return, last 30 days (%)" } },
          y: { title: { display: true, text: "Stock" } },
        } },
    }));
  }

  // 2. Risk vs reward — scatter, labelled points
  {
    const pts = rows.map(([t, v]) => ({ x: v.volatility, y: v.change_1m, t }));
    const labelPlugin = {
      id: "ptlabels",
      afterDatasetsDraw(c) {
        const ctx = c.ctx;
        ctx.save();
        ctx.font = "11px system-ui, sans-serif";
        ctx.fillStyle = dark ? "#eef1f6" : "#1c1c28";
        const meta = c.getDatasetMeta(0);
        meta.data.forEach((p, i) => { ctx.fillText(chartName(pts[i].t, true), p.x + 6, p.y - 6); });
        ctx.restore();
      },
    };
    insightCharts.push(new Chart(document.getElementById("chart-risk"), {
      type: "scatter",
      data: { datasets: [{ data: pts,
        backgroundColor: pts.map((p) => (isBench(p.t) ? gray : (p.y >= 0 ? up : down))),
        pointRadius: 6, pointHoverRadius: 8 }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` ${nameOf(c.raw.t)}: ${c.raw.y > 0 ? "+" : ""}${c.raw.y}% return, ${c.raw.x} vol` } } },
        scales: {
          x: { title: { display: true, text: "Risk — annualized volatility (σ)" } },
          y: { title: { display: true, text: "Reward — return, last 30 days (%)" } },
        } },
      plugins: [labelPlugin],
    }));
  }

  // 3. How far from the top? — distance below 52w high
  {
    const sorted = rows.filter(([, v]) => v.pct_off_high != null)
      .sort((a, b) => a[1].pct_off_high - b[1].pct_off_high);
    fitHeight("chart-high", sorted.length);
    insightCharts.push(new Chart(document.getElementById("chart-high"), {
      type: "bar",
      data: { labels: sorted.map(([t]) => chartName(t) + (isBench(t) ? " ★" : "")),
        datasets: [{ data: sorted.map(([, v]) => v.pct_off_high),
          backgroundColor: sorted.map(([, v]) => (v.pct_off_high > -10 ? up : down)), borderRadius: 4 }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` ${c.parsed.x}% below 52-week high` } } },
        scales: {
          x: { title: { display: true, text: "Distance below 52-week high (%)" }, reverse: true },
          y: { title: { display: true, text: "Stock" } },
        } },
    }));
  }

  // 4. Above or below trend? — distance from MA50
  {
    const sorted = rows.filter(([, v]) => v.dist_ma50_pct != null)
      .sort((a, b) => a[1].dist_ma50_pct - b[1].dist_ma50_pct);
    fitHeight("chart-trend", sorted.length);
    insightCharts.push(new Chart(document.getElementById("chart-trend"), {
      type: "bar",
      data: { labels: sorted.map(([t]) => chartName(t) + (isBench(t) ? " ★" : "")),
        datasets: [{ data: sorted.map(([, v]) => v.dist_ma50_pct),
          backgroundColor: sorted.map(([, v]) => (v.dist_ma50_pct >= 0 ? up : down)), borderRadius: 4 }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` ${c.parsed.x > 0 ? "+" : ""}${c.parsed.x}% ${c.parsed.x >= 0 ? "above" : "below"} the 50-day average` } } },
        scales: {
          x: { title: { display: true, text: "Distance from 50-day average (%)" } },
          y: { title: { display: true, text: "Stock" } },
        } },
    }));
  }
}

async function init() {
  try {
    readHash();
    indexData = await loadJSON(`${DATA_DIR}index.json`);
    if (indexData.schema_version !== EXPECTED_SCHEMA) throw new Error("index.json schema mismatch — rebuild output/");
    const gen = new Date(indexData.generated_at);
    document.getElementById("gen-stamp").textContent =
      `Data: ${gen.toLocaleString()} UTC`;
    const ageDays = (Date.now() - gen.getTime()) / 864e5;
    if (ageDays > 3) {
      const b = document.getElementById("stale-banner");
      b.style.display = "block";
      b.textContent = `Data is ${Math.floor(ageDays)} days old (generated ${indexData.generated_at}). The scheduled refresh may have failed.`;
    }
    const sel = document.getElementById("ticker");
    const secSel = document.getElementById("sector");
    [...new Set(indexData.tickers.map(sectorOf))].sort().forEach((s) => {
      const o = document.createElement("option");
      o.value = o.textContent = s;
      secSel.appendChild(o);
    });
    secSel.addEventListener("change", () => {
      state.sector = secSel.value;
      buildTickerOptions();
      renderInsightCharts();
      renderMarket();
      resetCmpToIndustry();
      updateCompare().catch((e) => console.error(e));
      if (state.ticker) selectTicker(state.ticker).catch((e) => showError(e));
    });
    document.getElementById("search").addEventListener("input", (e) => {
      state.q = e.target.value.trim().toLowerCase();
      buildTickerOptions();
    });
    buildTickerOptions();
    if (!state.ticker || !indexData.tickers.includes(state.ticker)) state.ticker = indexData.tickers[0];
    sel.value = state.ticker;
    sel.addEventListener("change", () => selectTicker(sel.value).catch((e) => showError(e)));
    document.querySelectorAll(".range-btn").forEach((b) => b.addEventListener("click", () => {
      state.range = parseInt(b.dataset.range, 10); writeHash(); setControls(); render(cache[state.ticker]);
    }));
    [["t-ma20", "showMA20"], ["t-ma50", "showMA50"], ["t-fc", "showFc"], ["t-an", "showAn"]]
      .forEach(([id, key]) => document.getElementById(id).addEventListener("change", (e) => {
        state[key] = e.target.checked; render(cache[state.ticker]);
      }));
    const hz = document.getElementById("horizon");
    hz.addEventListener("input", () => {
      state.fcDays = parseInt(hz.value, 10); writeHash(); setControls(); render(cache[state.ticker]);
    });
    document.getElementById("btn-csv").addEventListener("click", currentCSV);
    document.getElementById("btn-png").addEventListener("click", currentPNG);
    window.__onThemeChange = () => {
      if (cache[state.ticker]) render(cache[state.ticker]);
      renderInsightCharts();
      if (state.cmp.length) updateCompare().catch((e) => console.error(e));
    };
    setControls();
    renderMarket();
    renderPairs();
    renderInsightCharts();
    if (!state.cmp.length) state.cmp = [state.ticker, indexData.tickers.find((t) => t !== state.ticker && sectorOf(t) === sectorOf(state.ticker))].filter(Boolean).slice(0, 2);
    await selectTicker(state.ticker);
    await updateCompare();
  } catch (err) {
    showError(err);
  }
}

function showError(err) {
  console.error(err);
  document.querySelector("main").innerHTML =
    `<div class="error-box"><strong>Could not load stock data.</strong><br>${err.message}<br><br>` +
    `Run <code>uv run main.py</code> to generate <code>output/stocks/</code>. ` +
    `If you just updated the site, hard-refresh (<code>Ctrl+Shift+R</code>) — ` +
    `your browser may be running cached code against the new page.</div>`;
}

init();
