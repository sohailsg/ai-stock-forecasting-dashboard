"""build.py — assemble per-ticker JSON + stock_index.json (S5-ST5.4, S12).

Schema v1:
  output/stocks/<TICKER>.json:
    {ticker, schema_version, generated_at, dates, close, ma20, ma50,
     forecast {dates, mean, lower, upper, method, horizon},
     stats {last_close, change_1m, volatility, sharpe, max_drawdown},
     anomalies [{date, price, return_pct, z}], backtest {...}}
  output/stocks/index.json:
    {schema_version, tickers, sectors, correlations, generated_at}
Insights (S9) are merged into index.json by insights.py; build leaves {}.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
import pathlib

import pandas as pd
from dotenv import load_dotenv

from src import anomalies as anz
from src import backtest as bt
from src import fetch as fet
from src import forecast as fc
from src import process as proc
from src import sectors as sec

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 1
OUT_DIR = pathlib.Path("output/stocks")


def _clean_num(v):
    if v is None:
        return None
    f = float(v)
    return None if math.isnan(f) else round(f, 2)


def build_ticker(ticker: str, df: pd.DataFrame) -> dict:
    feat = proc.add_features(df)
    dates = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in feat["date"]]
    horizon = fc.get_horizon()
    payload = {
        "ticker": ticker,
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "currency": sec.get_currency(ticker),
        "dates": dates,
        "close": [_clean_num(v) for v in feat["close"]],
        "ma20": [_clean_num(v) for v in feat["ma20"]],
        "ma50": [_clean_num(v) for v in feat["ma50"]],
        "forecast": fc.forecast_close(df, horizon),
        "stats": proc.risk_metrics(df),
        "anomalies": anz.detect(df),
        "backtest": bt.rolling(df, horizon),
    }
    return payload


def build_all() -> dict:
    load_dotenv()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = fet.fetch_all()
    if not frames:
        raise RuntimeError("no tickers fetched — check network/TICKERS")
    index = {
        "schema_version": SCHEMA_VERSION,
        "tickers": sorted(frames),
        "sectors": {t: sec.get_sector(t) for t in frames},
        "correlations": proc.correlation_matrix(frames),
        "insights": {},
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    for t, df in frames.items():
        payload = build_ticker(t, df)
        (OUT_DIR / f"{t}.json").write_text(json.dumps(payload))  # compact (S17)
        logger.info("%s: stats=%s backtest=%s anomalies=%d", t,
                    payload["stats"], payload["backtest"].get("verdict"),
                    len(payload["anomalies"]))
    # Lightweight snapshot for ranking/heatmap/compare without loading all files
    index["snapshot"] = {}
    for t in frames:
        d = json.loads((OUT_DIR / f"{t}.json").read_text())
        index["snapshot"][t] = {
            "sector": sec.get_sector(t),
            "currency": sec.get_currency(t),
            "last_close": d["stats"].get("last_close"),
            "change_1m": d["stats"].get("change_1m"),
            "volatility": d["stats"].get("volatility"),
            "sharpe": d["stats"].get("sharpe"),
            "max_drawdown": d["stats"].get("max_drawdown"),
            "pct_off_high": d["stats"].get("pct_off_high"),
            "dist_ma50_pct": d["stats"].get("dist_ma50_pct"),
            "above_ma50": d["stats"].get("above_ma50"),
            "verdict": d["backtest"].get("verdict"),
            "model_mape": d["backtest"].get("model_mape"),
            "anomalies": len(d.get("anomalies", [])),
        }
    (OUT_DIR / "index.json").write_text(json.dumps(index))
    logger.info("wrote %d tickers + index.json", len(frames))
    return index


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_all()
