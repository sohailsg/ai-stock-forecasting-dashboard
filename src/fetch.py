"""fetch.py — S4 stock data ingestion (EPIC EP-1).

Downloads daily adjusted-close history via yfinance, validates it,
and caches per-ticker CSVs under data/stocks/<TICKER>.csv.

Design (per S4 acceptance criteria):
- Ticker list configurable via TICKERS env var (default 12-ticker US+India set).
- 5 years of daily prices, auto-adjusted for splits/dividends.
- Handles the yfinance multi-index column quirk (recent versions).
- Validates: min rows, no future dates, no non-positive prices,
  sorted / unique / timezone-naive index.
- Retry with exponential backoff on throttling; fall back to cache;
  skip a bad ticker without failing the whole run.
"""

from __future__ import annotations

import logging
import os
import pathlib
import time

import pandas as pd

from src import sectors as sec

logger = logging.getLogger(__name__)

CACHE_DIR = pathlib.Path("data/stocks")
DEFAULT_TICKERS = tuple(sec.DEFAULT_TICKERS)
MIN_ROWS = 200
MAX_RETRIES = 4
INTER_TICKER_DELAY = 2  # seconds between tickers to ease throttling (12-ticker universe)


def get_tickers() -> list[str]:
    """Read the ticker universe from TICKERS env var (comma-separated)."""
    raw = os.environ.get("TICKERS", "")
    if not raw.strip():
        return list(DEFAULT_TICKERS)
    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    return tickers or list(DEFAULT_TICKERS)


def _download(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Download one ticker with retries. Raises on final failure."""
    import yfinance as yf

    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            df = yf.download(
                ticker,
                period=period,
                auto_adjust=True,  # splits + dividends adjusted (S4-ST4.5.2)
                progress=False,
            )
            if df is None or df.empty:
                raise ValueError(f"empty response for {ticker}")
            return df
        except Exception as e:  # noqa: BLE001 — network errors vary
            last_err = e
            wait = 2**attempt * 5  # 5, 10, 20, 40s
            logger.warning(
                "%s fetch failed (attempt %d/%d): %s — retry in %ds",
                ticker, attempt + 1, MAX_RETRIES, e, wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"failed to fetch {ticker}: {last_err}")


def _normalize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten multi-index columns, keep date+close, validate (S4-ST4.3.2/3)."""
    # yfinance >=0.2.32 returns MultiIndex columns like ('Close', 'AAPL');
    # batch group_by="ticker" frames arrive as plain per-ticker frames.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Prefer Close (already adjusted via auto_adjust=True); fall back to Adj Close
    col = "Close" if "Close" in df.columns else "Adj Close"
    if col not in df.columns:
        raise ValueError(f"{ticker}: no Close column in {list(df.columns)}")
    out = pd.DataFrame({"date": pd.to_datetime(df.index), "close": df[col].to_numpy(dtype=float)})
    out["date"] = out["date"].dt.tz_localize(None)  # timezone-naive (S4-ST4.3.3d)
    out = out.dropna().sort_values("date").drop_duplicates("date").reset_index(drop=True)

    if len(out) < MIN_ROWS:
        raise ValueError(f"{ticker}: only {len(out)} rows (< {MIN_ROWS})")
    if (out["close"] <= 0).any():
        raise ValueError(f"{ticker}: non-positive prices found")
    today = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    if (out["date"] > today).any():
        raise ValueError(f"{ticker}: future dates found")
    return out


def fetch_ticker(ticker: str, use_cache_on_failure: bool = True) -> pd.DataFrame | None:
    """Fetch one ticker; save cache; fall back to cache; None = skip (S4-ST4.4)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{ticker}.csv"
    try:
        raw = _download(ticker)
        clean = _normalize(raw, ticker)
        clean.to_csv(cache_path, index=False)
        logger.info("%s: fetched %d rows -> %s", ticker, len(clean), cache_path)
        return clean
    except Exception as e:  # noqa: BLE001 — per-ticker failure must not stop run
        logger.error("%s: fetch failed: %s", ticker, e)
        if use_cache_on_failure and cache_path.exists():
            logger.info("%s: falling back to cache %s", ticker, cache_path)
            return pd.read_csv(cache_path, parse_dates=["date"])
        logger.warning("%s: skipped (no cache)", ticker)
        return None


def _save_cache(ticker: str, clean: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CACHE_DIR / f"{ticker}.csv", index=False)


def _load_cache(ticker: str) -> pd.DataFrame | None:
    p = CACHE_DIR / f"{ticker}.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def _download_batch(tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """One batched download for the whole universe (fast at 200+ tickers).

    Returns {ticker: raw frame}. Tickers missing from the response are simply
    absent — the caller falls back to individual fetch for those.
    """
    import yfinance as yf

    logger.info("batch downloading %d tickers (%s)", len(tickers), period)
    df = yf.download(
        tickers, period=period, auto_adjust=True, progress=False,
        group_by="ticker", threads=True,
    )
    if df is None or df.empty:
        raise ValueError("empty batch response")
    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            if sub is not None and not sub.empty:
                out[t] = sub
        except (KeyError, TypeError):
            continue
    logger.info("batch: %d/%d tickers present", len(out), len(tickers))
    return out


def fetch_all(tickers: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Batch download first, individual retry for gaps, cache fallback last.

    Bad tickers are skipped, never fatal.
    """
    tickers = tickers or get_tickers()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}
    try:
        batch = _download_batch(tickers)
    except Exception as e:  # noqa: BLE001 — whole batch failed, go individual
        logger.error("batch failed (%s) — falling back to individual fetch", e)
        batch = {}
    missing = [t for t in tickers if t not in batch]
    for i, t in enumerate(missing):
        if i > 0:
            time.sleep(INTER_TICKER_DELAY)
        df = fetch_ticker(t)  # individual path with own retries + cache fallback
        if df is not None:
            results[t] = df
    for t, raw in batch.items():
        try:
            clean = _normalize(raw.copy(), t)
            _save_cache(t, clean)
            results[t] = clean
        except Exception as e:  # noqa: BLE001 — bad slice, try individual
            logger.warning("%s: batch slice unusable (%s) — individual retry", t, e)
            df = fetch_ticker(t)
            if df is not None:
                results[t] = df
    # Final safety net: cache for anything still missing
    for t in tickers:
        if t not in results:
            cached = _load_cache(t)
            if cached is not None:
                logger.info("%s: using cache", t)
                results[t] = cached
    logger.info("fetch_all: %d/%d tickers OK", len(results), len(tickers))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    fetch_all()
