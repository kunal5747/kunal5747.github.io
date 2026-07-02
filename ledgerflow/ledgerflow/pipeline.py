"""The end-to-end pipeline: ingest -> classify -> suspense -> export."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import connectors, ingest, rules_engine, suspense
from .models import Transaction, TxnStatus


@dataclass
class PipelineResult:
    transactions: list[Transaction]
    review_queue: list[dict]
    review_groups: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)


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
    connector: str = "tally",
    sync: bool = False,
    tally_host: str = "localhost",
    tally_port: int = 9000,
    statement_file: str | Path | None = None,
    statement_source: str = "bank",
) -> PipelineResult:
    """Run all four stages and write outputs to ``output_dir``.

    If ``statement_file`` is given, that single real file is ingested (with
    format auto-detection); otherwise the known feeds in ``input_dir`` are used.
    ``connector`` selects the accounting-software adapter for export.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1 — Ingestion.
    if statement_file:
        txns = ingest.read_statement_auto(statement_file, source=statement_source)
    else:
        txns = ingest.ingest_directory(input_dir)

    # Stage 2 — Rules engine.
    rules = rules_engine.load_rules(rules_path)
    rules_engine.classify(txns, rules)

    # Stage 3 — Suspense loop.
    queue = suspense.flag_suspense(txns)
    responses = suspense.load_responses(responses_path)
    if responses:
        suspense.apply_responses(txns, responses)
        queue = suspense.flag_suspense(txns)  # refresh; resolved items drop off

    # Stage 4 — Export via the selected connector plugin.
    conn = connectors.get(connector)
    artifacts = conn.render(txns, company=company)
    for filename, content in artifacts.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    (output_dir / "review_queue.json").write_text(
        json.dumps(queue, indent=2), encoding="utf-8"
    )
    groups = suspense.group_review(txns)
    (output_dir / "review_groups.json").write_text(
        json.dumps(groups, indent=2), encoding="utf-8"
    )

    stats = _compute_stats(txns)
    stats["unique_review_parties"] = len(groups)
    stats["connector"] = conn.name
    if sync:
        ok, message = conn.push(
            txns, company=company, host=tally_host, port=tally_port
        )
        stats["sync_ok"] = ok
        stats["sync_message"] = message
    (output_dir / "summary.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    return PipelineResult(
        transactions=txns,
        review_queue=queue,
        review_groups=groups,
        stats=stats,
        artifacts=sorted(artifacts)
        + ["review_queue.json", "review_groups.json", "summary.json"],
    )
