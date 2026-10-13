"""anomalies.py — S8 rolling 60-day z-score on returns, |z| > 3."""

from __future__ import annotations

import pandas as pd

WINDOW = 60
THRESHOLD = 3.0
MAX_ANOMALIES = 20  # cap payload (ST8.2.2)


def detect(df: pd.DataFrame, window: int = WINDOW, threshold: float = THRESHOLD) -> list[dict]:
    """Return [{date, price, return_pct, z}] most-recent-first, capped."""
    feat = df.copy().sort_values("date").reset_index(drop=True)
    feat["ret"] = feat["close"].pct_change()
    mu = feat["ret"].rolling(window).mean()
    sd = feat["ret"].rolling(window).std()
    feat["z"] = (feat["ret"] - mu) / sd
    hits = feat[feat["z"].abs() > threshold].dropna(subset=["z"])
    out = [
        {
            "date": pd.to_datetime(r["date"]).strftime("%Y-%m-%d"),
            "price": round(float(r["close"]), 2),
            "return_pct": round(float(r["ret"]) * 100, 2),
            "z": round(float(r["z"]), 2),
        }
        for _, r in hits.iterrows()
    ]
    return out[-MAX_ANOMALIES:][::-1]  # most recent first
