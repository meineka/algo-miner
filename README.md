# aziz-brain

Algorithmic day-trading engine built around Andrew Aziz's
*How to Day Trade for a Living* / *Advanced Techniques in Day Trading*
playbook and the Bear Bull Traders curriculum.

> **What this is**: a bar-by-bar Python backtester + six regime-aware
> Aziz strategies + a seven-layer quality gate + a walk-forward
> strategy tournament. Tested on real XAUUSD M1 data; the architecture
> is asset-agnostic.

## Strategies

| Rule | Idea (Aziz source) |
|---|---|
| `vwap_reclaim` | Reclaim or loss of session VWAP with a confirming bar (*his favourite indicator*) |
| `opening_range_breakout` | First-N-bar range break with volume confirmation (*his "bread and butter"*) |
| `bull_flag` | Flagpole → tight consolidation → breakout w/ volume (first 1.5 h only) |
| `abcd_pattern` | 38.2 – 61.8 % retrace of an impulse, re-entry above swing |
| `red_to_green` | Cross of the prior-day close inside the morning window |
| `ma_trend_pullback` | 9 / 20 EMA pullback bounce, hold until 20 EMA break |

All rules return `{-1, 0, +1}` aligned to the bar index and accept the
same `regimes` argument the framework computes once per bar.

## Seven-layer quality gate

1. **Regime** — ADX trend direction, blocks counter-trend at ADX > 30
2. **Agreement** — minimum number of rules must agree (default 2 / 6)
3. **Daily loss** — circuit-breaker at 2 % of equity (Aziz "walk away")
4. **Portfolio heat** — cap total open risk at 4 %
5. **Rolling health** — Sharpe + Profit-Factor on last 30 closed trades
6. **Classic** — drawdown kill (6 %), 3-strike loss cutoff, cooldown, ATR floor
7. **LLM** — optional Claude-Haiku sanity check (`--llm`)

Position sizing combines ATR-based and half-Kelly, hard-capped at 1 %
risk per trade.

## Quick start

```bash
pip install -r requirements.txt

# Aziz preset on real XAUUSD M1 data
python main.py --csv data/xauusd_m1_sample.csv

# Synthetic 1500-bar smoke
python main.py --bars 1500

# Walk-forward tournament: mine the best Aziz variant
python main.py --csv data/xauusd_m1_sample.csv --mine --variants 30 --top-k 5

# Integrity tests
python -m pytest tests/ -v
```

## Project layout

```
aziz-brain/
├── brain/
│   ├── aziz_rules.py        # the 6 Aziz strategies
│   ├── intraday.py          # session-aware helpers (VWAP, ORB, …)
│   ├── rules.py             # Rules registry (style='aziz'|'classic'|'hybrid')
│   ├── quality_checks.py    # layers 1-6 quality gate + position sizing
│   ├── llm_validator.py     # layer 7 — Claude Haiku approve/reject
│   ├── config.py            # AZIZ / STRICT / MEDIUM / DEFAULT / LOOSE presets
│   ├── strategy_genome.py   # genome dataclass + miner (Aziz seeds)
│   ├── tournament.py        # walk-forward IS-mine → OOS-validate
│   ├── health_rules.py      # walk-forward + regime-coverage health
│   └── prerequisites.py     # data sanity (NaN, spread, gaps)
│
├── simulator/
│   ├── ohlc_data.py         # synthetic GBM + CSV loader (MT5 auto-detect)
│   └── trade_simulator.py   # bar-by-bar event loop
│
├── tests/
│   ├── test_aziz_rules.py        # 17 smoke + integration tests
│   └── test_backtest_integrity.py # permutation, shadow-PnL, golden fixtures
│
├── data/xauusd_m1_sample.csv     # 50 000 bars XAUUSD M1 from MT5
├── research/aziz/                # living knowledge base + 9 transcripts (5 curated + 4 raw) + video index
├── .github/workflows/ci.yml      # pytest matrix + Aziz CLI smoke
└── main.py
```

## CLI reference (excerpt)

```
--csv PATH                Real OHLC CSV (auto-detects MT5 format)
--bars N                  Synthetic bars (default 500)
--preset {aziz|strict|medium|default|loose}     default: aziz
--style   {aziz|classic|hybrid}                 default: aziz
--mine                    Run walk-forward tournament
--variants N              Random genomes (default 50)
--top-k N                 IS survivors tested on OOS (default 10)
--llm                     Enable Claude-Haiku layer-7 validator
--verbose                 Print every trade in real time
```

## Research vault

Everything we know about Andrew Aziz's methodology — strategies, risk
rules, direct quotes, open follow-ups — lives in `research/aziz/`.
The knowledge base is **append-only**; new findings get dated entries
in the `Change log` section so prior facts stay verifiable.

Content currently captured (May 2026):

- `knowledge.md` — living, dated change log with 30+ extracted rules,
  quotes, risk thresholds and trade examples
- `youtube_videos.md` — curated content map of 13 top Aziz videos
- `transcripts/` — 5 curated transcripts + 4 raw Tactiq dumps
- `download_queue.md` — `yt-dlp` recipe for primary-source extraction
- `tick_prompt.md` — prompt template for the 15-min research loop

Key concepts indexed: ORB, VWAP, Bull Flag, ABCD, Red-to-Green,
9/20-EMA reversal, Stocks-in-Play scanner, 1 % / 6 % risk rules,
Camarilla pivots (Thor), Bookmap order flow, **Market Atlas** (Aziz ×
NASDAQ tool, $99/month), confluence gate, the 2025 Tariff-War bear
market lessons.

## Promote to its own GitHub repo

This branch lives inside `meineka/algo-miner` for now. To move it
into its own repo:

```bash
# 1. Create an empty repo on github.com (e.g. meineka/aziz-brain)
# 2. Clone this branch:
git clone --branch aziz-brain --single-branch \
  https://github.com/meineka/algo-miner.git aziz-brain
cd aziz-brain

# 3. Re-point origin to the new repo:
git remote set-url origin git@github.com:meineka/aziz-brain.git

# 4. Push as the new main:
git push -u origin aziz-brain:main
```

For a clean history with only Aziz-related commits, use
`git filter-repo --path brain/aziz_rules.py --path brain/intraday.py …`
before the final push.
