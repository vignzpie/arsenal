# team-health

A Claude Code skill and script that check whether a team of long-running Claude Code sessions is actually up and able to talk. A team is a lead session in tmux plus whatever it dispatches to: member sessions, their Discord bots, on-demand agents and timers.

"The tmux session exists" isn't the same as "the team works". A lead can look alive while every member it sends work to is down, or while its members' bots silently drop its messages. This checks the things that broke for real, says which one, and suggests the next step.

It pairs with [`team-up`](../team-up/): run it as the last step of standing up a team, have a lead run it before dispatching work, or put it on a timer that stays quiet unless something fails.

## Install

```sh
ln -s "$PWD/claude/skills/team-health" ~/.claude/skills/team-health
mkdir -p ~/.config/team-health
cp claude/skills/team-health/assets/teams.example.json ~/.config/team-health/teams.json
```

Edit `teams.json` to describe your teams (every field is in [`references/config.md`](references/config.md)), or ask Claude:

> Run a team-health check.

and it will help build the config from what's running.

## What it checks

| Check | FAIL | WARN |
|---|---|---|
| `session` | tmux session or window missing; `claude` not running (checked twice, 10s apart); stuck on the folder-trust dialog, a login screen or a "No conversation found to continue" loop | |
| `pane` | | usage-limit banner; a permission prompt waiting; typed text left unsubmitted since the last run (dimmed suggestions are ignored) |
| `channels` | Discord plugin process missing under a session that runs it | |
| `rc` | | not running with Remote Control when the config says it should |
| `discord` | token rejected; Message Content intent off; bot can't view, send or read history in its channel | the owner's last message got no reply or reaction while the session sat idle |
| `hearing` | a member's bot would drop messages from the lead's bot in their shared channel, or the other way round | |
| `agent` | an on-demand agent's definition is missing or lacks `name`/`description` | |
| `timer` | timer inactive; last run failed; status file stale or reporting failures; new log lines matching a failure pattern | timer not enabled |
| `boot` | | no boot unit, unit not enabled, or the boot path drops Remote Control |
| `gh` | logged in as the wrong account, or not at all | GitHub unreachable; repo has no local commit email |
| `host` | tmux server down; disk below half the threshold | disk below the threshold |

Exit code: 0 nothing failed, 1 at least one FAIL, 2 bad usage or config. `--json` for machine-readable output. `--help` for every option.

## Things to know

- **Read-only by default.** It reads tmux panes (`tmux capture-pane`), the process list, systemd state and local files, and sends `GET` requests to the Discord API with each team's bot token and to the GitHub API with `gh`. `--offline` skips the network calls.
- **`--alert` writes.** It posts to the Discord channel in the config's `alert` section, using the token file named there or, if that bot can't post, another team bot that checked out. It also runs the config's `on_fail_cmd`, if you set one. `--alert-dry-run` prints what it would post and run, and changes nothing.
- **It never fixes anything.** No restarts, no messages to sessions, no config edits. Acting on the result is up to you, or to whatever you hook into `on_fail_cmd`.
- **Tokens stay in their files.** The config names the folder or file holding a token, never the token, and the script never prints one.
- **It keeps state** in `~/.local/state/team-health/` (or `$TEAM_HEALTH_STATE`): which alerts were already sent, a 24-hour cache of each bot's intent setting, log offsets, and `last.json` with the latest full result.
- **It can't see everything.** A Discord send path that reports success but delivers nothing only shows up indirectly, as an unanswered owner message. In-process teammates inside a lead's session are covered only by the lead's own checks.

## Running it on a timer

`assets/team-health.service` and `assets/team-health.timer` run it every 30 minutes. [`references/timer.md`](references/timer.md) has the install steps. With `--alert` it posts only new failures and recoveries, repeats a still-open failure every `repeat_hours`, holds posts during `quiet_hours`, and sends warnings once a day as a digest.

## Requirements

- Python 3.9 or newer, standard library only.
- `tmux` and `ps`. `systemctl --user` for the timer and boot checks, `gh` for the GitHub check. A check whose tool is missing reports a warning rather than crashing.
- For Discord checks: teams using the official Discord channel plugin, one state folder per bot (`.env` + `access.json`), as `team-up`'s `discord` module sets up.

## Files

| File | What it's for |
|---|---|
| `SKILL.md` | Instructions for Claude: when to run it and how to read the result |
| `scripts/team-health.py` | The check itself (`--help`) |
| `references/config.md` | Every config field |
| `references/timer.md` | Installing the systemd timer |
| `assets/teams.example.json` | Example config with invented teams |
| `assets/team-health.service`, `assets/team-health.timer` | Example systemd user units |
