# Aziz research tick — prompt template

Used by the `/loop 15m` agent that wakes every 15 minutes to add more
Andrew Aziz knowledge to the project.

## Prompt

```
Read research/aziz/knowledge.md and research/aziz/download_queue.md
to learn what's already captured. Do NOT repeat facts that are
already in knowledge.md — the goal is to *add* new material.

Pick ONE open research question from the bottom of knowledge.md
(section "Open research questions") OR identify a new angle if all
listed ones have already been addressed. Use WebSearch (and WebFetch
when the host is allowed) to gather material on that angle —
prefer direct Aziz quotes, exact numbers, dated interviews, paper
abstracts, or Bear Bull Traders material.

Append your findings to research/aziz/knowledge.md under a new
dated heading inside the "Change log" section, e.g.:

  ### 2026-05-14 14:30 — <topic>
  - <fact 1 with source>
  - <fact 2 with source>

Then commit and push the change with a message
"aziz: research tick <UTC timestamp>".

Important:
- Be frugal: 60-120 seconds of research per tick is enough.
- Don't open new PRs.
- Don't touch any files outside research/aziz/.
- If you can't find new material after one round of searching,
  add a note "no new material — searched <queries>" instead of
  committing empty changes.
- Run quietly — no end-of-tick summary text to the user beyond
  what the commit message conveys.
```
