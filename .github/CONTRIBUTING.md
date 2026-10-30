# Contributing

arsenal is a small set of tools I actually use with Claude Code. Every change goes through a review gate before it reaches `main`, whoever wrote it, me included. This is what the gate checks.

A review ends in **PASS**, or **BLOCK** with a numbered list of exactly what has to change. A BLOCK isn't a rejection. Fix the list and it gets reviewed again.

## 1. Privacy and safety

This is checked first, and any miss is a BLOCK. The repo is public, and search engines keep copies.

- No secrets: tokens, keys, credentials.
- No internal identifiers: chat or workspace IDs, internal hostnames, paths that reveal private infrastructure.
- No personal details about anyone.
- Files a tool updates on its own (like a skill's `learnings.md`) record how the tool worked, never facts about the person using it.
- Examples are invented or generic, not lifted from real sessions.

## 2. It earns its place

A tool I use, or one I've chosen to publish. Not a speculative or one-off script.

## 3. It works

Someone ran it and saw it behave. "Should work" doesn't pass.

- **Scripts:** `shellcheck` (or `zsh -n` for zsh), plus a dry run where possible.
- **Skills:** the frontmatter is valid (`name`, `description`), and every file the skill references exists.
- **Install steps:** they work from a clean copy.

## 4. It's correct and consistent

- A tool's files don't contradict each other (`SKILL.md`, references, README).
- Anything reworded or renamed is updated everywhere.
- Changes follow the tool's own rules, or say openly why not.
- No placeholders or TODOs left in.

## 5. It's honest

The README describes what the tool actually does, including its limits and anything destructive or permission-sensitive.

## 6. It fits

- Claude Code tools go in `claude/`. Skills go in `claude/skills/<name>/`, each with its own README.
- The root README index has a one-line entry for every tool, and its links resolve.
- Everything is covered by the [LICENSE](../LICENSE).

## Not checked by the gate

A tool's voice and content belong to whoever owns it. The gate covers safety, correctness and fit, not taste.
