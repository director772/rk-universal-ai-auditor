# RK Universal AI Auditor v0.2 — GitHub/Vercel starter

This is a functional **Phase 1** application, not a finished autonomous auditor.

## Implemented
- Owner API-key gate (no key stored by browser)
- Register multiple named systems + URLs in a database
- Choose specific audit scopes per system (no automatic full audit)
- Run evidence-labeled CRM snapshot comparisons with user-provided JSON
- Save audit history to database
- No connection to actual CRM, PMS, BUSY, Google Sheets, or Cloudflare; system URLs are **registered, not crawled**
- No business-source write/delete API endpoints

## Deploy on Vercel
1. Upload **only these application files** to a private GitHub repository. Do **not** upload local `.venv`, `.db`, real credentials, or business exports.
2. Import that private repo into Vercel and configure `DATABASE_URL` (hosted PostgreSQL, such as Neon) and `AUDITOR_API_KEY` (long random secret) in project environment variables. Do not include values in the repo.
3. Deploy, open `/health`, then open `/` and enter the configured API key.
4. For local test, `python -m pip install -r requirements.txt` then set `AUDITOR_API_KEY` in PowerShell and run `uvicorn api.index:app --reload`.

**Important**: Without `DATABASE_URL` Vercel's ephemeral local SQLite cannot guarantee saved registry or audit history. Set database before deploying. This prototype has a single owner secret; do not place it on a shared device or expose production customer data. Production requires managed user authentication, rate limits, backup policy, access logs, and least-privilege connectors.

## Audit input example
System type `Web App + Google Sheets`. Tick `Missing Records` and/or `Status & Assignment`, then paste JSON arrays:

App: `[ {"lead_id":"L001","status":"Pending"} ]`
Sheet: `[ {"lead_id":"L001","status":"Converted"} ]`

This flags *potential mismatch*, not a proved software defect or staff fault.

## Roadmap — not implemented yet
Read-only connector setup, automatic discovery of actual code/app/sheets, non-mutating browser checks, actual audit evidence links, AI reasoning with citations, scoped per-module runs for all systems, scheduled jobs, and approval/retest workflows.
