# API — Business Automation Playbook

A free, serverless API exposing all five automation engines, deployable to **Netlify Functions**
(JavaScript). The handlers are a 1:1 port of the Python reference implementation in each
blueprint's `src/`, verified to produce identical output — so the API and the tested Python agree.

Zero dependencies: no `node_modules`, no build step.

## Deploy (to your existing Netlify account)

1. Connect this repo as a Netlify site (or copy `netlify/` + `netlify.toml` into your site's repo).
2. Netlify auto-detects `netlify.toml` — `publish = "."` serves the demo site, `functions = "netlify/functions"` deploys the API.
3. Done. Endpoints are live at `https://<your-site>.netlify.app/api/<name>`.

Run locally with the Netlify CLI: `npx netlify dev` → `http://localhost:8888/api/lead-score`.

## Endpoints

All accept `POST` with a JSON body (and most also accept `GET` with query params for quick testing).
All return JSON with permissive CORS, so your portfolio front-end can call them directly.

| Method | Route | Body |
|--------|-------|------|
| POST | `/api/lead-score` | `{ email, company?, message? }` |
| POST | `/api/onboarding-run` | `{ company, plan, already_provisioned?: [] }` |
| POST | `/api/invoice-build` | `{ client_id, period, as_of?, line_items: [{description, qty, unit_price}] }` |
| POST | `/api/ticket-route` | `{ subject, body, received_at?, as_of? }` |
| POST | `/api/report-build` | `{ current?, previous?, threshold? }` (empty body → sample digest) |

### Examples

```bash
curl -s https://<your-site>.netlify.app/api/lead-score \
  -H 'Content-Type: application/json' \
  -d '{"email":"priya@globalsystems.com","company":"Global Systems","message":"need a demo and pricing urgently, budget approved"}'
# -> { "score": 100, "tier": "hot", "next_action": "notify_sales_immediately", ... }

curl -s "https://<your-site>.netlify.app/api/ticket-route" \
  -H 'Content-Type: application/json' \
  -d '{"subject":"URGENT: production is down","body":"500 error, API is down, outage, asap","received_at":"2026-06-23T10:30:00+00:00","as_of":"2026-06-23T12:00:00+00:00"}'
# -> { "topic": "technical", "urgency": "high", "queue": "oncall-pager", "breaching": true, ... }
```

## Call it from your portfolio site

```js
// Drop into your Netlify-hosted portfolio. Same-origin if the API is on the same site.
async function scoreLead(lead) {
  const res = await fetch("/api/lead-score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lead),
  });
  return res.json();
}

scoreLead({ email: "buyer@acme-corp.com", company: "Acme", message: "send pricing and a demo" })
  .then((r) => console.log(`${r.tier} (${r.score}) -> ${r.next_action}`));
```

If the API lives on a **different** site than your portfolio, use the full URL
(`https://<api-site>.netlify.app/api/lead-score`) — CORS is already enabled for any origin.

## Note on Python

Netlify Functions run JavaScript, not Python — so the live API uses the verified JS port. The
**Python** implementation remains the tested source of truth (108 passing tests across the five
blueprints) and powers the dataset-validation harnesses in `validate/`. If you need literal
Python HTTP endpoints, wrap the `src/` pipelines in FastAPI and deploy to Render (free) instead.
