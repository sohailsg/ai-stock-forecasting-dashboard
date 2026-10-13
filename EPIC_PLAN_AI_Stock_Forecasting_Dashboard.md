# EPIC EP-1: AI-Powered Stock Forecasting & Insights Dashboard (Capstone)

**Owner:** Sohail Ahmed  **Domain:** sohail-ahmed.space (Network Solutions)  **Base repo:** `arslnyhy/sales-dashboard`
**Status:** Planning  **Target duration:** 4 weeks (about 80 to 100 hours)  **Last updated:** 13 Oct 2026

---

## 0. How to read this plan

Hierarchy: **Epic → Story (S) → Task (T) → Subtask (ST) → Sub-subtask (a, b, c)**.

| Marker | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done |
| **P0 / P1 / P2** | Must-have / Should-have / Nice-to-have |
| **Est.** | Estimated hours (solo developer) |
| **Dep.** | Must be finished first |

---

## 1. Epic definition

### 1.1 Vision
Evolve the session's static sales dashboard into a capstone-grade, interactive, AI-assisted analytics product that fetches stock data, forecasts prices with an honest accuracy backtest, detects anomalies, explains results in plain English with Gemini, and is deployed automatically to a personal domain.

### 1.2 Goals
1. A publicly accessible site on `sohail-ahmed.space` showing interactive stock analytics.
2. A repeatable, scheduled pipeline (fetch → process → forecast → insight → deploy) with no manual steps.
3. A portfolio-quality repository (README, screenshots, tests, architecture diagram) usable on a resume.
4. Demonstrated skills in Python and pandas, time-series forecasting, LLM integration, vanilla JS and Chart.js, SFTP deployment, secrets management, Git and CI.

### 1.3 Non-goals (this epic)
- Real-time (tick-level) trading data or order execution.
- User accounts or a database. All data stays static JSON.
- Financial advice. The site is educational only.

### 1.4 Constraints
- Network Solutions hosting is **static only**, so no Python on the server. Python runs locally or in CI and only results are uploaded via SFTP.
- Gemini free tier only (`gemini-2.5-flash-lite`). Rate limits apply, so batch calls.
- No frontend framework (vanilla HTML, CSS and JS plus Chart.js via CDN), to stay consistent with the course.
- Python 3.13, `uv` for dependency management.

### 1.5 Success metrics
| Metric | Target |
|---|---|
| Site live on custom domain over HTTPS | Yes |
| Tickers supported | 6 to 10 |
| Pipeline end-to-end runtime | Under 10 minutes |
| Pipeline run success rate (scheduled) | At least 95% over 2 weeks |
| Dashboard load time | Under 3 s on broadband |
| Lighthouse (performance / accessibility) | At least 90 / at least 90 |
| Test coverage on pipeline logic | At least 70% |
| Secrets in git history | Zero |

### 1.6 Definition of Done (applies to every story)
- [ ] Code committed to a feature branch and merged via pull request.
- [ ] Runs from a clean clone with `uv sync` and documented commands.
- [ ] No secrets in code or git history.
- [ ] Acceptance criteria for the story verified and ticked.
- [ ] README or docs updated where behaviour changed.
- [ ] Manually verified locally and on the live site where applicable.

---

## 2. Story map overview

| ID | Story | Pri | Est. h | Dep. |
|---|---|---|---|---|
| S1 | Project foundation and repository | P0 | 4 | None |
| S2 | Hosting, domain and DNS | P0 | 5 | S1 |
| S3 | Baseline: run and deploy the existing sales dashboard | P0 | 4 | S1, S2 |
| S4 | Stock data ingestion | P0 | 6 | S1 |
| S5 | Data processing and feature engineering | P0 | 6 | S4 |
| S6 | Forecasting engine | P0 | 8 | S5 |
| S7 | Backtesting and model evaluation | P0 | 6 | S6 |
| S8 | Anomaly detection | P1 | 4 | S5 |
| S9 | AI insights with Gemini | P0 | 6 | S5, S6, S7 |
| S10 | Core interactive frontend | P0 | 10 | S5, S6 |
| S11 | Advanced interactivity | P1 | 10 | S10 |
| S12 | Pipeline orchestration and deployment | P0 | 5 | S3, S4 to S9 |
| S13 | Automation and scheduling | P1 | 5 | S12 |
| S14 | Alerts and notifications | P2 | 4 | S8, S13 |
| S15 | Testing and quality assurance | P0 | 8 | Ongoing |
| S16 | Security and compliance | P0 | 3 | Ongoing |
| S17 | Performance, reliability and observability | P1 | 5 | S10, S12 |
| S18 | Documentation and portfolio packaging | P0 | 6 | Most stories |
| S19 | Release, launch and post-launch review | P0 | 3 | All P0 |
| S20 | Stretch backlog | P2 | n/a | After S19 |

---

## 3. Stories, tasks and subtasks

---

### S1. Project foundation and repository  `P0` `4h`

**Goal:** A clean, reproducible local environment with the course code running.
**Acceptance criteria:** `uv sync` succeeds on a fresh clone; `.env` is gitignored; project builds locally.

