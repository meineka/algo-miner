# Collab folder — Claude × ChatGPT review loop

This folder is the shared exchange channel between Claude (this repo)
and ChatGPT (running on the user's side).

## File-naming convention

| Filename                              | Direction | Meaning |
|---------------------------------------|-----------|---------|
| `<TIMESTAMP>_claude_export.zip`       | Claude → ChatGPT | Snapshot of brain/, simulator/, mt5/, tests/, research/aziz/ at that UTC time |
| `<TIMESTAMP>_claude_export.info.md`   | Claude → ChatGPT | Manifest: git SHA, commits, contents, review instructions |
| `<TIMESTAMP>_chatgpt_answer.md`       | ChatGPT → Claude | ChatGPT's review feedback / fix proposals matching that export |
| `<TIMESTAMP>_chatgpt_answer.zip`      | ChatGPT → Claude | Same as `.md` but as a zip with attachments |

`<TIMESTAMP>` is UTC, format `YYYY-MM-DDTHH-MMZ`.
The matching `_chatgpt_answer` must share the SAME timestamp as the
`_claude_export` it responds to. Different timestamps = different
review cycle.

## Workflow

```
┌── Claude (in sandbox) ──┐                ┌── you / ChatGPT (Windows) ──┐
│                         │                │                              │
│  scripts/export_brain   │   git push     │  scripts/collab_bridge.ps1   │
│   ↓ commits             │ ─────────────► │   ↓ git pull, copy to        │
│  collab/<TS>_export.zip │                │  C:\Users\...\Aziz folder    │
│                         │                │                              │
│                         │                │  ChatGPT reads, replies      │
│                         │                │  with <TS>_chatgpt_answer.md │
│                         │                │   ↓ collab_bridge auto       │
│  poll on heartbeat      │   git pull     │  copies into repo, commits   │
│   ↓ if new answer       │ ◄───────────── │  & pushes                    │
│  apply suggestions      │                │                              │
└─────────────────────────┘                └──────────────────────────────┘
```

## On the Claude side

- `scripts/export_brain.sh` is run every heartbeat tick (~15 min) and
  produces a fresh `<TS>_claude_export.zip`. The commit pushes it
  automatically.
- Each heartbeat also polls this folder for any `_chatgpt_answer.md`
  that wasn't there last cycle. New answers get processed
  immediately: read → implement → commit.

## On your side (Windows)

- One-time clone the repo locally:
  ```powershell
  git clone https://github.com/meineka/algo-miner.git C:\dev\algo-miner
  cd C:\dev\algo-miner
  git checkout claude/review-ross-cameron-project-pb2ni
  ```
- Edit the two paths at the top of `scripts/collab_bridge.ps1` if your
  local layout differs from the defaults.
- Run it from PowerShell:
  ```powershell
  pwsh -ExecutionPolicy Bypass -File .\scripts\collab_bridge.ps1
  ```
- Leave the window open. It does git pull every 30 s, mirrors new
  Claude exports into `C:\Users\Szymon\ross-cameron\99_2 Aziz claude
  chatgpt`, watches that folder for new `_chatgpt_answer.*` files, and
  pushes them back to GitHub the moment they appear.

## Manual fallback (no script)

If you don't want to run the bridge:

1. `git pull` periodically to fetch new exports.
2. Unzip the latest `_claude_export.zip`.
3. Paste relevant parts into ChatGPT.
4. Save ChatGPT's reply as `collab/<MATCHING_TIMESTAMP>_chatgpt_answer.md`
   inside the repo (matching the export's timestamp).
5. `git add . && git commit -m "chatgpt answer" && git push`.

Claude will pick it up at the next heartbeat tick.

## Format expectations for `_chatgpt_answer.md`

Free-form Markdown. Suggested sections:

```markdown
# ChatGPT review for <TIMESTAMP>

## Summary
1–2 sentences: what's the headline?

## Findings
- file:line — observation
- ...

## Concrete fixes proposed
1. Description of fix #1 — patch or pseudo-patch
2. ...

## Open questions
- ...
```

Claude reads these and either applies the fixes directly (committing
each one separately) or — if a proposal is ambiguous / architecturally
significant — opens a new question in the next commit instead of acting.
