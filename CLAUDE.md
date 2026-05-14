# aziz-brain — Project Brief for Claude

## What this project is

A standalone algorithmic day-trading engine built around Andrew Aziz's
strategies (How to Day Trade for a Living, Advanced Techniques in Day
Trading, Bear Bull Traders curriculum).

Owner: @meineka. Language: Python 3.11+.

Originated as branch `aziz-brain` of `meineka/algo-miner`. To extract
into its own GitHub repo, see the recipe at the bottom of README.md.

## Directory layout

```
aziz-brain/
├── brain/
│   ├── aziz_rules.py       # 6 Aziz strategies as Rule functions
│   ├── intraday.py         # session VWAP, opening range, prior-day close
│   ├── rules.py            # Rules registry — style='aziz' is the default
│   ├── quality_checks.py   # 6-layer gate + SessionFilter (zoneinfo DST)
│   ├── llm_validator.py    # Layer 7 — optional Claude-Haiku approve/reject
│   ├── config.py           # AZIZ preset is the default
│   ├── strategy_genome.py  # genome + miner (Aziz seeds + Aziz param space)
│   ├── tournament.py       # walk-forward IS-mine → OOS-validate
│   ├── health_rules.py     # walk-forward + regime-coverage health
│   └── prerequisites.py
├── simulator/
│   ├── ohlc_data.py        # OHLCData.generate() + from_csv (auto-MT5)
│   └── trade_simulator.py  # bar-by-bar event loop
├── tests/                  # pytest suite (integrity + Aziz)
├── data/xauusd_m1_sample.csv   # 50 000 bars XAUUSD M1
├── research/aziz/          # living knowledge base + transcripts + video index
├── .github/workflows/ci.yml
└── main.py
```

## Aziz strategies implemented (brain/aziz_rules.py)

| Rule | Aziz teaching |
|---|---|
| `vwap_reclaim` | *"VWAP is my favourite indicator."* |
| `opening_range_breakout` | *"ORB is my bread and butter for the market open."* |
| `bull_flag` | First 1.5 h only, retrace ≤ 50 % of pole, volume on break |
| `abcd_pattern` | A = day high, B = pullback, C = consolidation, D = re-entry; 38.2 – 61.8 % retrace |
| `red_to_green` | Cross of prior-day close in first 60 – 90 min |
| `ma_trend_pullback` | 9/20-EMA pullback bounce, ride until 20-EMA break |

## Defaults

- `--preset aziz` is the default (1 % risk, 2 % daily loss, 3-strike
  cooldown, 6 % drawdown kill, 1.5 ATR stops)
- `--style aziz` is the default rule set (6 Aziz rules); `--style hybrid`
  mixes both classic + Aziz (10 rules); `--style classic` returns to
  the original 4 rules

## Quality gate (7 layers)

1. **Regime** — ADX direction, block counter-trend at ADX > 30
2. **Agreement** — 2 of 6 rules (Aziz uses confluence, not majority)
3. **Daily loss** — 2 % of equity ("walk away")
4. **Portfolio heat** — 4 % open risk cap
5. **Rolling health** — Sharpe ≥ 0.7 + PF ≥ 1.20 over last 30 trades
6. **Classic** — 6 % drawdown kill, 3 consecutive losses, cooldown, ATR floor
7. **LLM** — opt-in via `--llm` (uses ANTHROPIC_API_KEY)

## Quick start

```bash
pip install -r requirements.txt
python main.py --csv data/xauusd_m1_sample.csv --preset aziz     # Aziz on real XAUUSD M1
python main.py --bars 1500                                       # synthetic smoke
python main.py --csv data/xauusd_m1_sample.csv --preset aziz --style aziz --mine
python -m pytest tests/ -v                                       # all tests
```

## Tests

```bash
pytest tests/test_aziz_rules.py -v          # 17 Aziz-specific tests
pytest tests/test_backtest_integrity.py -v  # permutation + shadow-PnL + golden fixtures
```

## Research vault

`research/aziz/knowledge.md` is **append-only**. New findings get dated
entries under "Change log". Never rewrite or delete prior entries —
older facts are still source-of-truth.

`research/aziz/transcripts/` — curated transcripts from Aziz YouTube
videos + Bear Bull Traders community webinars. 5 curated + 4 raw
Tactiq dumps so far.

`research/aziz/youtube_videos.md` — curated content map of the 13 most
relevant Aziz videos.

`research/aziz/download_queue.md` — primary-source URLs to fetch from
outside the sandbox (YouTube auto-captions via yt-dlp, BBT PDFs,
SSRN abstracts).

## Environment

- Python 3.11+, Linux / macOS / Windows
- Key packages: numpy, pandas, anthropic, tzdata, pytest
- `ANTHROPIC_API_KEY` env var for LLM layer 7 (optional)
