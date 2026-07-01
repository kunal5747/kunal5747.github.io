"""Stage 1 — Ingestion.

Pull bank statements, credit-card exports, and tax-portal data from
different formats into one normalised list of ``Transaction`` objects.

In production these readers would sit behind India's Account Aggregator and
GSTN APIs; here they read local files that simulate those feeds.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Direction, Transaction


def _money(value: str) -> Decimal:
    """Parse an Indian-formatted amount like '1,25,000.00' into a Decimal."""
    if value is None:
        return Decimal("0")
    cleaned = value.replace(",", "").replace("₹", "").strip()
    if not cleaned:
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _iso_date(value: str) -> str:
    """Normalise DD/MM/YYYY (or DD-MM-YYYY) to ISO YYYY-MM-DD."""
    value = value.strip().replace("-", "/")
    parts = value.split("/")
    if len(parts) == 3 and len(parts[0]) == 2:
        d, m, y = parts
        return f"{y}-{m}-{d}"
    return value  # already ISO or unknown; leave as-is


def read_bank_statement(path: str | Path) -> list[Transaction]:
    """Read a bank statement CSV.

    Expected columns: Date, Narration, Reference, Debit, Credit, Balance.
    Debit = money out (outflow); Credit = money in (inflow).
    """
    txns: list[Transaction] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            debit = _money(row.get("Debit", ""))
            credit = _money(row.get("Credit", ""))
            if debit > 0:
                amount, direction = debit, Direction.OUTFLOW
            else:
                amount, direction = credit, Direction.INFLOW
            txns.append(
                Transaction(
                    date=_iso_date(row["Date"]),
                    narration=row["Narration"].strip(),
                    amount=amount,
                    direction=direction,
                    source="bank",
                    reference=row.get("Reference", "").strip(),
                    contra_ledger="Bank Account",
                )
            )
    return txns


def read_credit_card(path: str | Path) -> list[Transaction]:
    """Read a credit-card export CSV.

    Expected columns: Date, Description, Reference, Amount, Type.
    Type = Debit (a spend) or Credit (a refund / bill payment).
    """
    txns: list[Transaction] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            amount = _money(row.get("Amount", ""))
            is_credit = row.get("Type", "").strip().lower() == "credit"
            direction = Direction.INFLOW if is_credit else Direction.OUTFLOW
            txns.append(
                Transaction(
                    date=_iso_date(row["Date"]),
                    narration=row["Description"].strip(),
                    amount=amount,
                    direction=direction,
                    source="credit_card",
                    reference=row.get("Reference", "").strip(),
                    contra_ledger="Credit Card",
                )
            )
    return txns


def read_gst_portal(path: str | Path) -> list[Transaction]:
    """Read tax-portal challans (simulating a GSTN feed) from JSON.

    Each entry is a tax payment: an outflow that always books to a
    statutory ledger.
    """
    txns: list[Transaction] = []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for entry in data:
        txns.append(
            Transaction(
                date=_iso_date(entry["date"]),
                narration=f"GST {entry.get('type', 'Payment')} challan "
                f"{entry.get('challan_no', '')}".strip(),
                amount=_money(str(entry["amount"])),
                direction=Direction.OUTFLOW,
                source="gst_portal",
                reference=entry.get("challan_no", ""),
                contra_ledger="Bank Account",
            )
        )
    return txns


def ingest_directory(input_dir: str | Path) -> list[Transaction]:
    """Ingest every known feed found in ``input_dir`` and merge them.

    Looks for: bank_statement.csv, credit_card.csv, gst_portal.json.
    Missing files are simply skipped.
    """
    input_dir = Path(input_dir)
    readers = {
        "bank_statement.csv": read_bank_statement,
        "credit_card.csv": read_credit_card,
        "gst_portal.json": read_gst_portal,
    }
    txns: list[Transaction] = []
    for filename, reader in readers.items():
        path = input_dir / filename
        if path.exists():
            txns.extend(reader(path))
    return txns
