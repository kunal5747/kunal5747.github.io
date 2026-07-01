"""Core data model shared across all four pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


class Direction:
    """Which way the money moved, from the account holder's point of view."""

    OUTFLOW = "outflow"  # money leaving the account (a payment)
    INFLOW = "inflow"    # money arriving in the account (a receipt)


class TxnStatus:
    """Lifecycle of a transaction as it passes through the pipeline."""

    AUTO = "auto"          # classified automatically by the rules engine
    SUSPENSE = "suspense"  # could not be classified; awaiting a human answer
    RESOLVED = "resolved"  # was in suspense, now answered by the client


class VoucherType:
    """Tally voucher types LedgerFlow emits."""

    PAYMENT = "Payment"
    RECEIPT = "Receipt"


@dataclass
class Transaction:
    """A single normalised line item, regardless of where it came from."""

    date: str            # ISO date, YYYY-MM-DD
    narration: str       # raw bank/card description
    amount: Decimal      # always positive; Direction carries the sign
    direction: str       # Direction.OUTFLOW / Direction.INFLOW
    source: str          # "bank" | "credit_card" | "gst_portal"
    reference: str = ""  # UPI ref / cheque no / challan no (stable id)

    # The bank/card account this transaction hits (the "contra" side).
    contra_ledger: str = "Bank Account"

    # Filled in by the rules engine / suspense loop.
    ledger: str | None = None
    voucher_type: str | None = None
    status: str = TxnStatus.SUSPENSE
    confidence: float = 0.0
    matched_rule: str | None = None
    review_token: str | None = None

    def signed_amount(self) -> Decimal:
        """Amount with an accounting sign: negative for outflow."""
        return -self.amount if self.direction == Direction.OUTFLOW else self.amount

    def as_row(self) -> dict:
        """Flat dict for CSV / JSON export and review queues."""
        return {
            "date": self.date,
            "narration": self.narration,
            "reference": self.reference,
            "amount": f"{self.amount:.2f}",
            "direction": self.direction,
            "source": self.source,
            "ledger": self.ledger or "",
            "voucher_type": self.voucher_type or "",
            "status": self.status,
            "confidence": f"{self.confidence:.2f}",
            "matched_rule": self.matched_rule or "",
        }
