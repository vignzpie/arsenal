# Output template

The skill delivers ONE file: `now-interview-YYYY-MM-DD.md`. Keep the section order stable, so anything downstream (an editor, a ghostwriter agent, a script) can find what it needs.

The file is written to be **handed on**. Someone who wasn't in the interview should be able to polish the draft from these notes alone, without inventing anything.

````markdown
---
type: now-interview
date: YYYY-MM-DD
mode: first-run | refresh
skill: now-interview
---

# /now interview, YYYY-MM-DD

## 1. Draft

<!-- Paste-ready /now page. Starts with the date line. -->

Last updated: DD Month YYYY.

...

## 2. Direction

**From intake:** links used, one line each on what they contributed.
**Confirmed with the user:** the play-back as corrected, e.g. length, structure, tone, how personal.
**Voice notes:** three to five concrete notes from the writing sample, if one was given.

## 3. Interview notes

<!-- One entry per question, in the order asked. Summarise faithfully; keep
the user's best lines as exact quotes. Struck items are replaced with
[struck at the user's request] and nothing else. -->

**Q1. What's eating most of your week right now?**
Summary of the answer. > "Exact quote worth keeping."

**Q2. ...**

## 4. Open threads

- Things that came up but didn't make the page, and why.
- Anything the user hedged on or wanted to think about.
- In refresh mode: lines dropped from the old page.

## 5. Session feedback

- Best question / weakest question, in the user's words.
- How they'd change the interview.
- If `learnings.md` wasn't writable: the learning entry, for the user to add by hand.
````

## Notes for whoever polishes the draft

- Edit the draft freely, but add claims only from section 3. If the notes don't support it, it doesn't go on the page.
- Exact quotes in section 3 are fair game for the page; they're the user's own words.
- Respect section 2. If the user said "no family stuff", it stays out, however good the line.
