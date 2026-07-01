"""Command-line entry point.

    python -m ledgerflow.cli run
    python -m ledgerflow.cli run --input ./data --output ./out --sync
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import pipeline

_PKG = Path(__file__).resolve().parent
_DEFAULT_INPUT = _PKG.parent / "sample_data"
_DEFAULT_RULES = _PKG.parent / "rules.json"
_DEFAULT_RESPONSES = _PKG.parent / "sample_data" / "client_responses.json"
_DEFAULT_OUTPUT = _PKG.parent / "output"


def _print_summary(result: pipeline.PipelineResult) -> None:
    s = result.stats
    print("\nLedgerFlow — run complete")
    print("-" * 40)
    print(f"  Transactions ingested : {s['total']}")
    print(f"  Auto-classified       : {s['auto_classified']}  "
          f"({s['auto_rate'] * 100:.1f}%)")
    print(f"  Resolved by client    : {s['resolved_by_client']}")
    print(f"  Still in suspense     : {s['pending_suspense']}")
    print(f"  Clean & Tally-ready   : {s['clean_rate'] * 100:.1f}%")
    if "tally_sync_ok" in s:
        state = "OK" if s["tally_sync_ok"] else "FAILED"
        print(f"  Tally port sync       : {state} — {s['tally_sync_message']}")
    if result.review_queue:
        print("\n  Pending review links (would be sent via WhatsApp):")
        for item in result.review_queue:
            print(f"    - {item['date']}  ₹{item['amount']:>10}  "
                  f"{item['narration'][:32]:32}  {item['review_link']}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledgerflow", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full ingest->export pipeline")
    run.add_argument("--input", default=str(_DEFAULT_INPUT),
                     help="Directory of input feeds")
    run.add_argument("--output", default=str(_DEFAULT_OUTPUT),
                     help="Directory for Tally-ready output")
    run.add_argument("--rules", default=str(_DEFAULT_RULES),
                     help="Path to rules.json")
    run.add_argument("--responses", default=str(_DEFAULT_RESPONSES),
                     help="Client suspense responses (set to '' to skip)")
    run.add_argument("--company", default="Demo Company",
                     help="Tally company name")
    run.add_argument("--sync", action="store_true",
                     help="POST the XML to Tally on port 9000")
    run.add_argument("--tally-host", default="localhost")
    run.add_argument("--tally-port", type=int, default=9000)

    args = parser.parse_args(argv)

    if args.command == "run":
        responses = args.responses or None
        result = pipeline.run(
            input_dir=args.input,
            output_dir=args.output,
            rules_path=args.rules,
            responses_path=responses,
            company=args.company,
            sync=args.sync,
            tally_host=args.tally_host,
            tally_port=args.tally_port,
        )
        _print_summary(result)
        print(f"  Output written to: {args.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