- [ ] **T1.1 Set up local tooling** (1h)
  - [ ] ST1.1.1 Install Python 3.13
    - [ ] a. Verify with `python --version`
    - [ ] b. Confirm it matches `.python-version` in the repo
  - [ ] ST1.1.2 Install `uv`
    - [ ] a. Verify with `uv --version`
    - [ ] b. Note the install method in the README prerequisites
  - [ ] ST1.1.3 Install Git and VS Code
    - [ ] a. Configure `user.name` and `user.email`
    - [ ] b. Install the Python extension and select the `.venv` interpreter
- [ ] **T1.2 Get the code** (0.5h)
  - [ ] ST1.2.1 Fork `arslnyhy/sales-dashboard` to your account
  - [ ] ST1.2.2 Clone your fork locally
  - [ ] ST1.2.3 Add the upstream remote (to pull his future fixes)
    - [ ] a. `git remote add upstream <original URL>`
    - [ ] b. Document the "update my fork" procedure in the README
- [ ] **T1.3 Install dependencies** (0.5h)
  - [ ] ST1.3.1 Run `uv sync`
  - [ ] ST1.3.2 Add new dependencies
    - [ ] a. `uv add yfinance statsmodels numpy`
    - [ ] b. Add dev dependencies: `uv add --dev pytest ruff`
  - [ ] ST1.3.3 Commit `pyproject.toml` and `uv.lock`
- [ ] **T1.4 Branching and workflow** (1h)
  - [ ] ST1.4.1 Define the branching model
    - [ ] a. `main` is always deployable
    - [ ] b. `feature/<story-id>-<name>` for work
  - [ ] ST1.4.2 Set up a GitHub Project board (Backlog / In progress / Review / Done)
    - [ ] a. Create one issue per story (S1 to S20)
    - [ ] b. Add tasks as checklist items inside each issue
  - [ ] ST1.4.3 Adopt Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- [ ] **T1.5 Secrets baseline** (1h)
  - [ ] ST1.5.1 Copy `.env.example` to `.env`
  - [ ] ST1.5.2 Verify `.env` is in `.gitignore`
  - [ ] ST1.5.3 Run a secret scan on the history (e.g. `git log -p | grep -i key`) before first push
  - [ ] ST1.5.4 Extend `.env.example` with `TICKERS`, `FORECAST_HORIZON` and other new variables

---

### S2. Hosting, domain and DNS  `P0` `5h`

**Goal:** `sohail-ahmed.space` resolves to a working static host with SFTP access.
**Acceptance criteria:** A test `index.html` uploaded via SFTP loads at `https://sohail-ahmed.space`.

- [ ] **T2.1 Verify hosting entitlement** (1h)
  - [ ] ST2.1.1 Confirm in Network Solutions → *Websites & Hosting* that a hosting plan exists (a domain alone has no SFTP)
  - [ ] ST2.1.2 If none exists, decide: purchase an entry plan, or use an alternative static host (GitHub Pages, Netlify, Cloudflare Pages) and keep the domain
    - [ ] a. Compare cost and effort
    - [ ] b. Record the decision in `docs/decisions.md` (ADR-001)
- [ ] **T2.2 Account hygiene** (0.5h)
  - [ ] ST2.2.1 Add the missing recovery email (flagged "Important" on your dashboard)
  - [ ] ST2.2.2 Enable two-factor authentication on Network Solutions
  - [ ] ST2.2.3 Enable 2FA on GitHub and Google
- [ ] **T2.3 Collect SFTP credentials** (0.5h)
  - [ ] ST2.3.1 Host, port (22), username, password
  - [ ] ST2.3.2 Web root (`htdocs` per course notes)
  - [ ] ST2.3.3 Store in `.env` only (never chat, screenshots or git)
- [ ] **T2.4 Test connection** (1h)
  - [ ] ST2.4.1 Connect with an SFTP client (FileZilla or WinSCP) to confirm credentials
  - [ ] ST2.4.2 Upload a test `hello.html`
  - [ ] ST2.4.3 Troubleshoot if it fails
    - [ ] a. Banner timeout (shared hosting is slow, hence `banner_timeout=60`)
    - [ ] b. Wrong remote directory
    - [ ] c. Firewall or VPN blocking port 22
- [ ] **T2.5 Domain to hosting** (1.5h)
  - [ ] ST2.5.1 Check DNS records in Network Solutions (A record, CNAME for `www`)
  - [ ] ST2.5.2 Point the domain at the hosting package if it is not automatic
  - [ ] ST2.5.3 Wait for propagation; verify with `nslookup` or an online DNS checker
  - [ ] ST2.5.4 Enable SSL/HTTPS
    - [ ] a. Install or activate the certificate
    - [ ] b. Force HTTP → HTTPS redirect
    - [ ] c. Verify there is no mixed-content warning (Chart.js CDN is HTTPS)
- [ ] **T2.6 Decide the URL layout** (0.5h)
  - [ ] ST2.6.1 Choose root (`/`) or subfolder (`/dashboard/`)
  - [ ] ST2.6.2 If a subfolder, fix the `DATA_DIR = "../output/"` path issue
    - [ ] a. Option A: keep the site at the root
    - [ ] b. Option B: change `DATA_DIR` to `"output/"` and deploy `output/` inside the same folder

---

### S3. Baseline: run and deploy the existing sales dashboard  `P0` `4h`

