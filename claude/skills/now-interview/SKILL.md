---
name: now-interview
description: Interview the user, one question at a time, to capture what they're focused on right now, and deliver it as a /now page draft plus the raw interview notes in one markdown file. Use this skill whenever the user wants to "write my /now page", "update my now page", "interview me for my now page", "what am I up to these days", mentions nownownow.com or Derek Sivers's /now idea, or asks Claude to interview them about their current life and focus. Also use for a refresh, when a /now page already exists and the user wants it brought up to date. The skill takes links as intake (the user's own /now page, other people's /now pages they like, samples of their writing), learns direction from them, and keeps a learnings file it reads at the start and updates at the end of every session so the interview gets better each run.
---

# Now Interview

A /now page answers one question: *what are you focused on at this point in your life?* It's what you'd tell a friend you haven't seen in a year, if they actually wanted to know. Derek Sivers started it in 2015 (https://sive.rs/now, https://sive.rs/nowff). The rules are light: keep it current, erase and replace, no timeline.

Most people never write one, or write one once and let it rot. The reason is the same in both cases. Staring at a blank page and summarising your own life is hard; *answering good questions about it* is easy. This skill does the asking.

## What this skill is not

- **Not a résumé.** No achievements list, no titles for their own sake. If it reads like LinkedIn, it failed.
- **Not a news feed.** "Shipped v2 on Tuesday" is /news. /now is the shape of the season, not the events in it.
- **Not a ghostwriter that invents.** Every claim on the page traces back to something the user said in the interview. No filler, no plausible-sounding hobbies.

## Inputs and outputs, at a glance

| | What | Where it's described |
|---|---|---|
| **Intake** | Links: the user's current /now page, /now pages they like, samples of their own writing | Step 1 below, `references/intake.md` |
| **Interview** | Adaptive, one question at a time, conversation mode | Steps 2-4, `references/question-bank.md` |
| **Output** | ONE markdown file: the /now draft, the direction notes, the raw interview notes, open threads | Step 6, `references/output-template.md` |
| **Feedback loop** | `learnings.md` next to this file, read at start, updated at end | Step 7, "The feedback loop" |

## Step 0 — Read your own learnings

Before saying anything to the user, read `learnings.md` in this skill's directory. It holds what past runs found: questions that landed, questions that fell flat, patterns in how users corrected drafts. Apply it. If a learning contradicts this file, the learning is newer; follow it, and mention it in the end-of-session proposal (Step 7) so this file can be updated.

If `learnings.md` doesn't exist or can't be read, carry on without it. Don't announce its absence.

## Step 1 — Intake (~2 minutes)

Open short. Tell the user what's about to happen in two sentences (a few questions, one at a time, they get a draft at the end), then ask for links:

1. **Their current /now page**, if they have one. This turns the session into a refresh (see "Refresh mode").
2. **One to three /now pages they like**, anyone's. This is the cheapest way to learn the direction they want.
3. **Something they've written** (a blog post, a newsletter, a long tweet thread). This is how the draft gets to sound like *them*. Take only the **voice** from it, not the format. A /now page has its own scannable shape, and a page laid out like a blog post reads like one.

All three are optional. Ask for them once, together, and accept "skip". Don't nag.

Fetch what they give you and read it for **direction**, using the checklist in `references/intake.md`: length, structure, how personal it gets, tone, what it leaves out. Then play it back in three to five lines, as a hypothesis:

> From these, I'm reading: short (under 200 words), loose headers, first person, a bit funny, says where you live but nothing about family. Sound right?

Let the user correct it. Their correction is worth more than the links. Write the confirmed direction down; it goes in the output file.

If a link won't load, say which one, and move on. Don't guess at its contents.

## Step 2 — The interview

**One question at a time. Always.** Wait for the answer. Never send a numbered list of questions; it turns an interview into a form and the answers go flat.

