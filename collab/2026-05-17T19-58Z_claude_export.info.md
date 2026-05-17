# Claude export — 2026-05-17T19-58Z

- git branch : claude/review-ross-cameron-project-pb2ni
- git SHA    : 2ffddfb47374e78a9a03dbf058fcff8370706729
- created at : 2026-05-17T19-58Z UTC

## Last 10 commits
    2ffddfb docs: HANDOFF.md — complete state dump for other-AI takeover
    0062614 feat(brain): intraday_momentum_boundary rule (Zarattini SPY) + expert review loop seed
    849d42e aziz: research tick 2026-05-14T20:31Z — Ladder partial-size recipe (paper paywalled, 3-tier 33/33/34 default proposed)
    8b83be7 mt5: one-shot PowerShell backtest runner
    db1786f mt5: rename NAS100 → NQ + Python EA-shadow + PowerShell backtest recipe
    8e02548 collab: git-remote-execution daemon + first MT5 backtest job
    366300e collab: Claude Desktop + Filesystem-MCP one-shot installer
    3cbed11 collab: ChatGPT review loop via git bridge
    97910db feat(mt5): Aziz NAS100 EA v3 — audited & improved
    2f12338 aziz: research tick 2026-05-14T19:31Z — Maróy SPY exit-rule improvements (Sharpe>3, 50% p.a.)

## Contents
- brain/         Python Aziz strategy engine (10 files)
- simulator/     OHLC + trade simulator
- mt5/           MetaTrader 5 Expert Advisor (Aziz_NQ.mq5)
- tests/         pytest suite
- research/aziz/ Living knowledge base + transcripts + video index
- main.py, requirements.txt, CLAUDE.md

## How to review
1. Unzip locally
2. Read research/aziz/knowledge.md (latest dated section at bottom is most recent finding)
3. Read mt5/AUDIT.md for the EA's current state and open items
4. To send feedback: write collab/2026-05-17T19-58Z_chatgpt_answer.md and commit+push
