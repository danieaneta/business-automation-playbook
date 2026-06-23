"use strict";
const E = require("./engines");

// POST/GET /api/lead-score  body: { email, company?, message? }
exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return E.reply(204, {});
  try {
    const b = E.payload(event);
    return E.reply(200, E.leadScore(b.email || "", b.company || "", b.message || ""));
  } catch (err) {
    return E.reply(400, { error: String(err.message || err) });
  }
};
