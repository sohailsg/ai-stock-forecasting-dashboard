"""sectors.py — ticker universe grouped by industry (US + India + benchmarks).

Analyst coverage: mega-cap leaders in each major sector so cross-industry
comparison is meaningful, plus home-market benchmarks for relative strength.
"""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL"],
    "Semiconductors": ["NVDA", "AVGO", "AMD"],
    "EV & Auto": ["TSLA", "MARUTI.NS"],
    "Financials": ["JPM", "V", "HDFCBANK.NS", "ICICIBANK.NS"],
    "Healthcare": ["JNJ", "LLY"],
    "Consumer": ["AMZN", "WMT"],
    "Energy": ["XOM", "CVX", "RELIANCE.NS"],
    "India IT": ["TCS.NS", "INFY.NS"],
    "Benchmark": ["^GSPC", "^NSEI"],
}

TICKER_SECTOR: dict[str, str] = {
    t: sector for sector, tickers in SECTORS.items() for t in tickers
}

DEFAULT_TICKERS: list[str] = [t for tickers in SECTORS.values() for t in tickers]

CURRENCY: dict[str, str] = {"USD": "$", "INR": "\u20b9"}


def get_sector(ticker: str) -> str:
    """Sector label for a ticker; 'Other' for user-added tickers."""
    return TICKER_SECTOR.get(ticker.upper(), "Other")


def get_currency(ticker: str) -> str:
    """ISO currency code: INR for NSE (.NS) listings, USD otherwise."""
    if ticker.upper().endswith(".NS"):
        return "INR"
    return "USD"


def currency_symbol(code: str) -> str:
    return CURRENCY.get(code, "$")
