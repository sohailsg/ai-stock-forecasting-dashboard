# Architecture

```
yfinance ──> src/fetch.py ──> data/stocks/<T>.csv (cache)
                                     │
                                     v
                          src/process.py (returns, MA20/50, vol, Sharpe, drawdown, correlations)
                                     │
                    ┌────────────────┼────────────────┐
                    v                v                v
            src/forecast.py   src/backtest.py   src/anomalies.py
          ARIMA(1,1,1)-log   MAPE vs naive      z-score |z|>3
                    └────────────────┼────────────────┘
                                     v
                          src/build.py ──> output/stocks/<T>.json + index.json
                                     │
                                     v
                          src/insights.py (Gemini batched, rule fallback)
                                     │
                                     v
              dashboard/stocks.html + stocks.js (Chart.js, lazy fetch)
                                     │
                                     v
              GitHub Actions (pages.yml / daily.yml) ──> GitHub Pages
                                     │
                                     v
                       https://sohail-ahmed.space/
```

- Static only: Python runs in CI/local; only JSON+HTML is published.
- Schema v1: per-ticker `{ticker, schema_version, generated_at, dates, close,
  ma20, ma50, forecast, stats, anomalies, backtest}`; index `{schema_version,
  tickers, correlations, insights, generated_at}`.
- Frontend checks `schema_version`, lazy-loads per ticker, cache-busts with
  fresh fetch, shows staleness banner if `generated_at` > 3 days old.
