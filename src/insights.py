"""insights.py — S9 AI insights with Gemini (batched, graceful fallback).

Sends compact per-ticker stats (never raw series) in ONE batched call,
requests strict JSON {TICKER: text}, retries 429, filters advice phrases,
falls back to rule-based text if Gemini unavailable.
Merges result into output/stocks/index.json -> insights.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import time

logger = logging.getLogger(__name__)
INDEX_PATH = pathlib.Path("output/stocks/index.json")
TICKER_DIR = pathlib.Path("output/stocks")
ADVICE_RE = re.compile(r"you should (buy|sell)|guaranteed|will (rise|fall|surge)",
                       re.IGNORECASE)


def _rule_fallback(ticker: str, stats: dict, backtest: dict) -> str:
    chg = stats.get("change_1m")
    vol = stats.get("volatility")
    verdict = backtest.get("verdict", "unknown")
    trend = "rose" if (chg or 0) > 0 else "fell"
    return (
        f"{ticker} {trend} {abs(chg or 0):.1f}% over the last month with "
        f"annualised volatility {vol}. "
        f"The statistical forecast {verdict} over recent history, so treat "
        f"the 30-day projection as an extrapolation, not a prediction."
    )


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def build_insights() -> dict[str, str]:
    """Generate insights for all tickers in index; returns {ticker: text}."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError("run src.build first — index.json missing")
    index = json.loads(INDEX_PATH.read_text())
    tickers: list[str] = index.get("tickers", [])
    compact: dict[str, dict] = {}
    for t in tickers:
        p = TICKER_DIR / f"{t}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        compact[t] = {
            "last_close": d["stats"].get("last_close"),
            "change_1m": d["stats"].get("change_1m"),
            "volatility": d["stats"].get("volatility"),
            "sharpe": d["stats"].get("sharpe"),
            "max_drawdown": d["stats"].get("max_drawdown"),
            "backtest": d["backtest"].get("verdict"),
            "model_mape": d["backtest"].get("model_mape"),
            "naive_mape": d["backtest"].get("naive_mape"),
            "forecast_method": d["forecast"].get("method"),
            "anomalies": len(d.get("anomalies", [])),
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("no GEMINI_API_KEY — rule-based fallback insights")
        return {t: _rule_fallback(t, _stats_of(t, compact), _bt_of(t, compact))
                for t in compact}

    prompt = (
        "You are a cautious market-data commentator. For each ticker below, "
        "write exactly 2 plain-English sentences: sentence 1 describes trend "
        "and risk from the stats; sentence 2 states forecast reliability using "
        "the backtest verdict. No buy/sell advice, no guarantees, no price "
        "targets. Reply STRICT JSON only: {\"TICKER\": \"text\", ...}\n\n"
        + json.dumps(compact)
    )
    from google import genai

    client = genai.Client(api_key=api_key)
    result: dict[str, str] = {}
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash-lite", contents=prompt)
            result = _parse_json_response(resp.text or "")
            break
        except Exception as e:  # noqa: BLE001
            if "429" in str(e) and attempt < 4:
                wait = 10 * (attempt + 1)
                logger.warning("rate limited — wait %ds (retry %d/4)", wait, attempt + 1)
                time.sleep(wait)
            else:
                logger.error("Gemini failed: %s — fallback", e)
                result = {}
                break
    out: dict[str, str] = {}
    for t in compact:
        txt = result.get(t, "")
        if not txt or ADVICE_RE.search(txt):
            txt = _rule_fallback(t, _stats_of(t, compact), _bt_of(t, compact))
        out[t] = txt
    index["insights"] = out
    INDEX_PATH.write_text(json.dumps(index))
    logger.info("insights written for %d tickers", len(out))
    return out


def _stats_of(t: str, compact: dict) -> dict:
    c = compact.get(t, {})
    return {"change_1m": c.get("change_1m"), "volatility": c.get("volatility")}


def _bt_of(t: str, compact: dict) -> dict:
    c = compact.get(t, {})
    return {"verdict": c.get("backtest", "unknown")}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    print(json.dumps(build_insights(), indent=2))
