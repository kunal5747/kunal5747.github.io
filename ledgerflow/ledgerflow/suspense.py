"""Stage 3 — Suspense loop.

The ~20% the rules engine can't place (vague UPI transfers, cash withdrawals)
are flagged. For each, we mint a secure, no-login review token and a link that
would be sent to the client over WhatsApp. They tap a dropdown on their phone
to say what it was; the answer flows straight back in and the transaction is
resolved.

Here the "WhatsApp round trip" is simulated by ``client_responses.json``,
keyed by transaction reference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import Direction, Transaction, TxnStatus, VoucherType

# Public base for the no-login review links (your GitHub Pages site).
REVIEW_LINK_BASE = "https://kunal5747.github.io/review"

# The dropdown a client sees on their phone. Kept short and plain-English.
DROPDOWN_OPTIONS = [
    "Sundry Creditors (paid a supplier)",
    "Sundry Debtors (money from a customer)",
    "Cash-in-Hand (cash withdrawal)",
    "Owner's Drawings (personal use)",
    "Capital / Owner's Funds",
    "Loan Repayment",
    "Office Expenses",
    "Staff Welfare",
    "Travelling Expenses",
    "Other (type a note)",
]

# Where an option maps once chosen (the label -> real Tally ledger).
_OPTION_TO_LEDGER = {
    "Sundry Creditors": "Sundry Creditors",
    "Sundry Debtors": "Sundry Debtors",
    "Cash-in-Hand": "Cash-in-Hand",
    "Owner's Drawings": "Drawings",
    "Capital": "Capital Account",
    "Loan Repayment": "Loan Account",
    "Office Expenses": "Office Expenses",
    "Staff Welfare": "Staff Welfare",
    "Travelling Expenses": "Travelling Expenses",
}


def _token(txn: Transaction) -> str:
    """Deterministic, unguessable-looking token for a transaction."""
    seed = f"{txn.date}|{txn.narration}|{txn.amount}|{txn.reference}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def flag_suspense(txns: list[Transaction]) -> list[dict]:
    """Attach review tokens/links to suspense txns and build a review queue."""
    queue: list[dict] = []
    for txn in txns:
        if txn.status != TxnStatus.SUSPENSE:
            continue
        txn.review_token = _token(txn)
        queue.append(
            {
                "token": txn.review_token,
                "review_link": f"{REVIEW_LINK_BASE}/{txn.review_token}",
                "date": txn.date,
                "narration": txn.narration,
                "reference": txn.reference,
                "amount": f"{txn.amount:.2f}",
                "direction": txn.direction,
                "options": DROPDOWN_OPTIONS,
            }
        )
    return queue


def _ledger_for_answer(answer: str) -> str:
    """Map a client's dropdown answer back to a Tally ledger name."""
    for key, ledger in _OPTION_TO_LEDGER.items():
        if key.lower() in answer.lower():
            return ledger
    return answer  # free-text "Other" answers pass through as-is


def apply_responses(
    txns: list[Transaction], responses: dict[str, str]
) -> int:
    """Fold client answers (keyed by transaction reference) back in.

    Returns the number of transactions resolved.
    """
    resolved = 0
    for txn in txns:
        if txn.status != TxnStatus.SUSPENSE:
            continue
        answer = responses.get(txn.reference)
        if not answer:
            continue
        txn.ledger = _ledger_for_answer(answer)
        txn.voucher_type = (
            VoucherType.PAYMENT
            if txn.direction == Direction.OUTFLOW
            else VoucherType.RECEIPT
        )
        txn.status = TxnStatus.RESOLVED
        txn.confidence = 1.0  # a human confirmed it
        txn.matched_rule = "client-response"
        resolved += 1
    return resolved


def load_responses(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
