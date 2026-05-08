# algo-miner — Project Brief for Claude

## What this project is

An algorithmic trading brain with a bar-by-bar backtester, 7-layer quality gate,
walk-forward strategy tournament, and integrity verification tests.
Owner: @meineka (GitHub).  Language: Python 3.11+.

---

## Directory layout

```
algo-miner/
├── brain/
│   ├── config.py           # QualityConfig presets (STRICT / MEDIUM / DEFAULT / LOOSE)
│   ├── prerequisites.py    # Layer 0 — data sanity (spread, gaps, NaN)
│   ├── rules.py            # 4 regime-aware signal rules + Rules registry
│   ├── quality_checks.py   # Layers 1-6 quality gate + SessionFilter (zoneinfo DST)
│   ├── llm_validator.py    # Layer 7 — Claude Haiku validates each trade
│   ├── health_rules.py     # Walk-forward, regime coverage, trade-count guards
│   ├── strategy_genome.py  # StrategyGenome + StrategyMiner (random + community seeds)
│   └── tournament.py       # Walk-forward tournament: IS mine → OOS validate → Champion
│
├── simulator/
│   ├── ohlc_data.py        # OHLCData.generate() (GBM) + from_csv() (auto-detects MT5)
│   └── trade_simulator.py  # TradeSimulator — bar-by-bar event loop
│
├── tests/
│   ├── conftest.py         # sys.path setup
│   └── test_backtest_integrity.py   # 31 integrity tests (permutation, shadow PnL, golden fixtures)
│
├── data/
│   └── xauusd_m1_sample.csv   # 50 000 bars of real XAUUSD M1 (MT5, Jan–Mar 2025)
│
├── main.py                 # CLI entry point
└── requirements.txt
```

---

## Quick start

```bash
pip install -r requirements.txt

# Synthetic data, medium quality gates
python main.py

# Real XAUUSD data
python main.py --csv data/xauusd_m1_sample.csv --preset medium --verbose

# Walk-forward tournament (mine best strategy)
python main.py --csv data/xauusd_m1_sample.csv --mine --variants 50 --top-k 10

# Run integrity tests
python -m pytest tests/ -v
```

---

## Key design decisions

| Decision | Reason |
|---|---|
| Session filter disabled during mining | MT5 M1 data covers all hours; session gate is for live execution only |
| `disable_session_filter` flag on QualityConfig | Separates backtest from live concerns cleanly |
| Walk-forward split 70% IS / 30% OOS | Champion is chosen on data the miner never saw |
| Community seeds always in pool | Known-good configs (9/21 EMA, MACD 12/26) anchor random search |
| Composite score = Sharpe × PF × (1-DD) × log(trades) | Rewards risk-adjusted edge, punishes drawdown, requires volume |
| zoneinfo for SessionFilter | DST handled automatically per local timezone — no hardcoded UTC offsets |
| LLM validator (Layer 7) disabled by default | Requires ANTHROPIC_API_KEY; enable with `--llm` |

---

## Real data format (MT5 M1)

File: `data/xauusd_m1_sample.csv`  
Instrument: XAUUSD (Gold/USD), 1-minute bars  
Source: MetaTrader 5 export  
Period: 2025-01-02 to ~2025-03-14 (50 000 bars)

```
# Format (UTF-16, semicolon-separated):
time;open;high;low;close;tick_volume;spread;real_volume
2025-01-02 01:00:00;2625.71;2626.18;2625.14;2625.34;123;13;0
```

`OHLCData.from_csv()` auto-detects UTF-16 encoding and semicolon separator.
`tick_volume` is mapped to `volume` automatically.

---

## Trade pipeline per bar

```
1. Prerequisites.check()       data valid? (NaN, spread, gaps)
2. Rules.evaluate()            4 regime-aware rules → majority vote signal
3. QualityChecks.check()       6-layer deterministic gate + position sizing
4. LLMValidator.validate()     Layer 7 — Claude Haiku sanity check (optional)
5. Execute trade / update equity curve
```

