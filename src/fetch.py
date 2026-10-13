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
    # yfinance >=0.2.32 returns MultiIndex columns like ('Close', 'AAPL')
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


def fetch_all(tickers: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Fetch every ticker; bad tickers are skipped, never fatal."""
    tickers = tickers or get_tickers()
    results: dict[str, pd.DataFrame] = {}
    for i, t in enumerate(tickers):
        if i > 0:
            time.sleep(INTER_TICKER_DELAY)
        t0 = time.time()
        df = fetch_ticker(t)
        if df is not None:
            results[t] = df
        logger.info("%s: done in %.1fs", t, time.time() - t0)
    logger.info("fetch_all: %d/%d tickers OK", len(results), len(tickers))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    fetch_all()
