"""sectors.py — ticker universe grouped by industry (US + India + benchmarks).

Analyst coverage: leaders in every major sector of both markets so
cross-industry comparison is meaningful, plus home-market benchmarks
for relative strength.
"""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT"],
    "Communication": ["GOOGL", "META", "NFLX"],
    "Semiconductors": ["NVDA", "AVGO", "AMD"],
    "EV & Auto": ["TSLA", "F", "GM", "MARUTI.NS", "M&M.NS"],
    "Financials": ["JPM", "V", "BAC", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
    "Healthcare": ["JNJ", "LLY", "UNH"],
    "Consumer": ["AMZN", "WMT", "COST", "HINDUNILVR.NS", "TITAN.NS"],
    "Energy": ["XOM", "CVX", "RELIANCE.NS"],
    "Industrials": ["CAT", "UNP"],
    "Utilities": ["NEE"],
    "Real Estate": ["AMT"],
    "India IT": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
    "India Pharma": ["SUNPHARMA.NS"],
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
    """ISO currency code: INR for NSE (.NS) listings and Nifty 50, USD otherwise."""
    upper = ticker.upper()
    if upper.endswith(".NS") or upper == "^NSEI":
        return "INR"
    return "USD"


def currency_symbol(code: str) -> str:
    return CURRENCY.get(code, "$")
