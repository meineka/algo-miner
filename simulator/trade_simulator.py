"""
Trade Simulator — event-driven bar-by-bar backtester.

Pipeline per bar:
  1. Prerequisites.check()       data valid?
  2. Rules.evaluate()            raw signal + individual rule votes
  3. QualityChecks.check()       6-layer gate → also computes position size
  4. Execute trade / update state
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from brain.prerequisites import Prerequisites
from brain.rules import Rules, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from brain.quality_checks import QualityChecks


# ══════════════════════════════════════════════════════════════════════
# Trade & Result data classes
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    entry_bar:   int
    entry_time:  pd.Timestamp
    direction:   str            # 'LONG' | 'SHORT'
    entry_price: float
    size:        float
    stop_price:  float          # pre-computed stop level
    tp_price:    float          # pre-computed take-profit level
    exit_bar:    Optional[int]           = None
    exit_time:   Optional[pd.Timestamp]  = None
    exit_price:  Optional[float]         = None
    exit_reason: Optional[str]           = None
    pnl:         Optional[float]         = None
    pnl_pct:     Optional[float]         = None

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    def close(
        self, bar: int, timestamp: pd.Timestamp,
        price: float, reason: str = "signal"
    ) -> None:
        self.exit_bar    = bar
        self.exit_time   = timestamp
        self.exit_price  = price
        self.exit_reason = reason
        sign = 1 if self.direction == "LONG" else -1
        self.pnl     = sign * (price - self.entry_price) * self.size
        self.pnl_pct = self.pnl / (self.entry_price * self.size)


@dataclass
class SimulationResult:
    trades:          List[Trade]
    equity_curve:    List[float]
    signals_df:      pd.DataFrame
    initial_capital: float

    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self.trades if not t.is_open]

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def win_rate(self) -> float:
        ct = self.closed_trades
        return sum(1 for t in ct if (t.pnl or 0) > 0) / len(ct) if ct else 0.0

    @property
    def max_drawdown(self) -> float:
        peak, mdd = self.initial_capital, 0.0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            mdd  = max(mdd, (peak - eq) / peak)
        return mdd

    @property
    def profit_factor(self) -> float:
        wins  = sum(t.pnl for t in self.closed_trades if (t.pnl or 0) > 0)
        loss  = abs(sum(t.pnl for t in self.closed_trades if (t.pnl or 0) < 0))
        return wins / loss if loss > 0 else float("inf")

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else self.initial_capital

    @property
    def return_pct(self) -> float:
        return (self.final_equity - self.initial_capital) / self.initial_capital

    def summary(self) -> str:
        ct = self.closed_trades
        wins = sum(1 for t in ct if (t.pnl or 0) > 0)
        by_reason = {}
        for t in ct:
            by_reason[t.exit_reason] = by_reason.get(t.exit_reason, 0) + 1
        reason_str = "  ".join(f"{k}:{v}" for k, v in sorted(by_reason.items()))
        return "\n".join([
            "=" * 50,
            "  SIMULATION RESULTS",
            "=" * 50,
            f"  Initial capital  : {self.initial_capital:>12,.2f}",
            f"  Final equity     : {self.final_equity:>12,.2f}",
            f"  Total PnL        : {self.total_pnl:>+12,.2f}",
            f"  Return           : {self.return_pct*100:>11.2f}%",
            f"  Max Drawdown     : {self.max_drawdown*100:>11.2f}%",
            f"  Profit Factor    : {self.profit_factor:>12.2f}",
            f"  Total trades     : {len(ct):>12}",
            f"  Win / Loss       : {wins:>5} / {len(ct)-wins:<5}",
            f"  Win rate         : {self.win_rate*100:>11.2f}%",
            f"  Exit reasons     : {reason_str}",
            "=" * 50,
        ])

    def trades_df(self) -> pd.DataFrame:
        if not self.closed_trades:
            return pd.DataFrame()
        return pd.DataFrame([{
            "entry_time":  t.entry_time,
            "exit_time":   t.exit_time,
            "direction":   t.direction,
            "entry_price": t.entry_price,
            "exit_price":  t.exit_price,
            "size":        t.size,
            "pnl":         round(t.pnl, 4),
            "pnl_pct":     round(t.pnl_pct * 100, 3),
            "exit_reason": t.exit_reason,
        } for t in self.closed_trades])


# ══════════════════════════════════════════════════════════════════════
# TradeSimulator
# ══════════════════════════════════════════════════════════════════════

class TradeSimulator:
    """
    Bar-by-bar trade simulator wired to the Brain quality-check pipeline.

    Parameters
    ----------
    initial_capital    : starting equity
    commission_pct     : one-way commission as fraction of trade value
    allow_short        : whether SELL signals open short positions
    stop_loss_atr_mult : stop distance in ATR multiples (fed to QualityChecks sizer)
    take_profit_mult   : take-profit = stop_loss * this multiplier (R:R ratio)

    Quality gate params are passed through to QualityChecks — see that class
    for full documentation.
    """

    def __init__(
        self,
        initial_capital:        float = 10_000.0,
        commission_pct:         float = 0.001,
        allow_short:            bool  = True,
        stop_loss_atr_mult:     float = 2.0,
        take_profit_mult:       float = 2.0,    # 2:1 R:R by default
        # QualityChecks params
        max_risk_pct:           float = 0.02,
        block_counter_trend:    bool  = True,
        min_agreement:          int   = 3,
        max_daily_loss_pct:     float = 0.02,
        max_portfolio_heat_pct: float = 0.06,
        health_window:          int   = 30,
        min_sharpe:             float = 0.5,
        min_profit_factor:      float = 1.1,
        max_drawdown_pct:       float = 0.10,
        max_consecutive_losses: int   = 4,
        cooldown_bars:          int   = 2,
    ):
        self.initial_capital    = initial_capital
        self.commission_pct     = commission_pct
        self.allow_short        = allow_short
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.take_profit_mult   = take_profit_mult

        self._prereqs = Prerequisites()
        self._rules   = Rules()
        self._quality = QualityChecks(
            block_counter_trend    = block_counter_trend,
            min_agreement          = min_agreement,
            max_daily_loss_pct     = max_daily_loss_pct,
            max_portfolio_heat_pct = max_portfolio_heat_pct,
            health_window          = health_window,
            min_sharpe             = min_sharpe,
            min_profit_factor      = min_profit_factor,
            max_drawdown_pct       = max_drawdown_pct,
            max_consecutive_losses = max_consecutive_losses,
            cooldown_bars          = cooldown_bars,
            max_risk_pct           = max_risk_pct,
            atr_stop_multiplier    = stop_loss_atr_mult,
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(self, df: pd.DataFrame, verbose: bool = False) -> SimulationResult:
        prereq = self._prereqs.check(df)
        if not prereq.passed:
            raise ValueError(f"Prerequisites failed:\n{prereq}")

        signals_df = self._rules.evaluate(df)
        rule_cols  = [c for c in signals_df.columns if c not in ("vote_sum", "signal")]

        equity           = self.initial_capital
        equity_curve     = [equity]
        all_trades: List[Trade]  = []
        closed_trades:   List[Trade] = []
        open_trade: Optional[Trade]  = None

        consecutive_losses = 0
        bars_since_trade   = 999
        daily_pnl          = 0.0
        current_date       = df.index[0].date() if len(df) > 0 else None

        for i in range(len(df)):
            bar       = df.iloc[i]
            signal    = int(signals_df["signal"].iloc[i])
            ts        = df.index[i]
            bar_date  = ts.date()

            # Reset daily PnL at start of new day
            if bar_date != current_date:
                daily_pnl    = 0.0
                current_date = bar_date

            # ── Manage open position ──────────────────────────────────
            if open_trade is not None:
                exit_price, exit_reason = self._check_exit(open_trade, bar, signal)
                if exit_price is not None:
                    open_trade.close(i, ts, exit_price, exit_reason)
                    commission = self._commission(open_trade)
                    equity    += open_trade.pnl - commission
                    daily_pnl += open_trade.pnl - commission
                    equity_curve.append(round(equity, 4))
                    closed_trades.append(open_trade)

                    if (open_trade.pnl or 0) < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0
                    bars_since_trade = 0

                    if verbose:
                        print(f"[{ts}] CLOSE {open_trade.direction} "
                              f"@ {exit_price:.4f}  PnL={open_trade.pnl:+.2f} "
                              f"({exit_reason})")
                    open_trade = None

            bars_since_trade += 1

            # ── Try to open new position ──────────────────────────────
            if open_trade is None:
                atr          = self._quality._atr(df, i)
                portfolio_heat = 0.0   # no open trade at this point

                rule_votes = signals_df[rule_cols].iloc[i]
                qc = self._quality.check(
                    signal               = signal,
                    rule_votes           = rule_votes,
                    df                   = df,
                    bar_index            = i,
                    equity               = equity,
                    equity_curve         = equity_curve,
                    closed_trades        = closed_trades,
                    consecutive_losses   = consecutive_losses,
                    bars_since_last_trade= bars_since_trade,
                    daily_pnl            = daily_pnl,
                    portfolio_heat       = portfolio_heat,
                )

                if qc.approved:
                    direction = "LONG" if signal == SIGNAL_BUY else "SHORT"
                    if direction == "SHORT" and not self.allow_short:
                        continue

                    entry_px  = float(bar["close"])
                    atr_val   = atr or entry_px * 0.01
                    stop_dist = atr_val * self.stop_loss_atr_mult

                    if direction == "LONG":
                        stop_px = entry_px - stop_dist
                        tp_px   = entry_px + stop_dist * self.take_profit_mult
                    else:
                        stop_px = entry_px + stop_dist
                        tp_px   = entry_px - stop_dist * self.take_profit_mult

                    trade = Trade(
                        entry_bar   = i,
                        entry_time  = ts,
                        direction   = direction,
                        entry_price = entry_px,
                        size        = qc.size,       # ← from QualityChecks sizer
                        stop_price  = round(stop_px, 4),
                        tp_price    = round(tp_px, 4),
                    )
                    all_trades.append(trade)
                    open_trade       = trade
                    bars_since_trade = 0

                    if verbose:
                        regime_str = f" [{qc.regime}]" if qc.regime else ""
                        print(f"[{ts}] OPEN {direction} @ {entry_px:.4f}  "
                              f"size={qc.size:.4f}  SL={stop_px:.4f}  "
                              f"TP={tp_px:.4f}{regime_str}")

        # Close any remaining open position at last bar
        if open_trade is not None:
            last = df.iloc[-1]
            open_trade.close(len(df) - 1, df.index[-1], float(last["close"]), "end_of_data")
            equity += open_trade.pnl - self._commission(open_trade)
            equity_curve.append(round(equity, 4))
            closed_trades.append(open_trade)

        return SimulationResult(
            trades          = all_trades,
            equity_curve    = equity_curve,
            signals_df      = signals_df,
            initial_capital = self.initial_capital,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_exit(
        self, trade: Trade, bar: pd.Series, new_signal: int
    ) -> tuple[Optional[float], Optional[str]]:
        """
        Returns (exit_price, reason) or (None, None) if no exit triggered.
        Priority: stop-loss > take-profit > signal flip.
        """
        low  = float(bar["low"])
        high = float(bar["high"])

        if trade.direction == "LONG":
            if low <= trade.stop_price:
                return trade.stop_price, "stop_loss"
            if high >= trade.tp_price:
                return trade.tp_price, "take_profit"
            if new_signal == SIGNAL_SELL:
                return float(bar["close"]), "signal_flip"
        else:  # SHORT
            if high >= trade.stop_price:
                return trade.stop_price, "stop_loss"
            if low <= trade.tp_price:
                return trade.tp_price, "take_profit"
            if new_signal == SIGNAL_BUY:
                return float(bar["close"]), "signal_flip"

        return None, None

    def _commission(self, trade: Trade) -> float:
        return trade.entry_price * trade.size * self.commission_pct
