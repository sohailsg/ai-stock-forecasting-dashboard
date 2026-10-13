import yfinance as yf

candidates = ["CRM", "PFE", "DIS", "LIN", "ULTRACEMCO.NS", "ITC.NS",
              "BAJFINANCE.NS", "POWERGRID.NS", "TATASTEEL.NS"]
for t in candidates:
    try:
        d = yf.download(t, period="1mo", progress=False)
        print(t, "rows:", len(d))
    except Exception as e:
        print(t, "FAIL", str(e)[:80])
