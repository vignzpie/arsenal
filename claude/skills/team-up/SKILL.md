---
name: team-up
description: Stand up a new Claude Code project with its own lead agent, end to end. Audits what already exists, asks only what's missing, presents one complete plan for approval, then builds it - project folder, agent definition, CLAUDE.md and a long-running tmux session for the lead, plus optional modules such as a separate GitHub identity or a Discord bot so you can talk to the lead from your phone. Works on existing, half-set-up projects too; it fills gaps and never redoes what's there. Use when the user says "spin up a team", "new project team", "bring up a team for X", "team-up", "start a new project with an agent", or "I need an agent for this repo".
license: Apache-2.0
---

# team-up

You're setting up a project for the user: a folder on disk, a lead agent who owns the project, and a session that keeps that lead running. You build the **infrastructure**. The lead does the **project work**. Don't write the project's code, specs or commits for them. Don't clone their repo unless the user asks you to.

The flow is five phases. Phases 0 and 2 are never skipped. Everything optional is a **module** (below). This file never names a module's details. Each module's reference does.

## Modules

| Module | Turn it on when | Reference |
|---|---|---|
| `github-identity` | The project acts as a different GitHub account from the machine's default `gh` login | `references/github-identity.md` |
| `discord` | The user wants to talk to the lead from Discord | `references/discord.md` |
| `unattended` | The lead should work without stopping at permission prompts | `references/unattended.md` |

Every module reference has the same sections: **Ask, Audit, Plan, Build, Verify, Report, Gotchas**. Read a module's reference as soon as it's on, and run its matching section in each phase. Modules that are off are never read.

## Phase 0: Audit

Before asking anything, check what exists. Report it honestly: ✅ only for things you verified just now, ❌ for missing, ⚠️ for partial.

| Check | How |
|---|---|
| Project folder | `ls -la <projects-root>/<name>` |
| Project `CLAUDE.md` | read it; whose identity does it set? |
| Agent definition | `ls ~/.claude/agents/` and the project's `.claude/agents/` |
| Git state | `.git/` present? remotes? |
| Session | `tmux ls` |
| Modules already set up | a project folder for one (e.g. `.gh/`, `.discord/`) means that module is probably on: read its reference and run its Audit |

If the project is partly set up, say exactly what exists and only fill the gaps.

## Phase 1: Discovery

Ask only what the audit didn't answer. One short round; push for "good enough for v1" over perfect.

**Project.** Name, where projects live on this machine (`<projects-root>`, e.g. `~/projects`), one-line purpose, where the repo is (or will be), and whether the repo lives at the project root or as a subfolder of a wider workspace.

**Lead agent.** Name, role, what they own, model tier (complex judgement → the strongest model; implementation → a mid tier). Default to **one lead**. Add teammates only when the scope is clear; two or three agents is plenty.

**Modules.** Go down the table in one question: which of these does the user want? For each one that's on, read its reference now and run its **Ask** and **Audit**. Run `github-identity`'s before anything else that calls GitHub.

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
├── docs/              ← notes and plans that don't belong in the repo
├── <module folders>   ← only for modules that are on
└── <repo>/            ← cloned by the lead, if the repo is a subfolder

### Repo
<owner>/<repo>   Remote: <url>

### Modules
<module>: <its Plan line>     (or "none")

### Steps I'll run
<only the ones still needed>
```

## Phase 3: Build

Run only the steps that are still needed. Check each one before doing it.

1. **Folder.** `mkdir -p <projects-root>/<name>/docs`.
2. **Agent definition.** Write `~/.claude/agents/<lead>.md`. Use `<project>/.claude/agents/<lead>.md` instead only if the user wants the lead to exist in this project alone. Frontmatter needs `name` and `description`. The body covers identity, what they own, how they work (branch per change, every merge to `main` goes past the user first), how they verify, and an **On session start** checklist. If the lead should clone the repo, put the exact clone and identity commands in the definition.
3. **`CLAUDE.md`.** A few lines in the project folder: who the session is, a pointer to the agent definition, where the repo lives, which GitHub account to use, and which files must never be committed.
4. **Modules.** For each module that's on, run its **Build**.
5. **Launch.** `scripts/launch.sh <project-dir> --module <module> …` (relative to this skill's folder), with one `--module` for each module that's on and has a launcher hook. It starts a tmux session named `cc-<name>` with Claude Code in a restart loop. Run it with `--dry-run` first if you're unsure what it will do. It refuses to touch a session that's already running unless you pass `--replace`.
6. **Get through boot.** Watch `tmux capture-pane -t cc-<name> -p`. The folder-trust prompt defaults to **"No, exit"**. Answer it with `Down` then `Enter`, never a bare `Enter`. Only do this for a folder you just created or the user trusts. Modules may add their own boot prompts (see their Gotchas).
7. **Verify with one turn.** Send the lead a short first instruction with `tmux send-keys -t cc-<name> '<text>' Enter`. If the text sits unsubmitted in the input box, send `Enter` once more. Ask the lead to read their definition and report in. Then run each module's **Verify**.

## Phase 4: Report

```
## <name>: live

✅/❌ Folder: <path>
✅/❌ Lead: <name> (<definition path>)
✅/❌ Session: cc-<name> running
<one line per module, from its Report section>

### Open questions for the lead
<anything they'll need answered>
```

Green-tick only what you checked in this phase.

## Later: restarting a lead

`scripts/launch.sh <project-dir> --continue --replace`, with the same `--module` flags, restarts the session and resumes the lead's last conversation, e.g. after a Claude Code update. Check the pane first (see Gotchas).

## Gotchas

- **The folder-trust prompt defaults to "No, exit".** A bare `Enter` quits the lead's session before it starts. Send `Down`, then `Enter`.
- **Text sent with `tmux send-keys` can sit unsubmitted** in the input box. Read the pane back. If the text is still there, send `Enter` once more.
- **Don't restart a lead mid-task.** If the pane shows `esc to interrupt`, the lead is working. Wait, or ask the user, before passing `--replace`.
- **`--continue` needs a saved conversation.** On a lead that never had one, the pane loops on "No conversation found to continue". Relaunch with `--replace` and without `--continue`.
- **Restarting drops a module if you leave out its flag.** Pass the same `--module` flags every time. The exception is `github-identity`, which turns itself on whenever `<project>/.gh/hosts.yml` exists.

## Rules

- **Audit first, plan before building.** No exceptions.
- **Only ✅ what you verified.** If you can't check it, say so.
- **Skip what exists.** Fill gaps, don't redo.
- **Infrastructure, not project work.** Folders, configs, sessions and bots are yours. Code, specs, clones and commits are the lead's, unless the user says otherwise.
- **Project config lives in the project folder**, not in `~/.claude/`. The agent definition is the one exception.
- **Credentials:** tokens go in files with `chmod 600` and are never echoed into chat or summaries.
- **Keep teams small.** One lead to start.
