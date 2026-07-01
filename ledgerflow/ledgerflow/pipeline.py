"""The end-to-end pipeline: ingest -> classify -> suspense -> export."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import export, ingest, rules_engine, suspense
from .models import Transaction, TxnStatus


@dataclass
class PipelineResult:
    transactions: list[Transaction]
    review_queue: list[dict]
    stats: dict = field(default_factory=dict)


def _compute_stats(txns: list[Transaction]) -> dict:
    total = len(txns)
    auto = sum(1 for t in txns if t.status == TxnStatus.AUTO)
    resolved = sum(1 for t in txns if t.status == TxnStatus.RESOLVED)
    pending = sum(1 for t in txns if t.status == TxnStatus.SUSPENSE)
    return {
        "total": total,
        "auto_classified": auto,
        "resolved_by_client": resolved,
        "pending_suspense": pending,
        "auto_rate": round(auto / total, 4) if total else 0.0,
        "clean_rate": round((auto + resolved) / total, 4) if total else 0.0,
    }


def run(
    input_dir: str | Path,
    output_dir: str | Path,
    rules_path: str | Path | None = None,
    responses_path: str | Path | None = None,
    company: str = "Demo Company",
    sync: bool = False,
    tally_host: str = "localhost",
    tally_port: int = 9000,
) -> PipelineResult:
    """Run all four stages and write outputs to ``output_dir``."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1 — Ingestion.
    txns = ingest.ingest_directory(input_dir)

    # Stage 2 — Rules engine.
    rules = rules_engine.load_rules(rules_path)
    rules_engine.classify(txns, rules)

    # Stage 3 — Suspense loop.
    queue = suspense.flag_suspense(txns)
    responses = suspense.load_responses(responses_path)
    if responses:
        suspense.apply_responses(txns, responses)
        # Refresh the queue so resolved items drop off.
        queue = suspense.flag_suspense(txns)

    # Stage 4 — Export.
    xml = export.to_tally_xml(txns, company=company)
    (output_dir / "tally_import.xml").write_text(xml, encoding="utf-8")
    export.to_daybook_csv(txns, output_dir / "daybook.csv")
    (output_dir / "review_queue.json").write_text(
        json.dumps(queue, indent=2), encoding="utf-8"
    )

    stats = _compute_stats(txns)
    (output_dir / "summary.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    if sync:
        ok, message = export.sync_to_tally(xml, host=tally_host, port=tally_port)
        stats["tally_sync_ok"] = ok
        stats["tally_sync_message"] = message

    return PipelineResult(transactions=txns, review_queue=queue, stats=stats)
