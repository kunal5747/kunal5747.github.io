#!/usr/bin/env bash
#
# install.sh — install the ATLAS Mac Mini agent as a launchd job.
#
# Substitutes real paths into the plist template and loads it. Idempotent:
# safe to re-run after you change the cadence or branch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE="$SCRIPT_DIR/com.atlas.claude-agent.plist"
LABEL="com.atlas.claude-agent"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
BRANCH="${ATLAS_AGENT_BRANCH:-$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)}"

echo "Repo:   $REPO_DIR"
echo "Branch: $BRANCH"
echo "Dest:   $DEST"

# --- Sanity checks -----------------------------------------------------------
command -v claude >/dev/null 2>&1 || {
  echo "ERROR: 'claude' (Claude Code) not found on PATH. Install and sign in first." >&2
  exit 1
}
chmod +x "$SCRIPT_DIR/run-agent.sh"
mkdir -p "$SCRIPT_DIR/logs" "$HOME/Library/LaunchAgents"

# --- Render the template -----------------------------------------------------
sed -e "s#__REPO_DIR__#${REPO_DIR}#g" \
    -e "s#__BRANCH__#${BRANCH}#g" \
    "$TEMPLATE" > "$DEST"

# --- (Re)load the job --------------------------------------------------------
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"

echo
echo "Installed and loaded $LABEL."
echo "It will run every 15 minutes and once now (RunAtLoad)."
echo "Watch it:  tail -f $SCRIPT_DIR/logs/agent.log"
echo "Remove it: launchctl unload $DEST && rm $DEST"
