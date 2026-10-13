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


def test_correlation_pairs_shape():
    from src import process as proc

    frames = {"A": _prices(60), "B": _prices(60), "C": _prices(60, base=50.0)}
    pairs = proc.correlation_pairs(frames, k=2)
    assert set(pairs) == {"low", "high"}
    assert len(pairs["low"]) == 2 and len(pairs["high"]) == 2
    assert all(set(p) == {"a", "b", "v"} for p in pairs["low"] + pairs["high"])
    assert all(p["a"] != p["b"] for p in pairs["low"] + pairs["high"])


def test_correlation_peers_shape():
    from src import process as proc

    frames = {"A": _prices(60), "B": _prices(60), "C": _prices(60, base=50.0)}
    peers = proc.correlation_peers(frames, k=1)
    assert set(peers) == {"A", "B", "C"}
    assert all(len(v["high"]) == 1 and len(v["low"]) == 1 for v in peers.values())
    assert all(t not in [x[0] for x in v["high"] + v["low"]] for t, v in peers.items())


def test_holdout_has_frontend_keys():
    df = _prices(200)
    r = bt.holdout(df, horizon=10)
    assert {"model_mape", "naive_mape", "verdict", "horizon"} <= set(r)


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


def test_sector_universe_is_us_india():
    from src import sectors as sec

    assert len(sec.DEFAULT_TICKERS) == 236
    assert len(set(sec.DEFAULT_TICKERS)) == 236  # no duplicates
    assert len(sec.SECTORS) == 20
    assert "RELIANCE.NS" in sec.DEFAULT_TICKERS
    assert "AAPL" in sec.DEFAULT_TICKERS
    assert "^GSPC" in sec.DEFAULT_TICKERS
    assert sec.get_sector("NVDA") == "Semiconductors"
    assert sec.get_sector("TCS.NS") == "India IT"
    assert sec.get_sector("META") == "Communication"
    assert sec.get_sector("SBIN.NS") == "BFSI"
    assert sec.get_sector("HDFCBANK.NS") == "BFSI"
    assert sec.get_sector("JPM") == "Financials"
    assert sec.get_sector("^NSEI") == "Benchmark"
    assert sec.get_sector("UNKNOWN.X") == "Other"
    assert sec.get_currency("INFY.NS") == "INR"
    assert sec.get_currency("^NSEI") == "INR"
    assert sec.get_currency("MSFT") == "USD"


def test_fetch_defaults_to_sector_universe(monkeypatch):
    import os

    from src import fetch as fet

    monkeypatch.delenv("TICKERS", raising=False)
    assert fet.get_tickers() == list(fet.DEFAULT_TICKERS)
    assert len(fet.get_tickers()) == 236


def test_position_metrics_known():
    df = _prices(300)
    m = proc.risk_metrics(df)
    assert m["pct_off_high"] == 0.0  # monotonic rise: at the high
    assert m["above_ma50"] is True
    assert m["dist_ma50_pct"] is not None and m["dist_ma50_pct"] > 0


def test_insights_fallback_persists_to_index(tmp_path, monkeypatch):
    """Regression: fallback path must write insights into index.json."""
    import os

    from src import insights as ins

    idx = {
        "schema_version": 1,
        "tickers": ["AAA"],
        "insights": {},
        "generated_at": "2026-01-01T00:00:00+00:00",
    }
    (tmp_path / "AAA.json").write_text(json.dumps({
        "stats": {"last_close": 10.0, "change_1m": 2.0, "volatility": 0.2,
                  "sharpe": 1.0, "max_drawdown": -5.0},
        "backtest": {"verdict": "beats naive", "model_mape": 1.0, "naive_mape": 2.0},
        "forecast": {"method": "ARIMA(1,1,1)-log"},
        "anomalies": [],
    }))
    (tmp_path / "index.json").write_text(json.dumps(idx))
    monkeypatch.setattr(ins, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(ins, "TICKER_DIR", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    out = ins.build_insights()
    assert out["AAA"].startswith("AAA rose")
    saved = json.loads((tmp_path / "index.json").read_text())
    assert saved["insights"]["AAA"] == out["AAA"]  # persisted, not {}
    assert "market_insight" in saved and "AAA" in saved["market_insight"]


def test_market_fallback_names_movers():
    from src import insights as ins

    snap = {
        "AAA": {"sector": "Tech", "change_1m": 5.0, "volatility": 0.2,
                "sharpe": 1.0, "verdict": "beats naive"},
        "BBB": {"sector": "Energy", "change_1m": -3.0, "volatility": 0.3,
                "sharpe": 0.2, "verdict": "worse than naive"},
    }
    txt = ins._market_fallback(snap)
    assert "AAA" in txt and "BBB" in txt and "1 of 2" in txt


def test_fallback_composes_from_numbers():
    from src import insights as ins

    stats = {"sector": "Energy", "change_1m": -4.5, "volatility": 0.30,
             "sharpe": -0.2, "max_drawdown": -20.0, "pct_off_high": -26.0,
             "dist_ma50_pct": -8.0, "anomalies": 3}
    txt = ins._rule_fallback("XOM", stats, {"verdict": "worse than naive",
                                            "model_mape": 5.0})
    assert txt.startswith("XOM fell 4.5%")
    assert "Energy" in txt and "26.0% below its 52-week high" in txt
    assert "below its 50-day trend line" in txt and "choppy" in txt
    assert "3 unusual daily moves" in txt and "illustrative only" in txt

    stats2 = dict(stats, change_1m=6.0, volatility=0.10, sharpe=1.5,
                  dist_ma50_pct=2.0, anomalies=0)
    txt2 = ins._rule_fallback("AAA", stats2, {"verdict": "beats naive",
                                              "model_mape": 1.2})
    assert "calm" in txt2 and "strong risk-adjusted" in txt2
    assert "deserves some attention" in txt2
