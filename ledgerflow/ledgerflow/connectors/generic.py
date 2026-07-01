"""Generic connectors for software without a bespoke adapter yet.

* ``generic``     — a neutral day-book CSV + a vouchers.json any importer can read.
* ``zoho_books``  — a Manual Journals CSV shaped for Zoho Books' importer.
* ``busy``        — a voucher CSV shaped for Busy Accounting's importer.

The Zoho/Busy column layouts approximate their published import templates and
are deliberately easy to adjust — treat them as starting points to map onto a
specific customer's template.
"""

from __future__ import annotations

import csv
import io
import json

from .. import export
from ..models import Transaction
from .base import AccountingConnector


class GenericConnector(AccountingConnector):
    name = "generic"
    label = "Generic (CSV day book + vouchers.json)"

    def render(self, txns: list[Transaction], company: str = "Demo Company") -> dict[str, str]:
        return {
            "daybook.csv": export.daybook_csv_string(txns),
            "vouchers.json": json.dumps(
                {"company": company, "vouchers": export.voucher_dicts(txns)},
                indent=2,
            ),
        }


class ZohoBooksConnector(AccountingConnector):
    name = "zoho_books"
    label = "Zoho Books (Manual Journals CSV)"

    def render(self, txns: list[Transaction], company: str = "Demo Company") -> dict[str, str]:
        fields = ["Journal Date", "Reference Number", "Description",
                  "Account", "Debit", "Credit"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields)
        w.writeheader()
        for v in export.voucher_dicts(txns):
            # Each voucher becomes two journal lines (debit + credit).
            w.writerow({"Journal Date": v["date"], "Reference Number": v["reference"],
                        "Description": v["narration"], "Account": v["debit_ledger"],
                        "Debit": v["amount"], "Credit": "0.00"})
            w.writerow({"Journal Date": v["date"], "Reference Number": v["reference"],
                        "Description": v["narration"], "Account": v["credit_ledger"],
                        "Debit": "0.00", "Credit": v["amount"]})
        return {"zoho_books_journals.csv": buf.getvalue()}


class BusyConnector(AccountingConnector):
    name = "busy"
    label = "Busy Accounting (voucher CSV)"

    def render(self, txns: list[Transaction], company: str = "Demo Company") -> dict[str, str]:
        fields = ["Date", "Voucher Type", "Ref No", "Debit Account",
                  "Credit Account", "Amount", "Narration"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields)
        w.writeheader()
        for v in export.voucher_dicts(txns):
            w.writerow({"Date": v["date"], "Voucher Type": v["voucher_type"],
                        "Ref No": v["reference"], "Debit Account": v["debit_ledger"],
                        "Credit Account": v["credit_ledger"], "Amount": v["amount"],
                        "Narration": v["narration"]})
        return {"busy_vouchers.csv": buf.getvalue()}
