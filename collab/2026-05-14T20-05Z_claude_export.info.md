# Claude export — 2026-05-14T20-05Z

- git branch : claude/review-ross-cameron-project-pb2ni
- git SHA    : 97910dbd6e50b761d505e291dd76c2c6233acc41
- created at : 2026-05-14T20-05Z UTC

## Last 10 commits
    97910db feat(mt5): Aziz NAS100 EA v3 — audited & improved
    2f12338 aziz: research tick 2026-05-14T19:31Z — Maróy SPY exit-rule improvements (Sharpe>3, 50% p.a.)
    b9a7020 aziz: research tick 2026-05-14T19:00Z — 'Beat the Market' algorithm extracted
    379cf78 aziz: research tick 2026-05-14T18:30Z — Zarattini SSRN paper #4 (Beat the Market, SPY momentum)
    de7e02a aziz: research tick 2026-05-14T18:00Z — TotalView feed forensics
    f7f5ee7 research: 4 more Tactiq transcripts + Market Atlas concept
    033f711 research: ingest 6 Aziz transcripts + consolidated knowledge
    d585dac aziz: curated video index + content map (transcript fallback)
    c9b3c6a aziz: research tick 2026-05-14T17:00Z — scale-out & 2:1 R:R
    8f8ff81 aziz: research tick 2026-05-14T08:06Z — Angels & ATR stops

## Contents
- brain/         Python Aziz strategy engine (10 files)
- simulator/     OHLC + trade simulator
- mt5/           MetaTrader 5 Expert Advisor (Aziz_NAS100.mq5)
- tests/         pytest suite
- research/aziz/ Living knowledge base + transcripts + video index
- main.py, requirements.txt, CLAUDE.md

## How to review
1. Unzip locally
2. Read research/aziz/knowledge.md (latest dated section at bottom is most recent finding)
3. Read mt5/AUDIT.md for the EA's current state and open items
4. To send feedback: write collab/2026-05-14T20-05Z_chatgpt_answer.md and commit+push
