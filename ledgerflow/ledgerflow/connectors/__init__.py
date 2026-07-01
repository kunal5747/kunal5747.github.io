"""Connector registry.

Register a new accounting-software adapter by adding its class to
``_CONNECTORS`` below. Everything else (pipeline, CLI) discovers it by name.
"""

from __future__ import annotations

from .base import AccountingConnector
from .generic import BusyConnector, GenericConnector, ZohoBooksConnector
from .tally import TallyConnector

_CONNECTORS: dict[str, type[AccountingConnector]] = {
    cls.name: cls
    for cls in (TallyConnector, GenericConnector, ZohoBooksConnector, BusyConnector)
}


def get(name: str) -> AccountingConnector:
    """Instantiate a connector by name (raises KeyError with a helpful list)."""
    try:
        return _CONNECTORS[name]()
    except KeyError:
        raise KeyError(
            f"Unknown connector '{name}'. Available: {', '.join(available())}"
        ) from None


def available() -> list[str]:
    return sorted(_CONNECTORS)


def describe() -> list[tuple[str, str, bool]]:
    """(name, label, can_push) for each registered connector."""
    return [(c.name, c.label, c.can_push) for c in
            sorted(_CONNECTORS.values(), key=lambda c: c.name)]


__all__ = ["AccountingConnector", "get", "available", "describe"]
