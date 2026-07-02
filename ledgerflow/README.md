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

## Feed your own statement

Point it at a real bank or credit-card file — CSV, Excel (`.xlsx`), **or PDF**.
The reader auto-detects the layout (preamble rows, different column names, date
formats, separate Debit/Credit *or* a single Amount + Dr/Cr column, and the
`AMOUNT{Dr|Cr}  BALANCE` rows used in Indian bank PDF statements):

```bash
python -m ledgerflow.cli run --statement /path/to/mystatement.xlsx
python -m ledgerflow.cli run --statement statement.pdf     # needs: pip install pypdf
python -m ledgerflow.cli run --statement card.csv --statement-type credit_card
```

The results land in `output/` ready to import. Tested on a real 16-page Bank of
Maharashtra PDF: **1,108 transactions** parsed into balanced Tally vouchers.

### Ask each payee only once

Transfer-heavy accounts can have thousands of unclassified lines but only a
handful of distinct payees. The suspense loop **groups by counterparty**
(`review_groups.json`), merging truncated name variants ('Kunal' /
'Kunal Dnyanoba'), so the client answers once per party — not once per
transaction. In the run above, 979 suspense lines collapsed to ~272 parties.

### Gets smarter every month

Answers are remembered. Once a client says "Vishal = Sundry Creditors",
LedgerFlow stores it (`--memory`) and auto-applies it to that payee on every
future statement. On the real statement above, **2 answers auto-classified 59
transactions** on the next run — the auto-rate climbs the more it's used.

---

## Connectors (plug in to whatever they use)

Export is handled by pluggable **connectors**, so LedgerFlow can target
different accounting software without changing the pipeline:

```bash
python -m ledgerflow.cli connectors                     # list them
python -m ledgerflow.cli run --connector tally --sync   # push live to Tally
python -m ledgerflow.cli run --connector zoho_books     # or export a file
```

| Connector | Output | Live sync |
|-----------|--------|-----------|
| `tally` | Native Tally import XML + day-book CSV | Yes — port 9000 |
| `zoho_books` | Zoho Books Manual Journals CSV | File export |
| `busy` | Busy Accounting voucher CSV | File export |
| `generic` | Neutral day-book CSV + `vouchers.json` | File export |

Adding support for new software is one small class in
[`ledgerflow/connectors/`](ledgerflow/connectors/) — implement `render()`
(and optionally `push()`), register it, done.

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
│   └── connectors/      #   pluggable export adapters (Tally, Zoho, Busy, ...)
├── rules.json           # ledger-mapping rules (editable by a CA)
├── sample_data/         # simulated bank / card / GST feeds
└── tests/               # unittest suite (18 tests, stdlib only)
```

---

## Status & roadmap

This is a working prototype of the core engine. It already handles real
statement formats (CSV/XLSX, auto-detected) and exports to Tally, Zoho Books,
and Busy via the connector layer. Natural next steps:

- Live Account Aggregator + GSTN ingestion (replace the file readers).
- A hosted review page that renders `review_queue.json` as the phone dropdown.
- More connectors (QuickBooks, Marg, Vyapar) — one class each.
- Confidence-based review (send borderline auto-matches for confirmation too).
- Learning from client answers to grow the rule set over time.

See the product write-up: [`docs/10-ledgerflow.md`](../docs/10-ledgerflow.md).
