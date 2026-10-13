/**
 * stocks.js — S10 core interactive frontend.
 * Lazy-loads per-ticker JSON from ../output/stocks/, checks schema_version,
 * renders history + MA + forecast band + anomaly markers, persists state in hash.
 */
const DATA_DIR = "../output/stocks/";
const EXPECTED_SCHEMA = 1;

let chart = null;
const state = { ticker: "", range: 365, showMA20: true, showMA50: true, showFc: true, showAn: true };
let cache = {}; // ticker -> payload
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
}
function writeHash() {
  location.hash = `t=${state.ticker}&r=${state.range}`;
}

function setControls() {
  document.getElementById("t-ma20").checked = state.showMA20;
  document.getElementById("t-ma50").checked = state.showMA50;
  document.getElementById("t-fc").checked = state.showFc;
  document.getElementById("t-an").checked = state.showAn;
  document.querySelectorAll(".range-btn").forEach(b =>
    b.setAttribute("aria-pressed", parseInt(b.dataset.range, 10) === state.range ? "true" : "false"));
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

function render(payload) {
  const s = sliceRange(payload);
  const fc = payload.forecast;
  const labels = [...s.dates, ...(state.showFc ? fc.dates : [])];
  const histN = s.dates.length;

  const datasets = [{
    label: "Close", data: [...s.close, ...Array(state.showFc ? fc.dates.length : 0).fill(null)],
    borderColor: "#4361ee", pointRadius: 0, tension: 0.2, spanGaps: true,
  }];
  if (state.showMA20) datasets.push({ label: "MA20", data: [...s.ma20, ...Array(labels.length - histN).fill(null)], borderColor: "#f3722c", pointRadius: 0, tension: 0.2, spanGaps: true });
  if (state.showMA50) datasets.push({ label: "MA50", data: [...s.ma50, ...Array(labels.length - histN).fill(null)], borderColor: "#43aa8b", pointRadius: 0, tension: 0.2, spanGaps: true });
  if (state.showFc) {
    const fcPad = Array(histN - 1).fill(null).concat([s.close[s.close.length - 1]], fc.mean);
    datasets.push({ label: "Forecast", data: fcPad, borderColor: "#7209b7", borderDash: [6, 4], pointRadius: 0, tension: 0.2, spanGaps: true });
    datasets.push({ label: "Upper 95%", data: Array(histN).fill(null).concat(fc.upper), borderColor: "#7209b722", backgroundColor: "#7209b722", fill: "+1", pointRadius: 0 });
    datasets.push({ label: "Lower 95%", data: Array(histN).fill(null).concat(fc.lower), borderColor: "#7209b722", backgroundColor: "#7209b722", fill: false, pointRadius: 0 });
  }
  if (state.showAn) {
    const anDates = new Set((payload.anomalies || []).map(a => a.date));
    const pts = labels.map((d, i) => (anDates.has(d) && i < histN ? s.close[i - (labels.length - histN - (state.showFc ? 0 : 0)) - (histN - s.dates.length)] ?? null : null));
    // simpler: map anomalies onto sliced window
    const idx = new Map(s.dates.map((d, i) => [d, i]));
    const markers = Array(labels.length).fill(null);
    (payload.anomalies || []).forEach(a => {
      if (idx.has(a.date)) {
        const pos = idx.get(a.date);
        markers[pos] = s.close[pos];
      }
    });
    datasets.push({ label: "Anomaly", data: markers, type: "scatter", backgroundColor: "#e63946", pointRadius: 5 });
  }

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById("chart-main"), {
    type: "line",
    data: { labels, datasets },
    options: {
      animation: labels.length > 800 ? false : undefined,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: { x: { ticks: { maxTicksLimit: 10 } }, y: { beginAtZero: false } },
    },
  });

  // KPIs
  const st = payload.stats, bt = payload.backtest;
  document.getElementById("kpi-close").textContent = `$${st.last_close}`;
  document.getElementById("kpi-chg").textContent = `${st.change_1m > 0 ? "+" : ""}${st.change_1m}%`;
  document.getElementById("kpi-vol").textContent = st.volatility ?? "—";
  document.getElementById("kpi-sharpe").textContent = st.sharpe ?? "—";
  document.getElementById("kpi-dd").textContent = `${st.max_drawdown}%`;
  document.getElementById("kpi-bt").textContent =
    `MAPE ${bt.model_mape}% vs naive ${bt.naive_mape}% — ${bt.verdict}`;
  document.getElementById("chart-title").textContent =
    `${payload.ticker} — ${payload.forecast.method} (${payload.forecast.horizon}d)`;
  document.getElementById("ai-insight").textContent =
    (indexData.insights && indexData.insights[payload.ticker]) || "No insight available.";
  const ul = document.getElementById("anomaly-list");
  ul.innerHTML = "";
  (payload.anomalies || []).slice(0, 10).forEach(a => {
    const li = document.createElement("li");
    li.textContent = `${a.date}: $${a.price} (${a.return_pct}%, z=${a.z})`;
    ul.appendChild(li);
  });
}

async function selectTicker(t) {
  state.ticker = t;
  writeHash();
  document.getElementById("ai-insight").textContent = "Loading…";
  if (!cache[t]) {
    const p = await loadJSON(`${DATA_DIR}${t}.json`);
    if (p.schema_version !== EXPECTED_SCHEMA) throw new Error(`Schema mismatch for ${t}`);
    cache[t] = p;
  }
  render(cache[t]);
}

async function init() {
  try {
    readHash();
    indexData = await loadJSON(`${DATA_DIR}index.json`);
    if (indexData.schema_version !== EXPECTED_SCHEMA) throw new Error("index schema mismatch");
    // staleness banner (S13-ST13.4.1): warn if older than 3 days
    const age = (Date.now() - new Date(indexData.generated_at).getTime()) / 864e5;
    if (age > 3) {
      const b = document.getElementById("stale-banner");
      b.style.display = "block";
      b.textContent = `Data is ${Math.floor(age)} days old (generated ${indexData.generated_at}). Scheduled refresh may have failed.`;
    }
    const sel = document.getElementById("ticker");
    indexData.tickers.forEach(t => {
      const o = document.createElement("option");
      o.value = o.textContent = t;
      sel.appendChild(o);
    });
    if (!state.ticker || !indexData.tickers.includes(state.ticker)) state.ticker = indexData.tickers[0];
    sel.value = state.ticker;
    sel.addEventListener("change", () => selectTicker(sel.value));
    document.querySelectorAll(".range-btn").forEach(b => b.addEventListener("click", () => {
      state.range = parseInt(b.dataset.range, 10); writeHash(); setControls(); render(cache[state.ticker]);
    }));
    [["t-ma20", "showMA20"], ["t-ma50", "showMA50"], ["t-fc", "showFc"], ["t-an", "showAn"]]
      .forEach(([id, key]) => document.getElementById(id).addEventListener("change", e => {
        state[key] = e.target.checked; render(cache[state.ticker]);
      }));
    setControls();
    await selectTicker(state.ticker);
  } catch (err) {
    console.error(err);
    document.querySelector("main").innerHTML =
      `<div style="padding:2rem;color:#c0392b"><strong>Could not load stock data.</strong><br>${err.message}<br><br>Run the pipeline to generate <code>output/stocks/</code> JSON, then serve via <code>python -m http.server</code>.</div>`;
  }
}
init();
