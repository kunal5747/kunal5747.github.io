"""Learning memory — remember how payees were classified, apply next time.

Once a client tells us "Kunal = Sundry Creditors", we never need to ask again.
Answers are stored keyed by the normalised counterparty name and auto-applied
to matching suspense transactions on future statements, so the auto-classified
rate climbs month over month.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Direction, Transaction, TxnStatus, VoucherType
from .suspense import canon, extract_counterparty


def load_memory(path: str | Path | None) -> dict[str, str]:
    """Load {normalised_counterparty: ledger}. Missing/empty → {}."""
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data.get("payees", data) if isinstance(data, dict) else {}


def save_memory(path: str | Path | None, memory: dict[str, str]) -> None:
    if not path:
        return
    Path(path).write_text(
        json.dumps({"payees": memory}, indent=2, sort_keys=True), encoding="utf-8"
    )


def apply_memory(txns: list[Transaction], memory: dict[str, str]) -> int:
    """Auto-classify suspense txns whose payee we have seen before."""
    if not memory:
        return 0
    applied = 0
    for txn in txns:
        if txn.status != TxnStatus.SUSPENSE:
            continue
        key = canon(extract_counterparty(txn.narration))
        ledger = memory.get(key)
        if not ledger:
            continue
        txn.ledger = ledger
        txn.voucher_type = (
            VoucherType.PAYMENT
            if txn.direction == Direction.OUTFLOW
            else VoucherType.RECEIPT
        )
        txn.status = TxnStatus.RESOLVED
        txn.confidence = 0.99
        txn.matched_rule = "memory"
        applied += 1
    return applied


def learn(txns: list[Transaction], memory: dict[str, str]) -> int:
    """Record classifications a client just made, keyed by payee.

    Learns from client-answered transactions so the same payee auto-applies
    next time. Returns the number of new/updated payee mappings.
    """
    learned = 0
    for txn in txns:
        if txn.matched_rule != "client-response" or not txn.ledger:
            continue
        key = canon(extract_counterparty(txn.narration))
        if not key:
            continue
        if memory.get(key) != txn.ledger:
            memory[key] = txn.ledger
            learned += 1
    return learned
