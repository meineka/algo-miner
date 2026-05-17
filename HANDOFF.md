# HANDOFF — algo-miner / Aziz brain

**Snapshot for transferring this work to another AI assistant.** Read top
to bottom. Everything you need to pick up where Claude (cloud sandbox)
left off is in this document; deep dives live in the linked files.

---

## 0. Identity & constraints of the AI that wrote this

- **Who**: Claude Code, cloud-hosted in an isolated Linux container
  (Ubuntu, no Windows, no GUI).
- **Tools available**: Read/Write/Edit (files), Bash, GitHub MCP
  (read/write of one specific repo only), WebSearch/WebFetch, Monitor
  (long-running background scripts that emit events).
- **Cannot do**: reach the user's local Windows PC, start MT5,
  use Cloudflare/ngrok tunnels, install software on user's machine,
  create new GitHub repos (scope locked to `meineka/algo-miner`).
- **GitHub repo scope**: `meineka/algo-miner` only. Branch in use:
  `claude/review-ross-cameron-project-pb2ni`. There is also a
  branch `aziz-brain` which is a standalone snapshot.

---

## 1. Project: algo-miner — Aziz day-trading brain

Bar-by-bar Python backtester + 7-layer quality gate + walk-forward
strategy tournament + MetaTrader 5 Expert Advisor — all built around
**Andrew Aziz's day-trading playbook** (How to Day Trade for a Living,
Advanced Techniques in Day Trading, Bear Bull Traders curriculum).

Owner: GitHub user `meineka`. Target asset: **NQ (NASDAQ-100 CFD)** on
GoMarkets MT5, also XAUUSD M1 (50 000-bar dataset shipped).

---

## 2. Repo layout

```
algo-miner/
├── brain/
│   ├── aziz_rules.py       # 7 Aziz strategies as vectorised pandas Rules
│   ├── intraday.py         # session VWAP, ORB, prior-day close helpers
│   ├── rules.py            # Registry: style='classic'|'aziz'|'hybrid'
│   ├── quality_checks.py   # 6-layer quality gate + position sizing
│   ├── llm_validator.py    # Optional Claude-Haiku layer-7 validator
│   ├── config.py           # Presets: STRICT / MEDIUM / DEFAULT / LOOSE / AZIZ
│   ├── strategy_genome.py  # Genome dataclass + StrategyMiner (Aziz seeds)
│   ├── tournament.py       # Walk-forward IS-mine → OOS-validate
│   ├── health_rules.py     # Walk-forward + regime-coverage health
│   └── prerequisites.py    # Data sanity (NaN, spread, gaps)
│
├── simulator/
│   ├── ohlc_data.py        # Synthetic GBM + CSV loader (MT5 auto-detect)
│   └── trade_simulator.py  # Bar-by-bar event loop with style switch
│
├── tests/                  # 70 pytest cases (all green)
│   ├── test_aziz_rules.py  # Aziz-specific tests (17 + 6 new for IMB)
│   └── test_backtest_integrity.py  # Permutation, shadow-PnL, golden
│
├── data/xauusd_m1_sample.csv   # 50 000 bars XAUUSD M1 from MT5
│
├── mt5/                    # MetaTrader 5 Expert Advisor
│   ├── Aziz_NQ.mq5         # The EA (v4 — partial; see §6)
│   ├── README.md           # Install + GoMarkets setup + Strategy Tester
│   ├── AUDIT.md            # v1 → v2 → v3 audit findings (17 fixes)
│   └── RUN_BACKTEST_POWERSHELL.md  # tester.ini schema + recipe
│
├── research/aziz/          # Living knowledge base (append-only)
│   ├── knowledge.md        # 700+ lines — Aziz playbook + research log
│   ├── youtube_videos.md   # Curated map of 13 Aziz videos
│   ├── download_queue.md   # yt-dlp recipe for primary-source pulls
│   ├── tick_prompt.md      # Prompt template for the 15-min loop
│   ├── transcripts/        # 5 curated + 4 raw Tactiq transcripts
│   └── expert_reviews/     # "Aziz himself" reviews — start at 20-min-cadence
│
├── scripts/                # PowerShell + Python helpers
│   ├── run_mt5_backtest.ps1     # ONE-SHOT: clone → compile → backtest → push
│   ├── aziz_remote_runner.ps1   # Daemon: poll GitHub jobs, execute, push back
│   ├── collab_bridge.ps1        # Sync GitHub ↔ local Aziz folder
│   ├── install_claude_desktop_mcp.ps1  # Claude Desktop + filesystem MCP setup
│   ├── export_brain.sh          # Build a snapshot ZIP for ChatGPT review
│   └── aziz_ea_shadow.py        # Python re-impl of EA logic (validation)
│
├── collab/                 # Claude × ChatGPT × user collaboration channel
│   ├── README.md           # Naming convention + workflow
│   ├── CLAUDE_DESKTOP_SETUP.md  # How to wire Claude Desktop to the folder
│   ├── jobs/
│   │   ├── README.md       # Job-format spec + permission model
│   │   ├── incoming/       # Jobs Claude wants user PC to execute
│   │   ├── processed/      # Audit trail
│   │   └── results/        # Output artefacts
│   └── *_claude_export.zip + .info.md  # Periodic brain snapshots
│
├── main.py                 # CLI entry point
├── requirements.txt
├── CLAUDE.md               # Project brief for AI assistants
└── HANDOFF.md              # ← this file
```

