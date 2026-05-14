# Aziz NQ EA — Audit log

Three iterations: v1 → v2 → v3. This file documents what was found and
fixed at each stage so the next reviewer (or ChatGPT collaborator) can
verify the corrections.

---

## v1 → v2 audit (10 findings)

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | CRITICAL | `position.SelectByMagic(symbol, magic)` does not exist on stock `CPositionInfo` — code would fail to compile. | Replaced with manual `for(i=0..PositionsTotal()) { SelectByIndex(i); filter by symbol+magic; }` |
| 2 | HIGH | `RolloverDay()` only ran on date change → on day 1, `g_session_open_time = 0`, `g_orb_low = DBL_MAX`. `IsInTradingWindow` blocked → no trades on first day. | Call `RolloverDay(TodayDate())` at end of `OnInit()`. |
| 3 | MEDIUM | After `PositionClosePartial`, the existing `position` object was reused for `PositionModify` without refresh. | Re-call `SelectOwnPosition()` after partial close. |
| 4 | MEDIUM | `CopyRates(symbol, M1, 1, 2, …)` requested 2 bars but used only one. | Reduced to count=1; cleaner intent. |
| 5 | MEDIUM | No input-sanity validation (EMA_Fast vs EMA_Slow, ORB window, session times). | Added explicit checks in `OnInit()`, return `INIT_PARAMETERS_INCORRECT` on violation. |
| 6 | LOW | Tick-volume on CFDs ≠ real volume — caveat undocumented. | Documented in README §Known limitations. |
| 7 | LOW | No `OnTester()` for backtest-end summary. | Added `OnTester()` returning profit factor; prints summary block to journal. |
| 8 | LOW | Only ORB entry route; VWAP-reclaim never implemented. | Added second route in `ComputeSignal()` using streak counters. |
| 9 | LOW | `Inp_MagicNumber` declared as `ulong`, compared via cast. | Type now `ulong` consistently; compare with `(long) Inp_MagicNumber`. |
| 10 | DOC | GoMarkets server-time offset poorly explained. | README §"Server time vs. session time" with explicit cheat-sheet. |

---

## v2 → v3 audit (7 findings)

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | CRITICAL | **VWAP-reclaim never triggered** — streak counter was reset on cross before the entry check, so `streak_below >= ConfirmBars` was always false when `prev_close_above_vwap` was true. | Track `g_streak_*_at_prev` (snapshot BEFORE the latest bar updates the streak) and `g_streak_*_cur` (after). Entry condition is now `streak_below_at_prev >= ConfirmBars && streak_above_cur == 1 && bull_bar`. |
| 2 | HIGH | Signal evaluation ran on every tick → multiple decisions inside the same M1 bar were possible. | Added `NewM1BarClosed()` gate so signal logic runs exactly once per closed M1. |
| 3 | MEDIUM | No auto-flat before session close → positions could carry over into low-liquidity hours. | Optional `Inp_AutoFlatOnClose` (default true) closes everything N min before session close. |
| 4 | MEDIUM | No spread filter → wide spread spikes (news) inflated computed stop distance and ruined risk math. | Added `Inp_MaxSpreadPoints` filter; trades blocked when spread exceeds. |
| 5 | LOW | `g_open_ticket = trade.ResultDeal()` was unused (real tracking via `SelectOwnPosition`). | Removed. |
| 6 | LOW | `g_stat_blocked_*` counters incremented per tick → millions over years, misleading. | Now increment only inside the OnNewBar block, so once per evaluation cycle. |
| 7 | LOW | `lots` rounded via `MathFloor / step * step` but never `NormalizeDouble`'d → tiny float residues possible. | Applied `NormalizeDouble(.., 2)` after the floor. |

---

## v3 known-good behaviours (sanity verified by reading)

- `OnInit` rejects bad inputs and emits clear journal messages.
- `RolloverDay` resets every session-scoped field including the streak
  counters and the ORB/VWAP-reclaim "already-traded" flags.
- `OnTick`:
  - exits early on DD-kill (permanent), day-stop (until tomorrow),
    auto-flat trigger, cooldown, daily-trade cap, out-of-window, and
    wide-spread conditions in the correct order
  - manages open position (TP1 partial → BE) on every tick
  - signal evaluation **once per closed M1 bar**
- `ComputeSignal` enforces three independent gates per route: VWAP
  filter, EMA-trend filter, volume filter (for ORB) — all are
  toggleable via inputs.
- `OpenTrade` normalises every price level to broker `digits`, applies
  broker volume step and min/max, and logs every attempt.
- `ManageOpenPosition` re-selects the position before modifying SL,
  closes only up to but never exceeding remaining volume.
- `OnTradeTransaction` accumulates realised PnL on exit deals only
  (filters by `DEAL_ENTRY_OUT` / `_INOUT`), updates win/loss/consec
  counters consistently.
- `OnTester` prints the summary and returns the profit factor as a
  custom optimisation criterion.

---

## Open items for the next review (ChatGPT or human)

1. **News filter** — skip trades 5 min before/after scheduled high-impact
   news (Fed, NFP, CPI). Currently only spread filter is in place.
2. **MFE / MAE tracking** — per-trade max favourable/adverse excursion
   would help diagnose where stops are too tight or targets too tight.
3. **Trailing stop on the runner** — after TP1 partial, the remaining
   half rides to TP2 at the broker level. Optionally trail by ATR or
   by VWAP touch for a Maróy-style "VWAP exit" hybrid.
4. **Multi-symbol portability** — currently single-instance per chart;
   spawning multiple charts works but logging mixes magic numbers.
   A multi-symbol single-instance variant is a future iteration.
5. **Walk-forward optimisation harness** — the strategy tester's
   built-in optimiser can be used but does not split IS/OOS cleanly.
   A small Python wrapper that drives MT5 via WebRequest or files
   could enforce proper walk-forward windows.
6. **No fractional-lot guard** — if account currency conversion makes
   `loss_per_lot` very small for NQ ($1/point CFDs in JPY/AUD
   accounts), `risk_money / loss_per_lot` could exceed `max_lot`. The
   `if(lots > max_lot) lots = max_lot;` clamps it but the user is
   then over-risking on the broker's max-lot cap. Add a warning.
7. **Day rollover at 00:00 server time** while the EA is in the
   middle of a position — currently positions are not affected, but
   the day's "realised PnL" counter is wiped, which means the day-loss
   circuit could be evaded by a midnight rollover. Edge case.

These are non-blocking — the EA is functional and ready for a
real-tick backtest as-is. They are candidates for v4.