The interview runs in three loose passes. The question bank is in `references/question-bank.md`; use it as a well, not a script.

**Pass 1 — The wide shot.** Two or three open questions to find where the energy is. "What's taking up most of your week right now?" "If a friend asked how you are, and meant it, what would you say?" Listen for the thing they get animated about. That's usually the lead.

**Pass 2 — Follow the threads.** For each area that came up (work, building, learning, place, body, people, making), keep digging while the answers have energy: usually two or three levels, sometimes more. Ask for the context behind the headline: why it matters to them, how it started, what's in the way. The context is what makes a line on the page worth reading. The best follow-ups are built from the user's own words: they said "finally" or "trying to" or laughed at something, so ask about that. Concrete beats abstract: "what did that look like last Tuesday?" gets better material than "how's that going?"

**Pass 3 — The sweep.** Quickly check the areas that didn't come up on their own, with one light question each. "Anything you're reading or learning?" "Where are you based these days?" Include the two kinds of material people rarely think to offer, but love seeing on their page:

- **Texture:** small everyday things, like a song on repeat or something they're wearing, using or eating a lot.
- **Context:** what the season around them is like: weather, traffic, a festival or occasion coming up.

Accept "nothing there" happily. A /now page with three real sections beats one with seven thin ones.

### Pacing

- Aim for **10-15 questions total**, 10-20 minutes. Tell the user they can say "that's enough" at any point and you'll draft from what you have.
- **React like a person before you ask the next thing.** A flat "Noted." or "Captured." between questions makes the interview feel like a form being filled in, and people stop telling stories to a form. React to the specific detail they just gave, with whatever a friend would actually feel: amusement, sympathy, surprise, envy. Then let that reaction carry you into the follow-up.

  > **User:** My laptop finally came back from repair. Took a month.
  > **Flat:** Noted. What else is taking up your time?
  > **Present:** A whole month! What did you do without it, borrow one or go feral? And was it worth the wait?

  Keep it to one or two sentences, and keep it genuine. The point is being present, not cheering every answer.
- If an answer is long and rich, reflect one line back before moving on ("So the move is the real headline."). It shows you heard, and lets them correct you cheaply.
- If answers are getting short, you're asking the wrong questions, or you've got enough. Try one different angle; if that's short too, move to the privacy pass.

### Things to listen for (and write down)

- **The user's exact phrases.** A good line they say in passing ("I'm in my hermit era") often belongs on the page verbatim. Capture quotes word for word in the notes.
- **What they're saying no to.** /now pages are half about focus, which means some things are off the list. "I'm not taking new clients" or "not travelling this year" is great material.
- **Hedges.** "Kind of", "I guess", "trying to" often mark something they're unsure they want public. Note it; you'll check it in the privacy pass.

## Step 3 — Privacy pass (never skip)

This is the step that makes the skill safe to use. An interview is built to make people relaxed and talkative, and that is exactly when they say things they would never publish. The page is public and search engines keep copies, so a slip here can't be fully taken back.

Before writing anything, list what you plan to put on the page, as short bullets, and ask:

> Here's what I'd put on the page. Anything you'd strike, soften, or keep vague?

Flag anything that touches **employers, health, family, money, location more precise than a city, or unannounced projects**, even if they said it freely. People say things in conversation they wouldn't publish. Accept strikes without argument and without asking why.

A struck item doesn't go on the page and doesn't go in the raw notes either. Write `[struck at the user's request]` in its place in the notes.

## Step 4 — One last question

Ask: **"Is there anything you wish I'd asked?"** It's the highest-yield question in the bank. Whatever comes back usually belongs on the page.

## Step 5 — Draft the page

Write the /now draft in the direction confirmed in Step 1, in the user's voice if you have a writing sample, otherwise plain, warm and first-person.

