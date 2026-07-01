"""Stage 2 — Rules engine.

Recognise patterns in the narration and auto-assign each transaction to the
right Tally ledger. The goal is to clear ~80% of lines with zero human touch
(Swiggy -> Staff Welfare, Jio -> Telephone Expenses, ...).

Rules live in ``rules.json`` so a CA can tune them without touching code.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Direction, Transaction, TxnStatus, VoucherType

_DEFAULT_RULES = Path(__file__).resolve().parent.parent / "rules.json"


class Rule:
    """One classification rule loaded from ``rules.json``."""

    def __init__(self, spec: dict):
        self.name: str = spec["name"]
        self.ledger: str = spec["ledger"]
        # Keywords are matched case-insensitively against the narration.
        self.keywords: list[str] = [k.lower() for k in spec.get("keywords", [])]
        # Optional direction constraint: "outflow", "inflow", or None (any).
        self.direction: str | None = spec.get("direction")
        # Optional source constraint: "bank", "credit_card", "gst_portal".
        self.source: str | None = spec.get("source")
        self.confidence: float = float(spec.get("confidence", 0.9))

    def matches(self, txn: Transaction) -> bool:
        if self.direction and txn.direction != self.direction:
            return False
        if self.source and txn.source != self.source:
            return False
        narration = txn.narration.lower()
        # Source-only rules (no keywords) match any narration for that source.
        if not self.keywords:
            return self.source is not None
        return any(kw in narration for kw in self.keywords)


def load_rules(path: str | Path | None = None) -> list[Rule]:
    path = Path(path) if path else _DEFAULT_RULES
    specs = json.loads(path.read_text(encoding="utf-8"))
    return [Rule(spec) for spec in specs]


def _voucher_type(txn: Transaction) -> str:
    return VoucherType.PAYMENT if txn.direction == Direction.OUTFLOW else VoucherType.RECEIPT


def classify(txns: list[Transaction], rules: list[Rule]) -> list[Transaction]:
    """Apply rules in order; first match wins. Unmatched stay in suspense."""
    for txn in txns:
        for rule in rules:
            if rule.matches(txn):
                txn.ledger = rule.ledger
                txn.voucher_type = _voucher_type(txn)
                txn.status = TxnStatus.AUTO
                txn.confidence = rule.confidence
                txn.matched_rule = rule.name
                break
        else:
            # No rule matched — leave for the suspense loop (stage 3).
            txn.status = TxnStatus.SUSPENSE
            txn.confidence = 0.0
    return txns
