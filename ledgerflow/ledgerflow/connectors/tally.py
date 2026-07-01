"""Tally connector — native XML import + live sync on port 9000."""

from __future__ import annotations

from .. import export
from ..models import Transaction
from .base import AccountingConnector


class TallyConnector(AccountingConnector):
    name = "tally"
    label = "Tally (native XML + port 9000 sync)"
    can_push = True

    def render(self, txns: list[Transaction], company: str = "Demo Company") -> dict[str, str]:
        return {
            "tally_import.xml": export.to_tally_xml(txns, company=company),
            "daybook.csv": export.daybook_csv_string(txns),
        }

    def push(
        self,
        txns: list[Transaction],
        company: str = "Demo Company",
        host: str = "localhost",
        port: int = 9000,
        **options,
    ) -> tuple[bool, str]:
        xml = export.to_tally_xml(txns, company=company)
        return export.sync_to_tally(xml, host=host, port=port)
