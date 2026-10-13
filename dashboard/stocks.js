/**
 * stocks.js — S10 core UI + S11 utilities (what-if horizon, CSV/PNG export, dark mode).
 * Lazy-loads per-ticker JSON, checks schema_version, persists state in URL hash.
 */
const DATA_DIR = "../output/stocks/";
const EXPECTED_SCHEMA = 1;

let chart = null;
let cmpChart = null;
const state = { ticker: "", range: 365, showMA20: true, showMA50: true, showFc: true, showAn: true, fcDays: 30, cmp: [], sector: "", q: "" };
let cache = {};
let indexData = null;

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
              if (ctx.dataset.label === "Anomaly") return ` Anomaly: $${v.toFixed(2)}`;
              return ` ${ctx.dataset.label}: $${v.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 10, maxRotation: 0 } },
        y: { beginAtZero: false, ticks: { callback: (v) => `$${v}` } },
      },
    },
  });

  const st = payload.stats, bt = payload.backtest;
  const set = (id, txt) => {
    const el = document.getElementById(id);
    el.classList.remove("loading");
    el.textContent = txt;
  };
  set("kpi-close", `$${st.last_close.toLocaleString()}`);
  set("kpi-chg", `${st.change_1m > 0 ? "+" : ""}${st.change_1m}%`);
  set("kpi-vol", st.volatility ?? "—");
  set("kpi-sharpe", st.sharpe ?? "—");
  set("kpi-dd", `${st.max_drawdown}%`);
  set("kpi-bt", `MAPE ${bt.model_mape}% vs naive ${bt.naive_mape}% — ${bt.verdict}`);
  document.getElementById("chart-title").textContent =
    `${payload.ticker} · ${payload.forecast.method} · next ${fd}d`;
  document.getElementById("ai-insight").textContent =
    (indexData.insights && indexData.insights[payload.ticker]) || "No insight available.";
  const verdict = (payload.backtest || {}).verdict || "unknown";
  document.getElementById("ai-tag").textContent =
    `Forecast reliability: ${verdict} (model MAPE ${payload.backtest.model_mape}% vs naive ${payload.backtest.naive_mape}%)`;
  const ul = document.getElementById("anomaly-list");
  ul.innerHTML = "";
  const anomalies = payload.anomalies || [];
  if (!anomalies.length) ul.innerHTML = "<li>No anomalies flagged in this window.</li>";
  anomalies.slice(0, 10).forEach((a) => {
    const li = document.createElement("li");
    li.textContent = `${a.date}: $${a.price} (${a.return_pct > 0 ? "+" : ""}${a.return_pct}%, z=${a.z})`;
    ul.appendChild(li);
  });
  if (indexData.snapshot) renderMarket();
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

function sectorOf(t) {
  return (indexData.sectors && indexData.sectors[t]) || "Other";
}

function buildTickerOptions() {
  const sel = document.getElementById("ticker");
  sel.innerHTML = "";
  const groups = {};
  indexData.tickers.forEach((t) => {
    if (state.sector && sectorOf(t) !== state.sector) return;
    if (state.q && !t.toLowerCase().includes(state.q)) return;
    (groups[sectorOf(t)] = groups[sectorOf(t)] || []).push(t);
  });
  Object.keys(groups).sort().forEach((g) => {
    const og = document.createElement("optgroup");
    og.label = g;
    groups[g].forEach((t) => {
      const o = document.createElement("option");
      o.value = o.textContent = t;
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

function renderMarket() {
  document.getElementById("market-insight").textContent =
    indexData.market_insight || "Market overview unavailable.";
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
    div.innerHTML = `<h2></h2><p class="kpi-value" style="font-size:1.25rem"></p><p class="kpi-sub"></p>`;
    div.querySelector("h2").textContent = s;
    div.querySelector(".kpi-value").textContent = `${avg > 0 ? "+" : ""}${avg.toFixed(1)}%`;
    div.querySelector(".kpi-sub").textContent = `${arr.length} stock${arr.length > 1 ? "s" : ""} · avg 1M`;
    wrap.appendChild(div);
  });
  // Ranking table by 1M change
  const rows = Object.entries(snap)
    .filter(([, v]) => v.change_1m != null)
    .sort((a, b) => b[1].change_1m - a[1].change_1m);
  const tb = document.querySelector("#rank-table tbody");
  tb.innerHTML = "";
  rows.forEach(([t, v], i) => {
    const tr = document.createElement("tr");
    if (t === state.ticker) tr.className = "me";
    tr.innerHTML = `<td>${i + 1}</td><td><a href="#" data-goto="${t}"><strong>${t}</strong></a></td>` +
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
  indexData.tickers.forEach((t) => {
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
    lab.append(cb, document.createTextNode(` ${t}`));
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
  if (cmpChart) { cmpChart.destroy(); cmpChart = null; }
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
      label: t,
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
        x: { ticks: { maxTicksLimit: 8, maxRotation: 0 } },
        y: { ticks: { callback: (v) => `${v}` }, title: { display: true, text: "Rebased = 100" } },
      },
    },
  });
}

function comparePair(a, b) {
  state.cmp = [a, b];
  writeHash();
  updateCompare().catch((e) => console.error(e));
  document.getElementById("chart-cmp").scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ── Correlation heatmap ─────────────────────────────────────────────────── */

function heatColor(v) {
  // -1..1 → red..neutral..green
  const a = Math.abs(v);
  const bg = v >= 0 ? `rgba(30,158,106,${(0.08 + a * 0.55).toFixed(2)})`
                    : `rgba(230,57,70,${(0.08 + a * 0.55).toFixed(2)})`;
  return bg;
}

function renderHeatmap() {
  const corr = indexData.correlations || {};
  const ts = indexData.tickers;
  const tbl = document.getElementById("heatmap");
  tbl.innerHTML = "";
  const head = document.createElement("tr");
  head.innerHTML = "<th></th>" + ts.map((t) => `<th>${t}</th>`).join("");
  tbl.appendChild(head);
  ts.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<th>${r}</th>` + ts.map((c) => {
      const v = corr[r] && corr[r][c];
      const txt = v == null ? "—" : v.toFixed(2);
      const style = v == null ? "" : ` style="background:${heatColor(v)}"`;
      return `<td class="cell" data-r="${r}" data-c="${c}"${style} title="${r} vs ${c}: ${txt}">${txt}</td>`;
    }).join("");
    tbl.appendChild(tr);
  });
  tbl.querySelectorAll("td.cell").forEach((td) => td.addEventListener("click", () => {
    if (td.dataset.r !== td.dataset.c) comparePair(td.dataset.r, td.dataset.c);
  }));
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
      if (state.cmp.length) updateCompare().catch((e) => console.error(e));
    };
    setControls();
    renderMarket();
    renderHeatmap();
    if (!state.cmp.length) state.cmp = [state.ticker, indexData.tickers.find((t) => t !== state.ticker)].filter(Boolean).slice(0, 2);
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
    `Run <code>uv run main.py</code> to generate <code>output/stocks/</code>, then serve via ` +
    `<code>python -m http.server 8000</code> and open <code>/dashboard/stocks.html</code>.</div>`;
}

init();
