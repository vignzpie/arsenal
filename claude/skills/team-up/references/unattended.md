# Module: unattended

Runs the lead with Claude Code's `--dangerously-skip-permissions`, so it runs commands and edits files without stopping to ask. A lead that works while nobody is watching stalls on the first permission prompt without it. It's also risky anywhere the user would mind the lead changing things.

## Ask

Will the lead work unattended? Explain the trade-off in two lines: without this, it stalls on prompts when nobody is watching. With it, nothing stops it from doing something the user wouldn't approve. Let the user choose. Default to off.

## Audit

None. It's a launch flag. Nothing is stored in the project.

## Plan

`unattended: on (permission prompts skipped)`

## Build

Nothing to build. Add a line to the lead's definition saying it runs without permission prompts, so it's careful with anything destructive.

**Launcher:** `--module unattended` adds `--dangerously-skip-permissions`.

## Verify

During the first-turn check, the lead doesn't stop at a permission prompt.

## Report

`✅/❌ Unattended: on`

## Gotchas

- **A warning can appear at boot.** Claude Code may ask you to accept bypass-permissions mode. Its default is "No, exit", and the restart loop then shows it again every few seconds. Read the prompt in the pane. Accept it only if the user chose this module, and never with a bare `Enter`. Once it's accepted, it stays accepted.
- **Only for a folder the user trusts**, on a machine they're fine with it changing.
