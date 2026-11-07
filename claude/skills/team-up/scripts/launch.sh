#!/usr/bin/env bash
# Start (or restart) a project lead's Claude Code session in tmux.
# Session name: cc-<folder name>. Claude Code runs in a restart loop, so the
# session survives crashes and `/exit` restarts it (e.g. to apply an update).

set -euo pipefail

usage() {
  cat <<EOF2
Usage: $(basename "$0") <project-dir> [--continue] [--discord] [--skip-permissions] [--replace] [--dry-run]

  --continue          Resume the lead's last conversation instead of starting fresh.
  --discord           Connect the Discord channel plugin, using <project-dir>/.discord
                      as the bot's state folder (token, allowlist).
  --skip-permissions  Run Claude Code with --dangerously-skip-permissions. The lead
                      will run commands and edit files without asking. Only use
                      this for a folder you trust, on a machine you're fine with
                      it changing.
  --replace           If a cc-<name> session is already running, kill it and start
                      a new one. Without this, the script refuses and leaves it alone.
  --dry-run           Print the tmux command it would run, and whether it would
                      replace a running session. Changes nothing.

If <project-dir>/.gh/hosts.yml exists, GH_CONFIG_DIR points at it, so gh acts as
the project's own GitHub account. Otherwise GH_CONFIG_DIR and DISCORD_STATE_DIR
are unset, so the lead never inherits the caller's account or bot.

Exit codes: 0 started (or dry run), 1 a check failed, 2 bad usage.
EOF2
}

dir_arg=""
continue_flag=""
discord=0
perm_flag=""
replace=0
dry_run=0
for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --continue) continue_flag="--continue" ;;
    --discord) discord=1 ;;
    --skip-permissions) perm_flag="--dangerously-skip-permissions" ;;
    --replace) replace=1 ;;
    --dry-run) dry_run=1 ;;
    -*) echo "Unknown option: $arg. Try --help." >&2; exit 2 ;;
    *) [ -z "$dir_arg" ] || { echo "Only one <project-dir>, please (got '$dir_arg' and '$arg'). Try --help." >&2; exit 2; }
       dir_arg="$arg" ;;
  esac
done

[ -n "$dir_arg" ] || { usage >&2; exit 2; }
[ -d "$dir_arg" ] || { echo "No such folder: $dir_arg. Create the project folder first, or check the path." >&2; exit 1; }
project_dir="$(cd "$dir_arg" && pwd)"

command -v tmux >/dev/null 2>&1 || { echo "tmux is required. Install it (e.g. 'sudo apt install tmux' or 'brew install tmux') and re-run." >&2; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required and isn't on PATH. Install it, or open a shell where 'claude' runs, and re-run." >&2; exit 1; }

name="$(basename "$project_dir" | sed -E 's/[^A-Za-z0-9_-]+/-/g')"
session="cc-${name}"

# Start clean: a new tmux server would otherwise pass on the caller's GitHub
# and Discord settings, and the lead would act as the wrong account or bot.
env_setup="unset GH_CONFIG_DIR DISCORD_STATE_DIR; "
claude_args="$perm_flag"

if [ "$discord" -eq 1 ]; then
  [ -f "$project_dir/.discord/.env" ] || {
    echo "--discord needs $project_dir/.discord/.env with the bot token. Set it up with the skill's references/discord.md, or launch without --discord." >&2
    exit 1
  }
  command -v bun >/dev/null 2>&1 || {
    echo "--discord needs bun (the Discord plugin runs on it). Install it from https://bun.sh and re-run." >&2
    exit 1
  }
  env_setup+="export DISCORD_STATE_DIR=$(printf '%q' "$project_dir/.discord"); "
  claude_args+=" --channels plugin:discord@claude-plugins-official"
fi

if [ -f "$project_dir/.gh/hosts.yml" ]; then
  env_setup+="export GH_CONFIG_DIR=$(printf '%q' "$project_dir/.gh"); "
fi

# First start uses --continue only if asked; every automatic restart after
# that resumes the conversation, so a crash or /exit doesn't lose context.
first="claude $continue_flag $claude_args"
again="claude --continue $claude_args"
cmd="${env_setup}${first}; while true; do sleep 5; ${again}; done"

running=0
tmux has-session -t "=$session" 2>/dev/null && running=1

if [ "$dry_run" -eq 1 ]; then
  if [ "$running" -eq 1 ]; then
    if [ "$replace" -eq 1 ]; then echo "Would kill the running session '$session' (--replace)."
    else echo "Would refuse: '$session' is already running. Pass --replace to restart it."; exit 0; fi
  fi
  echo "Would run, in $project_dir:"
  echo "  tmux new-session -d -s $session -c $(printf '%q' "$project_dir") \"$cmd\""
  exit 0
fi

if [ "$running" -eq 1 ]; then
  if [ "$replace" -eq 0 ]; then
    echo "Session '$session' is already running. Check it isn't mid-task (tmux capture-pane -t $session -p), then re-run with --replace to restart it." >&2
    exit 1
  fi
  tmux kill-session -t "=$session" 2>/dev/null || true
fi

tmux new-session -d -s "$session" -c "$project_dir" "$cmd"

echo "Started tmux session '$session' in $project_dir"
echo "  Attach: tmux attach -t $session"
echo "  Stop:   tmux kill-session -t $session"
