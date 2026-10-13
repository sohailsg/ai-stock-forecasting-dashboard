"""insights.py — S9 AI insights with Gemini (batched, graceful fallback).

Sends compact per-ticker stats (never raw series) in ONE batched call,
requests strict JSON {TICKER: text}, retries 429, filters advice phrases,
falls back to rule-based text if Gemini unavailable.
Merges result into output/stocks/index.json -> insights.
"""

from __future__ import annotations

import datetime as dt
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
        "stocks grouped by sector (1-month change %, volatility, forecast verdict), "
        "write exactly 3 plain-English sentences: which sectors led "
        "and lagged, what that suggests about the market mood, "
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


NEWS_CACHE = pathlib.Path("output/news_insights_cache.json")
NEWS_BATCH = 6


def _biggest_recent_move(anomalies: list[dict], days: int = 45) -> dict | None:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    recent = [a for a in anomalies if str(a.get("date", "")) >= cutoff]
    if not recent:
        return None
    a = max(recent, key=lambda x: abs(x.get("return_pct") or 0))
    return {"date": a.get("date"), "return_pct": a.get("return_pct")}


def _news_prompt(batch: dict) -> str:
    return (
        "You are a sharp, plain-spoken markets analyst writing for ordinary investors. "
        "For EACH ticker below you get: company, industry, price statistics, its biggest recent "
        "one-day move, and numbered recent headlines. Write 3 to 4 sentences per company that "
        "REASON about why the stock looks the way it does:\n"
        "- Start from what the price has actually done (use the stats), then connect it to the "
        "headlines that genuinely explain it, citing them like [2]. If no headline explains the "
        "move, say plainly that no clear news driver was found instead of guessing.\n"
        "- Bring in what matters specifically for THIS industry and THIS company's business "
        "(for example rates for banks, crude for oil, subscriber trends for telecom), not generic filler.\n"
        "- Be specific and different for every company. Never reuse stock phrases. "
        "Use the company's full name, no ticker symbols.\n"
        "- Do not invent facts beyond the stats and headlines. No buy/sell advice, no price targets, "
        "no guarantees. Plain words, no jargon like Sharpe or MAPE.\n"
        "Reply STRICT JSON only: {\"TICKER\": {\"text\": \"...\", \"cites\": [headline numbers used]}, ...}\n\n"
        + json.dumps(batch, ensure_ascii=False)
    )


def _clean_news_item(raw, n_headlines: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    text = str(raw.get("text", "")).strip()
    if len(text) < 40 or ADVICE_RE.search(text):
        return None
    cites = [c for c in raw.get("cites", []) if isinstance(c, int) and 1 <= c <= n_headlines]
    return {"text": text, "cites": sorted(set(cites))}


def _gemini_news_insights(client, compact: dict, news: dict, names: dict) -> dict:
    """Per-ticker, news-grounded commentary. Same-day cache avoids re-spending on redeploys."""
    today = dt.date.today().isoformat()
    cache = {}
    if NEWS_CACHE.exists():
        try:
            blob = json.loads(NEWS_CACHE.read_text())
            if blob.get("date") == today:
                cache = blob.get("items", {})
        except (OSError, json.JSONDecodeError):
            cache = {}

    def sig(t: str) -> str:
        return "|".join(h["title"] for h in news.get(t, []))

    result: dict[str, dict] = {}
    todo = []
    for t in compact:
        hit = cache.get(t)
        if hit and hit.get("sig") == sig(t) and hit.get("value"):
            result[t] = hit["value"]
        else:
            todo.append(t)
    logger.info("news insights: %d cached, %d to generate", len(result), len(todo))

    for i in range(0, len(todo), NEWS_BATCH):
        chunk = todo[i:i + NEWS_BATCH]
        batch = {}
        for t in chunk:
            c = compact[t]
            batch[t] = {
                "company": names.get(t, t),
                "industry": c.get("sector"),
                "as_of": today,
                "change_1m_pct": c.get("change_1m"),
                "annual_volatility": c.get("volatility"),
                "worst_fall_from_peak_pct": c.get("max_drawdown"),
                "pct_below_52w_high": c.get("pct_off_high"),
                "pct_vs_50day_average": c.get("dist_ma50_pct"),
                "biggest_move_last_45d": c.get("biggest_move"),
                "headlines": [
                    {"n": n, "date": h["date"], "source": h["source"], "title": h["title"]}
                    for n, h in enumerate(news.get(t, []), 1)
                ],
            }
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model="gemini-2.5-flash", contents=_news_prompt(batch))
                parsed = _parse_json_response(resp.text or "")
                for t in chunk:
                    item = _clean_news_item(parsed.get(t), len(news.get(t, [])))
                    if item:
                        item["as_of"] = today
                        result[t] = item
                        cache[t] = {"sig": sig(t), "value": item}
                break
            except Exception as e:  # noqa: BLE001
                if "429" in str(e) and attempt < 2:
                    wait = 20 * (attempt + 1)
                    logger.warning("rate limited — wait %ds", wait)
                    time.sleep(wait)
                else:
                    logger.error("Gemini news batch failed: %s", e)
                    break
        time.sleep(4)  # stay under free-tier requests-per-minute
    try:
        NEWS_CACHE.write_text(json.dumps({"date": today, "items": cache}))
    except OSError as e:
        logger.warning("could not write news cache: %s", e)
    return result


def build_insights() -> dict[str, str]:
    """Generate insights for all tickers in index; returns {ticker: text}."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError("run src.build first — index.json missing")
    index = json.loads(INDEX_PATH.read_text())
    tickers: list[str] = index.get("tickers", [])
    compact: dict[str, dict] = {}
    payloads: dict[str, dict] = {}
    for t in tickers:
        p = TICKER_DIR / f"{t}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        payloads[t] = d
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
            "biggest_move": _biggest_recent_move(d.get("anomalies", [])),
        }

    # Recent headlines for every ticker (no key needed); stored with each ticker's data.
    news: dict[str, list[dict]] = {}
    if os.environ.get("SKIP_NEWS") != "1":
        from src import news as news_mod
        news = news_mod.fetch_all(list(compact))
        for t, items in news.items():
            payloads[t]["news"] = items
            (TICKER_DIR / f"{t}.json").write_text(json.dumps(payloads[t]))
        logger.info("headlines fetched for %d tickers (%d with news)",
                    len(news), sum(1 for v in news.values() if v))

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
    out = {t: _rule_fallback(t, _stats_of(t, compact), _bt_of(t, compact))
           for t in compact}
    index["news_insights"] = {}
    if not api_key:
        logger.warning("no GEMINI_API_KEY — rule-based fallback, headlines only")
        index["market_insight"] = _market_fallback(snapshot)
        return _save(index, out)

    from google import genai

    from src import news as news_mod

    client = genai.Client(api_key=api_key)
    index["news_insights"] = _gemini_news_insights(
        client, compact, news, news_mod.company_names())
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