---

## 3. Aziz strategies implemented

| # | Rule (Python: `brain/aziz_rules.py`) | What it is |
|---|---|---|
| 1 | `vwap_reclaim_rule` | Reclaim/loss of session VWAP with confirming bar |
| 2 | `opening_range_breakout_rule` | First-N-bar range break + volume confirmation |
| 3 | `bull_flag_rule` | Flagpole → tight consolidation → breakout w/ volume |
| 4 | `abcd_pattern_rule` | 38.2–61.8 % retrace of an impulse, re-entry above swing |
| 5 | `red_to_green_rule` | Cross of prior-day close in morning window |
| 6 | `ma_trend_pullback_rule` | 9 EMA / 20 EMA pullback bounce |
| 7 | `intraday_momentum_boundary_rule` | **NEW** Zarattini × Aziz "Beat the Market" SPY boundary breakout (HH:00/HH:30 ticks, 14-day lookback, gap-adjusted bands) |

Style selector in `brain/rules.py`:
- `Rules(style='classic')` — original 4 regime-aware rules
- `Rules(style='aziz')` — these 7 Aziz rules
- `Rules(style='hybrid')` — both (11 total)

---

## 4. Aziz playbook — what the AI receiving this needs to know

### Strategies (Aziz teaches 10 in his books; 7 implemented above)
- ORB (5-min preferred since 2024), Bull Flag, ABCD, VWAP, 9/20 EMA
  Trend Pullback, Red-to-Green, 920 Reversal (counter-trend, 2-min
  chart, between 10:00–10:30), Fallen Angel (low-float only), Top/Bottom
  Reversal, Mountain Pass.

### Risk-management rules
- **1 % per trade** (max 2 %; new traders 0.5 %)
- **2 % daily loss** circuit-breaker — walk away
- **3 consecutive losses** → cooldown for the rest of the session
- **6 % monthly drawdown** → return to simulator for 2 weeks
- Min **2 : 1 R:R** to enter
- Scale-out: **½ at +1R → SL → break-even; ½ rides to +2R+**
- Never trade penny stocks (< 20 M float)

### Indicators on Aziz' chart
- VWAP (his favourite), 9 EMA + 20 EMA (exponential), 50 SMA + 200 SMA
  (simple), prior-day close, Camarilla pivots (R3/R4/S3/S4 only)
- **No trendlines** — Aziz: "trendlines are subjective"

### Tools
- Broker: **Interactive Brokers**; Platform: **DAS Trader Pro**
- 2024–2026 addition: **Market Atlas** (Aziz × NASDAQ partnership tool,
  Level-2 with time axis, $99/mo)
- Avoid Robinhood ("plastic knife to a gunfight")