**Goal:** Prove the full pipeline works end to end before adding features.
**Acceptance criteria:** Sales dashboard visible at your domain with AI insight text.

- [ ] **T3.1 Obtain a Gemini API key** (0.5h)
  - [ ] ST3.1.1 Create a key at Google AI Studio
  - [ ] ST3.1.2 Add it to `.env` as `GEMINI_API_KEY`
  - [ ] ST3.1.3 Restrict or monitor key usage in the console
- [ ] **T3.2 Run locally** (1h)
  - [ ] ST3.2.1 `uv run analyze.py` produces the five JSON files in `output/`
  - [ ] ST3.2.2 Serve with `python -m http.server 8000`
  - [ ] ST3.2.3 Open `localhost:8000/dashboard/` and verify all charts render
  - [ ] ST3.2.4 Handle problems
    - [ ] a. 429 rate limits (retry loop exists)
    - [ ] b. Model name deprecated, so check the current free model
    - [ ] c. CORS or `file://` fetch failure, so always use the local server
- [ ] **T3.3 First deploy** (1h)
  - [ ] ST3.3.1 `uv run upload.py`
  - [ ] ST3.3.2 Verify files exist on the server and the page loads on the public URL
  - [ ] ST3.3.3 Check the browser console for 404s on JSON paths
- [ ] **T3.4 Baseline snapshot** (0.5h)
  - [ ] ST3.4.1 Tag `v0.1.0-baseline`
  - [ ] ST3.4.2 Take a screenshot for the README "before" image
- [ ] **T3.5 Study the code** (1h)
  - [ ] ST3.5.1 Read `analyze.py`, `upload.py`, `app.js` end to end
  - [ ] ST3.5.2 Sketch the architecture diagram (Python → JSON → SFTP → browser)
  - [ ] ST3.5.3 List extension points (where the stock pipeline plugs in)

---

### S4. Stock data ingestion  `P0` `6h`

**Goal:** Reliable daily price history for a configurable ticker list.
**Acceptance criteria:** Running the fetch step creates a clean CSV per ticker, and survives API failure using cache.

- [ ] **T4.1 Choose data source** (1h)
  - [ ] ST4.1.1 Evaluate `yfinance` (free, unofficial), Alpha Vantage, Twelve Data, Stooq
    - [ ] a. Compare limits, reliability, licence and terms of use
    - [ ] b. Record the decision (ADR-002)
  - [ ] ST4.1.2 Note the terms-of-use caveat for public display of data
- [ ] **T4.2 Define the ticker universe** (0.5h)
  - [ ] ST4.2.1 US set: AAPL, MSFT, NVDA, TSLA
  - [ ] ST4.2.2 India set: RELIANCE.NS, TCS.NS (relevant to your location)
  - [ ] ST4.2.3 Make configurable via `TICKERS` in `.env`
- [ ] **T4.3 Implement fetch** (2h)
  - [ ] ST4.3.1 Download 5 years of daily adjusted close
  - [ ] ST4.3.2 Handle the multi-index column quirk in recent `yfinance`
  - [ ] ST4.3.3 Validate results
    - [ ] a. Minimum row count (about 200)
    - [ ] b. No future dates
    - [ ] c. No non-positive prices
    - [ ] d. Sorted, unique, timezone-naive index
  - [ ] ST4.3.4 Retry with exponential backoff on throttling
- [ ] **T4.4 Caching and resilience** (1.5h)
  - [ ] ST4.4.1 Save to `data/stocks/<TICKER>.csv`
  - [ ] ST4.4.2 Fall back to cache if the fetch fails
  - [ ] ST4.4.3 Incremental update (fetch only missing days) as an optimisation
  - [ ] ST4.4.4 Skip a bad ticker without failing the whole run
- [ ] **T4.5 Handle market realities** (1h)
  - [ ] ST4.5.1 Different holiday calendars across US and India
  - [ ] ST4.5.2 Stock splits and dividends (use adjusted prices)
  - [ ] ST4.5.3 Delisted or renamed tickers

---

### S5. Data processing and feature engineering  `P0` `6h`

**Goal:** Derive the metrics and series the dashboard and models need.
**Acceptance criteria:** Each ticker has computed MA20/MA50, returns, volatility, Sharpe, max drawdown; unit tests pass.

- [ ] **T5.1 Core series** (1.5h)
  - [ ] ST5.1.1 Daily simple returns (`pct_change`)
  - [ ] ST5.1.2 Log returns (for modelling)
  - [ ] ST5.1.3 Moving averages: 20, 50, optionally 200
- [ ] **T5.2 Risk metrics** (2h)
  - [ ] ST5.2.1 Annualised volatility (30-day rolling, times √252)
  - [ ] ST5.2.2 Sharpe ratio (assume a risk-free rate of 0, and state it)
  - [ ] ST5.2.3 Maximum drawdown
  - [ ] ST5.2.4 Optional: beta against an index (S&P 500 or Nifty 50)
- [ ] **T5.3 Cross-asset analysis** (1h)
  - [ ] ST5.3.1 Correlation matrix of daily returns
  - [ ] ST5.3.2 Handle misaligned calendars (pairwise `min_periods`)
