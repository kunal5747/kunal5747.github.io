"""Connector plugin interface.

A *connector* is a pluggable destination adapter. It takes the neutral,
classified transactions LedgerFlow produces and turns them into whatever the
customer's accounting software wants — Tally, Zoho Books, Busy, or a generic
CSV/JSON. New software support is added by writing one small connector class;
nothing else in the pipeline changes.

Two responsibilities:

* ``render(txns, company)``  → files to write (name → text content).
* ``push(txns, company, **opts)`` → optional live sync to a running system.

The pipeline calls ``render`` always and ``push`` only when asked (``--sync``).
"""

from __future__ import annotations

import abc

from ..models import Transaction


class AccountingConnector(abc.ABC):
    """Base class every connector implements."""

    #: short id used on the CLI (``--connector tally``)
    name: str = "base"
    #: human label shown in listings
    label: str = "Base connector"
    #: whether this connector can push live to a running system
    can_push: bool = False

    @abc.abstractmethod
    def render(self, txns: list[Transaction], company: str = "Demo Company") -> dict[str, str]:
        """Return a mapping of output filename → file content (text)."""
        raise NotImplementedError

    def push(
        self,
        txns: list[Transaction],
        company: str = "Demo Company",
        **options,
    ) -> tuple[bool, str]:
        """Live-sync to a running system. Default: unsupported."""
        return False, f"{self.label} does not support live push (file export only)."
