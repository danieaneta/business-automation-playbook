# Blueprint 04 -- Real-Data Routing Validation (CFPB)

A validation harness that feeds **real-schema, real-language consumer complaints**
from the **CFPB Consumer Complaint Database** through blueprint 04's *own* ticket
classifier and routing engine, then reports how often the routing matches an
expected support-desk topic derived from the complaint's CFPB `Product`.

It does **not** reimplement the classifier. It imports `classify()` and `route()`
straight from `04-support-ticket-routing/src/` and runs them unchanged. Nothing in
the blueprint folder is modified.

## What it produces

- `python validate.py` prints an ASCII report and writes the same text to
  `report.md`: total records, skipped (empty narrative), scored count,
  routing-match accuracy %, a per-topic breakdown, and 5 worked examples.

**Observed accuracy on the bundled 32-row sample: 63.3% (19/30 scored; 2 skipped
for empty narratives).**

## The dataset

[CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
-- real complaints U.S. consumers filed about financial products, including a free-text
"Consumer complaint narrative" (with PII redacted by the CFPB as `XXXX`).

`data/cfpb_sample.json` is a small (~32 row) sample that mirrors the **exact CFPB
field names**: `Date received`, `Product`, `Sub-product`, `Issue`, `Sub-issue`,
`Consumer complaint narrative`, `Company`, `State`, `ZIP code`, `Submitted via`,
`Company response to consumer`, `Complaint ID`.

### How this sample was sourced -- be honest about it

The CFPB public search API
(`https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/`)
was attempted first. From this environment it is **WAF-blocked for programmatic
clients** -- direct `requests` calls return **HTTP 403**, and a browser-style fetch
returns a payload too large to retrieve here. So this sample was **hand-authored to
mirror the exact CFPB schema and narrative style** (real field names, real CFPB
`Product`/`Issue` values, `XXXX` PII redactions, realistic complaint language),
spanning **9 different CFPB Products**, including rows with empty/whitespace
narratives to exercise the skip path.

It is therefore *schema-real and language-realistic*, but the records are
**synthetic, not pulled live**. To run against genuine live rows, see below.

### Get the real, full data

- **Download bulk:** the full database (CSV/JSON) is at the
  [CFPB data download page](https://www.consumerfinance.gov/data-research/consumer-complaints/search/?from=0&searchField=all&tab=List)
  ("Download options" -> CSV or JSON).
- **API (when not WAF-blocked):**
  `https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/?size=50&has_narrative=true&format=json`
  -- records live under `hits.hits[]._source`. Save those `_source` objects as a
  JSON array into `data/cfpb_sample.json` (the field names already match) and re-run.

## The Product -> topic mapping

The blueprint routes on a support-desk taxonomy: `billing / technical / account /
sales / general`. CFPB uses a *financial-product* taxonomy. These do **not** line
up cleanly, so `adapter.py` defines a deliberately-coarse best-effort map (the
single most representative bucket per Product):

| CFPB `Product`                                                   | Expected topic |
|------------------------------------------------------------------|----------------|
| Credit card or prepaid card                                      | billing        |
| Mortgage                                                         | billing        |
| Vehicle loan or lease                                            | billing        |
| Student loan                                                     | billing        |
| Payday loan, title loan, or personal loan                       | billing        |
| Checking or savings account                                     | account        |
| Money transfer, virtual currency, or money service              | technical      |
| Debt collection                                                 | general        |
| Credit reporting, credit repair services, or other reports      | general        |
| *(unknown Product)*                                             | general        |

There is **no CFPB Product** that corresponds to the `sales` topic, so `sales`
never appears as an expected label. (A narrative mentioning "demo/quote/upgrade"
can still be *predicted* as sales by the keyword classifier -- that shows up as a
mismatch, which is honest signal, not a bug.)

### What the accuracy number actually means

This harness measures **routing behaviour and stability** -- "does the keyword
classifier send a real, messy consumer narrative to a *sensible* queue?" -- not
classification accuracy against a gold support-desk label set (none exists for
CFPB data). The expected labels are a coarse proxy, so treat ~63% as "the
keyword router agrees with a rough product-based expectation about two-thirds of
the time," not as a precision metric. The `general`/`technical` rows mismatch
most, because debt-collection and credit-reporting narratives are full of
billing/account keywords that the keyword classifier (correctly, by its own
rules) latches onto.

## Field mapping (CFPB record -> blueprint `Ticket`)

| `Ticket` field | CFPB source                      |
|----------------|----------------------------------|
| `id`           | `Complaint ID`                   |
| `subject`      | `Issue`                          |
| `body`         | `Consumer complaint narrative`   |
| `received_at`  | `Date received` (-> ISO-8601)    |
| `sender`       | (blank -- CFPB exposes no email) |
| `raw`          | the full original record         |

Rows with an empty or whitespace-only narrative are **skipped and counted**, never
scored (a blank body has nothing for the classifier to read).

## Run it

```
cd validate/04-support-routing
python validate.py
```

Exit code 0, ASCII-only output (Windows cp1252 safe, `->` not unicode arrows),
report mirrored to `report.md`. No dependencies beyond the standard library and
the blueprint itself.

## Files

- `adapter.py`  -- CFPB record -> blueprint `Ticket`; Product -> topic map; path bootstrap.
- `validate.py` -- loads sample, runs blueprint `classify()` + `route()`, scores, reports.
- `data/cfpb_sample.json` -- the CFPB-schema sample.
- `report.md`   -- generated each run.
