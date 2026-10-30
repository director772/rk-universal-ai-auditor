# RK Universal AI Auditor V3 — Hinglish Report Starter

- HTML report page with Issue Location Map and evidence fields.
- Print / Save as PDF via browser's print dialog.
- One system and specific checks at a time.
- No permanent audit history; systems saved only in that browser's localStorage.
- No database or API secrets required in this limited prototype.
- No live CRM, PMS, BUSY, Google Sheet or web app connector. The only working audit is read-only comparison of user-supplied JSON lead snapshots.
- Only comparisons with visible evidence become 'Mismatch Found — Verification Pending'. No source records are changed.

## GitHub + Vercel
Replace old V2 files with contents of V3 folder, preserving paths `api/index.py` and `public/index.html`, and commit. Vercel project can import the repository. Do not set `DATABASE_URL`; V3 does not use it. The deployed URL serves the dashboard.

## Locally
`pip install -r requirements.txt`
`uvicorn api.index:app --reload`
Open http://127.0.0.1:8000

## Limitations
Browser localStorage is not shared between browsers/devices and is not a secure credential store. Do not paste real sensitive customer data into the demo until a secure authentication, connector, and server-side privacy layer are built. Do not use this prototype to claim a complete automated audit.
