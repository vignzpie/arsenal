# team-up

A Claude Code skill that stands up a new project with its own lead agent: a folder, an agent definition, a `CLAUDE.md`, and a long-running tmux session that keeps the lead going. Optional modules add a separate GitHub identity, a Discord bot so you can talk to the lead from your phone, or unattended mode.

I use it every time I start a project. It's the setup I kept repeating by hand: audit what's there, ask what's missing, show the plan, then build it and check it works.

## Install

```sh
ln -s "$PWD/claude/skills/team-up" ~/.claude/skills/team-up
```

Then, in Claude Code:

> Spin up a team for my-project. The lead is called Ada.

## How a session goes

1. **Audit.** It checks what already exists (folder, agent, repo, session, any modules) and tells you, honestly.
2. **Questions.** Only the ones the audit didn't answer: what the project is, who leads it, and which modules you want.
3. **Plan.** One message with everything it's about to do. Nothing is built until you say yes.
4. **Build.** Folder, agent definition, `CLAUDE.md`, each module, then the session. It gets past the folder-trust prompt and has the lead introduce itself, to prove it's alive.
5. **Report.** What's live, each item checked just now.

It builds the infrastructure only. The lead clones the repo and does the project work.

## Modules

Anything optional is a module. Turn on only what you need, and the skill never reads the rest.

| Module | What it adds |
|---|---|
| `github-identity` | The project acts as its own GitHub account, e.g. a personal account for open-source work on a machine logged in as a work account. A project-local `gh` login and an SSH host alias, both verified. |
| `discord` | A Discord bot per project, so you can talk to the lead from your phone. Its own token and allowlist live in the project's `.discord/` folder, and the allowlist starts with just you. |
| `unattended` | The lead runs with `--dangerously-skip-permissions`, so it works without stopping to ask. Useful when nobody is watching, risky anywhere you'd mind it changing things. Off by default. |

**Adding a module** (e.g. Slack) doesn't change the core flow:

1. `references/<module>.md` with the same sections as the others: Ask, Audit, Plan, Build, Verify, Report, Gotchas.
2. If it changes how the lead is launched, `scripts/modules/<module>.sh` defines four functions: `<module>_vars`, `_check`, `_env` and `_args`, plus an optional `_auto` to turn itself on. The contract is at the top of `scripts/modules/discord.sh`. `launch.sh --module <module>` picks it up.
3. A row in the Modules table in `SKILL.md`.

## Requirements

- Claude Code, `tmux`, and `gh`.
- For `discord`: the official Discord channel plugin (`plugin:discord@claude-plugins-official`), [`bun`](https://bun.sh) (the plugin runs on it, and the launcher checks for it), and a bot you create in the Discord Developer Portal. The skill walks you through it.

## Things to know

- **`unattended` skips permission prompts.** See the Modules table. It's off unless you turn it on (`--module unattended`, or the older `--skip-permissions`).
- **The session restarts itself.** Claude Code runs in a loop inside tmux. `/exit` in the lead's session restarts it with its conversation intact, which is handy after an update. To stop it for good, kill the tmux session.
- **Relaunching never kills a running lead by surprise.** If a `cc-<name>` tmux session is already running, `launch.sh` refuses and says so. Pass `--replace` to kill it and start a new one. `--dry-run` shows what it would do without changing anything.
- **Each lead starts with a clean environment.** The launcher unsets the GitHub settings (`GH_CONFIG_DIR`, `GH_TOKEN`, `GITHUB_TOKEN`, `GH_HOST`) and the Discord setting (`DISCORD_STATE_DIR`) before turning modules on. A lead doesn't inherit the account or bot of the shell that launched it.

## Files

| File | What it's for |
|---|---|
| `SKILL.md` | Instructions for Claude: the phases, the modules table and the rules |
| `references/<module>.md` | One per module. Only read when that module is on |
| `scripts/launch.sh` | Starts or restarts a lead's tmux session (`--module`, `--continue`, `--replace`, `--dry-run`; see `--help`) |
| `scripts/modules/<module>.sh` | Launcher hooks for the modules that change how the lead starts |
