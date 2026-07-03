#!/usr/bin/env bash
#
# run-agent.sh — one scheduled tick of the ATLAS Mac Mini agent.
#
# Fired by launchd (see com.atlas.claude-agent.plist). Each run:
#   1. Takes a lock so overlapping ticks can't stomp each other.
#   2. Pulls the latest queue from git.
#   3. Exits cheaply (zero Claude tokens) if there is no open job.
#   4. Otherwise runs Claude Code headless against agent-prompt.md.
#   5. Commits and pushes whatever the agent produced.
#   6. Logs the outcome.
#
# Designed for a Claude Pro/Max *subscription* login — do NOT export
# ANTHROPIC_API_KEY in this environment or you'll be billed per token.

set -uo pipefail

# --- Resolve paths -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/agent.log"
LOCK_FILE="$SCRIPT_DIR/.agent.lock"
PROMPT_FILE="$SCRIPT_DIR/agent-prompt.md"
TASKS_FILE="$SCRIPT_DIR/TASKS.md"
BRANCH="${ATLAS_AGENT_BRANCH:-main}"

mkdir -p "$LOG_DIR"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"; }

# --- Single-flight lock ------------------------------------------------------
# If a previous, slower run is still going, skip this tick instead of piling up.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "SKIP  previous run still active; skipping this tick"
  exit 0
fi

cd "$REPO_DIR" || { log "FATAL cannot cd into repo $REPO_DIR"; exit 1; }

# --- Sync the queue ----------------------------------------------------------
if ! git pull --rebase --autostash origin "$BRANCH" >>"$LOG_FILE" 2>&1; then
  log "WARN  git pull failed; continuing with local state"
fi

# --- Cheap exit: nothing to do ----------------------------------------------
# An "open" job is a markdown checkbox that is not yet ticked: "- [ ] ..."
if ! grep -qE '^\s*-\s*\[ \]' "$TASKS_FILE" 2>/dev/null; then
  log "IDLE  no open jobs in TASKS.md — exiting without spending tokens"
  exit 0
fi

OPEN_COUNT="$(grep -cE '^\s*-\s*\[ \]' "$TASKS_FILE")"
log "START $OPEN_COUNT open job(s); invoking Claude Code"

# --- Run Claude Code headless ------------------------------------------------
# --permission-mode acceptEdits  → apply file edits without prompting
# --allowedTools                 → constrain what it may do unattended
# Prompt is piped in from agent-prompt.md so the standing instructions live
# in version control, not in this script.
if claude -p "$(cat "$PROMPT_FILE")" \
      --permission-mode acceptEdits \
      --allowedTools "Edit,Write,Read,Grep,Glob,Bash(python*),Bash(git status),Bash(git diff*),Bash(git add*),Bash(pytest*),Bash(ls*)" \
      >>"$LOG_FILE" 2>&1; then
  log "OK    Claude run completed"
else
  log "ERROR Claude run exited non-zero (see above)"
fi

# --- Persist the result ------------------------------------------------------
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A >>"$LOG_FILE" 2>&1
  git commit -m "agent: automated tick $(date '+%Y-%m-%d %H:%M')" >>"$LOG_FILE" 2>&1
  if git push origin "$BRANCH" >>"$LOG_FILE" 2>&1; then
    log "PUSH  changes committed and pushed to $BRANCH"
  else
    log "WARN  commit made but push failed; will retry next tick"
  fi
else
  log "NOOP  agent made no file changes this tick"
fi

log "END   tick complete"
