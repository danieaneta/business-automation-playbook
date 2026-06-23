"use strict";
const E = require("./engines");

// POST /api/invoice-build  body: { client_id, period (YYYY-MM), as_of? (YYYY-MM-DD), line_items: [{description, qty, unit_price}] }
exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return E.reply(204, {});
  try {
    const b = E.payload(event);
    const lines = Array.isArray(b.line_items) ? b.line_items : [];
    return E.reply(200, E.buildInvoice(b.client_id || "client", lines, b.period || "2026-04", b.as_of || null));
  } catch (err) {
    return E.reply(400, { error: String(err.message || err) });
  }
};
