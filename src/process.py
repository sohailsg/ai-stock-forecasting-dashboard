"""process.py — S5 data processing and feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add simple/log returns and MA20/MA50. Input: date, close."""
    out = df.copy().sort_values("date").reset_index(drop=True)
    out["ret"] = out["close"].pct_change()  # ST5.1.1
    out["log_ret"] = np.log(out["close"] / out["close"].shift(1))  # ST5.1.2
    out["ma20"] = out["close"].rolling(20).mean()  # ST5.1.3
    out["ma50"] = out["close"].rolling(50).mean()
    return out


def risk_metrics(df: pd.DataFrame) -> dict:
    """Volatility (30d ann.), Sharpe (rf=0), max drawdown. (ST5.2)"""
    feat = add_features(df)
    ret = feat["ret"].dropna()
    vol = float(ret.rolling(30).std().iloc[-1] * np.sqrt(TRADING_DAYS)) if len(ret) >= 30 else None
    sharpe = float(ret.mean() / ret.std() * np.sqrt(TRADING_DAYS)) if ret.std() else None
    roll_max = feat["close"].cummax()
    dd = (feat["close"] - roll_max) / roll_max
    max_dd = float(dd.min()) if len(dd) else None
    last = float(feat["close"].iloc[-1])
    m1 = float(feat["close"].iloc[-1] / feat["close"].iloc[-22] - 1) if len(feat) >= 22 else None
    pos = position_metrics(feat)
    return {
        "last_close": round(last, 2),
        "change_1m": round(m1 * 100, 2) if m1 is not None else None,
        "volatility": round(vol, 4) if vol is not None else None,
        "sharpe": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown": round(max_dd * 100, 2) if max_dd is not None else None,
        **pos,
    }


def position_metrics(feat: pd.DataFrame) -> dict:
    """Where price sits: vs 52-week high and vs MA50 trend. (analyst positioning)"""
    close = feat["close"]
    last = float(close.iloc[-1])
    tail = close.iloc[-252:] if len(close) >= 252 else close
    high52 = float(tail.max())
    pct_off_high = round((last / high52 - 1) * 100, 2) if high52 else None
    ma50 = float(feat["ma50"].iloc[-1]) if not pd.isna(feat["ma50"].iloc[-1]) else None
    dist_ma50 = round((last / ma50 - 1) * 100, 2) if ma50 else None
    above_ma50 = bool(last > ma50) if ma50 else None
    return {
        "high_52w": round(high52, 2),
        "pct_off_high": pct_off_high,
        "dist_ma50_pct": dist_ma50,
        "above_ma50": above_ma50,
    }


def correlation_matrix(frames: dict[str, pd.DataFrame]) -> dict:
    """Correlation of daily returns across tickers (pairwise min_periods). (ST5.3)"""
    if len(frames) < 2:
        return {}
    aligned = None
    for t, df in frames.items():
        s = df.set_index("date")["close"].pct_change().rename(t)
        aligned = s if aligned is None else pd.concat([aligned, s], axis=1)
    corr = aligned.corr(min_periods=30).round(3)
    return corr.where(pd.notnull(corr), None).to_dict()
