# AI Stock Forecasting Dashboard

Live: **https://sohail-ahmed.space/**

> Educational only, not financial advice. Market data: Yahoo Finance via
> yfinance (unofficial).

Interactive stock analytics for 23 US + India stocks and indexes across 9 industries
(tech, chips, EV, finance, healthcare, consumer, energy, India IT/bank/energy):
daily fetch → MA20/50, volatility, Sharpe, drawdown → ARIMA(1,1,1) 30-day
forecast with 95% band → honest backtest vs naive → z-score anomalies →
Gemini insights + market overview → Chart.js UI with sector filter, search,
compare mode (rebased), correlation heatmap and ranking table →
GitHub Pages auto-deploy with weekday refresh.

Docs: `docs/architecture.md`, `docs/forecasting.md`, `docs/deployment.md`,
`docs/decisions.md` (ADR-001 Pages, ADR-002 yfinance).

---

## Quickstart

```bash
uv sync
cp .env.example .env   # add GEMINI_API_KEY (optional; fallback works without)
uv run pytest tests/ -q
uv run main.py
python -m http.server 8000   # open http://localhost:8000/dashboard/
```

Env: `TICKERS` (default 23 US+India industry set, see `src/sectors.py`),
`FORECAST_HORIZON` (default 30), `GEMINI_API_KEY`.

---

## Project structure

```
├── src/
│   ├── fetch.py      # yfinance download, validate, cache data/stocks/
│   ├── process.py    # returns, MA20/50, volatility, Sharpe, drawdown, correlations
│   ├── forecast.py   # ARIMA(1,1,1) on log prices + naive fallback
│   ├── backtest.py   # hold-out + walk-forward MAPE vs naive + verdict
│   ├── anomalies.py  # rolling z-score flags
│   ├── sectors.py    # 12-ticker US+India universe by industry
│   ├── build.py      # per-ticker JSON + index.json (snapshot, sectors)
│   └── insights.py   # batched Gemini insights + market overview (rule fallback)
├── dashboard/
│   ├── index.html    # stocks homepage
│   ├── stocks.js     # charts, compare, heatmap, ranking, exports
│   ├── theme.js      # shared light/dark theme
│   └── style.css     # design system
├── tests/            # pytest suite (no network)
├── output/stocks/    # generated JSON (gitignored, built by pipeline)
├── data/stocks/      # cached CSVs (gitignored, cached in CI)
├── main.py           # one-command pipeline: build + insights
└── .github/workflows # ci, pages (deploy on push), daily (weekday refresh)
```

---

## Features

- **23 stocks, indexes, 9 industries:** US tech/chips/EV/finance/health/consumer/energy + India IT/bank/energy/auto + S&P 500 & Nifty 50 benchmarks
- **Forecasts with honesty:** every ticker shows model MAPE vs naive MAPE + verdict
- **Compare mode:** overlay up to 3 tickers rebased to 100, shareable via URL hash
- **Correlation heatmap:** click a cell to compare that pair
- **Ranking table + market overview:** best/worst movers, sector averages
- **AI insights:** per-ticker commentary + market overview (Gemini, rule-based fallback)
- **What-if horizon slider, CSV/PNG export, dark mode, staleness banner**

---

## Limitations & disclaimer

Statistical extrapolation, not event prediction; daily data only; the naive
baseline is often competitive (shown openly). Educational use only — not
financial advice. See `docs/forecasting.md`.
