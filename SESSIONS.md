# Sessions

A running changelog of what was built each working session, newest first. Each entry records
the goal, what shipped, key decisions, and anything left open — so any session can pick up
exactly where the last one stopped.

> Format: one `## Session N — YYYY-MM-DD` heading per session. Add a new entry at the top.

---

## Session 1 — 2026-06-23 → 2026-06-24

**Goal:** Build an open-source business-automation portfolio repo to show prospective clients
and employers, grounded in what real automation job/contract descriptions ask for.

### Shipped
- **Research → plan.** Reviewed business-automation job/contract descriptions; distilled the
  in-demand patterns (workflow tools incl. n8n, API/webhook integration with error handling,
  Python, the five money use-cases, docs) into `PLAN.md` and the repo design.
- **Repo created** and published: https://github.com/danieaneta/business-automation-playbook
  (public). Authored solely under Danielle's account.
- **Five blueprints built, runnable, and tested — 108 passing tests:**
  - `01-lead-capture-to-crm` (16) — enrich → ICP score → idempotent CRM upsert → route
  - `02-client-onboarding` (15) — won deal → per-plan checklist → idempotent provisioning
  - `03-invoicing-billing` (29) — usage → invoice math (tax/due dates) → reminders → reconcile
  - `04-support-ticket-routing` (24) — classify → route → SLA deadline + breach detection
  - `05-automated-reporting` (24) — multi-source KPIs → period deltas → digest → idempotent delivery
  - Each reuses the `shared/` layer (retry/backoff, structured logging, idempotent store), ships
    an n8n `workflow.json`, a `.env.example`, and runs on bundled dummy data with no API keys.
- **Interactive browser demos** (`index.html`) — tabbed, self-contained (works via `file://`),
  with each engine ported from Python to JS and **verified to match the Python output exactly**.
- **Serverless API** (`netlify/functions/` + `netlify.toml`, documented in `API.md`) — five
  zero-dependency endpoints reusing the verified JS engines; CORS on; `/api/*` routes.
- **Real-data validation harnesses** (`validate/`):
  - `03-invoicing` ← **real** UCI Online Retail II data — invoice reconciliation **PASS** within
    $0.01 across 3 customers; messy rows (returns, blank IDs, $0 prices) skipped with logged reasons.
  - `04-support-routing` ← CFPB Consumer Complaints — **63.3%** routing-match on the sample.

### Key decisions
- **Primary tool: n8n** (open-source, self-hostable, inspectable in git).
- **Dropped CI/GitHub Actions** — the account had a billing lock that blocked Actions; the badge
  added no value for a portfolio. Tests run locally instead.
- **Browser-first showcase** — interactive demos beat a CI badge for non-technical clients.
- **API on Netlify Functions (JS), not Python** — Netlify can't run Python serverless; the JS
  port (verified against Python) keeps the API free, same-domain, no second host. Python remains
  the tested source of truth + the validation layer.
- **No `Co-Authored-By` trailer** on commits (portfolio is attributed to Danielle only).

### Open / next steps
- Record ~90-sec walkthrough clips for `docs/` (one per blueprint).
- Add a `social-preview.png` (1280×640) and set it in GitHub repo settings.
- Optionally wire one live `/api/...` call into `index.html` so visitors hit the deployed endpoint.
- Swap the CFPB stand-in sample for the real bulk download (the API was WAF-blocked from the build
  environment; works from a normal machine — see `validate/04-support-routing/README.md`).
- Deploy the Netlify site/API and link it from the portfolio.
