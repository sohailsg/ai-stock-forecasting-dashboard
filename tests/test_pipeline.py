"""S15 unit tests — hand-calculated fixtures, no network."""

import json
import math

import pandas as pd

from src import anomalies as anz
from src import backtest as bt
from src import forecast as fc
from src import insights as ins
from src import process as proc


def _prices(n=80, base=100.0, step=0.5):
    dates = pd.bdate_range("2023-01-02", periods=n)
    px = [base + i * step for i in range(n)]
    return pd.DataFrame({"date": dates, "close": px})


def test_returns_and_mas():
    df = pd.DataFrame({
        "date": pd.bdate_range("2023-01-02", periods=5),
        "close": [100.0, 110.0, 105.0, 115.0, 120.0],
    })
    f = proc.add_features(df)
    assert abs(f["ret"].iloc[1] - 0.10) < 1e-9  # simple return
    assert math.isnan(f["ma20"].iloc[0])  # not enough history
    assert f["ma20"].isna().sum() == 5


def test_volatility_drawdown_known():
    df = _prices(60)
    m = proc.risk_metrics(df)
    assert m["last_close"] == round(100 + 59 * 0.5, 2)
    assert m["max_drawdown"] == 0.0  # monotonic rise, no drawdown
    assert m["volatility"] is not None and m["volatility"] >= 0


def test_anomaly_planted_spike():
    df = _prices(100)
    df.loc[90, "close"] = df.loc[90, "close"] * 1.5  # +50% spike
    hits = anz.detect(df)
    assert hits, "planted spike must be flagged"
    assert any(abs(h["return_pct"]) > 20 for h in hits)


def test_forecast_shape_and_bands():
    df = _prices(200)
    out = fc.forecast_close(df, horizon=10)
    assert len(out["mean"]) == len(out["dates"]) == 10
    for lo, m, hi in zip(out["lower"], out["mean"], out["upper"]):
        assert lo <= m <= hi


def test_forecast_naive_fallback_short_history():
    df = _prices(10)
    out = fc.forecast_close(df, horizon=5)
    assert out["method"].startswith("naive")


def test_backtest_verdict_logic():
    assert bt.verdict(1.0, 3.0) == "beats naive"
    assert bt.verdict(2.9, 3.0) == "comparable"
    assert bt.verdict(5.0, 3.0) == "worse than naive"
    assert bt.verdict(None, 3.0) == "insufficient data"


def test_holdout_on_synthetic():
    df = _prices(200)
    r = bt.holdout(df, horizon=10)
    assert r["verdict"] in ("beats naive", "comparable", "worse than naive")
    assert r["model_mape"] >= 0 and r["naive_mape"] >= 0


def test_gemini_parser_fenced_and_malformed():
    assert ins._parse_json_response('```json\n{"AAPL": "hi"}\n```') == {"AAPL": "hi"}
    assert ins._parse_json_response("not json {{{") == {}
    assert ins._parse_json_response('["list"]') == {}


def test_nan_to_null_in_json():
    payload = {"a": float("nan"), "b": [1.0, float("nan")]}
    text = json.dumps(payload, allow_nan=False) if False else None
    # our builder uses _clean_num -> None -> null; verify contract:
    from src.build import _clean_num

    assert _clean_num(float("nan")) is None
    assert json.dumps({"x": _clean_num(float("nan"))}) == '{"x": null}'
