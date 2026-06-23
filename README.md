# Business Automation Playbook

![Made with n8n](https://img.shields.io/badge/built%20with-n8n-EA4B71)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

> **Open-source automation blueprints that eliminate manual business work.**
> Each one ships with the **n8n workflow**, the **Python integration code** (retry, structured
> logging, idempotency), **tests**, and a **measured before/after** — so you can see exactly
> what gets automated and exactly how it's built.

### ▶ Try the live demo

**[Open `index.html`](index.html) in your browser** — no install, no server. Type in a lead and
watch the automation score and route it in real time (the same logic as the Python pipeline).
Just download the repo and double-click the file.

Most "automation" portfolios show a screenshot of a Zapier canvas. This one ships inspectable,
testable, self-hostable systems. Clone it, run it on the included dummy data, and read the code.

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
