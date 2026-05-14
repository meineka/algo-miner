# Aziz NQ — MetaTrader 5 Expert Advisor

Implementation of Andrew Aziz's day-trading strategies for the NASDAQ-100
CFD on **GoMarkets** (or any broker that offers the same instrument).

## Files

```
mt5/
├── Aziz_NQ.mq5   ← the Expert Advisor source (compile with MetaEditor)
├── README.md         ← this file
└── AUDIT.md          ← code-audit findings (v1 → v2 → v3)
```

## What the EA does

| Component | Behavior |
|---|---|
| **Entry route 1: ORB** | Buys breakouts of the first 15-min range after NY open with volume confirmation; longs only above session VWAP and 9 EMA > 20 EMA. Mirrored for shorts. |
| **Entry route 2: VWAP reclaim** | After N consecutive M1 closes below session VWAP, the first bullish close back above VWAP triggers a long (mirrored for loss-of-VWAP shorts). |
| **Stop loss** | `ATR(14) × 1.5` from entry |
| **Take profit** | TP1 at +1R (closes 50%, moves SL to break-even); TP2 at +2R on the remainder |
| **Risk per trade** | 1 % of equity, lot size auto-computed from broker tick-size & tick-value |
| **Daily circuit-breaker** | Halt for the day after 2 % realised loss |
| **Cooldown** | After 3 consecutive losses, no new trades for the rest of the session |
| **Drawdown kill** | Permanent halt if account drops 6 % below peak |
| **Auto-flat** | Optional: close everything 5 min before session close |
| **Spread filter** | Skip new trades when spread > 50 points (configurable) |

## Install

1. **Copy** `Aziz_NQ.mq5` to:
   ```
   <MT5 install>\MQL5\Experts\
   ```
   (or via MT5 menu: *File → Open Data Folder → MQL5/Experts*)

2. **Compile** in MetaEditor (`F7`). You should see "0 errors, 0 warnings".

3. **Restart** MT5 or refresh the Navigator (Ctrl+N) and drag the EA onto a
   **NQ M1 chart**.

## GoMarkets-specific setup

GoMarkets MT5 exposes the NASDAQ-100 CFD under a broker-dependent name:

| Symbol seen on GoMarkets | Try in this order |
|---|---|
| `NQ`, `NQ.cfd` | most common |
| `US100`                 | alternative naming |
| `USTEC`                 | some account types |

Leave `Inp_SymbolAlias` empty if you attach the EA to a NQ chart — it
auto-detects via `_Symbol`. Otherwise set the alias explicitly.

### Server time vs. session time

The EA's `Inp_SessionOpenHour/Min` are in **MT5 server time**. New York
cash open is 09:30 ET. GoMarkets' MT5 server clock is typically **UTC+2**
(winter) / **UTC+3** (DST = summer).

Cheat-sheet (NY 09:30 ET ⇔ GoMarkets server time):
- US DST (March → November): NY 09:30 EDT = **15:30 server time** (UTC+3)
- US standard time (November → March): NY 09:30 EST = **16:30 server time** (UTC+2)

US DST and EU DST do *not* shift on the same day; in mid-March and
early-November there is a 1-week window where the offset differs by 1 hour.
Check your platform's clock vs. NY directly during those weeks.

Default inputs assume UTC server time. Override with the values above for
GoMarkets, **or** switch GoMarkets to GMT-server-time via account settings.

## Backtest in Strategy Tester

1. **Download M1 historical data** for the symbol — *Tools → History Center*
   (Ctrl+Shift+J for the History Center on some MT5 builds; otherwise
   right-click the symbol in *Market Watch → Specification → Update Data*).
2. **Strategy Tester** (Ctrl+R or *View → Strategy Tester*):
   - Expert: `Aziz_NQ`
   - Symbol: `NQ` (or your broker's alias)
   - Period: **M1**
   - Date: **From 2024-04-01 To today**
   - Forward: optional
   - Modelling: **Every tick based on real ticks**  ← *this is "mode 4"*
   - Deposit: 10 000 USD (default), Leverage as per your account
   - Optimisation: Disabled for a single run
3. Click **Start**.

The **Journal** tab prints state transitions and a final summary block
(also printed by `OnTester()`).

## Reading the journal output

```
[AZIZ_NQ] v3 init OK on NQ | risk=1.00% | day-stop=2.00% | DD=6.00% | ...
[AZIZ_NQ] ORB 2024.04.01 13:45 HI=18234.50 LO=18201.25 avgVol=412
[AZIZ_NQ] LONG @ 18236.10  SL=18225.40  TP1=18246.80  TP2=18257.50  lots=0.20  ATR=7.13  spread=12pt
[AZIZ_NQ] TP1 partial 0.10 lots @ 18246.85, stop→BE
[AZIZ_NQ] deal pnl=10.50 day_pnl=10.50 consec_loss=0
...
══════════════════════════════════════════════════════════════════
 Aziz NQ EA — backtest summary
══════════════════════════════════════════════════════════════════
 Symbol                : NQ
 Trades opened         : 128  (won 71 / lost 57)
 Partial fills (TP1)   : 71
 Win rate              : 55.47%
 Net P&L               : +1,824.30
 Profit factor         : 1.43
 Avg win / avg loss    : 32.17 / 24.86  (R≈1.29)
 Signals  ORB / VWAP   : 96 / 32
 Auto-flats (close)    : 14
 Blocked  day-stop     : 6
 Blocked  DD-kill      : 0
 Blocked  cooldown     : 11
 Blocked  spread       : 23
══════════════════════════════════════════════════════════════════
```

(numbers above are illustrative — your actual run will differ)

## Optimisation hints

The EA exposes a custom criterion in `OnTester()` returning **profit factor**.
Useful parameters to sweep:

- `Inp_ATR_StopMult`: 1.0 … 2.5 (step 0.25)
- `Inp_TP2_R_Multiple`: 1.5 … 3.0 (step 0.5)
- `Inp_BreakoutVolMult`: 1.1 … 2.0 (step 0.1)
- `Inp_ORB_WindowMinutes`: 5, 10, 15, 30
- `Inp_RiskPerTradePct`: 0.5, 1.0, 1.5 (don't go higher without a
  good reason; Aziz' rule book caps at 2 % and most retail traders
  blow up at higher sizes)

Walk-forward: 70 % IS / 30 % OOS, no over-fit on test set.

## Known limitations

1. **Tick-volume**, not real volume, on CFDs — the volume filter is a
   proxy for activity, not order flow.
2. **No news filter** — wide spreads + slippage around scheduled news
   (Fed, NFP, CPI) can blow stops. The spread filter mitigates this but
   does not eliminate it.
3. **Single-instrument** — pairs trading and multi-symbol baskets are
   out of scope. Run multiple chart instances if you want to trade
   several symbols.
4. **Server time misconfiguration** is the most common cause of "EA
   does nothing in the backtest". Double-check `Inp_SessionOpenHour/Min`
   against your broker's clock.

## Companion Python project

The same Aziz strategies are implemented in pure Python (vectorised
pandas) under `brain/aziz_rules.py` in the parent
[meineka/algo-miner](https://github.com/meineka/algo-miner)
repository, with a 7-layer quality gate, walk-forward tournament,
and a 50 000-bar XAUUSD M1 test dataset. Use the Python version for
research, parameter mining, and statistical validation; use this
MT5 EA for live and broker-realistic backtests.

## License

Same as the parent repository.
