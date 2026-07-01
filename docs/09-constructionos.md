# 09 · ConstructionOS

**The first commercial product.** ConstructionOS is chosen because of existing
domain experience, giving a realistic route to early customers while
strengthening the shared [ATLAS platform](02-architecture.md).

---

## Why construction first

- **Domain experience** de-risks the first build and shortens sales cycles.
- **High coordination pain** — construction and real estate development involve
  many parties, documents, approvals, and cash flows, which is exactly what a
  coordination layer of AI agents excels at.
- **Concrete, high-value outcomes** — faster due diligence, tighter cost
  control, better collections — that fit the outcome-focused philosophy.

---

## Modules

ConstructionOS spans the lifecycle of a development, from acquiring land to
reporting to investors.

| Module | What it does |
|--------|--------------|
| **Land acquisition** | Sourcing, evaluating, and acquiring land parcels. |
| **Due diligence** | Legal, title, and technical checks before commitment. |
| **Development agreements** | Structuring and managing development contracts. |
| **JV modelling** | Modelling joint-venture structures and returns. |
| **Cost estimation** | Estimating and tracking project costs. |
| **Procurement** | Sourcing materials and services; managing vendors. |
| **Site monitoring** | Tracking on-site progress and status. |
| **Contractor management** | Managing contractors and their performance. |
| **Sales CRM** | Managing buyers and the sales pipeline. |
| **Collections** | Tracking and driving payment collection. |
| **Investor reporting** | Reporting performance to investors. |
| **Finance** | Project and company financial management. |
| **Compliance** | Regulatory and statutory compliance. |

---

## How the modules use the platform

Each module is not a standalone app — it is a configuration of ATLAS's shared
capabilities:

- **Specialized agents** (research, finance, legal, planning) from the
  [AI Agent Framework](02-architecture.md#ai-agent-framework) do the work.
- The **[Multi-Agent Workflow Engine](02-architecture.md#multi-agent-workflow-engine)**
  chains them — e.g. due diligence flows from a research agent to a legal agent
  to a planning agent.
- The **[Memory System](02-architecture.md#memory-system)** holds project
  documents, customer history, and SOPs shared across modules.
- The **[Workflow Orchestrator](02-architecture.md#workflow-orchestrator)**
  enforces approvals — a **payment**, **contract**, or **bank transfer** in
  Procurement, Finance, or Collections pauses for human sign-off.

---

## Example: due diligence flow

```
Research Agent   → gathers title, zoning, and market data
     ↓
Legal Agent      → flags legal and title risks
     ↓
Finance Agent    → models cost and return impact
     ↓
Planning Agent   → assembles a go / no-go recommendation
     ↓
HUMAN            → approves the decision to proceed
```

This is the [human-in-the-loop](01-product-vision.md#human-in-the-loop)
principle applied to a real construction workflow: agents do the legwork; the
human makes the irreversible call.

---

*Previous ← [08 · Roadmap](08-roadmap.md)  ·  Back to [Overview](00-overview.md)*
