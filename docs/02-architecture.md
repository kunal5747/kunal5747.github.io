# 02 · Architecture

The reusable **AI Agent Platform** is the heart of ATLAS. Everything — every
industry vertical, every customer deployment — is built on top of it.

---

## Core platform at a glance

```
┌───────────────────────────────────────────────────────────────┐
│                        INDUSTRY OS LAYER                       │
│   ConstructionOS · HospitalOS · ManufacturingOS · RetailOS …  │
└───────────────────────────────┬───────────────────────────────┘
                               │
┌───────────────────────────────▼───────────────────────────────┐
│                    REUSABLE AI AGENT PLATFORM                 │
│                                                               │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ AI Agent      │  │ Multi-Agent   │  │ Workflow         │  │
│  │ Framework     │  │ Workflow      │  │ Orchestrator     │  │
│  │               │  │ Engine        │  │                  │  │
│  └───────────────┘  └───────────────┘  └──────────────────┘  │
│                                                               │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ Memory System │  │ Integrations  │  │ Enterprise       │  │
│  │ (shared org   │  │ Layer         │  │ Controls         │  │
│  │  knowledge)   │  │               │  │ (auth, audit)    │  │
│  └───────────────┘  └───────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## AI Agent Framework

The framework for creating and governing individual agents.

- **Agent creation** — define an agent's role, capabilities, and tools.
- **Agent registry** — a catalog of available agents and their permissions.
- **Role-based permissions** — each agent can only do what its role allows.
- **Specialized agents** — research, finance, legal, planning, coding, QA, and
  more, each an expert in a narrow domain.

---

## Multi-Agent Workflow Engine

Agents **collaborate** instead of working independently. Work flows from one
specialist to the next, each adding value and handing off context.

```
Research Agent
     ↓
Finance Agent
     ↓
Legal Agent
     ↓
Planning Agent
     ↓
Coding Agent
     ↓
QA Agent
```

Each hand-off carries shared context from the [Memory System](#memory-system),
so no agent starts from scratch.

---

## Memory System

A **shared organizational memory** — the institutional knowledge of the company,
accessible to every agent that is permitted to see it.

Includes:

- Company knowledge
- Documents
- Conversations
- Projects
- SOPs (standard operating procedures)
- Customer history
- Long-term learning

This is what lets ATLAS behave like a coordinated organization rather than a set
of disconnected bots. It is also a primary surface for
[security and access control](04-operations.md).

---

## Workflow Orchestrator

The component that turns a plan into coordinated, reliable execution.

It coordinates:

- **Tasks** — the units of work.
- **Dependencies** — what must happen before what.
- **Human approvals** — pausing for sign-off on important decisions.
- **Scheduling** — when work runs.
- **Retries** — recovering from transient failures.
- **Notifications** — keeping humans informed.

The orchestrator is where the
[human-in-the-loop](01-product-vision.md#human-in-the-loop) principle is
enforced: irreversible actions cannot proceed without approval.

---

## Integrations

ATLAS connects to the systems companies already use:

- Tally
- ERP systems
- CRM
- Email
- WhatsApp
- Calendar
- Cloud storage
- Accounting software
- Banking systems
- Government portals
- Future enterprise software

The integrations layer is designed to be **replaceable and extensible** — new
connectors can be added without changing the core platform.

---

## Enterprise controls

Cross-cutting concerns that every component participates in:

- Enterprise permissions
- Audit logs
- Monitoring
- Security

These are detailed in [04 · Operations](04-operations.md).

---

*Previous ← [01 · Product Vision](01-product-vision.md)  ·  Next → [03 · Engineering](03-engineering.md)*
