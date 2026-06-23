"use strict";
const E = require("./engines");

// POST/GET /api/report-build  body: { current?: {"source.metric": value}, previous?: {...}, threshold? }
// With no body it returns the sample weekly digest.
exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return E.reply(204, {});
  try {
    const b = E.payload(event);
    return E.reply(200, E.buildReport(b.current || null, b.previous || null, b.threshold));
  } catch (err) {
    return E.reply(400, { error: String(err.message || err) });
  }
};
