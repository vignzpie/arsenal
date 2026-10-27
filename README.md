# arsenal

Small tools I actually use with Claude Code.

## What's here

| Tool | What it does |
|---|---|
| [`claude/claude-session.sh`](claude/claude-session.sh) | Starts Claude Code in a fresh timestamped folder inside tmux (`new [label]`), or reattaches to or resumes one (`bounce <name>`). |
| [`claude/skills/now-interview/`](claude/skills/now-interview/) | A skill that interviews you, one question at a time, and drafts your [/now page](https://sive.rs/now). It learns your direction from links you give it and gets better with each run. |

## now-interview

Install it by copying or symlinking the folder into your skills directory:

```sh
ln -s "$PWD/claude/skills/now-interview" ~/.claude/skills/now-interview
```

Then, in Claude Code, ask: *"Interview me for my /now page."*

Optionally, give it links first: your current /now page, /now pages you like, something you've written. It reads them for tone and shape, checks its read with you, then asks its questions. The result is one markdown file, `now-interview-YYYY-MM-DD.md`, with a paste-ready draft, the interview notes, and anything left open. It's made to hand to an editor (or your own red pen) for polishing.

The skill keeps a `learnings.md` next to itself. That file is about how the interview went, never about you. If you installed from a clone, pull requests with your learnings are welcome.

## A warning about claude-session.sh

It starts Claude with `--dangerously-skip-permissions`, which lets it run commands without asking first. I use it on a machine set aside for this. Read the script before you run it, and remove the flag if that isn't your setup.
