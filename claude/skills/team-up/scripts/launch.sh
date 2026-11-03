#!/usr/bin/env bash
# Start (or restart) a project lead's Claude Code session in tmux.
# Session name: cc-<folder name>. Claude Code runs in a restart loop, so the
# session survives crashes and `/exit` restarts it (e.g. to apply an update).

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") <project-dir> [--continue] [--discord] [--skip-permissions]

  --continue          Resume the lead's last conversation instead of starting fresh.
  --discord           Connect the Discord channel plugin, using <project-dir>/.discord
                      as the bot's state folder (token, allowlist).
  --skip-permissions  Run Claude Code with --dangerously-skip-permissions. The lead
                      will run commands and edit files without asking. Only use
                      this for a folder you trust, on a machine you're fine with
                      it changing.

If <project-dir>/.gh/hosts.yml exists, GH_CONFIG_DIR points at it, so gh acts as
the project's own GitHub account.

An existing cc-<name> session is killed first.
EOF
}

[ $# -ge 1 ] || { usage; exit 1; }
case "$1" in -h|--help) usage; exit 0 ;; esac

[ -d "$1" ] || { echo "No such folder: $1" >&2; exit 1; }
project_dir="$(cd "$1" && pwd)"
shift

continue_flag=""
discord=0
perm_flag=""
for arg in "$@"; do
  case "$arg" in
    --continue) continue_flag="--continue" ;;
    --discord) discord=1 ;;
    --skip-permissions) perm_flag="--dangerously-skip-permissions" ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 1 ;;
  esac
done

command -v tmux >/dev/null 2>&1 || { echo "tmux is required" >&2; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required" >&2; exit 1; }

name="$(basename "$project_dir" | sed -E 's/[^A-Za-z0-9_-]+/-/g')"
session="cc-${name}"

env_setup=""
claude_args="$perm_flag"

if [ "$discord" -eq 1 ]; then
  [ -f "$project_dir/.discord/.env" ] || {
    echo "--discord needs $project_dir/.discord/.env (see references/discord.md)" >&2
    exit 1
  }
  env_setup+="export DISCORD_STATE_DIR=$(printf '%q' "$project_dir/.discord"); "
  claude_args+=" --channels plugin:discord@claude-plugins-official"
fi

if [ -f "$project_dir/.gh/hosts.yml" ]; then
  env_setup+="export GH_CONFIG_DIR=$(printf '%q' "$project_dir/.gh"); "
fi

tmux kill-session -t "$session" 2>/dev/null || true

# First start uses --continue only if asked; every automatic restart after
# that resumes the conversation, so a crash or /exit doesn't lose context.
first="claude $continue_flag $claude_args"
again="claude --continue $claude_args"

tmux new-session -d -s "$session" -c "$project_dir" \
  "${env_setup}${first}; while true; do sleep 5; ${again}; done"

echo "Started tmux session '$session' in $project_dir"
echo "  Attach: tmux attach -t $session"
echo "  Stop:   tmux kill-session -t $session"
