# now-interview

A Claude Code skill that interviews you, one question at a time, and drafts your [/now page](https://sive.rs/now).

A /now page says what you're focused on at this point in your life. It's the answer you'd give a friend you haven't seen in a year. Writing one from a blank page is hard. Answering good questions about your life is easy, so this skill asks the questions.

## Install

Copy or symlink this folder into your skills directory:

```sh
ln -s "$PWD/claude/skills/now-interview" ~/.claude/skills/now-interview
```

Then, in Claude Code:

> Interview me for my /now page.

## How a session goes

1. **Intake.** It asks for up to three kinds of link, all optional: your current /now page, /now pages you like, and something you've written. It reads them for length, tone, structure and how personal they get, then tells you what it picked up so you can correct it.
2. **Interview.** About 10–15 questions, one at a time. It starts broad, follows whatever you seem most into, then quickly checks anything that didn't come up. You can say "that's enough" at any point.
3. **Privacy pass.** Before it writes anything, it shows you everything it plans to put on the page and asks what to strike. It never skips this.
4. **Draft.** A short page in the direction you agreed, dated at the top.
5. **Feedback.** Two quick questions about how the interview went.

What it sounds like (an illustrative example, not a real session):

> **Claude:** What's taking up most of your week right now?
>
> **You:** Honestly, a side project that was supposed to be a weekend thing. It's been three months.
>
> **Claude:** Three months of weekends. What is it, and what keeps you on it?

If you give it your existing /now page, it switches to **refresh mode**. It walks through the old page asking "still true?", asks what's new, and writes a full replacement.

## What you get

One file, `now-interview-YYYY-MM-DD.md`, in the folder you're working in:

1. **Draft:** the /now page, ready to paste
2. **Direction:** what it learned from your links, as you corrected it
3. **Interview notes:** each question with a faithful summary of your answer, with your best lines kept word for word
4. **Open threads:** things that came up but didn't make the page
5. **Session feedback**

The notes are there so someone else (an editor, a ghostwriter, you next month) can polish the draft without making anything up.

## It gets better with use

The skill keeps `learnings.md` next to itself. It reads that file before each interview and adds a short entry afterwards: which questions worked, which fell flat, and where you corrected it. When the same signal shows up three times, it suggests a change to its own instructions, and makes it only if you agree.

`learnings.md` records how the interview went, **never anything about you**, so it's safe to share. If you installed from a clone, pull requests with your learnings are welcome. They help everyone's interviews.

## Files

| File | What it's for |
|---|---|
| `SKILL.md` | Instructions for Claude: the flow, the rules and the tone |
| `references/intake.md` | How to read your links for direction |
| `references/question-bank.md` | The questions it draws from |
| `references/output-template.md` | The structure of the file you get |
| `learnings.md` | What past sessions taught it |
