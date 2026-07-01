"""Command-line entry point.

    python -m ledgerflow.cli run
    python -m ledgerflow.cli run --statement mystatement.xlsx --connector tally
    python -m ledgerflow.cli connectors        # list available adapters
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import connectors, pipeline

_PKG = Path(__file__).resolve().parent
_DEFAULT_INPUT = _PKG.parent / "sample_data"
_DEFAULT_RULES = _PKG.parent / "rules.json"
_DEFAULT_RESPONSES = _PKG.parent / "sample_data" / "client_responses.json"
_DEFAULT_OUTPUT = _PKG.parent / "output"


def _print_summary(result: pipeline.PipelineResult, output: str) -> None:
    s = result.stats
    print("\nLedgerFlow — run complete")
    print("-" * 44)
    print(f"  Transactions ingested : {s['total']}")
    print(f"  Auto-classified       : {s['auto_classified']}  "
          f"({s['auto_rate'] * 100:.1f}%)")
    print(f"  Resolved by client    : {s['resolved_by_client']}")
    print(f"  Still in suspense     : {s['pending_suspense']}")
    print(f"  Clean & ready         : {s['clean_rate'] * 100:.1f}%")
    print(f"  Connector             : {s.get('connector')}")
    if "sync_ok" in s:
        state = "OK" if s["sync_ok"] else "FAILED"
        print(f"  Live sync             : {state} — {s['sync_message']}")
    if result.review_queue:
        print("\n  Pending review links (would be sent via WhatsApp):")
        for item in result.review_queue:
            print(f"    - {item['date']}  {item['amount']:>12}  "
                  f"{item['narration'][:34]:34}  {item['review_link']}")
    print(f"\n  Output files: {', '.join(result.artifacts)}")
    print(f"  Written to  : {output}\n")


def _cmd_connectors() -> int:
    print("\nAvailable connectors (--connector <name>):\n")
    for name, label, can_push in connectors.describe():
        push = "live sync" if can_push else "file export"
        print(f"  {name:12}  {label:44}  [{push}]")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledgerflow", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("connectors", help="List available accounting connectors")

    run = sub.add_parser("run", help="Run the full ingest->export pipeline")
    run.add_argument("--input", default=str(_DEFAULT_INPUT),
                     help="Directory of input feeds (sample mode)")
    run.add_argument("--statement", default=None,
                     help="A single real statement file (CSV or XLSX) to ingest")
    run.add_argument("--statement-type", default="bank",
                     choices=["bank", "credit_card"],
                     help="How to treat --statement (default: bank)")
    run.add_argument("--output", default=str(_DEFAULT_OUTPUT),
                     help="Directory for the ready-to-import output")
    run.add_argument("--rules", default=str(_DEFAULT_RULES),
                     help="Path to rules.json")
    run.add_argument("--responses", default=str(_DEFAULT_RESPONSES),
                     help="Client suspense responses (set to '' to skip)")
    run.add_argument("--company", default="Demo Company",
                     help="Company name for the export")
    run.add_argument("--connector", default="tally",
                     choices=connectors.available(),
                     help="Accounting-software adapter (default: tally)")
    run.add_argument("--sync", action="store_true",
                     help="Push live to the target system (e.g. Tally port 9000)")
    run.add_argument("--tally-host", default="localhost")
    run.add_argument("--tally-port", type=int, default=9000)

    args = parser.parse_args(argv)

    if args.command == "connectors":
        return _cmd_connectors()

    if args.command == "run":
        # When a real statement is supplied, don't also assume sample responses.
        responses = args.responses or None
        if args.statement and args.responses == str(_DEFAULT_RESPONSES):
            responses = None
        result = pipeline.run(
            input_dir=args.input,
            output_dir=args.output,
            rules_path=args.rules,
            responses_path=responses,
            company=args.company,
            connector=args.connector,
            sync=args.sync,
            tally_host=args.tally_host,
            tally_port=args.tally_port,
            statement_file=args.statement,
            statement_source=args.statement_type,
        )
        _print_summary(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