### 11 Rules of Day Trading (Aziz's curriculum)
1. Day trading is not a get-rich-quick scheme.
2. Day trading is a serious business, not easy.
3. Trade **stocks of the day**, not random stocks.
4. Pick a direct-access broker and platform.
5. Risk management trumps everything.
6. Build a detailed pre-market plan every day.
7. The best day traders rarely trade — they wait.
8. Discipline is the most important quality.
9. Be independent — don't blindly follow chatroom calls.
10. Keep a trading journal, review weekly.
11. Take breaks when emotional, tired, or on tilt.

### 2025 Tariff-War lesson (Aziz publicly confessed $2 M loss April 2025)
- Lost on leveraged ETFs (SPXL, TQQQ, TNA) during 3-day volatility spike
- Cause: ego trading, no risk-management plan, "feeling invincible"
- Fix Aziz himself prescribed: **volatility-regime detector** — when
  short-ATR / long-ATR > 2, shrink position size, widen stops, multiply
  cooldown, disable counter-trend setups.

---

## 5. Research vault highlights (read `research/aziz/knowledge.md` for full)

- 9 transcripts ingested (5 curated, 4 raw Tactiq)
- 4 academic papers from Zarattini × Aziz × Barbon × Maróy on SSRN:
  1. *Can Day Trading Really Be Profitable?* (4416622, 2023)
  2. *A Profitable Day Trading Strategy For The U.S. Equity Market* (4729284, 2024) — **Stocks-in-Play ORB, Sharpe 2.4**
  3. *Beat the Market: Intraday Momentum SPY* (4824172, 2024) — **+1985 % / 19.6 % p.a. / Sharpe 1.33**, the rule now coded as `intraday_momentum_boundary_rule`
  4. *Improvements to Intraday Momentum (Maróy 2025)* (5095349) — **Sharpe > 3, > 50 % p.a.** with VWAP / Ladder exits
- Curated content map of 13 most relevant YouTube videos with topic timestamps

---

## 6. Code state — what's done, what's partial

### ✅ Done & green
- 70/70 pytest cases pass (`pytest tests/ -q`)
- 7 Aziz strategies as Python rules with genome integration
- AZIZ preset in `brain/config.py`
- Walk-forward tournament with Aziz seeds
- MT5 EA v3 — ORB + VWAP-reclaim + EMA filter + scale-out (audited twice)
- Python EA-shadow (`scripts/aziz_ea_shadow.py`) — runs on XAUUSD,
  21 trades / 52.4 % WR / +17.83 net / PF 1.02 (logic validation only)
- Collab bridge (git-based) + Windows PowerShell daemon

### 🚧 Partial / in-progress
- **EA v4** (`mt5/Aziz_NQ.mq5` v4.00): inputs for news-blackout +
  vol-regime + risk-base-mode are **added to the INPUTS block** but
  the **logic functions to use them are NOT wired yet**. Need to add:
  - `IsInNewsBlackout()` — parse `Inp_NewsTimesUTC`, return true within
    blackout window
  - `IsInChaosRegime()` — compute 5-day vs 60-day ATR ratio
  - Modify `CalculateLotSize` to honor `Inp_RiskBaseMode = 0` (lock to
    starting balance, reset after +20 %)
  - MFE/MAE per-position trackers + journal print in `OnTradeTransaction`
- **EA v4 README/AUDIT update** — not yet written
- **Expert review loop** seeded with first review; should fire on every
  2nd 15-min heartbeat tick (= 30 min cadence). Currently runs manually.

