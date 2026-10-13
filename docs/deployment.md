# Deployment (GitHub Pages + sohail-ahmed.space)

ADR-001: domain-only at Network Solutions; no SFTP. `upload.py` retired.

## One-time DNS (Network Solutions panel)

Domains → `sohail-ahmed.space` → DNS:
- `A @ → 185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- `CNAME www → <github-user>.github.io`

Repo → Settings → Pages → Custom domain = `sohail-ahmed.space` → Enforce HTTPS.
`dashboard/CNAME` (and `_site/CNAME` in workflows) holds the domain.

## Pipelines

- Push to `main` → `pages.yml`: test → build stocks → insights (uses repo
  secret `GEMINI_API_KEY`; falls back to rule-based without it) → publish `_site`.
- Weekdays 22:30 UTC → `daily.yml`: same, with `data/stocks` cache.
  US close ≈ 21:00 UTC; weekends skipped (cron `1-5`).
- Only repo secret needed: `GEMINI_API_KEY`.

## Local

```bash
uv sync
uv run pytest tests/ -q
uv run main.py                      # sales + stocks + insights -> output/
python -m http.server 8000          # open /dashboard/ and /dashboard/stocks.html
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Stocks page "Could not load" | Run pipeline first; always use http.server, not file:// |
| Stale banner (>3d) | Check daily.yml runs; re-run via workflow_dispatch |
| 429 Gemini | Retries built in; falls back to rule-based text |
| Schema mismatch | Rebuild JSON; frontend expects `schema_version: 1` |
