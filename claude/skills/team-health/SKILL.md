---
name: team-health
description: Check that a Claude Code team is actually up and able to talk, not just that its tmux session exists. Covers the lead's session (claude running, not stuck at a trust, login or "No conversation found" screen), each member it dispatches to, Discord bots (token, Message Content intent, channel permissions, whether members' allowlists let the lead's bot through), timers, boot persistence, the gh login and disk space. Use after standing up a team, before a lead dispatches work, when the user asks "is the team up", "health check", "why isn't X answering", "team-health", or on a timer that alerts on failure.
license: Apache-2.0
---

# team-health

A team is a long-running Claude Code lead session in tmux, plus whatever it dispatches work to: member sessions, their Discord bots, on-demand agents and timers. This skill runs one script that checks all of it and reports `OK`, `WARN` or `FAIL` per check. It reads; it doesn't fix. Fixing is a separate step the user approves.

## Steps

1. **Find the config.** The script reads `~/.config/team-health/teams.json` (or `$TEAM_HEALTH_CONFIG`). If it's missing, build it with the user: copy `assets/teams.example.json`, then fill in one entry per team from what's on the machine (`tmux ls`, `systemctl --user list-unit-files`, each project's Discord state folder). Read `references/config.md` for every field. Never put a token in the config; it points at the folder that holds the token.
2. **Run it.**

   ```sh
   python3 scripts/team-health.py                 # every team, plus host checks
   python3 scripts/team-health.py --team <name>   # one team, e.g. before dispatching to it
   ```

   It takes about 5–10 seconds per team with a bot, and longer only when a session looks down (it re-checks once after 10 seconds, so a restart loop between runs isn't reported as dead). Add `--json` if you need to parse the result, `--quiet` to see only problems, `--offline` to skip Discord and GitHub.
3. **Read the result.** Exit code 0 means nothing failed, though there may be warnings. 1 means at least one `FAIL`. 2 means bad usage or an unreadable config. `FAIL` means broken now; `WARN` means it will break later or needs a look. Each line says what to do next.
4. **Confirm before calling something dead.** A `FAIL` from the pane alone is a strong signal, not proof. Before telling the user a session or bot is down, look at the pane yourself (`tmux capture-pane -e -p -t <session>`) and, for a bot, at its channel.
5. **Report** to the user: one line per `FAIL` and `WARN`, the fix the script suggests, and nothing about checks that passed beyond a count.

## When another skill or a lead calls it

- **At the end of setting up a team** (e.g. after a team-up run), run it with `--team <name>` and include the result in the setup report. A new team usually shows `WARN boot` until its systemd unit is enabled.
- **A lead before dispatching**: run `--team <own team>`. On a `FAIL` for the member you're about to use, don't dispatch to it; tell the user. Runs without `--alert` don't change what the timer will report.
- **On a timer**, run it with `--quiet --alert`. It posts only new failures, recoveries and a reminder for a failure still open after `repeat_hours`, and stays silent when everything passes. `assets/` has example systemd units; read `references/timer.md` before installing them.

## Gotchas

- **Ghost suggestions aren't typed text.** Claude Code shows a dimmed suggestion after the `❯` prompt. Plain `tmux capture-pane -p` drops the dimming, so it looks like text waiting to be sent. The script captures with `-e` and ignores dim text. Do the same if you look by hand.
- **`--continue` on a lead with no saved conversation** loops forever on "No conversation found to continue". The fix is to relaunch without `--continue`, not to restart again.
- **A Discord bot without Message Content intent exits silently.** No error and no plugin process. The `channels` check catches the missing process; the `discord` check names the cause.
- **Some Discord plugin builds ignore every message from a bot.** Newer builds of the official plugin return early when the author is a bot, before `access.json` is read, so no allowlist lets a lead's bot reach a member's bot. The `hearing` check reads the plugin source each running session uses and fails when it does this. Dispatch by tmux or by subagent instead, or pin a build that lets bots through.
- **"Allowed" isn't the same as "reachable".** With `requireMention` on, a member's bot only hears the lead when the lead sends a real `<@id>` mention (or text matching the member's `mentionPatterns`). Typing "@Name" as plain text mentions nobody. The `hearing` check says which applies.
- **Every session missing at once is one problem**, the tmux server, not N dead sessions. The script reports it once, as `host tmux`, also under `--team`.
- **Timers that exit 0 can still have failed.** A job that logs per-item errors and carries on looks fine to systemd. Give such a timer a `status_file` or `log_file` + `fail_regex` in the config.
- **A healthy check can't see a stalled send path** on its own. The `discord` check's "no reply to the owner's last message" warning is the end-to-end signal; it needs `owner_id` in the config and only judges an idle session.
