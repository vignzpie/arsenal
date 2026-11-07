# team-up

A Claude Code skill that stands up a new project with its own lead agent: a folder, an agent definition, a `CLAUDE.md`, the right GitHub identity, and a long-running tmux session that keeps the lead going. Optionally, the lead gets its own Discord bot, so you can talk to it from your phone.

I use it every time I start a project. It's the setup I kept repeating by hand: audit what's there, ask what's missing, show the plan, then build it and check it works.

## Install

```sh
ln -s "$PWD/claude/skills/team-up" ~/.claude/skills/team-up
```

Then, in Claude Code:

> Spin up a team for my-project. The lead is called Ada.

## How a session goes

1. **Audit.** It checks what already exists (folder, agent, repo, session, bot) and tells you, honestly.
2. **Questions.** Only the ones the audit didn't answer: what the project is, who leads it, which GitHub account it uses, whether you want Discord.
3. **Plan.** One message with everything it's about to do. Nothing is built until you say yes.
4. **Build.** Folder, agent definition, `CLAUDE.md`, GitHub identity, then the session. It gets past the folder-trust prompt and has the lead introduce itself, to prove it's alive.
5. **Report.** What's live, each item checked just now.

It builds the infrastructure only. The lead clones the repo and does the project work.

## Requirements

- Claude Code, `tmux`, and `gh`.
- For Discord: the official Discord channel plugin (`plugin:discord@claude-plugins-official`), [`bun`](https://bun.sh) (the plugin runs on it; `launch.sh --discord` checks for it and stops with a pointer if it is missing), and a bot you create in the Discord Developer Portal. The skill walks you through it.

## Things to know

- **`scripts/launch.sh --skip-permissions`** runs the lead with `--dangerously-skip-permissions`, so it acts without asking. That's useful for a lead that works unattended, and risky anywhere you'd mind it changing things. It's off unless you pass the flag.
- **The session restarts itself.** Claude Code runs in a loop inside tmux. `/exit` in the lead's session restarts it with its conversation intact, which is handy after an update. To stop it for good, kill the tmux session.
- **Relaunching never kills a running lead by surprise.** If a `cc-<name>` tmux session is already running, `launch.sh` refuses and says so. Pass `--replace` to kill it and start a new one. `--dry-run` shows what it would do without changing anything.
- **One bot per project.** Each lead's bot has its own token and allowlist in the project's `.discord/` folder. The allowlist starts with just you.
- **A project can use its own GitHub account.** For example, a personal account for open-source work on a machine that's logged in as a work account. The skill sets up a project-local `gh` login and an SSH host alias, and it verifies both.

## Files

| File | What it's for |
|---|---|
| `SKILL.md` | Instructions for Claude: the four phases and the rules |
| `references/discord.md` | Bot creation, the allowlist, launching with Discord. Only read when Discord is on |
| `scripts/launch.sh` | Starts or restarts a lead's tmux session (`--continue`, `--discord`, `--skip-permissions`, `--replace`, `--dry-run`; see `--help`) |
