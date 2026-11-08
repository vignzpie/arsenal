#!/usr/bin/env bash
# Launcher hook for the unattended module (see references/unattended.md).
# Sourced by launch.sh; the function contract is described in modules/discord.sh.

unattended_vars() { :; }

unattended_check() { :; }

unattended_env() { :; }

unattended_args() { echo "--dangerously-skip-permissions"; }