---

## Quality gate layers

| Layer | What it checks |
|---|---|
| 1 Regime | ADX trend direction; blocks counter-trend trades when ADX > 30 |
| 2 Agreement | Minimum N rules must agree (default 3/4) |
| 3 Daily loss | Circuit-breaker if daily loss exceeds threshold |
| 4 Portfolio heat | Max total open risk as fraction of equity |
| 5 Rolling health | Sharpe + Profit Factor on last 30 closed trades |
| 6 Classic | Drawdown kill-switch, consecutive-loss limit, cooldown, ATR floor |
| 7 LLM | Claude Haiku approves/rejects with confidence score (optional) |

---

## Strategy rules

| Rule | Active when | Signal |
|---|---|---|
| EMA Crossover | ADX >= 20 (trending) | fast > slow → BUY |
| RSI Mean Reversion | ADX < 25 (sideways) | RSI < oversold → BUY |
| Donchian Breakout | ADX >= 20 + volume > avg | close > 20-bar high → BUY |
| Volume Spike | Any (3× required in HIGH-vol) | spike + up bar → BUY |

---

## Walk-forward tournament

```bash
python main.py --csv data/xauusd_m1_sample.csv --mine --variants 50 --top-k 10 --is-split 0.7
```

1. Generates pool: 5 community seeds + N random genomes
2. Runs all on IS (70%) → scores by Sharpe × PF × (1-DD) × log(trades)
3. Top-K survivors run on OOS (30%) → never seen during mining
4. Champion = best OOS score, Challengers = ranked standby

---

## Tests

```bash
python -m pytest tests/ -v        # all 31 tests
python -m pytest tests/ -k "Permutation"   # only lookahead-bias tests
python -m pytest tests/ -k "Shadow"        # only PnL arithmetic tests
python -m pytest tests/ -k "Golden"        # only logic fixture tests
```

Three independent test classes:
- `TestPermutation` — shuffles bar order; lookahead bias would still profit on random data
- `TestShadowPnL` — re-derives PnL from raw OHLC independently; catches arithmetic bugs
- `TestGoldenFixtures` — hand-crafted scenarios with mathematically certain outcomes

---

## CLI reference

```
python main.py [options]

Data:
  --csv PATH          Real OHLC CSV (auto-detects MT5 format)
  --bars N            Synthetic bars to generate (default 500)
  --seed N            Random seed (default 42)

Quality preset:
  --preset            strict | medium | default | loose  (default: medium)

Simulation:
  --capital N         Initial capital (default 10000)
  --no-short          Disable short trades
  --rr N              Take-profit R:R multiplier (default 2.0)

LLM (Layer 7):
  --llm               Enable Claude Haiku validator
  --llm-key KEY       API key (or set ANTHROPIC_API_KEY)

Output:
  --verbose           Print each trade in real time
  --save-trades       Export trades.csv

Health check:
  --health            Run walk-forward + regime coverage report
  --free-params N     Number of free parameters (for overfitting guard)

Tournament (strategy mining):
  --mine              Run walk-forward tournament
  --variants N        Random genomes to generate (default 50)
  --top-k N           IS survivors tested on OOS (default 10)
  --is-split F        IS fraction 0-1 (default 0.70)
```

---

## Environment

- Python 3.11+, Windows 11 (also works on Linux/macOS)
- Key packages: numpy, pandas, anthropic, tzdata, pytest
- `ANTHROPIC_API_KEY` env var for LLM layer (optional)
- MT5 installed locally (MetaTrader 5) — used as data source

---

## What the owner wants next

The owner (Szymon) wants to eventually connect this to live trading via MT5/broker API,
with the Champion strategy executing real orders and Challengers running in shadow/paper mode.
The tournament re-evaluates periodically; best OOS performer rotates to live slot.