- [ ] **T5.4 Output schema** (1.5h)
  - [ ] ST5.4.1 Design per-ticker JSON: `dates, close, ma20, ma50, forecast, bands, stats, anomalies, backtest`
  - [ ] ST5.4.2 Design `stock_index.json`: tickers, correlations, insights, `generated_at`
  - [ ] ST5.4.3 Version the schema (`schema_version` field) so the frontend can detect mismatches
  - [ ] ST5.4.4 Convert NaN to `null` (invalid in JSON otherwise)
  - [ ] ST5.4.5 Round numbers to keep file size small

---

### S6. Forecasting engine  `P0` `8h`

**Goal:** A defensible 30-day forecast with uncertainty bands.
**Acceptance criteria:** Forecast and 95% band produced per ticker; method documented with limitations.

- [ ] **T6.1 Research and baseline** (1.5h)
  - [ ] ST6.1.1 Understand why price forecasting is hard (efficient-market behaviour, near random walk)
  - [ ] ST6.1.2 Define baselines: naive (last value) and drift
- [ ] **T6.2 Primary model: ARIMA** (3h)
  - [ ] ST6.2.1 Fit ARIMA(1,1,1) with drift on log prices
  - [ ] ST6.2.2 Produce the mean forecast and 95% confidence interval; convert back with `exp`
  - [ ] ST6.2.3 Generate business-day dates for the horizon
  - [ ] ST6.2.4 Handle failures
    - [ ] a. Non-convergence warnings
    - [ ] b. Fall back to the naive forecast, and flag it in the JSON
- [ ] **T6.3 Model selection (optional upgrade)** (2h)
  - [ ] ST6.3.1 Compare ARIMA orders via AIC on a small grid
  - [ ] ST6.3.2 Compare against Holt-Winters (damped trend)
  - [ ] ST6.3.3 Select the best model per ticker using backtest error (S7), not AIC alone
- [ ] **T6.4 Make horizon configurable** (0.5h)
  - [ ] ST6.4.1 `FORECAST_HORIZON` env var (default 30)
  - [ ] ST6.4.2 Frontend reads the horizon from the JSON, not a hard-coded value
- [ ] **T6.5 Document limitations** (1h)
  - [ ] ST6.5.1 Write a "How the forecast works" explainer for the page
  - [ ] ST6.5.2 State plainly that it is a statistical extrapolation, not a prediction of events

---

### S7. Backtesting and model evaluation  `P0` `6h`

**Goal:** Show honestly whether the model beats naive.
**Acceptance criteria:** Every ticker displays model MAPE vs naive MAPE and a plain verdict.

- [ ] **T7.1 Hold-out backtest** (2h)
  - [ ] ST7.1.1 Train on all but the last H days, forecast H days, compare with actuals
  - [ ] ST7.1.2 Compute MAPE for the model and for naive
- [ ] **T7.2 Rolling-origin evaluation (stronger)** (2.5h)
  - [ ] ST7.2.1 Walk-forward over several cut-off points (e.g. 5 windows)
  - [ ] ST7.2.2 Average MAPE and RMSE across windows
  - [ ] ST7.2.3 Compute directional accuracy (up or down)
  - [ ] ST7.2.4 Check band coverage: how often actuals fall inside the 95% band
- [ ] **T7.3 Verdict logic** (0.5h)
  - [ ] ST7.3.1 Label "beats naive", "comparable" or "worse than naive" using a tolerance threshold
- [ ] **T7.4 Performance guardrail** (1h)
  - [ ] ST7.4.1 Cache backtest results so daily runs don't refit many windows needlessly
  - [ ] ST7.4.2 Log runtime per ticker

---

### S8. Anomaly detection  `P1` `4h`

**Goal:** Flag unusual daily moves visibly on the chart.
**Acceptance criteria:** Anomalies listed in JSON and drawn as markers; threshold documented.

- [ ] **T8.1 Statistical method** (1.5h)
  - [ ] ST8.1.1 Rolling 60-day z-score on returns; flag where |z| exceeds 3
  - [ ] ST8.1.2 Tune the window and threshold; test sensitivity
- [ ] **T8.2 Enrich anomalies** (1.5h)
  - [ ] ST8.2.1 Record date, price, return % and z-score
  - [ ] ST8.2.2 Cap to the most recent N to limit payload size
- [ ] **T8.3 Optional alternative** (1h)
  - [ ] ST8.3.1 Compare with Isolation Forest or a volume-based flag
  - [ ] ST8.3.2 Document the chosen approach and why

---

### S9. AI insights with Gemini  `P0` `6h`

**Goal:** Plain-English, cautious per-ticker commentary.
**Acceptance criteria:** Each ticker shows a 2-sentence insight; run does not exceed free-tier limits; failure degrades gracefully.

- [ ] **T9.1 Prompt design** (2h)
  - [ ] ST9.1.1 Send compact statistics (never raw price series)
  - [ ] ST9.1.2 Instruct: no buy/sell advice; mention forecast reliability using backtest results
  - [ ] ST9.1.3 Request strict JSON output: `{"TICKER": "text"}`
  - [ ] ST9.1.4 Iterate on prompt quality with 3 to 5 test runs
