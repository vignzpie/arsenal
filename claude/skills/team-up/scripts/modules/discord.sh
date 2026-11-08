#!/usr/bin/env bash
# Launcher hook for the discord module (see references/discord.md).
# Sourced by launch.sh. Defines functions only; every hook defines the same four:
#   <module>_vars           env vars this module owns; launch.sh unsets them for every lead
#   <module>_check <dir>    fail (non-zero, message on stderr) if the module isn't set up
#   <module>_env <dir>      shell 'export ...; ' lines for the lead's session
#   <module>_args           extra arguments for claude
# A hook may also define <module>_auto <dir>: succeed to turn the module on without a flag.

discord_vars() { echo DISCORD_STATE_DIR; }

discord_check() {
  [ -f "$1/.discord/.env" ] || {
    echo "The discord module needs $1/.discord/.env with the bot token. Set it up with the skill's references/discord.md, or launch without it." >&2
    return 1
  }
  command -v bun >/dev/null 2>&1 || {
    echo "The discord module needs bun (the Discord plugin runs on it). Install it from https://bun.sh and re-run." >&2
    return 1
  }
}

discord_env() { printf 'export DISCORD_STATE_DIR=%q; ' "$1/.discord"; }

discord_args() { echo "--channels plugin:discord@claude-plugins-official"; }
