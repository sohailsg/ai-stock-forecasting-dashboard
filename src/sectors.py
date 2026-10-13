"""sectors.py — ticker universe grouped by industry (US + India)."""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT"],
    "Semiconductors": ["NVDA", "AVGO"],
    "EV & Auto": ["TSLA"],
    "Financials": ["JPM"],
    "Consumer": ["AMZN"],
    "Energy": ["XOM"],
    "India IT": ["TCS.NS", "INFY.NS"],
    "India Financials": ["HDFCBANK.NS"],
    "India Energy": ["RELIANCE.NS"],
}

TICKER_SECTOR: dict[str, str] = {
    t: sector for sector, tickers in SECTORS.items() for t in tickers
}

DEFAULT_TICKERS: list[str] = [t for tickers in SECTORS.values() for t in tickers]


def get_sector(ticker: str) -> str:
    """Sector label for a ticker; 'Other' for user-added tickers."""
    return TICKER_SECTOR.get(ticker.upper(), "Other")