- [ ] **T9.2 Robust integration** (2h)
  - [ ] ST9.2.1 One batched call for all tickers
  - [ ] ST9.2.2 Retry on 429 with backoff (reuse the existing pattern)
  - [ ] ST9.2.3 Parse JSON defensively (strip code fences, catch malformed output)
  - [ ] ST9.2.4 Fall back to a rule-based text summary if Gemini fails
- [ ] **T9.3 Guardrails** (1h)
  - [ ] ST9.3.1 Filter out outputs containing advice-like phrases ("you should buy")
  - [ ] ST9.3.2 Label the text "AI-generated" in the UI
- [ ] **T9.4 Cost and quota management** (1h)
  - [ ] ST9.4.1 Cache insights; regenerate only if the data changed materially
  - [ ] ST9.4.2 Re-check the current free model name before each release
  - [ ] ST9.4.3 Optional: a Q&A box is out of scope here (needs a backend, see S20)

---

### S10. Core interactive frontend  `P0` `10h`

**Goal:** A polished, responsive stocks page.
**Acceptance criteria:** Ticker switching, range selection, indicator toggles, and KPI cards work with no console errors on desktop and mobile.

- [ ] **T10.1 Page structure** (1.5h)
  - [ ] ST10.1.1 `stocks.html` skeleton and shared header or nav with the sales page
  - [ ] ST10.1.2 Semantic HTML (header, main, section) and ARIA labels
- [ ] **T10.2 Data loading layer** (1.5h)
  - [ ] ST10.2.1 Fetch helper with clear error messages
  - [ ] ST10.2.2 Lazy-load per-ticker JSON on selection
  - [ ] ST10.2.3 Loading and error states (skeleton or spinner, friendly retry message)
  - [ ] ST10.2.4 Check `schema_version`
- [ ] **T10.3 Main price chart** (3h)
  - [ ] ST10.3.1 Line chart with history, forecast (dashed) and shaded 95% band
  - [ ] ST10.3.2 Tooltips with date, price and delta
  - [ ] ST10.3.3 Anomaly markers
  - [ ] ST10.3.4 Handle null values and gaps
  - [ ] ST10.3.5 Destroy and recreate charts on update to avoid memory leaks
- [ ] **T10.4 Controls** (2h)
  - [ ] ST10.4.1 Ticker dropdown
  - [ ] ST10.4.2 Range buttons: 1M, 6M, 1Y, 5Y
  - [ ] ST10.4.3 Toggles: MA20, MA50, forecast, anomalies
  - [ ] ST10.4.4 Persist selections in the URL hash (shareable links)
- [ ] **T10.5 KPI cards** (1h)
  - [ ] ST10.5.1 Last close, 1-month change, volatility, Sharpe, max drawdown
  - [ ] ST10.5.2 Backtest card: model vs naive MAPE and the verdict
- [ ] **T10.6 Responsive and accessible styling** (1h)
  - [ ] ST10.6.1 Mobile layout checked at 375px width
  - [ ] ST10.6.2 Colour contrast at least 4.5:1
  - [ ] ST10.6.3 Keyboard navigable controls with visible focus

---

### S11. Advanced interactivity  `P1` `10h`

**Goal:** Features that make this a capstone rather than a tutorial.
**Acceptance criteria:** At least 4 of the 6 tasks delivered and documented.

- [ ] **T11.1 Compare mode** (2h)
  - [ ] ST11.1.1 Overlay two tickers rebased to 100 at range start
  - [ ] ST11.1.2 Align by date across markets
- [ ] **T11.2 Correlation heatmap** (1.5h)
  - [ ] ST11.2.1 Colour-scaled table from the matrix
  - [ ] ST11.2.2 Click a cell to open compare mode for that pair
- [ ] **T11.3 Zoom and pan** (1.5h)
  - [ ] ST11.3.1 Add `chartjs-plugin-zoom` via CDN (pin the version)
  - [ ] ST11.3.2 Reset-zoom button
- [ ] **T11.4 Portfolio simulator** (3h)
  - [ ] ST11.4.1 Sliders for weights across selected tickers (sum to 100%)
  - [ ] ST11.4.2 Compute portfolio return and volatility in JS from per-ticker returns
  - [ ] ST11.4.3 Show the equal-weight benchmark
- [ ] **T11.5 What-if forecast horizon** (1h)
  - [ ] ST11.5.1 Slider to truncate the displayed forecast to 5 to 30 days
- [ ] **T11.6 Utility features** (1h)
  - [ ] ST11.6.1 Dark mode toggle (respect `prefers-color-scheme`)
  - [ ] ST11.6.2 Export the current view to CSV
  - [ ] ST11.6.3 Download the chart as PNG

---

### S12. Pipeline orchestration and deployment  `P0` `5h`

**Goal:** One command runs everything and publishes.
**Acceptance criteria:** `uv run main.py` completes fetch → analyze → forecast → insight → upload and the live site updates.

- [ ] **T12.1 Orchestration** (1.5h)
  - [ ] ST12.1.1 Update `main.py` with ordered steps and clear logging
  - [ ] ST12.1.2 Fail fast on critical errors and continue on per-ticker errors
  - [ ] ST12.1.3 Exit codes: 0 success, non-zero failure (needed by schedulers)
