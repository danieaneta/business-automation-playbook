"use strict";
const E = require("./engines");

// POST/GET /api/ticket-route  body: { id?, subject, body, received_at? (ISO), as_of? (ISO) }
exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return E.reply(204, {});
  try {
    const b = E.payload(event);
    return E.reply(200, E.routeTicket(b.id || null, b.subject || "", b.body || "", b.received_at || null, b.as_of || null));
  } catch (err) {
    return E.reply(400, { error: String(err.message || err) });
  }
};
