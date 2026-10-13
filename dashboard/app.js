/**
 * app.js — loads JSON data files and renders charts with Chart.js
 *
 * NOTE: This file uses fetch(), which only works over HTTP — not when opening
 * index.html directly as a file. Always use a local server for testing:
 *   python -m http.server 8000
 * Then open: http://localhost:8000/dashboard/
 */

// Path to the JSON files, relative to this page's location on the server.
// Deployed the pages sit at the site root, so ../output/ resolves to /output/;
// locally under /dashboard/ it resolves to /output/ as well.
const DATA_DIR = "../output/";

function palette() {
  const dark = document.documentElement.dataset.theme === "dark";
  return dark
    ? ["#8fa6ff", "#ff7ab8", "#6fd6f5", "#c77dff", "#ffa76b", "#a3d68c", "#5fd6b5", "#b79cff"]
    : ["#4361ee", "#f72585", "#4cc9f0", "#7209b7", "#f3722c", "#90be6d", "#43aa8b", "#3a0ca3"];
}

let charts = [];
let store = null;


// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Fetch a JSON file and return its parsed contents.
 * Throws a clear error if the file is not found or the server returns an error.
 */
async function loadJSON(filename) {
  const response = await fetch(DATA_DIR + filename);
  if (!response.ok) {
    throw new Error(`Could not load ${filename} (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * Format a number as a USD currency string.
 * Example: 12345.6 → "$12,345.60"
 *
 * Intl.NumberFormat is built into every browser — no library needed.
 */
function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}


// ── KPI cards ─────────────────────────────────────────────────────────────────

/**
 * Populate the four summary cards at the top of the page.
 * Each id matches an element in index.html.
 */
function renderSummary(summary) {
  const set = (id, txt) => {
    const el = document.getElementById(id);
    el.classList.remove("loading");
    el.textContent = txt;
  };
  set("kpi-revenue", formatCurrency(summary.total_revenue));

  // toLocaleString() adds thousands separators: 1234 → "1,234"
  set("kpi-units", summary.total_units.toLocaleString());

  set("kpi-top-product", summary.top_product);
  set("kpi-top-region", summary.top_region);
}


// ── Charts ────────────────────────────────────────────────────────────────────

/**
 * Line chart — monthly revenue over time.
 *
 * monthlyData shape: [{ "month": "2024-01", "revenue": 1234.56 }, ...]
 */
function renderMonthlyChart(monthlyData, colors) {
  const labels = monthlyData.map(d => d.month);
  const values = monthlyData.map(d => d.revenue);

  charts.push(new Chart(document.getElementById("chart-monthly"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Revenue",
        data: values,
        borderColor: colors[0],
        backgroundColor: colors[0] + "22", // "22" adds ~13% opacity in hex
        fill: true,
        tension: 0.3, // slight curve on the line
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales:  { y: { beginAtZero: true, ticks: { callback: v => `$${v.toLocaleString()}` } } },
    },
  }));
}

/**
 * Bar chart — revenue by product.
 *
 * productData shape: [{ "product": "Laptop", "revenue": 5000 }, ...]
 */
function renderProductChart(productData, colors) {
  const labels = productData.map(d => d.product);
  const values = productData.map(d => d.revenue);

  charts.push(new Chart(document.getElementById("chart-product"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Revenue",
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales:  { y: { beginAtZero: true, ticks: { callback: v => `$${v.toLocaleString()}` } } },
    },
  }));
}

/**
 * Pie chart — revenue by region.
 *
 * regionData shape: [{ "region": "North", "revenue": 3000 }, ...]
 */
function renderRegionChart(regionData, colors) {
  const labels = regionData.map(d => d.region);
  const values = regionData.map(d => d.revenue);

  charts.push(new Chart(document.getElementById("chart-region"), {
    type: "pie",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right" },
      },
    },
  }));
}

function renderAll() {
  if (!store) return;
  charts.forEach(c => c.destroy());
  charts = [];
  const colors = palette();
  renderSummary(store.summary);
  document.getElementById("ai-insights").textContent = store.insights.insights;
  renderMonthlyChart(store.monthly, colors);
  renderProductChart(store.byProduct, colors);
  renderRegionChart(store.byRegion, colors);
}

// Re-render charts when the theme toggles so colours stay readable.
window.__onThemeChange = renderAll;


// ── Entry point ───────────────────────────────────────────────────────────────

/**
 * Load all data files and render the dashboard.
 *
 * Promise.all([...]) fires all fetch() calls at the same time and waits
 * for all of them to finish before continuing — faster than four separate awaits.
 */
async function init() {
  try {
    const [summary, insights, monthly, byProduct, byRegion] = await Promise.all([
      loadJSON("summary.json"),
      loadJSON("insights.json"),
      loadJSON("monthly_revenue.json"),
      loadJSON("revenue_by_product.json"),
      loadJSON("revenue_by_region.json"),
    ]);

    store = { summary, insights, monthly, byProduct, byRegion };
    renderAll();

  } catch (error) {
    // Log the technical error for debugging, then show a friendly message
    console.error("Dashboard failed to load:", error);
    document.querySelector("main").innerHTML = `
      <div class="error-box">
        <strong>Could not load dashboard data.</strong><br><br>
        Make sure you have:
        <ol style="margin-top: 0.5rem; padding-left: 1.5rem; line-height: 2;">
          <li>Run <code>python analyze.py</code> to generate the JSON files</li>
          <li>Started a local server (<code>python -m http.server 8000</code>)
              rather than opening index.html directly</li>
        </ol>
      </div>
    `;
  }
}

init();
