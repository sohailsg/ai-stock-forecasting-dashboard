"""backtest.py — S7 honest evaluation: model MAPE vs naive MAPE + verdict."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecast import forecast_close


def _mape(actual: np.ndarray, pred: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = actual != 0
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100)


def holdout(df: pd.DataFrame, horizon: int = 30) -> dict:
    """Train on all but last H days, forecast H, compare vs naive. (ST7.1)"""
    hist = df.sort_values("date").reset_index(drop=True)
    h = min(horizon, len(hist) - 60)
    if h < 5:
        return {"model_mape": None, "naive_mape": None, "verdict": "insufficient data"}
    train, actual = hist.iloc[:-h], hist["close"].iloc[-h:].to_numpy(dtype=float)
    fc = forecast_close(train, horizon=h)
    model_mape = _mape(actual, np.array(fc["mean"]))
    naive_mape = _mape(actual, np.full(h, float(train["close"].iloc[-1])))
    return {
        "model_mape": round(model_mape, 2),
        "naive_mape": round(naive_mape, 2),
        "verdict": verdict(model_mape, naive_mape),
        "horizon": h,
    }


def rolling(df: pd.DataFrame, horizon: int = 30, windows: int = 5) -> dict:
    """Walk-forward over cut-offs: avg MAPE/RMSE, direction, band coverage. (ST7.2)"""
    hist = df.sort_values("date").reset_index(drop=True)
    h = min(horizon, 30)
    mapes, rmses, dirs, covs = [], [], [], []
    step = max(h, (len(hist) - 60 - h) // max(windows, 1))
    for i in range(windows):
        end = len(hist) - h - i * step
        start_cut = end - h
        if end < 60 or start_cut < 60:
            break
        train = hist.iloc[:end]
        actual = hist["close"].iloc[end:end + h].to_numpy(dtype=float)
        if len(actual) < h:
            break
        fc = forecast_close(train, horizon=h)
        pred = np.array(fc["mean"])
        mapes.append(_mape(actual, pred))
        rmses.append(float(np.sqrt(np.mean((actual - pred) ** 2))))
        prev = float(train["close"].iloc[-1])
        dirs.append(float(np.mean((np.sign(actual - prev) == np.sign(pred - prev)))))
        lo, hi = np.array(fc["lower"]), np.array(fc["upper"])
        covs.append(float(np.mean((actual >= lo) & (actual <= hi))))
    if not mapes:
        return holdout(df, horizon)
    out = {
        "model_mape": round(float(np.mean(mapes)), 2),
        "rmse": round(float(np.mean(rmses)), 2),
        "directional_accuracy": round(float(np.mean(dirs)), 3),
        "band_coverage": round(float(np.mean(covs)), 3),
        "windows": len(mapes),
        "horizon": h,
    }
    naive = holdout(df, h)["naive_mape"]
    out["naive_mape"] = naive
    out["verdict"] = verdict(out["model_mape"], naive)
    return out


def verdict(model_mape: float | None, naive_mape: float | None, tol: float = 0.5) -> str:
    """beats naive / comparable / worse than naive. (ST7.3.1)"""
    if model_mape is None or naive_mape is None:
        return "insufficient data"
    if model_mape < naive_mape - tol:
        return "beats naive"
    if model_mape <= naive_mape + tol:
        return "comparable"
    return "worse than naive"