- [ ] **T12.2 Safer deployment** (2h)
  - [ ] ST12.2.1 Upload to a temp name, then rename (avoid half-written files being served)
  - [ ] ST12.2.2 Upload only changed files (compare size or hash)
  - [ ] ST12.2.3 Handle new subfolders (the upload script currently skips subdirectories)
  - [ ] ST12.2.4 Pin or verify the SFTP host key instead of `AutoAddPolicy` (security hardening)
- [ ] **T12.3 Cache-busting** (1h)
  - [ ] ST12.3.1 Append `?v=<generated_at>` to JSON requests so browsers don't show stale data
  - [ ] ST12.3.2 Check hosting cache headers
- [ ] **T12.4 Post-deploy verification** (0.5h)
  - [ ] ST12.4.1 Script that requests the live URL and checks `generated_at` is fresh
  - [ ] ST12.4.2 Roll back by re-uploading the previous known-good JSON

---

### S13. Automation and scheduling  `P1` `5h`

**Goal:** Daily refresh with no manual action.
**Acceptance criteria:** Pipeline runs daily after market close and the site timestamp updates.

- [ ] **T13.1 Choose the runner** (0.5h)
  - [ ] ST13.1.1 Option A: Windows Task Scheduler on your PC (needs the PC on)
  - [ ] ST13.1.2 Option B: GitHub Actions cron (no PC needed, recommended)
  - [ ] ST13.1.3 Record the decision (ADR-003)
- [ ] **T13.2 Implement GitHub Actions** (3h)
  - [ ] ST13.2.1 Workflow file with `schedule` (cron) and `workflow_dispatch`
  - [ ] ST13.2.2 Steps: checkout, install `uv`, `uv sync`, run `main.py`
  - [ ] ST13.2.3 Add repository secrets
    - [ ] a. `GEMINI_API_KEY`
    - [ ] b. `SFTP_HOST`, `SFTP_USER`, `SFTP_PASS`, `SFTP_PORT`, `SFTP_REMOTE_DIR`
  - [ ] ST13.2.4 Cache `uv` and the `data/stocks` CSVs between runs
  - [ ] ST13.2.5 Handle schedule timing
    - [ ] a. US close is about 21:00 UTC, so run later than that
    - [ ] b. Skip weekends
- [ ] **T13.3 Failure handling** (1h)
  - [ ] ST13.3.1 Fail the workflow visibly on errors
  - [ ] ST13.3.2 Upload logs as a workflow artifact
  - [ ] ST13.3.3 Verify behaviour if SFTP blocks cloud IP ranges (fallback: Task Scheduler)
- [ ] **T13.4 Staleness guard on the page** (0.5h)
  - [ ] ST13.4.1 Show a warning banner if `generated_at` is older than 3 days

---

### S14. Alerts and notifications  `P2` `4h`

**Goal:** Get notified of notable events.
**Acceptance criteria:** An anomaly or pipeline failure triggers a Slack or email message.

- [ ] **T14.1 Slack webhook alerts** (2h)
  - [ ] ST14.1.1 Create an incoming webhook (store the URL as a secret)
  - [ ] ST14.1.2 Send a summary when new anomalies appear
  - [ ] ST14.1.3 Deduplicate so the same anomaly isn't sent twice
- [ ] **T14.2 Email alerts (optional)** (1h)
  - [ ] ST14.2.1 SMTP or a transactional email service
- [ ] **T14.3 Pipeline health alerts** (1h)
  - [ ] ST14.3.1 Notify on failed runs
  - [ ] ST14.3.2 Notify if data is stale

---

### S15. Testing and quality assurance  `P0` `8h`  (ongoing)

**Goal:** Confidence that changes don't break the pipeline or UI.
**Acceptance criteria:** Test suite passes in CI; at least 70% coverage on pipeline logic.

- [ ] **T15.1 Test setup** (1h)
  - [ ] ST15.1.1 `pytest` configuration and `tests/` folder
  - [ ] ST15.1.2 Small fixture CSV with known values
- [ ] **T15.2 Unit tests** (3h)
  - [ ] ST15.2.1 Returns, MAs, volatility, drawdown against hand-calculated values
  - [ ] ST15.2.2 Anomaly detector on a series with a planted spike
  - [ ] ST15.2.3 JSON serialisation (NaN becomes null; schema keys present)
  - [ ] ST15.2.4 Forecast shape (length equals horizon; lower is at most mean, which is at most upper)
  - [ ] ST15.2.5 Gemini parser handles fenced, malformed and empty responses (mock the API)
- [ ] **T15.3 Integration test** (1.5h)
  - [ ] ST15.3.1 Run the pipeline on fixture data with the network mocked
  - [ ] ST15.3.2 Validate the output JSON against the schema
- [ ] **T15.4 Frontend manual test matrix** (1.5h)
  - [ ] ST15.4.1 Browsers: Chrome, Firefox, Safari or Edge
  - [ ] ST15.4.2 Devices: desktop, phone
  - [ ] ST15.4.3 Edge cases: missing JSON, ticker with short history, slow network
- [ ] **T15.5 Linting and CI** (1h)
  - [ ] ST15.5.1 `ruff` for Python
  - [ ] ST15.5.2 GitHub Action running tests and lint on pull requests

---

### S16. Security and compliance  `P0` `3h`  (ongoing)

**Goal:** No leaks, safe defaults, legal clarity.
**Acceptance criteria:** Security checklist complete; disclaimer visible on the site.

