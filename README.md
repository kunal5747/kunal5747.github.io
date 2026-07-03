# Project ATLAS

**The AI Operating System for Businesses**

> ATLAS is not a chatbot. It is an AI Company Operating System — an intelligent
> layer that lets anyone run an entire company using teams of specialized AI
> agents working together under human supervision.

---

## What is ATLAS?

Today, companies stitch together dozens of disconnected products — ERP, CRM,
HRMS, accounting, email, WhatsApp, project management, BI, document management.
Employees spend their days manually coordinating work across these tools.

ATLAS sits **above** all of them as the intelligent coordination layer. Instead
of employees manually moving work between systems, **AI agents coordinate it**.

- The human becomes the **CEO**.
- ATLAS becomes the **management team**.

Every company should be able to operate like it has hundreds of highly skilled
digital employees.

---

## The Master Blueprint

This repository hosts the **ATLAS Master Blueprint** — the structured reference
manual for engineers, AI agents, executives, and investors. It is designed to
be read as a company plan that scales over decades, not just a software spec.

| # | Document | What it covers |
|---|----------|----------------|
| 00 | [Overview](docs/00-overview.md) | Mission, vision, and how the pieces fit |
| 01 | [Product Vision](docs/01-product-vision.md) | Philosophy, design principles, the human-in-the-loop model |
| 02 | [Architecture](docs/02-architecture.md) | Core platform, agent framework, memory, orchestration |
| 03 | [Engineering](docs/03-engineering.md) | Tech direction, modular services, development workflow |
| 04 | [Operations](docs/04-operations.md) | Security, auditability, monitoring, reliability |
| 05 | [Hiring & Team](docs/05-hiring-and-team.md) | Org design, roles, culture as the company grows |
| 06 | [Finance](docs/06-finance.md) | Revenue model, unit economics, funding strategy |
| 07 | [Go-to-Market](docs/07-go-to-market.md) | ConstructionOS first, then the vertical family |
| 08 | [Roadmap](docs/08-roadmap.md) | Phased plan from platform to industry operating systems |
| 09 | [ConstructionOS](docs/09-constructionos.md) | A commercial vertical, module by module |
| 10 | [LedgerFlow](docs/10-ledgerflow.md) | **The first tool being built** — bank statements → Tally |

---

## The first tool: LedgerFlow

The first product being built under ATLAS is **[LedgerFlow](ledgerflow/README.md)** —
a middleware that turns bank statements into clean, Tally-ready data for
Chartered Accountants in India.

Bank statements go in one end; sorted, ledger-tagged vouchers come out the
other, in four stages: **ingest → rules engine → suspense loop → export**.

A working prototype (runnable Python, stdlib only, with tests) lives in
[`/ledgerflow`](ledgerflow/README.md):

```bash
cd ledgerflow
python -m ledgerflow.cli run
# → 35 transactions · 80% auto-classified · Tally XML + CSV written
```

Read the product write-up: **[docs/10-ledgerflow.md](docs/10-ledgerflow.md)**.

---

## Running the agents cheaply: Mac Mini hosting

ATLAS agents don't need a data center to run. The
**[Mac Mini agent-hosting kit](infra/mac-mini-agent/README.md)** turns a single
always-on Mac Mini into a 24/7 worker for **~$21–23/month, flat** — a Claude
Pro/Max subscription plus a `launchd` schedule that wakes Claude Code, works a
job queue, and sleeps. It spends **zero tokens while idle**, avoiding the
pay-per-token trap of a nonstop API agent.

```bash
cd infra/mac-mini-agent
./install.sh          # loads the scheduled job; runs every 15 min
```

---

## Core Philosophy

- **Plain-English-first** interaction
- **AI executes; humans approve** important decisions
- **Planning before implementation**
- **Modular, reusable** architecture
- **One core platform** serving many industries
- **Outcome-focused** rather than tool-focused
- **Enterprise-grade** security, auditability, and scalability

---

## Strategy in one line

> Build one reusable AI Agent Platform → launch **ConstructionOS** as the first
> vertical → reuse the platform for additional industries → grow recurring
> enterprise revenue through subscriptions, implementation, and premium AI.

---

*This site is published via GitHub Pages. The landing page lives in
[`index.html`](index.html); the full blueprint lives in [`docs/`](docs/).*
