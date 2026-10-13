"""sectors.py — ticker universe grouped by industry (US + India + benchmarks).

Analyst coverage: leaders in every major industry of both markets so
cross-industry comparison is meaningful, plus home-market benchmarks
for relative strength. Every ticker verified live on yfinance.
"""

from __future__ import annotations

SECTORS: dict[str, list[str]] = {
    "Technology": [
        "AAPL", "MSFT", "CRM", "ORCL", "ADBE", "INTU", "NOW", "IBM",
        "ACN", "CDNS", "SNPS", "FTNT", "PANW", "WDAY", "CSCO", "ADP",
    ],
    "Communication": [
        "GOOGL", "META", "NFLX", "DIS", "TTWO", "TMUS", "CHTR", "VZ",
    ],
    "Semiconductors": [
        "NVDA", "AVGO", "AMD", "MU", "INTC", "QCOM", "AMAT", "LRCX",
        "NXPI", "TXN",
    ],
    "EV & Auto": [
        "TSLA", "F", "GM", "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS",
        "EICHERMOT.NS", "HEROMOTOCO.NS",
    ],
    "Financials": [
        "JPM", "V", "BAC", "C", "WFC", "GS", "MS", "AXP", "SCHW",
        "USB", "PNC", "TFC", "PRU", "MET", "CB", "AON", "ICE", "CME",
        "SPGI", "MCO", "MSCI", "BLK", "PYPL", "FIS",
    ],
    "BFSI": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BAJFINANCE.NS",
        "BAJAJFINSV.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS",
        "SHRIRAMFIN.NS",
    ],
    "Healthcare": [
        "JNJ", "LLY", "UNH", "PFE", "MRK", "ABBV", "TMO", "DHR",
        "ABT", "BSX", "MDT", "ISRG", "IQV", "SYK", "ZTS", "REGN",
        "RMD", "ELV", "HCA", "VRTX", "WAT", "GILD", "CI", "BMY",
        "APOLLOHOSP.NS",
    ],
    "Consumer": [
        "AMZN", "WMT", "COST", "TITAN.NS", "HD", "MCD", "NKE", "SBUX",
        "LOW", "BKNG", "ORLY", "TJX", "ROST", "TGT", "MAR", "HLT",
        "DHI", "LEN", "TRENT.NS", "KMX", "AZO", "GPC", "MAS",
    ],
    "Staples": [
        "PG", "KO", "PEP", "CL", "KMB", "MDLZ", "MO", "PM", "KDP",
        "KR", "SYY", "CLX", "CHD", "KHC",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "VLO", "MPC",
        "PSX", "HAL", "KMI", "ONGC.NS",
    ],
    "Industrials": [
        "CAT", "UNP", "HON", "GE", "RTX", "LMT", "NOC", "GD", "FDX",
        "UPS", "DE", "EMR", "ITW", "NSC", "ODFL", "RSG", "WM", "FAST",
        "CSX", "CTAS", "APH", "TEL", "DOV", "GLW", "OTIS", "PCAR",
        "GWW", "ROP", "FTV", "PH", "XYL", "LT.NS",
    ],
    "Utilities": [
        "NEE", "POWERGRID.NS", "DUK", "SO", "XEL", "ED", "SRE", "NTPC.NS",
    ],
    "Real Estate": ["AMT", "PLD", "EQIX", "O", "SPG", "PSA", "WELL"],
    "Materials": [
        "LIN", "ULTRACEMCO.NS", "TATASTEEL.NS", "SHW", "APD", "NUE",
        "FCX", "DOW", "ECL", "MLM", "VMC", "STLD", "ASIANPAINT.NS",
        "PPG", "NEM",
    ],
    "India IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "India Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    "India FMCG": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS"],
    "India Energy & Metals": [
        "RELIANCE.NS", "ADANIENT.NS", "HINDALCO.NS", "JSWSTEEL.NS",
        "COALINDIA.NS", "BPCL.NS",
    ],
    "India Infra": ["GRASIM.NS", "BEL.NS", "ADANIPORTS.NS"],
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
