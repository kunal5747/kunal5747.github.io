"""Stage 4 — Export.

Turn classified transactions into Tally-ready output:

* ``to_tally_xml`` — Tally's native voucher import XML.
* ``to_daybook_csv`` — a flat day-book CSV / Excel-friendly view.
* ``sync_to_tally`` — POST the XML straight to Tally running locally on
  port 9000 (Tally's HTTP/XML gateway).

Anything still unresolved is booked to "Suspense A/c" so nothing is ever
dropped — the CA can reclassify it later inside Tally.
"""

from __future__ import annotations

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib import request
from xml.sax.saxutils import escape

from .models import Direction, Transaction, TxnStatus, VoucherType

SUSPENSE_LEDGER = "Suspense A/c"


def _q(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _tally_date(iso: str) -> str:
    """YYYY-MM-DD -> YYYYMMDD (Tally's date format)."""
    return iso.replace("-", "")


def _effective_ledger(txn: Transaction) -> str:
    return txn.ledger or SUSPENSE_LEDGER


def _voucher_type(txn: Transaction) -> str:
    if txn.voucher_type:
        return txn.voucher_type
    return VoucherType.PAYMENT if txn.direction == Direction.OUTFLOW else VoucherType.RECEIPT


def _voucher_xml(txn: Transaction) -> str:
    """One Tally VOUCHER element with balanced ledger entries.

    Tally convention: a debit line carries ISDEEMEDPOSITIVE=Yes with a
    negative AMOUNT; a credit line carries No with a positive AMOUNT.
    """
    ledger = _effective_ledger(txn)
    vtype = _voucher_type(txn)
    amt = txn.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if txn.direction == Direction.OUTFLOW:
        # Payment: debit the expense/party ledger, credit the bank/card.
        debit_ledger, credit_ledger = ledger, txn.contra_ledger
    else:
        # Receipt: debit the bank/card, credit the income/party ledger.
        debit_ledger, credit_ledger = txn.contra_ledger, ledger

    def entry(name: str, deemed_positive: bool) -> str:
        signed = -amt if deemed_positive else amt
        return (
            "        <ALLLEDGERENTRIES.LIST>\n"
            f"          <LEDGERNAME>{escape(name)}</LEDGERNAME>\n"
            f"          <ISDEEMEDPOSITIVE>{'Yes' if deemed_positive else 'No'}</ISDEEMEDPOSITIVE>\n"
            f"          <AMOUNT>{_q(signed)}</AMOUNT>\n"
            "        </ALLLEDGERENTRIES.LIST>"
        )

    return (
        f'      <VOUCHER VCHTYPE="{escape(vtype)}" ACTION="Create">\n'
        f"        <DATE>{_tally_date(txn.date)}</DATE>\n"
        f"        <NARRATION>{escape(txn.narration)}</NARRATION>\n"
        f"        <VOUCHERTYPENAME>{escape(vtype)}</VOUCHERTYPENAME>\n"
        f"        <REFERENCE>{escape(txn.reference)}</REFERENCE>\n"
        f"{entry(debit_ledger, True)}\n"
        f"{entry(credit_ledger, False)}\n"
        "      </VOUCHER>"
    )


def to_tally_xml(txns: list[Transaction], company: str = "Demo Company") -> str:
    """Full Tally import envelope for the whole batch."""
    messages = "\n".join(
        f'    <TALLYMESSAGE xmlns:UDF="TallyUDF">\n{_voucher_xml(t)}\n    </TALLYMESSAGE>'
        for t in txns
    )
    return (
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <TALLYREQUEST>Import Data</TALLYREQUEST>\n"
        "  </HEADER>\n"
        "  <BODY>\n"
        "    <IMPORTDATA>\n"
        "      <REQUESTDESC>\n"
        "        <REPORTNAME>Vouchers</REPORTNAME>\n"
        "        <STATICVARIABLES>\n"
        f"          <SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>\n"
        "        </STATICVARIABLES>\n"
        "      </REQUESTDESC>\n"
        "      <REQUESTDATA>\n"
        f"{messages}\n"
        "      </REQUESTDATA>\n"
        "    </IMPORTDATA>\n"
        "  </BODY>\n"
        "</ENVELOPE>\n"
    )


def to_daybook_csv(txns: list[Transaction], path: str | Path) -> None:
    """Write a flat, Excel-friendly day book."""
    fields = [
        "date", "voucher_type", "reference", "narration",
        "debit_ledger", "credit_ledger", "amount", "status", "confidence",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for t in txns:
            ledger = _effective_ledger(t)
            if t.direction == Direction.OUTFLOW:
                debit_ledger, credit_ledger = ledger, t.contra_ledger
            else:
                debit_ledger, credit_ledger = t.contra_ledger, ledger
            writer.writerow(
                {
                    "date": t.date,
                    "voucher_type": _voucher_type(t),
                    "reference": t.reference,
                    "narration": t.narration,
                    "debit_ledger": debit_ledger,
                    "credit_ledger": credit_ledger,
                    "amount": _q(t.amount),
                    "status": t.status,
                    "confidence": f"{t.confidence:.2f}",
                }
            )


def sync_to_tally(
    xml: str, host: str = "localhost", port: int = 9000, timeout: int = 10
) -> tuple[bool, str]:
    """POST the import XML to a local Tally instance (HTTP gateway, port 9000).

    Returns (ok, message). Never raises — if Tally isn't running you get a
    clean failure the caller can report.
    """
    url = f"http://{host}:{port}"
    body = xml.encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "text/xml"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (local)
            return True, resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - depends on a live Tally
        return False, f"Could not reach Tally at {url}: {exc}"
