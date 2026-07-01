# LedgerFlow

**Bank statements in one end → clean, Tally-ready data out the other.**

LedgerFlow is a middleware for Chartered Accountants in India. Instead of
typing bank statements into Tally line by line, you feed LedgerFlow the raw
data and it returns sorted, ledger-tagged, Tally-ready vouchers.

It works in four stages:

```
 ┌───────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────┐
 │ 1. INGEST │ → │ 2. RULES     │ → │ 3. SUSPENSE   │ → │ 4. EXPORT│
 │ bank /    │   │ ~80% auto to │   │ ~20% flagged, │   │ Tally XML│
 │ card / GST│   │ right ledger │   │ asked via     │   │ / CSV /  │
 │           │   │              │   │ WhatsApp link │   │ port 9000│
 └───────────┘   └──────────────┘   └───────────────┘   └──────────┘
```

---

## Quick start

No dependencies — Python 3.10+ standard library only.

```bash
cd ledgerflow
python -m ledgerflow.cli run
```

That runs the whole pipeline on the bundled sample data and writes results to
`ledgerflow/output/`:

| File | What it is |
|------|------------|
| `tally_import.xml` | Tally-native voucher import (load via Gateway → Import) |
| `daybook.csv` | Flat, Excel-friendly day book |
| `review_queue.json` | The suspense items + no-login review links |
| `summary.json` | Counts and auto/clean rates |

Run the tests:

```bash
cd ledgerflow
python -m unittest discover -s tests
```

---

## The four stages

### 1 · Ingestion — `ingest.py`
Reads a bank statement CSV, a credit-card export CSV, and a GST-portal JSON
feed (simulating India's Account Aggregator / GSTN) into one normalised list of
`Transaction` objects. Debits become outflows, credits become inflows.

### 2 · Rules engine — `rules_engine.py`
Matches narration patterns against `rules.json` and books ~80% of lines to the
right Tally ledger automatically — *Swiggy → Staff Welfare*, *Jio → Telephone
Expenses*, *GST challans → Duties & Taxes*. Rules are data, not code, so a CA
can tune them without programming. First matching rule wins.

### 3 · Suspense loop — `suspense.py`
The ~20% the engine can't place (vague UPI transfers, ATM withdrawals) are
flagged. Each gets a secure, no-login **review token + link** that would be
sent to the client over WhatsApp. They tap a plain-English dropdown on their
phone; the answer (`client_responses.json` in this demo) flows straight back
in and the transaction is resolved. Anything still unanswered is safely booked
to **Suspense A/c** so nothing is ever lost.

### 4 · Export — `export.py`
Emits Tally's native import **XML** (balanced Payment/Receipt vouchers), a
day-book **CSV**, and can **sync directly to Tally** on `localhost:9000` via its
HTTP/XML gateway (`--sync`).

---

## CLI

```bash
python -m ledgerflow.cli run \
  --input  ./sample_data \
  --output ./output \
  --rules  ./rules.json \
  --responses ./sample_data/client_responses.json \
  --company "My Client Pvt Ltd" \
  --sync --tally-host localhost --tally-port 9000
```

- `--responses ''` runs *before* the client answers (everything unresolved is
  parked in Suspense A/c).
- `--sync` pushes the XML to a live Tally instance; without it you get files.

---

## Example run

```
Transactions ingested : 35
Auto-classified       : 28  (80.0%)
Resolved by client    : 3
Still in suspense     : 4
Clean & Tally-ready   : 88.6%
```

---

## Layout

```
ledgerflow/
├── ledgerflow/          # the package
│   ├── models.py        #   shared Transaction data model
│   ├── ingest.py        #   stage 1
│   ├── rules_engine.py  #   stage 2
│   ├── suspense.py      #   stage 3
│   ├── export.py        #   stage 4
│   ├── pipeline.py      #   orchestrates all four
│   └── cli.py           #   command-line entry point
├── rules.json           # ledger-mapping rules (editable by a CA)
├── sample_data/         # simulated bank / card / GST feeds
└── tests/               # unittest suite (10 tests, stdlib only)
```

---

## Status & roadmap

This is a working prototype of the core engine. Natural next steps:

- Real Account Aggregator + GSTN connectors (replace the file readers).
- A hosted review page that renders `review_queue.json` as the phone dropdown.
- Bank-specific statement parsers (HDFC, ICICI, SBI, Axis formats).
- Confidence-based review (send borderline auto-matches for confirmation too).
- Learning from client answers to grow the rule set over time.

See the product write-up: [`docs/10-ledgerflow.md`](../docs/10-ledgerflow.md).
