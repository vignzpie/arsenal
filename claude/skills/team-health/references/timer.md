# Running on a timer

`assets/team-health.service` and `assets/team-health.timer` run the check every 30 minutes as a systemd user service, with `--quiet --alert`. It stays silent while everything passes.

## Install

Ask the user before installing. It runs every 30 minutes and posts to Discord.

1. Check that `alert.token_file` and `alert.channel_id` are set in the config, and that a manual run with `--alert-dry-run` prints what you'd expect.
2. Copy both files to `~/.config/systemd/user/`. Change `ExecStart` if the skill isn't at `~/.claude/skills/team-health/`. Add the folder `gh` is installed in to `Environment=PATH=` if it isn't already listed (`command -v gh`).
3. `systemctl --user daemon-reload && systemctl --user enable --now team-health.timer`
4. If the machine should run it while nobody is logged in: `loginctl enable-linger "$USER"`.

## Check it

- `systemctl --user list-timers team-health.timer` shows the next run.
- After a run: `journalctl --user -u team-health.service -n 20` and `~/.local/state/team-health/last.json`.

## Gotchas

- **systemd's PATH is short.** A job that works in your shell can fail under systemd because `gh` or `tmux` isn't found. The unit sets `PATH`. Extend it rather than relying on your shell profile.
- **Exit code 1 is a finding, not a crash.** The unit lists it in `SuccessExitStatus` so a failing check doesn't mark the unit failed. Exit code 2 (bad config) still does.
- **The first `--alert` run posts every open FAIL**, because nothing has been sent yet. After that it only posts changes.
