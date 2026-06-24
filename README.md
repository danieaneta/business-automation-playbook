# Business Automation Playbook

![Made with n8n](https://img.shields.io/badge/built%20with-n8n-EA4B71)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

> **Open-source automation blueprints that eliminate manual business work.**
> Each one ships with the **n8n workflow**, the **Python integration code** (retry, structured
> logging, idempotency), **tests**, and a **measured before/after** — so you can see exactly
> what gets automated and exactly how it's built.

### ▶ Try it live

**[Open `index.html`](index.html) in your browser** — no install, no server. Tabbed, interactive
demos for **all five** automations: enter a lead, a won deal, usage lines, a support message, or
KPIs and watch the real engine run — the same logic as the Python, ported to JS and verified to
match exactly. Download the repo and double-click the file, or open the hosted version:

🔗 **Hosted demo:** https://raw.githack.com/danieaneta/business-automation-playbook/main/index.html

Most "automation" portfolios show a screenshot of a Zapier canvas. This one ships inspectable,
testable, self-hostable systems with live demos, a deployable API, and real-data validation.

---

## The blueprints

Each blueprint removes a recurring manual process. Together they cover the full customer
lifecycle: **acquire → onboard → bill → support → report.**

| # | Blueprint | The manual pain it kills | Designed to save |
|---|-----------|--------------------------|------------------|
| [01](01-lead-capture-to-crm/) | **Lead capture → CRM** | Copy-pasting leads, manual scoring, slow follow-up | ~10 hrs/week, 0 dropped leads |
| [02](02-client-onboarding/) | **Client onboarding** | Manual account setup + welcome emails after every deal | ~5 hrs/week per rep |
| [03](03-invoicing-billing/) | **Invoicing & billing** | Hand-built invoices, chasing late payments | ~6 hrs/week |
| [04](04-support-ticket-routing/) | **Support ticket routing** | Reading + triaging + assigning every inbound message | ~8 hrs/week |
| [05](05-automated-reporting/) | **Automated reporting** | Pulling KPIs into a weekly deck by hand | ~4 hrs/week |

> **All five blueprints are built, runnable, and tested — 108 passing tests in total**
> (01: 16 · 02: 15 · 03: 29 · 04: 24 · 05: 24). Each runs on bundled dummy data with no API keys.

---

## Run any blueprint in 2 minutes

```bash
# 1. Self-host n8n (optional — only needed to import the visual workflows)
docker compose up -d            # → http://localhost:5678

# 2. Run the Python pipeline on the included dummy data (no API keys required)
cd 01-lead-capture-to-crm
pip install -r ../requirements.txt
python run.py                   # processes sample leads, prints the results

# 3. Run the tests
pytest
```

Every blueprint runs on **sample data with no secrets** — `.env.example` documents the real
integrations, but nothing external is required to see it work.

---

## Live API

All five engines are also exposed as a free, zero-dependency serverless API (**Netlify
Functions**) — full reference in **[API.md](API.md)**. Endpoints return JSON with CORS enabled,
ready to call from a portfolio site:

```
POST /api/lead-score      POST /api/onboarding-run    POST /api/invoice-build
POST /api/ticket-route    POST /api/report-build
```

The handlers are a verified 1:1 port of the Python; deploy by pointing a Netlify site at this repo.

---

## Validated against real open data

The Python engines are checked against real public datasets in **[`validate/`](validate/)** —
run either with `python validate.py`:

| Harness | Dataset | What it proves |
|---------|---------|----------------|
| [`validate/03-invoicing`](validate/03-invoicing/) | UCI Online Retail II (real transactions) | Invoice math reconciles within $0.01; messy rows skipped with logged reasons |
| [`validate/04-support-routing`](validate/04-support-routing/) | CFPB Consumer Complaints | Routing-match accuracy on labeled complaints (honest taxonomy caveats) |

---

## How each blueprint is organized

```
NN-blueprint-name/
├── README.md          ← The Problem · The Fix (diagram) · Results · Stack · How to run
├── workflow.json      ← the n8n workflow, versioned in git, one-click import
├── src/               ← Python glue: API clients, scoring, orchestration
├── tests/             ← pytest covering the logic + edge cases
├── data/              ← sample input so it runs with zero setup
└── .env.example       ← documents the real-world integrations
```

The `shared/` package holds the reusable engineering layer every blueprint depends on:
retry-with-backoff, structured JSON logging, and an idempotent store interface.

And at the repo root:

```
business-automation-playbook/
├── 01..05-*/           ← the five blueprints (Python + n8n workflow + tests)
├── shared/             ← reusable retry / logging / idempotent-store layer
├── index.html          ← interactive browser demos for all five (no server)
├── netlify/functions/  ← serverless API (Netlify Functions) — see API.md
├── validate/           ← real-data validation harnesses (03 + 04)
├── docs/               ← walkthroughs, diagrams, social preview
├── docker-compose.yml  ← self-host n8n in one command
└── SESSIONS.md         ← changelog of what was built each session
```

---

## Why n8n

- **Open-source & self-hostable** — no vendor lock-in; the included `docker-compose.yml`
  stands up a full instance.
- **Inspectable in git** — workflows are committed as `workflow.json`, so they're reviewable
  in a pull request like any other code.
- **Native AI agents** — LLM scoring/classification steps live inside the same workflow.

---

## Work with me

I build automations like these for businesses — lead handling, onboarding, billing, support,
and reporting. If a manual process is eating your team's week, let's remove it.

📧 **danieaneta@gmail.com**

---

<sub>Built as an open-source portfolio. Workflows and code run on synthetic sample data; no real
customer data is included.</sub>
