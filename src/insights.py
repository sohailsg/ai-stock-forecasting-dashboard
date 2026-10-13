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


from src import sectors as sec


def _save(index: dict, out: dict[str, str]) -> dict[str, str]:
    """Persist insights into index.json on EVERY path (fix: fallback did not save)."""
    index["insights"] = out
    INDEX_PATH.write_text(json.dumps(index))
    logger.info("insights written for %d tickers", len(out))
    return out


def _vol_word(vol: float | None) -> str:
    if vol is None:
        return "unknown choppiness"
    if vol < 0.15:
        return "calm"
    if vol < 0.25:
        return "moderately choppy"
    if vol < 0.40:
        return "choppy"
    return "very choppy"


def _rule_fallback(ticker: str, stats: dict, backtest: dict) -> str:
    """Compose insight from the actual numbers — no fixed template.

    stats/backtest may be the slim _stats_of/_bt_of dicts or the full compact
    entry; every field is optional.
    """
    chg = stats.get("change_1m")
    vol = stats.get("volatility")
    sharpe = stats.get("sharpe")
    dd = stats.get("max_drawdown")
    off_high = stats.get("pct_off_high")
    dist_ma = stats.get("dist_ma50_pct")
    anoms = stats.get("anomalies")
    verdict = backtest.get("verdict", "unknown")
    mape = backtest.get("model_mape")
    sector = stats.get("sector")

    trend = "rose" if (chg or 0) >= 0 else "fell"
    s1 = f"{ticker} {trend} {abs(chg or 0):.1f}% over the last month"
    if sector and sector != "Other":
        s1 += f", a {sector} name"
    if off_high is not None:
        s1 += f" and now sits {abs(off_high):.1f}% below its 52-week high"
    if dist_ma is not None:
        s1 += f", {'above' if dist_ma >= 0 else 'below'} its 50-day trend line"
    s1 += "."

    s2 = f"Trading has been {_vol_word(vol)} (annualised volatility {vol})"
    if sharpe is not None:
        if sharpe > 1:
            s2 += f" with a strong risk-adjusted return (Sharpe {sharpe})"
        elif sharpe > 0:
            s2 += f" with a mildly positive risk-adjusted return (Sharpe {sharpe})"
        else:
            s2 += f" and risk-adjusted returns are negative (Sharpe {sharpe})"
    if dd is not None:
        s2 += f"; its worst fall from a peak was {abs(dd):.1f}%"
    s2 += "."

    if verdict == "beats naive":
        s3 = (f"The statistical forecast has recently beaten a naive "
              f"buy-and-hold guess (error {mape}%), so its 30-day projection "
              f"deserves some attention — still an extrapolation, not a prediction.")
    elif verdict == "comparable":
        s3 = (f"The statistical forecast is only as good as a naive guess "
              f"(error {mape}%), so read its 30-day projection with scepticism.")
    elif verdict == "worse than naive":
        s3 = (f"The statistical forecast has recently done worse than simply "
              f"repeating today's price (error {mape}%), so treat its 30-day "
              f"projection as illustrative only.")
    else:
        s3 = "There is not enough history to judge the forecast, so treat it cautiously."
    if isinstance(anoms, int) and anoms > 0:
        s3 += f" Note: {anoms} unusual daily move{'s' if anoms > 1 else ''} flagged recently."
    return f"{s1} {s2} {s3}"


