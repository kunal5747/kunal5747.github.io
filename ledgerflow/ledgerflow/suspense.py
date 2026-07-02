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
import re
from decimal import Decimal
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


# Bank/IFSC-ish codes and boilerplate tokens that are never a counterparty name.
_NON_PARTY = {
    "MB", "IMPS", "NEFT", "RTGS", "UPI", "BILL", "IMPSCHARGES", "CHARGES",
    "CHECK", "RETUR", "RETURN", "PAYMENT", "TRANSFER", "ACH", "ECS",
    "UTIB", "HDFC", "KKBK", "MAHB", "SBIN", "ICIC", "PUNB", "BARB", "IBKL",
    "YESB", "IDIB", "CNRB", "IOBA", "UBIN", "CBIN", "MAHG",
}


def canon(name: str) -> str:
    """Normalise a name for comparison: lowercase, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def cluster_parties(parties: set[str]) -> dict[str, str]:
    """Map each payee name to a representative, merging truncated duplicates.

    Bank narrations truncate names ('Kunal' / 'Kunal Dnyanoba'). We merge a
    shorter name into a longer one only when it is a **whole-word prefix** of
    the longer (so 'Shreya' does NOT absorb into 'Shreyash') — a conservative
    rule that avoids wrongly combining two different people.
    """
    rep_of: dict[str, str] = {}
    reps: list[str] = []
    for name in sorted(parties, key=len, reverse=True):  # longest = most complete
        low = name.lower().strip()
        placed = False
        for rep in reps:
            rl = rep.lower()
            if len(low) >= 4 and rl.startswith(low) and (
                len(rl) == len(low) or not rl[len(low)].isalnum()
            ):
                rep_of[name] = rep
                placed = True
                break
        if not placed:
            reps.append(name)
            rep_of[name] = name
    return rep_of


def extract_counterparty(narration: str) -> str:
    """Best-effort payee/payer name from a slash-delimited bank narration.

    e.g. 'MB/IMPS/615123743570/VISHAL/UTIB/XXXXXX5072/Bill' -> 'Vishal'.
    Returns '' when no name is present (e.g. bank charges).
    """
    for part in narration.split("/"):
        letters = re.sub(r"[^A-Za-z ]", "", part).strip()
        token = letters.replace(" ", "").upper()
        if len(letters) < 3 or token in _NON_PARTY:
            continue
        if set(token) <= {"X"}:  # masked account no. like 'XXXXXX6831'
            continue
        return letters.title()
    return ""


def group_review(txns: list[Transaction]) -> list[dict]:
    """Group still-in-suspense transactions by counterparty.

    A transfer-heavy account can have thousands of unclassified lines but only
    a handful of *distinct* payees. Grouping means the client answers once per
    party instead of once per transaction.
    """
    pending = [t for t in txns if t.status == TxnStatus.SUSPENSE]
    parties = {extract_counterparty(t.narration) or t.narration[:24] for t in pending}
    rep_of = cluster_parties(parties)

    groups: dict[str, dict] = {}
    for txn in pending:
        raw = extract_counterparty(txn.narration) or txn.narration[:24]
        party = rep_of.get(raw, raw)
        g = groups.setdefault(party, {
            "counterparty": party, "count": 0,
            "total_outflow": Decimal("0"), "total_inflow": Decimal("0"),
            "sample_narration": txn.narration, "options": DROPDOWN_OPTIONS,
        })
        g["count"] += 1
        if txn.direction == Direction.OUTFLOW:
            g["total_outflow"] += txn.amount
        else:
            g["total_inflow"] += txn.amount
    result = []
    for g in sorted(groups.values(), key=lambda x: x["count"], reverse=True):
        result.append({
            "key": canon(g["counterparty"]),  # stable id the review page answers by
            "counterparty": g["counterparty"],
            "count": g["count"],
            "total_outflow": f"{g['total_outflow']:.2f}",
            "total_inflow": f"{g['total_inflow']:.2f}",
            "sample_narration": g["sample_narration"],
            "options": g["options"],
        })
    return result


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


def apply_group_responses(txns: list[Transaction], mapping: dict[str, str]) -> int:
    """Apply per-payee answers from the hosted review page.

    ``mapping`` is keyed by the group ``key`` (canonical counterparty) as
    emitted by :func:`group_review`; the same clustering is recomputed so every
    transaction of a payee resolves from a single answer. Returns count resolved.
    """
    if not mapping:
        return 0
    pending = [t for t in txns if t.status == TxnStatus.SUSPENSE]
    parties = {extract_counterparty(t.narration) or t.narration[:24] for t in pending}
    rep_of = cluster_parties(parties)
    resolved = 0
    for txn in pending:
        raw = extract_counterparty(txn.narration) or txn.narration[:24]
        rep = rep_of.get(raw, raw)
        answer = mapping.get(canon(rep)) or mapping.get(rep)
        if not answer:
            continue
        txn.ledger = _ledger_for_answer(answer)
        txn.voucher_type = (
            VoucherType.PAYMENT
            if txn.direction == Direction.OUTFLOW
            else VoucherType.RECEIPT
        )
        txn.status = TxnStatus.RESOLVED
        txn.confidence = 1.0
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


def load_group_responses(path: str | Path | None) -> dict[str, str]:
    """Load answers from the review page: accepts {"answers": {...}} or a flat map."""
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "answers" in data:
        return data["answers"]
    return data if isinstance(data, dict) else {}
