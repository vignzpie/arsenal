#!/usr/bin/env bash
# Start (or restart) a project lead's Claude Code session in tmux.
# Session name: cc-<folder name>. Claude Code runs in a restart loop, so the
# session survives crashes and `/exit` restarts it (e.g. to apply an update).
# Optional behaviour comes from module hooks in modules/<name>.sh next to this file.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
available=()
for hook in "$here"/modules/*.sh; do
  [ -f "$hook" ] || continue
  # shellcheck source=/dev/null
  . "$hook"
  m="$(basename "$hook" .sh)"
  for part in vars check env args; do
    declare -F "${m//-/_}_$part" >/dev/null || { echo "Module hook $hook doesn't define ${m//-/_}_$part. Every hook needs _vars, _check, _env and _args (see modules/discord.sh)." >&2; exit 1; }
  done
  available+=("$m")
done

usage() {
  cat <<EOF
Usage: $(basename "$0") <project-dir> [--module <name>]... [--continue] [--replace] [--dry-run]

  --module <name>     Turn on a module. Repeat for more than one. Available:
                      ${available[*]:-none}
                      Each is described in the skill's references/<name>.md.
  --continue          Resume the lead's last conversation instead of starting fresh.
  --replace           If a cc-<name> session is already running, kill it and start
                      a new one. Without this, the script refuses and leaves it alone.
  --dry-run           Print the tmux command it would run, and whether it would
                      replace a running session. Changes nothing.
  --discord           Same as --module discord.
  --skip-permissions  Same as --module unattended: the lead runs commands and edits
                      files without asking. Only for a folder you trust.

github-identity turns itself on when <project-dir>/.gh/hosts.yml exists.
Every env var a module owns (GitHub: GH_CONFIG_DIR, GH_TOKEN, GITHUB_TOKEN, GH_HOST;
Discord: DISCORD_STATE_DIR) is unset for the lead before modules are turned on.

Use -- before a folder whose name starts with a dash.

Exit codes: 0 started (or dry run), 1 a check failed, 2 bad usage.
EOF
}

is_available() { local m; for m in ${available[@]+"${available[@]}"}; do [ "$m" = "$1" ] && return 0; done; return 1; }

dir_arg=""
continue_flag=""
replace=0
dry_run=0
modules=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --module)
      [ $# -ge 2 ] || { echo "--module needs a name, e.g. --module discord. Try --help." >&2; exit 2; }
      is_available "$2" || { echo "Unknown module: $2. Available: ${available[*]:-none}." >&2; exit 2; }
      modules+=("$2"); shift ;;
    --discord) modules+=(discord) ;;
    --skip-permissions) modules+=(unattended) ;;
    --continue) continue_flag="--continue" ;;
    --replace) replace=1 ;;
    --dry-run) dry_run=1 ;;
    --) [ $# -ge 2 ] || { echo "-- needs a <project-dir> after it." >&2; exit 2; }
        [ -z "$dir_arg" ] || { echo "Only one <project-dir>, please (got '$dir_arg' and '$2'). Try --help." >&2; exit 2; }
        dir_arg="$2"; shift ;;
    -*) echo "Unknown option: $1. Try --help." >&2; exit 2 ;;
    *) [ -z "$dir_arg" ] || { echo "Only one <project-dir>, please (got '$dir_arg' and '$1'). Try --help." >&2; exit 2; }
       dir_arg="$1" ;;
  esac
  shift
done

[ -n "$dir_arg" ] || { usage >&2; exit 2; }
[ -d "$dir_arg" ] || { echo "No such folder: $dir_arg. Create the project folder first, or check the path." >&2; exit 1; }
project_dir="$(cd -- "$dir_arg" && pwd)"

command -v tmux >/dev/null 2>&1 || { echo "tmux is required. Install it (e.g. 'sudo apt install tmux' or 'brew install tmux') and re-run." >&2; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude (Claude Code) is required and isn't on PATH. Install it, or open a shell where 'claude' runs, and re-run." >&2; exit 1; }

name="$(basename -- "$project_dir" | sed -E 's/[^A-Za-z0-9_-]+/-/g')"
session="cc-${name}"

# Modules that turn themselves on (github-identity when .gh/hosts.yml exists).
for m in ${available[@]+"${available[@]}"}; do
  fn="${m//-/_}"
  if declare -F "${fn}_auto" >/dev/null && "${fn}_auto" "$project_dir"; then modules+=("$m"); fi
done

# Start clean: unset every var any module owns, so a new tmux server can't pass
# on the caller's settings. Then each module that's on sets its own.
owned=""
for m in ${available[@]+"${available[@]}"}; do
  v="$("${m//-/_}_vars")"
  [ -z "$v" ] || owned+="${owned:+ }$v"
done
env_setup=""
[ -z "$owned" ] || env_setup="unset $owned; "

claude_args=""
on=""
for m in ${modules[@]+"${modules[@]}"}; do
  case " $on " in *" $m "*) continue ;; esac
  on+="${on:+ }$m"
  fn="${m//-/_}"
  "${fn}_check" "$project_dir" || exit 1
  env_setup+="$("${fn}_env" "$project_dir")"
  args="$("${fn}_args")"
  [ -z "$args" ] || claude_args+=" $args"
done

# First start uses --continue only if asked; every automatic restart after
# that resumes the conversation, so a crash or /exit doesn't lose context.
first="claude${continue_flag:+ $continue_flag}${claude_args}"
again="claude --continue${claude_args}"
cmd="${env_setup}${first}; while true; do sleep 5; ${again}; done"

running=0
tmux has-session -t "=$session" 2>/dev/null && running=1

if [ "$dry_run" -eq 1 ]; then
  if [ "$running" -eq 1 ]; then
    if [ "$replace" -eq 1 ]; then echo "Would kill the running session '$session' (--replace)."
    else echo "Would refuse: '$session' is already running. Pass --replace to restart it."; exit 0; fi
  fi
  echo "Modules on: ${on:-none}"
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

echo "Started tmux session '$session' in $project_dir (modules: ${on:-none})"
echo "  Attach: tmux attach -t $session"
echo "  Stop:   tmux kill-session -t $session"
