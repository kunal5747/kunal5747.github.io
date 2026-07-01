# 04 · Operations

Running an AI operating system that touches payments, contracts, and customer
data means **trust is the product**. Security, auditability, and reliability are
first-class, not afterthoughts.

---

## Security

- **Enterprise permissions.** Access is role-based across users *and* agents.
  Every agent operates under the least privilege its role requires.
- **Segregated memory access.** The [shared memory system](02-architecture.md#memory-system)
  enforces who — and which agents — can read or write each class of knowledge.
- **Secrets and credentials** for integrations (banking, ERP, government
  portals) are stored and accessed through controlled, isolated mechanisms.

---

## Auditability

Every consequential action is recorded. The audit log answers: *who (or which
agent) did what, when, on whose approval, and why.*

This matters most for the actions that
[always require human approval](01-product-vision.md#human-in-the-loop):

- Payments
- Contracts
- Hiring
- Loans
- Investments
- Legal filings
- Bank transfers

For each of these, the record ties the action to the approving human and the
plan that justified it.

---

## Monitoring

- **Monitoring agents observe production** continuously (see the
  [development workflow](03-engineering.md#development-workflow)).
- **Improvement agents** turn observations into proposed optimizations, which
  re-enter the plan → approve → build loop.
- Standard operational telemetry — health, latency, error rates, cost — is
  collected across the modular services.

---

## Reliability

The [Workflow Orchestrator](02-architecture.md#workflow-orchestrator) provides
the operational backbone:

- **Retries** recover from transient failures.
- **Dependencies** ensure work happens in the correct order.
- **Human-approval gates** stop irreversible actions from proceeding
  automatically.
- **Notifications** keep humans informed of progress, blocks, and approvals
  needed.

---

## Operating principle

> AI should never make irreversible business decisions automatically.

Operations exists to make that promise real and provable — through permissions
that prevent, audit logs that record, and monitoring that detects.

---

*Previous ← [03 · Engineering](03-engineering.md)  ·  Next → [05 · Hiring & Team](05-hiring-and-team.md)*
