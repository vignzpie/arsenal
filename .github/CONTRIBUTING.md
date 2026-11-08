# Contributing

arsenal is a small set of tools I actually use with Claude Code. It stays small on purpose. Every change goes through a review gate before it reaches `main`, whoever wrote it, me included. This page is the whole gate, and each rule gives its reason. If a reason doesn't fit your case, say so in the PR rather than working around the rule.

## How a change gets in

1. **Fixes and improvements:** open a PR. **A new tool:** open an issue first and say what it does and when you reach for it. Whether it fits is my call, and the issue is where I make it. A new skill starts from [`templates/skill/`](../templates/skill/): copy it to `claude/skills/<name>/` and replace every `<…>` slot. It passes the spec as it stands, and CI checks that it stays that way.
2. One change per PR. In the description, say what changed and why, and paste the commands you ran with their output.
3. The review ends in **PASS**, or **BLOCK** with a numbered list of exactly what has to change. A BLOCK isn't a rejection. Fix the list and the PR is re-reviewed.
4. I merge. Nothing reaches `main` without a PASS.

A tool's **owner** is its author, unless its README says otherwise. Changing what a tool says or does needs the owner's OK on the PR. Fixes don't.

If an AI agent wrote the change, that's fine: say so. Whoever opens the PR answers for it.

## The gate

Sections 1–4 block a merge. CI (`.github/scripts/check.sh`) runs the mechanical checks on every PR, and a reviewer reads for the rest.

### 1. Nothing private, nothing unsafe

*Why: the repo is public. Forks, mirrors and search engines keep copies, and GitHub keeps every comment's edit history, so deleting something later doesn't make it private again.*

- **No secrets:** tokens, keys or credentials, expired ones included. GitHub's secret scanning and push protection are on as a backstop.
- **No private references anywhere public:** code, docs, commit messages and trailers, branch names, PR titles and descriptions, comments and issues. That rules out:
  - links to private chats, sessions, documents or dashboards;
  - names of private tools, agents, machines, channels or accounts;
  - chat IDs and internal hostnames;
  - paths that reveal someone's setup;
  - internal shorthand.
  Test: would it make sense to a stranger who has only this repo?
