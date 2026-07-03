# Mac Mini Agent Hosting

**Run ATLAS's Claude agents 24/7 on a Mac Mini — the cheapest realistic Claude setup.**

This is the self-hosting kit referenced in the ATLAS blueprint. It turns a
single always-on Mac Mini into a low-cost worker that wakes on a schedule,
picks up jobs from a queue, does them with Claude Code, logs the result, and
goes back to sleep — spending **zero tokens while idle**.

---

## The idea in one line

> Claude Pro/Max subscription + Claude Code + a `launchd` schedule = a flat,
> predictable monthly cost instead of surprise pay-per-token API bills.

You are **not** running an infinite loop that burns tokens all day. You are
running a short job every N minutes. "Always available" without "always
spending."

---

## What it costs

| Item | Cost |
|------|------|
| Claude **Pro** (start here) | ~$20 / month |
| Claude **Max 5×** (if you hit limits) | ~$100 / month |
| Electricity (Apple-silicon Mini, 24/7) | ~$1–3 / month |
| **Realistic total** | **~$21–23 / month, flat** |

Idle time is free because no tokens are spent while the agent waits for its
next scheduled wake-up. Subscription usage limits reset roughly every 5 hours,
so the scheduled-job model fits comfortably inside a Pro/Max plan.

> Raw API keys + a nonstop agent is the expensive trap — it can run to hundreds
> of dollars a month. This kit deliberately avoids that.

---

## Files in this kit

| File | Purpose |
|------|---------|
| `run-agent.sh` | The wrapper each wake-up runs: locks, pulls latest, invokes Claude Code headless against the queue, logs, and commits/pushes. |
| `agent-prompt.md` | The standing instructions handed to Claude on every run. |
| `TASKS.md` | The job queue. Add jobs here; the agent works the top unchecked item. |
| `com.atlas.claude-agent.plist` | The `launchd` schedule (macOS's cron) that fires the wrapper. |
| `install.sh` | One-shot installer: fills in your paths and loads the `launchd` job. |

---

## Setup on the Mac Mini

### 1. Install Claude Code and sign in with your subscription

```bash
# Install (see https://docs.claude.com/claude-code for the current installer)
# Then authenticate with your Claude Pro/Max account — NOT an API key:
claude            # follow the browser login once; the token is cached
```

Signing in with the **subscription** is what keeps this flat-rate. Do not set
`ANTHROPIC_API_KEY` in the agent's environment or it will bill per token.

### 2. Keep the Mini awake and self-healing

```bash
# Never sleep while on power
sudo pmset -c sleep 0 disksleep 0

# Auto-restart after a power cut
sudo pmset -c autorestart 1
```

Also enable, in **System Settings → General → Login Items**: *automatic login*
and *"Reopen windows/restart after power failure"* so the Mini recovers
unattended.

### 3. Install the scheduled job

```bash
cd infra/mac-mini-agent
./install.sh
```

`install.sh` writes a copy of the plist into `~/Library/LaunchAgents/` with
your real repo path and username substituted, then `launchctl load`s it.
Default cadence: **every 15 minutes**.

### 4. Watch it work

```bash
tail -f infra/mac-mini-agent/logs/agent.log
```

---

## How a single run works

```
launchd fires (every 15 min)
      │
      ▼
run-agent.sh
  ├─ take a lock  (skip if a previous run is still going)
  ├─ git pull --rebase                      # get latest queue
  ├─ read TASKS.md → is there an open job?  # if none, exit cheap (0 tokens)
  ├─ claude -p  < agent-prompt.md           # headless; works the top job
  ├─ git add / commit / push                # persist the result
  └─ append outcome to logs/agent.log
```

If the queue is empty the run exits **before** calling Claude, so idle ticks
cost nothing.

---

## Changing the cadence

Edit `StartInterval` (seconds) in the plist, or swap it for a
`StartCalendarInterval` block for specific times, then re-run `./install.sh`.
Every 15 min = `900`. Hourly = `3600`.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.atlas.claude-agent.plist
rm ~/Library/LaunchAgents/com.atlas.claude-agent.plist
```

---

## Security note

The wrapper runs Claude Code non-interactively with `--permission-mode
acceptEdits` and a restricted tool allowlist, scoped to this repository only.
That lets it edit files and run the project's own commands without a human
clicking "approve" each time, while still blocking arbitrary destructive
actions. Review `run-agent.sh` before trusting it on a machine with anything
sensitive on it. Do **not** add `--dangerously-skip-permissions` unless you
fully understand the consequences.
