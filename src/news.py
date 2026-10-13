"""news.py — recent headlines per ticker from Google News RSS (no API key).

Used by insights.py so Gemini can ground its commentary in what was actually
reported, instead of guessing why a stock moved. Failures degrade to [].
"""

from __future__ import annotations

import datetime as dt
import email.utils
import logging
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
NAMES_JS = pathlib.Path(__file__).resolve().parent.parent / "dashboard" / "names.js"
_PAIR = re.compile(r'(?:"([^"]+)"|([A-Za-z0-9]+))\s*:\s*"([^"]+)"')
_SUFFIX = re.compile(
    r",?\s+(Inc\.?|Corporation|Corp\.?|Limited|Ltd\.?|plc|N\.V\.|Incorporated|Company|Co\.)$",
    re.IGNORECASE)
INDEX_QUERIES = {"^GSPC": "S&P 500 index", "^NSEI": "Nifty 50 index"}


def company_names() -> dict[str, str]:
    """Ticker -> official name, read from the single source of truth (names.js)."""
    text = NAMES_JS.read_text(encoding="utf-8")
    body = text.split("{", 1)[1]
    return {a or b: v for a, b, v in _PAIR.findall(body)}


def search_name(ticker: str, official: str) -> str:
    if ticker in INDEX_QUERIES:
        return INDEX_QUERIES[ticker]
    name = official
    for _ in range(2):
        name = _SUFFIX.sub("", name).strip()
    return name


def _query_url(ticker: str, name: str, days: int) -> str:
    extra = "share price" if ticker.endswith(".NS") else "stock"
    q = urllib.parse.quote(f'"{name}" {extra} when:{days}d')
    region = ("en-IN", "IN", "IN:en") if ticker.endswith(".NS") else ("en-US", "US", "US:en")
    return f"https://news.google.com/rss/search?q={q}&hl={region[0]}&gl={region[1]}&ceid={region[2]}"


def parse_feed(xml_bytes: bytes, limit: int = 6) -> list[dict]:
    out, seen = [], set()
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        key = re.sub(r"\W+", "", title.lower())[:60]
        if not title or key in seen:
            continue
        seen.add(key)
        try:
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "")
            date = when.astimezone(dt.UTC).date().isoformat()
        except (TypeError, ValueError):
            date = ""
        out.append({"title": title, "source": source, "date": date,
                    "link": (it.findtext("link") or "").strip()})
        if len(out) >= limit:
            break
    return out


def fetch_headlines(ticker: str, official: str, days: int = 14, limit: int = 6) -> list[dict]:
    url = _query_url(ticker, search_name(ticker, official), days)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return parse_feed(r.read(), limit)
    except Exception as e:  # noqa: BLE001
        logger.warning("news fetch failed for %s: %s", ticker, e)
        return []


def fetch_all(tickers: list[str], workers: int = 6) -> dict[str, list[dict]]:
    names = company_names()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = ex.map(lambda t: (t, fetch_headlines(t, names.get(t, t))), tickers)
        return dict(results)
