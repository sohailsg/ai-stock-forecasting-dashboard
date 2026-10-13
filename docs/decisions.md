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

## ADR-004: Scale to 200+ tickers — batch fetch, threaded build, holdout, pairs

- **Status:** Accepted (14 Oct 2026)
- **Context:** Universe grew 4→49→236. Sequential fetch (2s gaps) plus the
  5-window walk-forward backtest (5 ARIMA refits per ticker) cannot finish
  a 236-stock universe in reasonable CI time.
- **Decision:**
  1. `fetch_all` does ONE batched `yfinance.download` for the universe;
     individual fetch survives only as retry for gaps, cache as last resort.
  2. `build_all` builds tickers in a `ThreadPoolExecutor(8)`.
  3. Per-ticker backtest is the single hold-out window (`bt.holdout`,
     1 refit) instead of `bt.rolling` (5 refits). `bt.rolling` stays for
     research and tests. Verdicts are noisier per ticker — the page shows
     the error numbers so readers can see the margin.
  4. `index.json` stores only top/bottom-15 correlation pairs, not the
     N×N matrix (~1MB at this scale).
  5. Gemini insights go out in per-sector batches (≤12 tickers) so
     responses stay complete; one extra call for the market overview.
- **Consequences:** full pipeline fits CI; noisier single-window verdicts;
  criteria 95%-run-rate and <10min need re-measuring at this scale.

## ADR-002: Market data source — yfinance (unofficial) with cache + fallback

- **Status:** Accepted (13 Oct 2026)
- **Context:** Need free daily history for the ticker universe (S4-T4.1, now
  236 stocks). Evaluated
  yfinance, Alpha Vantage, Twelve Data, Stooq.
- **Decision:** **yfinance** with `auto_adjust=True`, 5y daily, validation,
  batched download with individual retry, per-ticker CSV cache (`data/stocks/`),
  cache fallback and skip-bad-ticker (see `src/fetch.py`, ADR-004).
- **Consequences:** Free, no key, matches course pandas flow; unofficial API
  risk (R3) mitigated by cache + single-function abstraction for later swap.
  Public display: attribute "Data: Yahoo Finance via yfinance (unofficial),
  educational use" on page + README (R10).
