"""LedgerFlow — bank statements in, Tally-ready data out.

A middleware that ingests bank/credit-card/tax-portal data, auto-classifies
most transactions to the right Tally ledger with a rules engine, routes the
rest through a human "suspense loop", and exports clean Tally XML/CSV.
"""

__version__ = "0.1.0"

from .models import Transaction, TxnStatus, Direction, VoucherType  # noqa: F401
