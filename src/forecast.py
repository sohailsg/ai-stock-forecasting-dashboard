"""forecast.py — S6 forecasting engine: ARIMA(1,1,1) on log prices + naive fallback."""

from __future__ import annotations

import logging
import os
import warnings

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def get_horizon() -> int:
    """FORECAST_HORIZON env var, default 30. (ST6.4.1)"""
    try:
        return max(5, min(60, int(os.environ.get("FORECAST_HORIZON", 30))))
    except ValueError:
        return 30


def _future_bdays(last_date: pd.Timestamp, h: int) -> list[str]:
    idx = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=h)
    return [d.strftime("%Y-%m-%d") for d in idx]


def forecast_close(df: pd.DataFrame, horizon: int | None = None) -> dict:
    """Return {dates, mean, lower, upper, method}. 95% band, exp from log. (ST6.2)"""
    h = horizon or get_horizon()
    hist = df.sort_values("date").reset_index(drop=True)
    last_date = pd.to_datetime(hist["date"].iloc[-1])
    last_px = float(hist["close"].iloc[-1])
    dates = _future_bdays(last_date, h)

    def naive(reason: str) -> dict:
        logger.warning("naive fallback: %s", reason)
        m = [round(last_px, 2)] * h
        return {"dates": dates, "mean": m, "lower": m, "upper": m,
                "method": f"naive ({reason})", "horizon": h}

    logp = np.log(hist["close"].to_numpy(dtype=float))
    if len(logp) < 60:
        return naive("short history")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from statsmodels.tsa.arima.model import ARIMA

            fit = ARIMA(logp, order=(1, 1, 1), trend="n").fit()  # drift via AR
            fc = fit.get_forecast(steps=h)
            mean = np.exp(fc.predicted_mean)
            ci = np.exp(fc.conf_int(alpha=0.05))
            lo, hi = ci[:, 0], ci[:, 1]
        return {
            "dates": dates,
            "mean": [round(float(v), 2) for v in mean],
            "lower": [round(float(v), 2) for v in np.minimum(lo, mean)],
            "upper": [round(float(v), 2) for v in np.maximum(hi, mean)],
            "method": "ARIMA(1,1,1)-log",
            "horizon": h,
        }
    except Exception as e:  # noqa: BLE001 — ST6.2.4: flag fallback in JSON
        return naive(f"ARIMA failed: {e}")
