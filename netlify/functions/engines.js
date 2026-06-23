"use strict";
/**
 * Shared automation engines for the Netlify Functions API.
 *
 * These are the SAME engines as the in-browser demos (index.html) and a 1:1 port of the
 * Python reference implementation in each blueprint's src/. Verified to produce identical
 * output. Zero dependencies, so the functions need no build step or node_modules.
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

/** Build a JSON HTTP response with CORS headers. */
function reply(statusCode, data) {
  return { statusCode, headers: { ...CORS, "Content-Type": "application/json" }, body: JSON.stringify(data, null, 2) };
}

/** Read the request payload from a POST body or GET query string. */
function payload(event) {
  if (event.body) {
    try { return JSON.parse(event.body); } catch (_) { return {}; }
  }
  return event.queryStringParameters || {};
}

const round2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;

/* ===== 01 · Lead -> CRM (src/scoring.py + enrichment.py + config.py) ===== */
const ICP = {
  intentKeywords: ["pricing", "demo", "quote", "buy", "urgent", "budget", "trial"],
  sizePoints: { smb: 15, mid: 30, enterprise: 40 },
  freeDomains: ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"],
  pointsBusiness: 25, pointsPerIntent: 10, pointsNamedCompany: 10, pointsHasMessage: 5,
  hotThreshold: 60, warmThreshold: 35,
};
const SIZE_HINTS = {
  enterprise: ["corp", "global", "group", "industries", "systems"],
  mid: ["labs", "tech", "software", "digital", "media"],
};
function leadEnrich(email, company) {
  const domain = email.includes("@") ? email.split("@")[1].toLowerCase() : "";
  const isFree = ICP.freeDomains.includes(domain);
  const isBusiness = !!domain && !isFree;
  let size = "smb";
  if (isBusiness) {
    let matched = false;
    for (const [cand, hints] of Object.entries(SIZE_HINTS)) {
      if (hints.some((h) => domain.includes(h))) { size = cand; matched = true; break; }
    }
    if (!matched) size = domain.endsWith(".io") ? "mid" : "smb";
  }
  let companyGuess = company;
  if (!companyGuess && isBusiness) companyGuess = domain.split(".")[0].replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return { domain, is_business_email: isBusiness, company_size: size, company_guess: companyGuess };
}
function leadScore(email, company, message) {
  email = (email || "").trim().toLowerCase();
  company = (company || "").trim();
  message = (message || "").trim();
  if (!email.includes("@") || !email.split("@")[1].includes(".")) {
    return { error: "invalid email — the pipeline skips leads without one", skipped: true };
  }
  const e = leadEnrich(email, company);
  let pts = 0; const reasons = [];
  if (e.is_business_email) { pts += ICP.pointsBusiness; reasons.push(`business email (+${ICP.pointsBusiness})`); }
  const sp = ICP.sizePoints[e.company_size] || 0;
  if (sp) { pts += sp; reasons.push(`company size '${e.company_size}' (+${sp})`); }
  const msg = message.toLowerCase();
  const hits = ICP.intentKeywords.filter((k) => msg.includes(k));
  if (hits.length) { const p = hits.length * ICP.pointsPerIntent; pts += p; reasons.push(`intent keywords [${hits.join(", ")}] (+${p})`); }
  if (company) { pts += ICP.pointsNamedCompany; reasons.push(`named company (+${ICP.pointsNamedCompany})`); }
  if (message) { pts += ICP.pointsHasMessage; reasons.push(`left a message (+${ICP.pointsHasMessage})`); }
  pts = Math.min(pts, 100);
  const tier = pts >= ICP.hotThreshold ? "hot" : pts >= ICP.warmThreshold ? "warm" : "cold";
  const next_action = { hot: "notify_sales_immediately", warm: "send_nurture_sequence", cold: "add_to_newsletter" }[tier];
  return { email, score: pts, tier, next_action, reasons, enrichment: e };
}

