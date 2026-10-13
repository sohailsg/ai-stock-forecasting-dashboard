/**
 * app.js — loads JSON data files and renders charts with Chart.js
 *
 * NOTE: This file uses fetch(), which only works over HTTP — not when opening
 * index.html directly as a file. Always use a local server for testing:
 *   python -m http.server 8000
 * Then open: http://localhost:8000/dashboard/
 */


// Path to the JSON files, relative to this page's location on the server.
// If your server layout is different, adjust this path.
const DATA_DIR = "../output/";

// Colour palette shared across all charts
const COLORS = [
  "#4361ee", "#f72585", "#4cc9f0", "#7209b7",
  "#f3722c", "#90be6d", "#43aa8b", "#3a0ca3",
];


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
  document.getElementById("kpi-revenue").textContent =
    formatCurrency(summary.total_revenue);

  // toLocaleString() adds thousands separators: 1234 → "1,234"
  document.getElementById("kpi-units").textContent =
    summary.total_units.toLocaleString();

  document.getElementById("kpi-top-product").textContent = summary.top_product;
  document.getElementById("kpi-top-region").textContent  = summary.top_region;
}


// ── Charts ────────────────────────────────────────────────────────────────────

/**
 * Line chart — monthly revenue over time.
 *
 * monthlyData shape: [{ "month": "2024-01", "revenue": 1234.56 }, ...]
 */
function renderMonthlyChart(monthlyData) {
  const labels = monthlyData.map(d => d.month);
  const values = monthlyData.map(d => d.revenue);

  new Chart(document.getElementById("chart-monthly"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Revenue",
        data: values,
        borderColor: COLORS[0],
        backgroundColor: COLORS[0] + "22", // "22" adds ~13% opacity in hex
        fill: true,
        tension: 0.3, // slight curve on the line
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales:  { y: { beginAtZero: true } },
    },
  });
}

/**
 * Bar chart — revenue by product.
 *
 * productData shape: [{ "product": "Laptop", "revenue": 5000 }, ...]
 */
function renderProductChart(productData) {
  const labels = productData.map(d => d.product);
  const values = productData.map(d => d.revenue);

  new Chart(document.getElementById("chart-product"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Revenue",
        data: values,
        backgroundColor: COLORS.slice(0, labels.length),
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales:  { y: { beginAtZero: true } },
    },
  });
}

/**
 * Pie chart — revenue by region.
 *
 * regionData shape: [{ "region": "North", "revenue": 3000 }, ...]
 */
function renderRegionChart(regionData) {
  const labels = regionData.map(d => d.region);
  const values = regionData.map(d => d.revenue);

  new Chart(document.getElementById("chart-region"), {
    type: "pie",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: COLORS.slice(0, labels.length),
      }],
    },
    options: {
      plugins: {
        legend: { position: "right" },
      },
    },
  });
}


// ── Entry point ───────────────────────────────────────────────────────────────

/**
 * Load all data files and render the dashboard.
 *
 * Promise.all([...]) fires all four fetch() calls at the same time and waits
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

    renderSummary(summary);
    document.getElementById("ai-insights").textContent = insights.insights;
    renderMonthlyChart(monthly);
    renderProductChart(byProduct);
    renderRegionChart(byRegion);

  } catch (error) {
    // Log the technical error for debugging, then show a friendly message
    console.error("Dashboard failed to load:", error);
    document.querySelector("main").innerHTML = `
      <div style="padding: 2rem; color: #c0392b;">
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