def _market_fallback(snapshot: dict) -> str:
    """Market overview composed from the data: movers, sectors, breadth, honesty."""
    rows = [(t, v) for t, v in snapshot.items() if v.get("change_1m") is not None]
    if not rows:
        return "Market overview unavailable."
    rows.sort(key=lambda kv: kv[1]["change_1m"])
    worst, best = rows[0], rows[-1]
    beats = sum(1 for _, v in rows if v.get("verdict") == "beats naive")
    above = sum(1 for _, v in rows
                if isinstance(v.get("dist_ma50_pct"), (int, float)) and v["dist_ma50_pct"] >= 0)
    measured = sum(1 for _, v in rows if isinstance(v.get("dist_ma50_pct"), (int, float)))
    by_sec: dict[str, list[float]] = {}
    for _, v in rows:
        if v.get("sector"):
            by_sec.setdefault(v["sector"], []).append(v["change_1m"])
    sec_avg = sorted(((s, sum(a) / len(a)) for s, a in by_sec.items()),
                     key=lambda kv: kv[1])
    s1 = (f"Across {len(rows)} tracked stocks, {best[0]} led at "
          f"+{best[1]['change_1m']:.1f}% while {worst[0]} lagged at "
          f"{worst[1]['change_1m']:.1f}% over the last month.")
    if sec_avg:
        s1 += (f" At industry level, {sec_avg[-1][0]} averaged "
               f"+{sec_avg[-1][1]:.1f}% and {sec_avg[0][0]} averaged "
               f"{sec_avg[0][1]:.1f}%.")
    s2 = (f"{above} of {measured} stocks trade above their 50-day trend line, "
          f"so breadth is {'healthy' if measured and above / measured > 0.5 else 'narrow'}.")
    s2 += (f" Statistical forecasts beat a naive guess for {beats} of {len(rows)} "
           f"tickers, so give each projection only the trust its backtest "
           f"verdict earns.")
    return f"{s1} {s2}"


def _market_via_gemini(client, snapshot: dict) -> str:
    """One short call: 3-sentence cross-sector market overview, no advice."""
    prompt = (
        "You are a cautious market-data commentator. Given this snapshot of "
        "stocks grouped by sector (1-month change %, volatility, backtest verdict "
        "vs naive), write exactly 3 plain-English sentences: which sectors led "
        "and lagged, how trustworthy the statistical forecasts look overall, "
        "and one caution. No buy/sell advice, no recommendations, no guarantees. "
        "Plain text only.\n\n" + json.dumps(snapshot)
    )
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash-lite", contents=prompt)
            txt = (resp.text or "").strip()
            if txt and not ADVICE_RE.search(txt):
                return txt
            return _market_fallback(snapshot)
        except Exception as e:  # noqa: BLE001
            if "429" in str(e) and attempt < 2:
                time.sleep(10 * (attempt + 1))
            else:
                logger.error("market Gemini failed: %s — fallback", e)
                return _market_fallback(snapshot)
    return _market_fallback(snapshot)


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
            "sector": sec.get_sector(t),
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
            "pct_off_high": d["stats"].get("pct_off_high"),
            "dist_ma50_pct": d["stats"].get("dist_ma50_pct"),
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    snapshot = {
        t: {
            "sector": c.get("sector"),
            "change_1m": c.get("change_1m"),
            "volatility": c.get("volatility"),
            "sharpe": c.get("sharpe"),
            "verdict": c.get("backtest"),
        }
        for t, c in compact.items()
    }
    if not api_key:
        logger.warning("no GEMINI_API_KEY — rule-based fallback insights")
        out = {t: _rule_fallback(t, _stats_of(t, compact), _bt_of(t, compact))
               for t in compact}
        index["market_insight"] = _market_fallback(snapshot)
        return _save(index, out)

    prompt = (
        "You are a cautious market-data commentator covering multiple sectors. "
        "For each ticker below, write exactly 2 plain-English sentences: "
        "sentence 1 names its sector and describes trend and risk from the stats; "
        "sentence 2 states forecast reliability using the backtest verdict "
        "('beats naive' = relatively trustworthy, 'worse than naive' = weak, "
        "say so plainly). No buy/sell advice, no recommendations, no guarantees, "
        "no price targets. Reply STRICT JSON only: {\"TICKER\": \"text\", ...}\n\n"
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
    index["market_insight"] = _market_via_gemini(client, snapshot)
    return _save(index, out)


def _stats_of(t: str, compact: dict) -> dict:
    c = compact.get(t, {})
    return {
        "sector": c.get("sector"),
        "change_1m": c.get("change_1m"),
        "volatility": c.get("volatility"),
        "sharpe": c.get("sharpe"),
        "max_drawdown": c.get("max_drawdown"),
        "pct_off_high": c.get("pct_off_high"),
        "dist_ma50_pct": c.get("dist_ma50_pct"),
        "anomalies": c.get("anomalies"),
    }


def _bt_of(t: str, compact: dict) -> dict:
    c = compact.get(t, {})
    return {"verdict": c.get("backtest", "unknown"), "model_mape": c.get("model_mape")}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    print(json.dumps(build_insights(), indent=2))