/* ===== 02 · Onboarding (src/config.py + engine.py) ===== */
const BASE_STEPS = ["provision_account", "create_workspace", "add_to_billing", "send_welcome_email", "schedule_kickoff"];
const PLAN_EXTRA = { smb: [], pro: [], enterprise: ["assign_csm"] };
function stepsFor(plan) {
  const steps = BASE_STEPS.slice();
  for (const extra of (PLAN_EXTRA[plan] || [])) if (!steps.includes(extra)) steps.push(extra);
  return steps;
}
/** Stateless idempotency: caller passes steps already provisioned on a prior run. */
function onboard(company, plan, alreadyProvisioned) {
  const done = new Set(alreadyProvisioned || []);
  const steps = stepsFor(plan), completed = [], skipped = [];
  for (const step of steps) (done.has(step) ? skipped : completed).push(step);
  return { company, plan, required_steps: steps, completed, skipped, percent_complete: 100, sla_hours: 48 };
}

/* ===== 03 · Invoicing (src/invoicing.py + reminders.py + config.py) ===== */
const BILLING = { taxRate: 0.08, termsDays: 30, reminderOffsets: [3, 7, 14], currency: "USD" };
function periodEnd(period) { const [y, m] = period.split("-").map(Number); return new Date(Date.UTC(m === 12 ? y + 1 : y, m === 12 ? 0 : m, 0)); }
function buildInvoice(clientId, lines, period, asOf) {
  let subtotal = 0; const items = [];
  for (const l of (lines || [])) {
    const qty = Number(l.qty) || 0, unit = Number(l.unit_price) || 0;
    const amount = round2(qty * unit);
    subtotal += amount;
    items.push({ description: l.description || "", qty, unit_price: unit, amount });
  }
  subtotal = round2(subtotal);
  const tax = round2(subtotal * BILLING.taxRate);
  const total = round2(subtotal + tax);
  const due = new Date(periodEnd(period).getTime() + BILLING.termsDays * 86400000);
  const as_of = asOf ? new Date(asOf + "T00:00:00Z") : null;
  let reminders = [], daysPast = 0;
  if (as_of) {
    daysPast = Math.max(Math.floor((as_of - due) / 86400000), 0);
    reminders = daysPast > 0 ? BILLING.reminderOffsets.filter((o) => daysPast >= o) : [];
  }
  return {
    id: `INV-${clientId}-${period}`, client_id: clientId, period, line_items: items,
    subtotal, tax, total, currency: BILLING.currency, due_date: due.toISOString().slice(0, 10),
    status: daysPast > 0 ? "overdue" : "open", days_overdue: daysPast,
    reminders_fired: reminders, next_reminder: reminders.length ? reminders[reminders.length - 1] : null,
  };
}

/* ===== 04 · Support routing (src/classifier.py + routing.py + config.py) ===== */
const ROUTING = {
  topicKeywords: {
    billing: ["invoice", "charge", "refund", "payment", "billing", "subscription", "pricing"],
    technical: ["error", "bug", "crash", "outage", "down", "broken", "fails", "500", "login"],
    account: ["password", "account", "access", "permission", "login", "reset", "locked"],
    sales: ["demo", "quote", "upgrade", "plan", "buy", "purchase", "trial", "sales"],
  },
  highSignals: ["urgent", "asap", "outage", "down", "critical", "emergency", "immediately"],
  lowSignals: ["whenever", "no rush", "no hurry", "low priority", "not urgent", "someday"],
  negative: ["angry", "frustrated", "unacceptable", "terrible", "worst", "disappointed", "ridiculous", "furious"],
  topicQueue: { billing: "billing-queue", technical: "tech-support-queue", account: "account-queue", sales: "sales-queue", general: "triage-queue" },
  slaMinutes: { high: 60, normal: 480, low: 1440 },
  oncallQueue: "oncall-pager",
};
function classify(subject, body) {
  const text = `${subject || ""}\n${body || ""}`.toLowerCase();
  let topic = "general", bestHits = [];
  for (const [t, kws] of Object.entries(ROUTING.topicKeywords)) {
    const hits = kws.filter((k) => text.includes(k));
    if (hits.length > bestHits.length) { topic = t; bestHits = hits; }
  }
  const high = ROUTING.highSignals.filter((s) => text.includes(s));
  const low = ROUTING.lowSignals.filter((s) => text.includes(s));
  const urgency = high.length ? "high" : low.length ? "low" : "normal";
  const sentiment = ROUTING.negative.some((s) => text.includes(s)) ? "negative" : "neutral";
  return { topic, urgency, sentiment, topic_keywords: bestHits };
}
function routeTicket(id, subject, body, receivedAt, asOf) {
  const c = classify(subject, body);
  const escalate = c.urgency === "high";
  const queue = escalate ? ROUTING.oncallQueue : (ROUTING.topicQueue[c.topic] || ROUTING.topicQueue.general);
  const assignee = escalate ? "on-call-engineer" : `${c.topic}-team`;
  let sla_deadline = null, breaching = null;
  if (receivedAt) {
    const deadline = new Date(new Date(receivedAt).getTime() + ROUTING.slaMinutes[c.urgency] * 60000);
    sla_deadline = deadline.toISOString().replace(".000Z", "+00:00");
    if (asOf) breaching = new Date(asOf) >= deadline;
  }
  return { id: id || null, ...c, queue, assignee, priority: c.urgency, escalate, sla_minutes: ROUTING.slaMinutes[c.urgency], sla_deadline, breaching };
}

