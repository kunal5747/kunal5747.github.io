# Agent job queue

The Mac Mini agent works the **topmost unchecked box** on each scheduled tick.
Add jobs as `- [ ]` items, most important first. The agent ticks them to
`- [x]` when done, or leaves a `> blocked:` note if it can't.

If every box is checked, the agent exits each tick without spending any tokens.

## How to add a job

Write one clear, small, self-contained instruction per line, e.g.:

```
- [ ] Add a "Cost" column to the README pricing table for the Max 20× plan (~$200/mo).
- [ ] Fix the typo in docs/06-finance.md line 40.
```

## Jobs

- [x] Bootstrap the Mac Mini hosting kit — done 2026-07-03
      (this file, run-agent.sh, agent-prompt.md, plist, install.sh)

<!-- Add new jobs below this line -->
