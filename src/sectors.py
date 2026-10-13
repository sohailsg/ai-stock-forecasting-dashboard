"""sectors.py — ticker universe grouped by industry (US + India + benchmarks).

Analyst coverage: leaders in every major industry of both markets so
cross-industry comparison is meaningful, plus home-market benchmarks
for relative strength.
"""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "CRM"],
    "Communication": ["GOOGL", "META", "NFLX", "DIS"],
    "Semiconductors": ["NVDA", "AVGO", "AMD"],
    "EV & Auto": ["TSLA", "F", "GM", "MARUTI.NS", "M&M.NS"],
    "Financials": ["JPM", "V", "BAC"],
    "BFSI": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BAJFINANCE.NS"],
    "Healthcare": ["JNJ", "LLY", "UNH", "PFE"],
    "Consumer": ["AMZN", "WMT", "COST", "TITAN.NS"],
    "Energy": ["XOM", "CVX", "RELIANCE.NS"],
    "Industrials": ["CAT", "UNP"],
    "Utilities": ["NEE", "POWERGRID.NS"],
    "Real Estate": ["AMT"],
    "India IT": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
    "India Pharma": ["SUNPHARMA.NS"],
    "Materials": ["LIN", "ULTRACEMCO.NS", "TATASTEEL.NS"],
    "India FMCG": ["ITC.NS", "HINDUNILVR.NS"],
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
