# arsenal

Small tools I actually use with Claude Code.

| Tool | What it does |
|---|---|
| [`claude/claude-session.sh`](claude/claude-session.sh) | Starts Claude Code in a fresh timestamped folder inside tmux (`new [label]`), or reattaches to or resumes one (`bounce <name>`). |
| [`claude/skills/now-interview/`](claude/skills/now-interview/) | A skill that interviews you, one question at a time, and drafts your [/now page](https://sive.rs/now). It learns your direction from links you give it and gets better with each run. |
| [`claude/skills/team-up/`](claude/skills/team-up/) | A skill that stands up a new project with its own lead agent: folder, agent definition, GitHub identity and a long-running tmux session, with an optional Discord bot per project. Audits first, builds only after you approve the plan. |

Each skill's folder has its own README with install steps.

Changes go through a review gate. See [CONTRIBUTING](.github/CONTRIBUTING.md).
