"""Adapter: UCI 'Online Retail II' rows -> blueprint 03 ``UsageRecord``.

The real dataset has one row per order line with these exact columns:

    Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country

We map each clean line to a blueprint :class:`UsageRecord`:

    client_id   <- Customer ID
    description <- Description
    qty         <- Quantity
    unit_price  <- Price
    date        <- InvoiceDate's calendar date

Data hygiene is explicit and *logged, never silent*: rows with a non-positive
Quantity (returns / credit notes), a missing Customer ID, or a non-numeric /
blank Price are skipped and counted by reason. This adapter does NOT reimplement
any invoice math — it only shapes rows. The blueprint engine owns the money.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Iterable, List, Tuple

# --- blueprint engine import (see sys.path bootstrap in validate.py) ---
from src.models import UsageRecord


# Real column names from the UCI Online Retail II dataset.
COL_INVOICE = "Invoice"
COL_STOCK = "StockCode"
COL_DESC = "Description"
COL_QTY = "Quantity"
COL_DATE = "InvoiceDate"
COL_PRICE = "Price"
COL_CUSTOMER = "Customer ID"
COL_COUNTRY = "Country"


@dataclass
class SkipLog:
    """Counts of rows dropped, by reason. Nothing is dropped silently."""

    non_positive_qty: int = 0
    missing_customer: int = 0
    bad_price: int = 0
    out_of_period: int = 0

    @property
    def total(self) -> int:
        return (
            self.non_positive_qty
            + self.missing_customer
            + self.bad_price
            + self.out_of_period
        )

    def as_rows(self) -> List[Tuple[str, int]]:
        return [
            ("non-positive Quantity (returns/credits)", self.non_positive_qty),
            ("missing Customer ID", self.missing_customer),
            ("non-numeric / blank Price", self.bad_price),
            ("outside target period", self.out_of_period),
        ]


def _parse_invoice_date(raw: str) -> date | None:
    """Parse the real ``InvoiceDate`` (e.g. '2009-12-01 07:45:00') to a date."""
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # ISO fallback
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def _clean_customer_id(raw: str) -> str:
    """Real file stores Customer ID as a float-ish string ('13085' or '13085.0')."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw


def load_records(
    csv_path: str, period: str
) -> Tuple[List[UsageRecord], SkipLog]:
    """Read the real CSV and return (clean UsageRecords in ``period``, SkipLog).

    ``period`` is ``YYYY-MM``. Only rows whose InvoiceDate falls in that month
    are kept. Every dropped row is attributed to a reason in the returned log.
    """
    skips = SkipLog()
    records: List[UsageRecord] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # --- period filter (date is also needed for the record) ---
            d = _parse_invoice_date(row.get(COL_DATE, ""))
            if d is None or d.strftime("%Y-%m") != period:
                skips.out_of_period += 1
                continue

            # --- missing Customer ID ---
            client_id = _clean_customer_id(row.get(COL_CUSTOMER, ""))
            if not client_id:
                skips.missing_customer += 1
                continue

            # --- Quantity: must be a positive number (skip returns/credits) ---
            qty_raw = (row.get(COL_QTY, "") or "").strip()
            try:
                qty = float(qty_raw)
            except (TypeError, ValueError):
                skips.non_positive_qty += 1
                continue
            if qty <= 0:
                skips.non_positive_qty += 1
                continue

            # --- Price: must be a positive number (skip blank/zero/garbage) ---
            price_raw = (row.get(COL_PRICE, "") or "").strip()
            try:
                price = float(price_raw)
            except (TypeError, ValueError):
                skips.bad_price += 1
                continue
            if price <= 0:
                skips.bad_price += 1
                continue

            records.append(
                UsageRecord(
                    client_id=client_id,
                    description=(row.get(COL_DESC, "") or "").strip(),
                    qty=qty,
                    unit_price=price,
                    date=d,
                )
            )

    return records, skips


def group_by_customer(
    records: Iterable[UsageRecord],
) -> Dict[str, List[UsageRecord]]:
    """Group clean usage records by client_id (Customer ID) for the period."""
    grouped: Dict[str, List[UsageRecord]] = defaultdict(list)
    for rec in records:
        grouped[rec.client_id].append(rec)
    return dict(grouped)
