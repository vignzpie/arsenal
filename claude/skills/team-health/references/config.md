# teams.json

The script reads `~/.config/team-health/teams.json`, or `$TEAM_HEALTH_CONFIG`, or `--config <path>`. `assets/teams.example.json` is a complete example. Paths may use `~` and `$VARS`. A check runs only when the config gives it something to check, so a team with nothing but a `name` and a `session` gets the session checks, plus a `boot` WARN until you set `boot_unit` or `boot_optional: true`.

The config never holds a token. It points at the files that do.

## Top level

| Field | Meaning |
|---|---|
| `owner_id` | Your Discord user ID. Turns on the "did the bot answer the owner's last message" check. |
| `disk` | List of `{ "path", "min_free_pct" }`. WARN below `min_free_pct`, FAIL below half of it. Default: `/` at 10%. |
| `alert` | Where `--alert` posts. See below. |
| `teams` | List of teams. |

## A team

| Field | Meaning |
|---|---|
| `name` | Required. Used in output and with `--team`. |
| `session` | The lead's tmux session. `window` picks a window (name or index) when the session has several. |
| `remote_control` | `true` if the lead should run with `--remote-control`. WARN if it doesn't, or if its boot unit won't restore it. |
| `boot_unit` | The systemd user unit that starts the session at boot. WARN if it's missing or not enabled. If the unit's `ExecStart` doesn't pass `--rc`/`--remote-control` but the launcher it calls adds it, set `boot_restores_rc: true`. A team that's meant to stay down after a reboot sets `boot_optional: true`. |
| `discord` | The lead's bot, see below. |
| `gh` | `{ "config_dir", "login" }`: `GH_CONFIG_DIR` for this team and the account it must be logged in as (without `login`, any logged-in account passes). Add `"repo"` and `"require_commit_email": true` to WARN when that repo has no local `user.email` (commits would fall back to the global identity). |
| `members` | What the lead dispatches to, see below. |

## `discord`

| Field | Meaning |
|---|---|
| `state_dir` | The bot's Discord plugin state folder: `.env` with `DISCORD_BOT_TOKEN=…`, and `access.json`. The same folder the session's `DISCORD_STATE_DIR` points at. |
| `channel` | The team's channel ID. Checked for view, send and read-history permission, and used for the hearing check. |
| `reply_window_min` | How long the owner's latest message to this bot may go unanswered before a WARN. Default 20. Only judged while the pane is idle. |
| `require_mention` | Set `true` if this bot only answers when mentioned; then only messages that mention it are judged. |

Which owner message is judged, newest first: one that mentions this bot (only this bot's reply or reaction answers it); otherwise one that mentions nobody (a reply from any bot answers it, so a channel shared with other bots doesn't raise false alarms). A message that mentions only some other bot or person is skipped.

## `members`

Each member has a `name` and a `kind`.

| `kind` | Fields | Checks |
|---|---|---|
| `session` | `session`, optional `window`, `remote_control`, `discord` | The same session, pane, plugin and bot checks as a lead. With `discord`, also **hearing** both ways: the member's `access.json` lets the lead's bot through in the shared channel, and the lead's lets the member's bot through, and the listening session's plugin build doesn't drop bot messages outright. |
| `agent` | `file` | A subagent the lead spawns on demand. Nothing runs between uses, so the check is that the definition exists and its frontmatter has `name` and `description`. |
| `timer` | `unit` (the `.timer`), `max_age_min`, optional `status_file`, `log_file` + `fail_regex`, `oneshot` | Timer active and enabled. Then either the `status_file` (below) or the job's last `Result` plus a last run within `max_age_min` (default 120). `log_file` + `fail_regex` counts matching lines added since the last `--alert` run, so a manual run shows them without using them up. `oneshot: true` skips a timer that disables itself after firing. |

In-process teammates that live inside the lead's own session aren't listed. They're covered by the lead's checks.

### `status_file`

For a job that exits 0 even when items inside it failed. The job writes JSON after each run:

```json
{ "last_run": "2030-01-01T08:00:00Z", "ok": true, "failures": 0 }
```

`last_run` is ISO 8601 or Unix seconds. FAIL when it's older than `max_age_min`, `ok` is `false`, or `failures` is above 0.

## `alert`

Used only with `--alert`.

| Field | Meaning |
|---|---|
| `token_file` | File holding the alert bot's token, either as `DISCORD_BOT_TOKEN=…` or alone. A bot's `.env` works. |
| `channel_id` | Where alerts go. One message per run, never one per team. |
| `fallback` | Default `true`. If the alert bot can't post, try each team bot whose token checked out this run. |
| `repeat_hours` | Re-post a FAIL that's still open after this long. Default 12. |
| `quiet_hours` | `"HH:MM-HH:MM"`. Posts are held and sent together at the first run after it ends. |
| `timezone` | IANA name for `quiet_hours` and `digest_hour`, e.g. `Europe/Berlin`. Default: the machine's. |
| `digest_hour` | WARNs never post on their own. Once a day, at the first run after this hour, any open WARNs go out in one message. Default 8. |
| `on_fail_cmd` | A command (list of arguments, or a string run with `sh -c`) run whenever there are new FAILs or recoveries, quiet hours or not, with the lines on stdin. Use it to hand failures to something that acts on them. |

What counts as already sent is kept in the state folder (`~/.local/state/team-health/`, or `$TEAM_HEALTH_STATE`), together with a 24-hour cache of each bot's intent flags (only once they show the intent on) and `last.json`, the latest full result.