/* ===== 05 · Reporting (src/transform.py + digest.py + config.py) ===== */
const METRICS = [
  { source: "crm", metric: "new_leads", display: "New Leads", prev: 120, cur: 138 },
  { source: "crm", metric: "qualified_leads", display: "Qualified Leads", prev: 44, cur: 46 },
  { source: "billing", metric: "mrr", display: "MRR ($)", prev: 48200, cur: 49100 },
  { source: "billing", metric: "new_customers", display: "New Customers", prev: 9, cur: 14 },
  { source: "billing", metric: "churned_customers", display: "Churned Customers", prev: 2, cur: 5 },
  { source: "analytics", metric: "website_visits", display: "Website Visits", prev: 9800, cur: 10250 },
  { source: "analytics", metric: "signups", display: "Signups", prev: 0, cur: 31 },
];
const pctChange = (v, p) => (p === 0 ? (v === 0 ? 0 : null) : ((v - p) / Math.abs(p)) * 100);
const fmtValue = (v) => (Number.isInteger(v) ? v.toLocaleString("en-US") : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const fmtPct = (p) => (p === null ? "new" : (p > 0 ? "+" : "") + p.toFixed(1) + "%");
const fmtDelta = (d) => (d > 0 ? "+" : "") + fmtValue(d);
function buildReport(current, previous, threshold) {
  threshold = threshold == null ? 10 : Number(threshold);
  const rows = METRICS.map((m) => {
    const key = `${m.source}.${m.metric}`;
    const value = current && current[key] != null ? Number(current[key]) : m.cur;
    const prev = previous && previous[key] != null ? Number(previous[key]) : m.prev;
    const delta = value - prev, pct = pctChange(value, prev);
    return { source: m.source, metric: m.metric, display_name: m.display, value, previous: prev, delta, pct_change: pct, direction: delta > 0 ? "up" : delta < 0 ? "down" : "flat", highlighted: pct !== null && Math.abs(pct) >= threshold };
  });
  const row = (r) => `${r.highlighted ? "* " : "  "}${r.display_name}: ${fmtValue(r.value)} (${fmtDelta(r.delta)}, ${fmtPct(r.pct_change)} ${r.direction} vs prior)`;
  const highlights = rows.filter((r) => r.highlighted);
  const lines = ["# Weekly Metrics Digest - 2026-W24", "_For Acme Inc (vs 2026-W23)_", ""];
  if (highlights.length) { lines.push("## Highlights (big movers)"); highlights.forEach((r) => lines.push(row(r))); lines.push(""); }
  lines.push("## All metrics"); rows.forEach((r) => lines.push(row(r)));
  lines.push("", `${rows.length} metrics reported, ${highlights.length} flagged as big movers (threshold reached). '*' = big mover.`);
  return { period: "2026-W24", previous_period: "2026-W23", threshold_pct: threshold, rows, highlights: highlights.length, digest: lines.join("\n") };
}

module.exports = { reply, payload, leadScore, onboard, buildInvoice, routeTicket, buildReport };