### ❌ Not started
- Range-expansion volume filter (replace tick-volume primary signal)
- 3-tier 33/33/34 ladder exit (Maróy's improvement)
- News-event-calendar auto-fetch (currently hardcoded UTC times)
- Walk-forward CI: GitHub Actions that runs the EA-shadow on every push

---

## 7. Active loops / background tasks

| Loop | Cadence | Mechanism | State |
|---|---|---|---|
| Heartbeat research tick | 15 min (sandbox-capped 30 min/monitor) | `Monitor` script `while true; sleep 900; date`; needs manual re-arm after each timeout | Most recent: `bv5xg3ap2` re-armed earlier. Active or near timeout. |
| Aziz-Expert review | 30 min (= every 2nd heartbeat) | Decision logic inside heartbeat handler | First review committed to `research/aziz/expert_reviews/2026-05-17T19-52Z_aziz_review.md`. Subsequent reviews fire on alternating ticks. |
| Auto-export | On heartbeat | `scripts/export_brain.sh` builds ZIP, commits | Last export: `collab/2026-05-14T20-05Z_claude_export.zip` |
| ChatGPT-answer polling | 5 min when bridge daemon running | `scripts/collab_bridge.ps1` (Windows) | **Inactive** — needs user to start daemon |
| MT5 backtest | On demand | `scripts/run_mt5_backtest.ps1` (Windows) | **Inactive** — needs user to start |

---

## 8. Open questions / unfinished investigations

(Append-only follow-ups from `research/aziz/knowledge.md`)
- Performance attribution per Aziz strategy in Market-Atlas era
- Whether Aziz publishes Market Atlas spec publicly (so we can clone it)
- Exact Maróy "Ladder" partial-size schedule (paper paywalled)
- Live verification of `Inp_SessionOpenHour/Min` defaults against
  actual GoMarkets server time

---

## 9. How to pick up where this AI left off

### If you are another cloud / hosted AI (no local PC access)
1. Pull the repo: `git clone https://github.com/meineka/algo-miner.git -b claude/review-ross-cameron-project-pb2ni`
2. Verify tests still green: `pytest tests/ -q`
3. Finish EA v4 logic wiring — start with `mt5/Aziz_NQ.mq5` lines
   currently containing the new input groups (`Inp_UseNewsBlackout`,
   `Inp_UseVolRegime`, `Inp_RiskBaseMode`). Add the helper functions
   listed in §6 "Partial".
4. Re-run `python scripts/aziz_ea_shadow.py` against the XAUUSD
   dataset and confirm shadow output still makes sense.
5. Commit findings into `research/aziz/expert_reviews/<UTC_TS>_<author>_review.md`.

### If you are a local AI (has Windows PC access)
You can additionally:
- Run the MT5 backtest:
  `pwsh -ExecutionPolicy Bypass -File .\scripts\run_mt5_backtest.ps1`
- Drop reviews / instructions into `C:\Users\Szymon\ross-cameron\99_2 Aziz claude chatgpt\<UTC_TS>_<author>_answer.md`
  → the bridge daemon (if running) pushes them to GitHub.

### If you are Andrew Aziz (or someone acting as him)
- Read `research/aziz/expert_reviews/` — start where the last review
  stopped. Add a new dated file there.
- Critique the EA defaults against your current 2026 playbook.
  Defaults in `mt5/Aziz_NQ.mq5` reflect what we know up to your
  publicly available material as of May 2026.

### Concrete first actions for any AI picking this up
1. `git log --oneline -10` to see the most recent commits
2. `cat HANDOFF.md` (this file)
3. `cat research/aziz/knowledge.md | tail -200` for latest research
4. `cat research/aziz/expert_reviews/$(ls -t research/aziz/expert_reviews/ | head -1)` for latest review
5. Decide: implement an open item, or run an expert review, or fix
   a bug, or add a new strategy. Commit + push.

---

## 10. Repo & branch coordinates

- **GitHub**: https://github.com/meineka/algo-miner
- **Working branch**: `claude/review-ross-cameron-project-pb2ni`
- **Standalone snapshot**: `aziz-brain` branch
- **PR**: #1 (draft, open, mergeable=clean)
- **Owner**: `meineka` (Szymon)

---

## 11. Tools, secrets, environment

- Python 3.11+
- Key packages: numpy, pandas, anthropic, tzdata, pytest
- `ANTHROPIC_API_KEY` env var for the optional LLM-validator layer
- No other secrets in repo

---

*Generated by Claude Code (cloud sandbox) on $(date -u +%Y-%m-%dT%H-%MZ).*
*This file is checked in. Keep it updated if you make non-trivial state changes.*