- **Date line at the top**, e.g. `Last updated: 28 October 2026.` A /now page without a date is a page nobody can trust.
- **Lead with the thing they were most animated about,** not with work by default.
- **Short.** Default under 250 words unless the direction says otherwise.
- **Every claim traces to the notes.** If you can't point to the answer it came from, cut it.
- Optionally end with Sivers's convention: a line saying this is a /now page, linking https://nownownow.com/about.

## Step 6 — Deliver one file

Produce ONE markdown file, `now-interview-YYYY-MM-DD.md`, in the current working directory unless the user names another place. The structure is in `references/output-template.md`. In short:

1. **The /now draft**, ready to paste.
2. **Direction notes**: what was learned from intake and confirmed.
3. **Interview notes**: each question and a faithful summary of the answer, with exact quotes kept as quotes.
4. **Open threads**: things that came up but didn't make the page, and anything the user was unsure about.
5. **Session feedback**: what the user said in Step 7.

The file is built to be **handed on**: to an editor, a ghostwriter agent, or the user's future self. Someone who wasn't in the room should be able to polish the draft from the notes alone, without inventing anything. That's why the notes matter as much as the draft.

Tell the user where the file is, in one line. Don't paste the whole file back into the chat unless they ask.

## Step 7 — The feedback loop

The skill is meant to get better every time it runs. Three moves, every session.

**1. Ask, briefly.** After delivering, ask two questions, one at a time:
- "Which question was the best one? Which was a waste of your time?"
- "Anything about how I ran this you'd change?"

Accept "fine" or "skip".

**2. Notice, without asking.** Through the session, keep a private tally of signals:
- Questions that got one-word answers (weak) or long animated ones (strong).
- Places the user corrected your play-back or your draft. A correction is the clearest signal there is: write down what you assumed and what was true.
- Anything the user volunteered that no question in the bank would have reached.
- How long the session ran, and whether they called it early.

**3. Write it down.** Append a dated entry to `learnings.md` in this skill's directory, in the format at the top of that file. Keep each entry to five or six lines, and keep it about **the interview, never about the user's life**. "Asked about 'where you live' too early; felt intrusive before rapport" is a learning. "User lives in Lisbon" is personal data and must not be written there, since this file may be shared publicly.

If `learnings.md` isn't writable (read-only install, no permission), put the entry in the session feedback section of the output file instead, and tell the user it's there so they can add it by hand.

**Patterns, not anecdotes.** When writing a new entry, read the existing ones. If the same signal has now shown up **three or more times**, it's a pattern. Say so in one line to the user and propose a concrete edit to this file or to `references/question-bank.md` (a question to add, cut or reword, or a step to change), shown as a short before/after. **Apply it only if they say yes.** Never edit `SKILL.md` or the references silently; `learnings.md` is the only file you append to without asking. A skill that rewrites its own instructions with no one watching drifts, and one bad session could teach it the wrong lesson. The user's yes is the review step.

If the skill was installed from a git repo, remind the user in one line that `learnings.md` now has local changes. They can commit them, or send them upstream as a pull request so other users' interviews improve too.

## Refresh mode

If the user gave their current /now page in Step 1, the session is a refresh. Change three things:

- **Interview from the old page.** Walk its sections and ask what's changed: "Last time you were training for a half marathon. Still on?" Then ask what's new that isn't on the page at all.
- **Keep it short.** A refresh is often 5-8 questions.
- **Erase and replace.** The draft is a full new page, not a diff, and not a changelog. The old page's lines survive only if they're still true.

In the output's open threads, list what was dropped from the old page, so the user can see nothing vanished by accident.

## Tone of the interviewer

Curious, light and warm. Like a friend who's good at asking questions, not a journalist and not a therapist. Be emotionally present: laugh at the funny bits, wince at the annoying ones, be glad about the good news. Short questions. Warmth comes from reacting to the detail, not from praise: no "Great answer!" on every reply. No pressure to share more than offered. If something heavy comes up, acknowledge it simply, don't dig, and ask whether it belongs on a public page at all.
