# Forecasting method, metrics, limits

- **Primary:** ARIMA(1,1,1) on log prices (`src/forecast.py`), 30-day
  business-day horizon (`FORECAST_HORIZON`), 95% band via `get_forecast`
  confidence interval, exponentiated back to prices. Falls back to naive
  (last value) with `method` flag when history is short or fit fails.
- **Honest backtest (`src/backtest.py`):** hold-out last H days + 5-window
  walk-forward; reports model MAPE vs naive MAPE, RMSE, directional accuracy,
  95% band coverage; verdict `beats naive / comparable / worse than naive`
  (±0.5pp tolerance). Current v1: AAPL beats naive, MSFT comparable,
  NVDA/TSLA worse than naive — displayed openly on the page.
- **Limits:** statistical extrapolation, not event prediction; daily data
  only; efficient-market behaviour means naive is often competitive.
  Educational only, not financial advice.
