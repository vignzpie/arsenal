#!/usr/bin/env bash
# Launcher hook for the github-identity module (see references/github-identity.md).
# Sourced by launch.sh; the function contract is described in modules/discord.sh.

# GH_TOKEN and GITHUB_TOKEN take priority over hosts.yml in gh, so they're cleared too.
github_identity_vars() { echo GH_CONFIG_DIR GH_TOKEN GITHUB_TOKEN GH_HOST; }

github_identity_auto() { [ -f "$1/.gh/hosts.yml" ]; }

github_identity_check() {
  [ -f "$1/.gh/hosts.yml" ] || {
    echo "The github-identity module needs a project login. Run: GH_CONFIG_DIR=$1/.gh gh auth login" >&2
    return 1
  }
}

github_identity_env() { printf 'export GH_CONFIG_DIR=%q; ' "$1/.gh"; }

github_identity_args() { :; }
