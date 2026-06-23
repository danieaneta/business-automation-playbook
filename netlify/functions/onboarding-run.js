"use strict";
const E = require("./engines");

// POST /api/onboarding-run  body: { company, plan, already_provisioned?: [] }
// Idempotency is stateless: pass the steps already provisioned on a prior run.
exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return E.reply(204, {});
  try {
    const b = E.payload(event);
    const plan = (b.plan || "smb").toLowerCase();
    const already = Array.isArray(b.already_provisioned) ? b.already_provisioned : [];
    return E.reply(200, E.onboard(b.company || "(unnamed)", plan, already));
  } catch (err) {
    return E.reply(400, { error: String(err.message || err) });
  }
};
