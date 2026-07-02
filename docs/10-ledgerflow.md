# 10 · LedgerFlow — the first tool

**Bank statements → Tally, automatically.**

LedgerFlow is the **first tool being built** under Project ATLAS. It is a
focused, shippable product for a real and painful problem, and it doubles as
the first concrete proof of the ATLAS philosophy: *AI/automation does the work,
humans approve what matters.*

> A working prototype of the full four-stage engine lives in
> [`/ledgerflow`](../ledgerflow/README.md) — runnable Python, stdlib only,
> with tests and sample data.

---

## The problem

Chartered Accountants in India waste enormous time typing bank statements into
Tally by hand, line by line. Every transaction has to be read, understood,
matched to a ledger, and keyed in. It is slow, repetitive, and error-prone.

LedgerFlow is software that does it automatically.

---

## The big idea: a middleware

A **machine that sits in the middle**. Bank statements go in one end; clean,
sorted, Tally-ready data comes out the other.

```
 ┌───────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────┐
 │ 1. INGEST │ → │ 2. RULES     │ → │ 3. SUSPENSE   │ → │ 4. EXPORT│
 │ bank /    │   │ ~80% auto to │   │ ~20% flagged, │   │ Tally XML│
 │ card / GST│   │ right ledger │   │ asked via     │   │ / CSV /  │
 │           │   │              │   │ WhatsApp link │   │ port 9000│
 └───────────┘   └──────────────┘   └───────────────┘   └──────────┘
```

---

## The four stages

### 1 · Ingestion

Pull in bank statements, credit-card data, and tax-portal data — simulating
India's **Account Aggregator** and **GSTN** systems. Everything is normalised
into one common transaction shape regardless of the source format.

### 2 · Rules engine

Automatically sort **~80% of transactions** to the right Tally ledger by
recognising patterns:

- *Swiggy → Staff Welfare*
- *Jio → Telephone Expenses*
- *GST challans → Duties & Taxes*

Rules are stored as editable data, so a CA can tune them to a client's chart of
accounts without touching code.

### 3 · Suspense loop

The **~20% it can't figure out** — vague UPI transfers, cash withdrawals — get
flagged instead of guessed. The system sends the client a **secure, no-login
link over WhatsApp**; they tap a simple dropdown on their phone to say what it
was, and the answer flows straight back in.

This is the [human-in-the-loop](01-product-vision.md#human-in-the-loop)
principle made concrete: the machine never invents a classification it isn't
sure of. Anything still unanswered is parked in **Suspense A/c** so nothing is
ever dropped.

### 4 · Export — a connector for whatever they use

Export is handled by **pluggable connectors**, so LedgerFlow isn't locked to one
package. The finished, clean data goes into **Tally** as XML (or **syncs
directly to Tally's local server on port 9000** via its HTTP/XML gateway), and
the same neutral vouchers can target **Zoho Books**, **Busy**, or a generic
CSV/JSON. Supporting a new system is one small connector class — nothing else in
the pipeline changes.

```bash
python -m ledgerflow.cli connectors                    # list adapters
python -m ledgerflow.cli run --connector tally --sync  # live to Tally:9000
python -m ledgerflow.cli run --connector zoho_books    # or a file export
```

### Ready for a real statement

Ingestion auto-detects real-world layouts — CSV, Excel (`.xlsx`), **and PDF** —
handling preamble/junk rows, different column names, 2-digit years,
`dd-MMM-yyyy` dates, separate Debit/Credit *or* a single Amount + Dr/Cr column,
and the `AMOUNT{Dr|Cr} BALANCE` rows of Indian bank PDF statements:

```bash
python -m ledgerflow.cli run --statement mystatement.xlsx --connector tally
python -m ledgerflow.cli run --statement statement.pdf   # needs: pip install pypdf
```

**Proven on real data.** A real 16-page Bank of Maharashtra PDF ran end-to-end:
**1,108 transactions** parsed into balanced Tally vouchers, bank charges
auto-classified, and the 979 remaining transfers grouped into ~272 unique
counterparties (truncated name variants merged) — so the client answers once
per payee, not once per line.

**It learns.** Answers are remembered per payee and auto-applied to future
statements. On that statement, **2 client answers auto-classified 59
transactions** on the next run — the auto-rate climbs the more it is used.

---

## How it maps to ATLAS

LedgerFlow is a self-contained product, but it is built on the same ideas as the
wider [ATLAS platform](02-architecture.md):

| ATLAS concept | LedgerFlow embodiment |
|---------------|-----------------------|
| Ingestion / integrations layer | Bank, card, and GST feed readers |
| Rules-driven automation | The pattern → ledger rules engine |
| Human-in-the-loop approvals | The WhatsApp suspense loop |
| Outcome-focused | Hours of manual data entry removed |
| Tally integration | Native XML export + port-9000 sync |

It is a realistic first step: a narrow, valuable wedge for CAs that also proves
out ingestion, rules, human-in-the-loop, and integrations — the building blocks
everything else reuses.

---

## Try the prototype

```bash
cd ledgerflow
python -m ledgerflow.cli run
```

Sample output:

```
Transactions ingested : 35
Auto-classified       : 28  (80.0%)
Resolved by client    : 3
Still in suspense     : 4
Clean & Tally-ready   : 88.6%
```

Full details, CLI options, and architecture are in the tool's
[README](../ledgerflow/README.md).

---

*Previous ← [09 · ConstructionOS](09-constructionos.md)  ·  Back to [Overview](00-overview.md)*
