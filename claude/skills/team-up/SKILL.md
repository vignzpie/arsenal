---
name: team-up
description: Stand up a new Claude Code project with its own lead agent, end to end. Audits what already exists, asks only what's missing, presents one complete plan for approval, then builds it - project folder, agent definition, CLAUDE.md, GitHub identity, and a long-running tmux session for the lead, with an optional Discord bot so you can talk to the lead from your phone. Works on existing, half-set-up projects too; it fills gaps and never redoes what's there. Use when the user says "spin up a team", "new project team", "bring up a team for X", "team-up", "start a new project with an agent", or "I need an agent for this repo".
license: Apache-2.0
---

# team-up

You're setting up a project for the user: a folder on disk, a lead agent who owns the project, and a session that keeps that lead running. You build the **infrastructure**. The lead does the **project work**. Don't write the project's code, specs or commits for them. Don't clone their repo unless the user asks you to.

The flow is four phases. Phases 0 and 2 are never skipped.

## Phase 0: Audit

Before asking anything, check what exists. Report it honestly: ✅ only for things you verified just now, ❌ for missing, ⚠️ for partial.

| Check | How |
|---|---|
| Project folder | `ls -la <projects-root>/<name>` |
| Project `CLAUDE.md` | read it; whose identity does it set? |
| Agent definition | `ls ~/.claude/agents/` and the project's `.claude/agents/` |
| Repo | `gh repo view <owner>/<repo>` **as the account the project will use** (see Phase 1) |
| Git state | `.git/` present? remotes? |
| Discord (if used) | `<project>/.discord/` present? `.env` present? (never print it) |
| Session | `tmux ls` |

If the project is partly set up, say exactly what exists and only fill the gaps.

## Phase 1: Discovery

Ask only what the audit didn't answer. One short round; push for "good enough for v1" over perfect.

**Project.** Name, where projects live on this machine (`<projects-root>`, e.g. `~/projects`), one-line purpose, where the repo is (or will be), and whether the repo lives at the project root or as a subfolder of a wider workspace.

**Lead agent.** Name, role, what they own, model tier (complex judgement → the strongest model; implementation → a mid tier). Default to **one lead**. Add teammates only when the scope is clear; two or three agents is plenty.

**GitHub identity.** Which account does this project act as? If it differs from the machine's default `gh` login, the project gets its own (see Phase 3, step 4). Get this right before any audit call that hits GitHub, or a private repo will look like it doesn't exist.

**Discord.** Does the user want to talk to the lead from Discord? If yes, read `references/discord.md` now and follow it. If no, skip every Discord step.

**Permissions.** Will the lead run unattended? Unattended sessions stall on permission prompts. Explain the trade-off and let the user choose (see `scripts/launch.sh --skip-permissions`).

## Phase 2: Plan

Present the whole plan in **one** message, then ask "Does this look right? Any changes before I build it?" Don't ask for tokens or credentials until the plan is approved.

```
## <name>

### Audit
<✅ / ❌ / ⚠️ per item>

### Lead
<name> - <role> - <model>
Owns: <...>

### Layout
<projects-root>/<name>/
├── CLAUDE.md          ← points the session at the lead's definition
├── .gh/               ← only if the project uses its own GitHub account
├── .discord/          ← only if Discord is on
├── docs/              ← notes and plans that don't belong in the repo
└── <repo>/            ← cloned by the lead, if the repo is a subfolder

### GitHub
Account: <login>   Remote: <ssh url>

### Discord
<off> | <bot name, channel, who's allowed>

### Steps I'll run
<only the ones still needed>
```

## Phase 3: Build

Run only the steps that are still needed. Check each one before doing it.

1. **Folder.** `mkdir -p <projects-root>/<name>/docs`.
2. **Agent definition.** Write `~/.claude/agents/<lead>.md` (reusable across projects) or `<project>/.claude/agents/<lead>.md` (this project only). Frontmatter needs `name` and `description`. The body covers identity, what they own, how they work (branch per change, every merge to `main` goes past the user first), how they verify, and an **On session start** checklist. If the lead should clone the repo, put the exact clone and identity commands in the definition.
3. **`CLAUDE.md`.** A few lines in the project folder: who the session is, a pointer to the agent definition, where the repo lives, which GitHub account to use, and which files must never be committed.
4. **GitHub identity (only if it differs from the default).**
   - Log a separate `gh` into the project: `GH_CONFIG_DIR=<project>/.gh gh auth login`. The launcher exports `GH_CONFIG_DIR` when `.gh/hosts.yml` exists.
   - Add an SSH host alias so git pushes as that account, e.g. `Host github-<name>` with that account's key. Use `git@github-<name>:<owner>/<repo>.git` as the remote.
   - Verify both: `GH_CONFIG_DIR=<project>/.gh gh api user -q .login` and `ssh -T git@github-<name>`.
   - Give the lead the repo-local commit identity to set (`git config user.name` / `user.email`, e.g. the account's noreply address).
5. **Discord (only if on).** Follow `references/discord.md`.
6. **Launch.** `scripts/launch.sh <project-dir>` (relative to this skill's folder). It starts a tmux session named `cc-<name>` with Claude Code in a restart loop. Add `--discord` when Discord is on.
7. **Get through boot.** Watch `tmux capture-pane -t cc-<name> -p`. The folder-trust prompt defaults to **"No, exit"**. Answer it with `Down` then `Enter`, never a bare `Enter`. Only do this for a folder you just created or the user trusts.
8. **Verify with one turn.** Send the lead a short first instruction with `tmux send-keys -t cc-<name> '<text>' Enter`. If the text sits unsubmitted in the input box, send `Enter` once more. Ask the lead to read their definition and report in, on Discord if it's on. Confirm the reply actually arrived.

## Phase 4: Report

```
## <name>: live

✅/❌ Folder: <path>
✅/❌ Lead: <name> (<definition path>)
✅/❌ GitHub: <login> (verified just now)
✅/❌ Discord: <bot> in <channel>, replied   (or "off")
✅/❌ Session: cc-<name> running

### Open questions for the lead
<anything they'll need answered>
```

Green-tick only what you checked in this phase.

## Later: restarting a lead

- `scripts/launch.sh <project-dir> --continue` restarts the session and resumes the lead's last conversation, e.g. after a Claude Code update.
- If the pane loops on "No conversation found to continue", the lead never had a saved conversation. Relaunch without `--continue`.
- Before restarting, check the pane isn't mid-task (`esc to interrupt` visible).

## Rules

- **Audit first, plan before building.** No exceptions.
- **Only ✅ what you verified.** If you can't check it, say so.
- **Skip what exists.** Fill gaps, don't redo.
- **Infrastructure, not project work.** Folders, configs, sessions and bots are yours. Code, specs, clones and commits are the lead's, unless the user says otherwise.
- **Project config lives in the project folder**, not in `~/.claude/`. The agent definition is the one exception.
- **Credentials:** tokens go in files with `chmod 600` and are never echoed into chat or summaries.
- **Keep teams small.** One lead to start.
