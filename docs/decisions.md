# Decisions (Architecture Decision Records)

## ADR-001: Static host — GitHub Pages instead of Network Solutions hosting

- **Status:** Accepted (13 Oct 2026)
- **Context:** `sohail-ahmed.space` is domain-only at Network Solutions
  ("Not connected to any services", 0 available services). Epic S2-T2.1.2
  allows an alternative static host. Course flow assumes SFTP to `htdocs`.
- **Decision:** Keep the domain at NS for DNS only; deploy the static site
  (dashboard + generated JSON) to **GitHub Pages** with custom domain
  `sohail-ahmed.space`. `upload.py` (SFTP/paramiko) is retained for course
  reference but removed from the pipeline.
- **Consequences:** $0 hosting, auto-HTTPS, no SFTP firewall risk (R7 gone);
  S12/S13 become git-push + Actions cron. Only secret needed: `GEMINI_API_KEY`.

## ADR-002: Market data source — yfinance (unofficial) with cache + fallback

- **Status:** Accepted (13 Oct 2026)
- **Context:** Need free daily history for 4–6 tickers (S4-T4.1). Evaluated
  yfinance, Alpha Vantage, Twelve Data, Stooq.
- **Decision:** **yfinance** with `auto_adjust=True`, 5y daily, validation,
  exponential-backoff retries, per-ticker CSV cache (`data/stocks/`),
  cache fallback and skip-bad-ticker (see `src/fetch.py`).
- **Consequences:** Free, no key, matches course pandas flow; unofficial API
  risk (R3) mitigated by cache + single-function abstraction for later swap.
  Public display: attribute "Data: Yahoo Finance via yfinance (unofficial),
  educational use" on page + README (R10).