- [ ] **T16.1 Secrets** (1h)
  - [ ] ST16.1.1 `.env` never committed; verify with `git ls-files`
  - [ ] ST16.1.2 Rotate keys immediately if ever exposed
  - [ ] ST16.1.3 Ensure nothing sensitive sits in `dashboard/` or `output/`
- [ ] **T16.2 Transport and host** (0.5h)
  - [ ] ST16.2.1 HTTPS enforced
  - [ ] ST16.2.2 Host key verification for SFTP
- [ ] **T16.3 Frontend safety** (0.5h)
  - [ ] ST16.3.1 Use `textContent` instead of `innerHTML` for AI-generated text
  - [ ] ST16.3.2 Pin the CDN version of Chart.js; consider Subresource Integrity (SRI) hashes
- [ ] **T16.4 Legal and disclaimers** (1h)
  - [ ] ST16.4.1 "Educational only, not financial advice" notice on the page and in the README
  - [ ] ST16.4.2 Data-source attribution
  - [ ] ST16.4.3 Check data-provider terms for public redisplay

---

### S17. Performance, reliability and observability  `P1` `5h`

**Goal:** Fast pages, stable runs, visible health.
**Acceptance criteria:** Lighthouse performance at least 90; run logs show timing and errors.

- [ ] **T17.1 Payload optimisation** (1.5h)
  - [ ] ST17.1.1 Round values; drop unneeded fields
  - [ ] ST17.1.2 Compact JSON (no indentation) in production
  - [ ] ST17.1.3 Enable gzip on the host if available
- [ ] **T17.2 Frontend performance** (1.5h)
  - [ ] ST17.2.1 Lazy-load per-ticker data
  - [ ] ST17.2.2 Disable chart animations for large datasets
  - [ ] ST17.2.3 Decimate or downsample the 5Y view if sluggish
- [ ] **T17.3 Observability** (1h)
  - [ ] ST17.3.1 Structured logging with timestamps and per-step duration
  - [ ] ST17.3.2 A `run_summary.json` (tickers OK or failed, runtime) shown in the footer
- [ ] **T17.4 Reliability** (1h)
  - [ ] ST17.4.1 Timeouts on all network calls
  - [ ] ST17.4.2 Idempotent runs (rerunning produces the same state)

---

### S18. Documentation and portfolio packaging  `P0` `6h`

**Goal:** Make the project impressive and reproducible.
**Acceptance criteria:** A stranger can clone and run it from the README alone.

- [ ] **T18.1 README** (2.5h)
  - [ ] ST18.1.1 Overview, live link, screenshots or GIF
  - [ ] ST18.1.2 Architecture diagram
  - [ ] ST18.1.3 Setup steps, `.env` reference table, commands
  - [ ] ST18.1.4 Features list and a "limitations and disclaimer" section
  - [ ] ST18.1.5 Roadmap (link to S20)
- [ ] **T18.2 Technical docs** (1.5h)
  - [ ] ST18.2.1 `docs/architecture.md` (data flow, schema)
  - [ ] ST18.2.2 `docs/decisions.md` (ADR-001 to ADR-003)
  - [ ] ST18.2.3 `docs/forecasting.md` (method, metrics, limits)
  - [ ] ST18.2.4 `docs/deployment.md` (SFTP, DNS, SSL, troubleshooting)
- [ ] **T18.3 Demo assets** (1h)
  - [ ] ST18.3.1 Screenshots (desktop and mobile)
  - [ ] ST18.3.2 A 60 to 90 second screen recording
- [ ] **T18.4 Career packaging** (1h)
  - [ ] ST18.4.1 Resume bullets with measurable outcomes
  - [ ] ST18.4.2 LinkedIn post with the demo
  - [ ] ST18.4.3 GitHub repo polish: description, topics, pinned repo

---

### S19. Release, launch and post-launch review  `P0` `3h`

**Goal:** Ship v1.0 and capture learnings.
**Acceptance criteria:** v1.0.0 tagged, live, announced; retrospective written.

- [ ] **T19.1 Release checklist** (1h)
  - [ ] ST19.1.1 All P0 stories at Done
  - [ ] ST19.1.2 Fresh clone smoke test
  - [ ] ST19.1.3 Live site check on desktop and mobile
  - [ ] ST19.1.4 Tag `v1.0.0` and write release notes
- [ ] **T19.2 Launch** (0.5h)
  - [ ] ST19.2.1 Share the link with the course group
  - [ ] ST19.2.2 Post on LinkedIn
- [ ] **T19.3 Post-launch monitoring (first 2 weeks)** (1h)
  - [ ] ST19.3.1 Check scheduled runs daily
  - [ ] ST19.3.2 Log and triage issues in GitHub
- [ ] **T19.4 Retrospective** (0.5h)
  - [ ] ST19.4.1 What went well, what didn't, what to change
  - [ ] ST19.4.2 Update the backlog

---

### S20. Stretch backlog  `P2`

Ideas to pull from after v1.0, each to be refined into its own story.

- [ ] **S20.1 Better models**
  - [ ] a. Prophet, SARIMAX with exogenous variables, gradient boosting on lag features
  - [ ] b. LSTM or small neural net, compared fairly in the backtest
  - [ ] c. Ensemble of models weighted by backtest performance