- **No personal details about private individuals.** Citing someone's public work is fine.
- **Files a tool updates itself** (like a skill's `learnings.md`) record how the tool worked, never facts about the person using it. These entries come from real runs, which is expected, so the reviewer reads every line of them.
- **Examples are invented**, not lifted from real sessions.
- **No surprises when it runs.** Anything that deletes, overwrites, kills a process, skips permission prompts (including `allowed-tools` in a skill) or uses the network says so in the README. Destructive actions sit behind an explicit flag. Bash entries in `allowed-tools` are scoped, e.g. `Bash(git:*)` and never bare `Bash`. Nothing fetches and runs *unpinned* remote code. A pinned runner (`uvx tool@1.2.3`) is fine.
- Your commit author email is public. Use your GitHub noreply address if you'd rather keep yours private.

### 2. Skills follow the Agent Skills spec

*Why: the [Agent Skills spec](https://agentskills.io/specification) is the open format skills are written in. Following it keeps a skill portable, and a validator can check the core of it.*

- **The spec's required rules, checked by `skills-ref validate`:**
  - `name` is 1–64 characters of lowercase letters, digits and hyphens, with no leading, trailing or double hyphens, and it matches the folder name;
  - `description` is 1–1024 characters and says what the skill does and when to use it.
- **`license: Apache-2.0` in the frontmatter.** It's a spec field, and a skill copied out of this repo would otherwise lose its license.
- **House rules, which go further than the spec:**
  - `SKILL.md` stays under 500 lines, because its whole body loads on every run and longer detail belongs in `references/`, `scripts/` or `assets/`;
  - file references are relative to the skill folder, with no chains (`SKILL.md` → `a.md` → `b.md`), because the skill may be installed anywhere.

### 3. It works

*Why: "should work" is the most common way a published tool turns out to be broken.*

- Someone ran it and watched it behave. The PR shows the command and its output.
- **Shell:** `shellcheck` is clean for bash/sh and `zsh -n` for zsh, picked by the shebang. Add a dry run where you can.
- **Scripts an agent runs** (a skill's `scripts/`) never prompt for input, have `--help`, and their errors say what to try next. An agent can't answer a prompt, so it just hangs. Scripts people run by hand say in their usage text what they'll ask for.
- Every file a skill references exists, and install steps work from a fresh clone.

### 4. It's honest, consistent and in its place

*Why: the README is the only thing most people read before running a tool, and a predictable layout lets each tool be copied out on its own.*

- The README describes what the tool actually does, including its limits, its requirements and everything on section 1's "no surprises" list.
- A tool's files don't contradict each other. Anything renamed is updated everywhere, except history records like `learnings.md`. There are no TODOs or placeholders, but clearly marked template slots (`<name>`) are fine.
- Tools go in `claude/`, and skills in `claude/skills/<name>/`, each with its own `README.md`. The root README has a one-line entry for each tool, and its links resolve.
- Everything is under the [LICENSE](../LICENSE) (Apache-2.0). Contributions are accepted on its terms (its section 5). Third-party material keeps its own license, which must be compatible, and the tool's README names it.

Existing tools are brought up to the gate the next time they change.

## Advice (raised in review, not blocking)

From the spec's guides on [writing skills](https://agentskills.io/skill-creation/best-practices), [scripts](https://agentskills.io/skill-creation/using-scripts), [descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) and [evals](https://agentskills.io/skill-creation/evaluating-skills). The two that matter most:

- **A gotchas section:** the concrete mistakes an agent makes without being told. Add to it each time you correct the agent.
- **One default, not a menu:** pick one approach and mention alternatives briefly.

Evals (`evals/evals.json`) are worth it for a skill that changes often, and optional.

### Optional parts are modules

*Why: `SKILL.md` loads in full on every run, so a part only some users want, like a chat integration, costs every run that doesn't use it. The spec has no way for one skill to include another, so the split happens inside the skill.*

When a skill has parts that users turn on or leave off (an integration, a second account, a riskier mode), keep them out of the core:

- **The core doesn't know how any module is set up.** Its steps say "for each module that's on, run its section for this step", and it works with every module off. Test: could someone add a new module, say Slack, without editing the core's steps?
- **One file per module:** `references/<module>.md`. Give every module the same sections in the same order, one per core step it takes part in, then Gotchas. `SKILL.md` has a table of the modules and when to turn each on, and says to read a module's file as soon as it's on. A module that's off is never read.
- **A gotcha that bites before a module's file is read goes in `SKILL.md`.** Everything else about the module, apart from its table row, stays in its file.
- **Scripts get hooks, not branches.** If a script behaves differently per module, each module adds a hook file (e.g. `scripts/modules/<module>.sh`) defining the same set of functions, and the script refuses to run if a hook is missing one.
- **The README lists the modules** and what each one needs.
- **A module becomes its own skill** only when it's useful without this skill. The spec can't make one skill load another, so after the split this skill can only tell the agent to use the other one.

Don't split a skill that has no optional parts, or whose only option fits in a line or two of a step. A single `references/<topic>.md` for long detail is enough. [`team-up`](../claude/skills/team-up/) is the worked example.

## Not checked by the gate

Voice and content belong to the tool's owner. The gate covers safety, correctness and fit, not taste.

## Checks you can run

```sh
# Everything CI runs. Needs shellcheck, zsh, and skills-ref (below) on your PATH.
.github/scripts/check.sh --base origin/main

# skills-ref, the spec's validator, installed in its own venv outside the repo.
# Its README calls it a demo tool, so it's one check among several, not the whole gate.
python3 -m venv ~/.venvs/skills-ref
~/.venvs/skills-ref/bin/pip install 'git+https://github.com/agentskills/agentskills@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref'
export PATH="$HOME/.venvs/skills-ref/bin:$PATH"
```

The private check in `check.sh` matches patterns such as private links, long chat IDs, home paths and email addresses. It can't recognise a private name it has never seen, so read your own diff too.
