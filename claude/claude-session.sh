#!/usr/bin/env zsh

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required (brew install tmux)" >&2
  exit 1
fi

usage() {
  cat <<EOF
Usage:
  $(basename "$0") new [label]     Create a new timestamped session dir, start Claude Code in a tmux session
  $(basename "$0") bounce <name>   Reattach to (if live) or resume (if not) an existing session, by full or partial dir name
EOF
}

# tmux-safe, filesystem-safe: keep alnum/dash/underscore, collapse everything else to a single dash
sanitize() {
  echo "$1" | sed -E 's/[^A-Za-z0-9_-]+/-/g; s/^-+//; s/-+$//'
}

cmd_new() {
  local label="${1:-}"
  if [[ -z "$label" ]]; then
    printf "Session label (leave blank for timestamp only): "
    read -r label
  fi

  local timestamp dir_name
  timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
  dir_name="$timestamp"
  if [[ -n "$label" ]]; then
    dir_name="${timestamp}-$(sanitize "$label")"
  fi

  local new_dir="${BASE_DIR}/${dir_name}"
  mkdir -p "$new_dir"
  echo "Created: $new_dir"

  local tmux_name
  tmux_name="$(sanitize "$dir_name")"

  echo "Starting tmux session '$tmux_name'..."

  # Check if running interactively; if so, exec into tmux (replaces shell)
  # Otherwise, start detached and print the attach command
  if [[ -t 0 ]]; then
    exec tmux new-session -A -s "$tmux_name" "cd '$new_dir' && claude --dangerously-skip-permissions"
  else
    tmux new-session -d -s "$tmux_name" -c "$new_dir" "claude --dangerously-skip-permissions"
    echo "Started detached. Attach with:"
    echo "  tmux attach -t $tmux_name"
  fi
}

cmd_bounce() {
  local term="${1:-}"
  if [[ -z "$term" ]]; then
    echo "Usage: $(basename "$0") bounce <session-name-or-partial>" >&2
    exit 1
  fi

  local -a matches
  for d in "$BASE_DIR"/*"$term"*/; do
    [[ -d "$d" ]] || continue
    matches+=("$(basename "$d")")
  done

  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "No session directory matching '$term' under $BASE_DIR" >&2
    exit 1
  fi

  local chosen
  if [[ ${#matches[@]} -eq 1 ]]; then
    chosen="${matches[1]}"
  else
    echo "Multiple matches for '$term':"
    select m in "${matches[@]}"; do
      [[ -n "$m" ]] && { chosen="$m"; break; }
    done
  fi

  local target_dir="${BASE_DIR}/${chosen}"
  local tmux_name
  tmux_name="$(sanitize "$chosen")"

  echo "Bouncing into '$chosen' (tmux session: $tmux_name)..."

  # Check if running interactively; if so, exec into tmux (replaces shell)
  # Otherwise, start/attach detached and print the attach command
  if [[ -t 0 ]]; then
    exec tmux new-session -A -s "$tmux_name" "cd '$target_dir' && claude --continue --dangerously-skip-permissions"
  else
    tmux new-session -A -d -s "$tmux_name" -c "$target_dir" "claude --continue --dangerously-skip-permissions"
    echo "Started/attached detached. Attach with:"
    echo "  tmux attach -t $tmux_name"
  fi
}

case "${1:-}" in
  new)
    shift
    cmd_new "${1:-}"
    ;;
  bounce)
    shift
    cmd_bounce "${1:-}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