- [ ] **S20.2 More data**
  - [ ] a. News sentiment (headlines summarised by Gemini)
  - [ ] b. Macro indicators and sector ETFs
  - [ ] c. Volume and fundamentals (P/E, earnings dates)
- [ ] **S20.3 Backend upgrade** (move beyond static hosting)
  - [ ] a. Host a small API (FastAPI) on a cloud service
  - [ ] b. Live data refresh and a database (SQLite or Postgres)
  - [ ] c. "Ask the data" chat box powered by Gemini
- [ ] **S20.4 Product features**
  - [ ] a. Watchlist saved per user in `localStorage`
  - [ ] b. Price-target alerts
  - [ ] c. Shareable report generation (PDF)
- [ ] **S20.5 Engineering polish**
  - [ ] a. Docker image for reproducibility
  - [ ] b. Type hints and `mypy`
  - [ ] c. Pre-commit hooks

---

## 4. Delivery roadmap

| Week | Sprint goal | Stories | Exit criteria |
|---|---|---|---|
| **1** | Foundation and live baseline | S1, S2, S3, S4 | Sales dashboard live at your domain; stock CSVs fetching |
| **2** | Analytics and forecasting core | S5, S6, S7, S8 | Per-ticker JSON with forecast, backtest and anomalies |
| **3** | AI and interactive UI | S9, S10, S11 (partial) | Stocks page live with insights and core interactions |
| **4** | Automation, hardening and launch | S11 (rest), S12, S13, S15, S16, S17, S18, S19 | Scheduled pipeline; v1.0.0 released |
| **After** | Stretch | S14, S20 | Pull as time allows |

**Critical path:** S1 → S2 → S3 (baseline live) · S4 → S5 → S6 → S7 → S9 → S10 → S12 → S13 → S19

**Buffer:** keep about 15% of time unallocated for DNS or SFTP surprises and API changes.

---

## 5. Risks and mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Hosting plan lacks SFTP or is not purchased | Medium | High | Verify in S2 before any build; fallback to GitHub Pages or Netlify with the same domain |
| R2 | DNS propagation delays | Medium | Medium | Start S2 on day 1; work locally in parallel |
| R3 | `yfinance` throttles or breaks (unofficial API) | High | High | Cache CSVs, retry with backoff, abstract the data source behind one function, alternate provider ready |
| R4 | Gemini free model changes or becomes paid | Medium | Medium | Model name in config, rule-based fallback text, check before release |
| R5 | Gemini rate limit (429) | High | Low | One batched call, retries, cached insights |
| R6 | Forecast looks poor and undermines credibility | High | Medium | Show backtest vs naive openly; frame as a learning exercise; disclaimers |
| R7 | GitHub Actions IPs blocked by the host's SFTP | Low | Medium | Test early in S13; fallback to Task Scheduler |
| R8 | Secrets leak into git | Low | High | `.gitignore`, secret scan, repo secrets only, rotate on exposure |
| R9 | Scope creep from the stretch ideas | High | Medium | Strict P0/P1/P2 tiers; stretch only after v1.0 |
| R10 | Public-display licence issues with market data | Medium | Medium | Review provider terms; attribute; consider showing derived metrics only |
| R11 | Time lost to frontend polish | Medium | Low | Time-box S10 and S11; drop P1 tasks first |

---

## 6. Dependencies and assumptions

**Dependencies**
- Active Network Solutions hosting with SFTP (S2).
- Gemini API key (S3).
- Internet access for the data provider (S4).
- GitHub account (for Actions, S13).

**Assumptions**
- Solo developer with about 20 hours per week.
- The free Gemini model remains available.
- Daily (not intraday) data is sufficient.
- Python runs outside the host (local PC or CI).

---

## 7. Open questions (decide early)

1. Does your Network Solutions account include a hosting plan with SFTP, or only the domain? *(blocks S2)*
2. Site at the root domain or a `/dashboard/` subfolder? *(affects the path fix in T2.6)*
3. Which tickers matter most (US only, India only, or both)?
4. Run the schedule from your PC or from GitHub Actions?
5. Which 4 or more advanced features from S11 will you commit to?

---

## 8. Progress tracker

| Story | Status | % | Notes |
|---|---|---|---|
| S1 Foundation | Not started | 0 | |
| S2 Hosting and domain | Not started | 0 | |
| S3 Baseline | Not started | 0 | |
| S4 Data ingestion | Not started | 0 | |
| S5 Processing | Not started | 0 | |
| S6 Forecasting | Not started | 0 | |
| S7 Backtesting | Not started | 0 | |
| S8 Anomalies | Not started | 0 | |
| S9 AI insights | Not started | 0 | |
| S10 Core UI | Not started | 0 | |
| S11 Advanced UI | Not started | 0 | |
| S12 Orchestration | Not started | 0 | |
| S13 Scheduling | Not started | 0 | |
| S14 Alerts | Not started | 0 | |
| S15 Testing | Not started | 0 | |
| S16 Security | Not started | 0 | |
| S17 Performance | Not started | 0 | |
| S18 Documentation | Not started | 0 | |
| S19 Release | Not started | 0 | |
| S20 Stretch | Backlog | n/a | |
