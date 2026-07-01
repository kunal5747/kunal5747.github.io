# 03 · Engineering

How ATLAS is built, and how it stays buildable as models and infrastructure
improve.

---

## Technology direction

Technologies will evolve; the **architecture** is what stays stable. ATLAS is
designed around a small set of durable building blocks:

- **AI agent framework**
- **Workflow orchestration**
- **Shared memory**
- **APIs and integrations**
- **Enterprise permissions**
- **Audit logs**
- **Monitoring**
- **Cloud-native infrastructure**
- **Modular services**

The guiding constraint: **keep components replaceable** so ATLAS can adopt
better AI models and better infrastructure over time without a rewrite.

---

## Design tenets for engineers

1. **Model-agnostic core.** Agents call models through an abstraction, not
   directly. Swapping or upgrading a model should be a configuration change, not
   a refactor.
2. **Modular services.** Each capability (memory, orchestration, integrations)
   is an independently deployable service with a clear contract.
3. **APIs first.** Every capability is exposed through a stable API so verticals
   and third parties can build on it.
4. **Stateless where possible, durable where it counts.** Long-lived state lives
   in the memory system and the orchestrator's durable stores; compute is
   disposable.
5. **Idempotent, retryable actions.** Because the orchestrator retries, every
   externally-visible action must be safe to attempt more than once.
6. **Everything is auditable.** No agent action bypasses the audit log.

---

## Development workflow

A core preference established for how work gets done in and around ATLAS — it
mirrors the product itself (plan first, then execute, with humans approving):

1. **User describes the goal** in plain English.
2. **Planning agents research and validate** it.
3. A **master project plan is generated**.
4. **User approves.**
5. **Coding agents build it.**
6. **QA agents test it.**
7. **Deployment agents release it.**
8. **Monitoring agents observe** production.
9. **Improvement agents suggest** optimizations.

```
Goal (plain English)
   → Plan (research + validate)
      → Approve (human)
         → Build → Test → Deploy
            → Monitor → Improve → (loop back)
```

This is both how we build ATLAS *and* a template for how ATLAS builds software
for its customers.

---

## Why "planning before implementation" is enforced

Letting agents jump straight to building is fast but fragile. Requiring a
validated, human-approved plan:

- surfaces bad assumptions before code is written,
- creates a reviewable artifact for stakeholders, and
- gives QA and monitoring a spec to check against.

---

*Previous ← [02 · Architecture](02-architecture.md)  ·  Next → [04 · Operations](04-operations.md)*
