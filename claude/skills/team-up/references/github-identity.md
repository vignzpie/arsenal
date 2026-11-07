# Module: github-identity

Gives the project its own GitHub account, separate from the machine's default `gh` login. For example, a personal account for open-source work on a machine that's logged in as a work account.

## Ask

Which account does this project act as? If it's the machine's default `gh` login, this module stays off.

## Audit

Run these first, before any other audit call that hits GitHub.

- `<project>/.gh/hosts.yml` present?
- `GH_CONFIG_DIR=<project>/.gh gh api user -q .login` prints the right account?
- `ssh -T git@github-<name>` greets the right account?
- `GH_CONFIG_DIR=<project>/.gh gh repo view <owner>/<repo>`: does the repo exist, as that account?

## Plan

`github-identity: <login> via <project>/.gh, remote git@github-<name>:<owner>/<repo>.git`

## Build

1. Log a separate `gh` into the project: `GH_CONFIG_DIR=<project>/.gh gh auth login`.
2. Add an SSH host alias so git pushes as that account, e.g. `Host github-<name>` with that account's key. Use `git@github-<name>:<owner>/<repo>.git` as the remote.
3. Give the lead the repo-local commit identity to set (`git config user.name` / `user.email`, e.g. the account's noreply address). Put it in the lead's definition.
4. Add `.gh/` to the files `CLAUDE.md` says must never be committed.

**Launcher:** `--module github-identity` points `GH_CONFIG_DIR` at `<project>/.gh`. It turns itself on whenever `<project>/.gh/hosts.yml` exists, so you don't need to pass it.

## Verify

Both must print the project's account, checked just now: `GH_CONFIG_DIR=<project>/.gh gh api user -q .login` and `ssh -T git@github-<name>`.

## Report

`✅/❌ GitHub: <login> (verified just now)`

## Gotchas

- **Audit as the project's account, not the default one.** With the machine's default `gh` login, a private repo looks like it doesn't exist, and the audit reports ❌ for something that's there.
- **`ssh -T` exits 1 even when it works.** GitHub greets you by name and closes. Read the greeting, not the exit code.
