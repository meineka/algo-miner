"""
Trade Simulator — event-driven bar-by-bar backtester.

Pipeline per bar:
  1. Prerequisites.check()       → data valid?
  2. Rules.evaluate()            → raw signal
  3. QualityChecks.check()       → signal approved?
  4. Execute trade / update state
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd

from brain.prerequisites import Prerequisites
from brain.rules import Rules, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from brain.quality_checks import QualityChecks


@dataclass
class Trade:
    entry_bar:   int
    entry_time:  pd.Timestamp
    direction:   str          # 'LONG' | 'SHORT'
    entry_price: float
    size:        float        # units / contracts
    exit_bar:    Optional[int]        = None
    exit_time:   Optional[pd.Timestamp] = None
    exit_price:  Optional[float]      = None
    pnl:         Optional[float]      = None
    pnl_pct:     Optional[float]      = None

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    def close(self, bar: int, timestamp: pd.Timestamp, price: float) -> None:
        self.exit_bar   = bar
        self.exit_time  = timestamp
        self.exit_price = price
        if self.direction == "LONG":
            self.pnl = (price - self.entry_price) * self.size
        else:
            self.pnl = (self.entry_price - price) * self.size
        self.pnl_pct = self.pnl / (self.entry_price * self.size)


@dataclass
class SimulationResult:
    trades:          List[Trade]
    equity_curve:    List[float]
    signals_df:      pd.DataFrame
    initial_capital: float

    # ---- performance metrics ---- #
    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self.trades if not t.is_open]

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def win_rate(self) -> float:
        wins = sum(1 for t in self.closed_trades if (t.pnl or 0) > 0)
        n = len(self.closed_trades)
        return wins / n if n > 0 else 0.0

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        mdd = 0.0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            mdd  = max(mdd, (peak - eq) / peak)
        return mdd

    @property
    def profit_factor(self) -> float:
        gross_win  = sum(t.pnl for t in self.closed_trades if (t.pnl or 0) > 0)
        gross_loss = abs(sum(t.pnl for t in self.closed_trades if (t.pnl or 0) < 0))
        return gross_win / gross_loss if gross_loss > 0 else float("inf")

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else self.initial_capital

    @property
    def return_pct(self) -> float:
        return (self.final_equity - self.initial_capital) / self.initial_capital

    def summary(self) -> str:
        ct = self.closed_trades
        lines = [
            "=" * 48,
            "  SIMULATION RESULTS",
            "=" * 48,
            f"  Initial capital : {self.initial_capital:>12,.2f}",
            f"  Final equity    : {self.final_equity:>12,.2f}",
            f"  Total PnL       : {self.total_pnl:>+12,.2f}",
            f"  Return          : {self.return_pct*100:>11.2f}%",
            f"  Max Drawdown    : {self.max_drawdown*100:>11.2f}%",
            f"  Profit Factor   : {self.profit_factor:>12.2f}",
            f"  Total trades    : {len(ct):>12}",
            f"  Win rate        : {self.win_rate*100:>11.2f}%",
            "=" * 48,
        ]
        return "\n".join(lines)

    def trades_df(self) -> pd.DataFrame:
        if not self.closed_trades:
            return pd.DataFrame()
        rows = []
        for t in self.closed_trades:
            rows.append({
                "entry_time":  t.entry_time,
                "exit_time":   t.exit_time,
                "direction":   t.direction,
                "entry_price": t.entry_price,
                "exit_price":  t.exit_price,
                "size":        t.size,
                "pnl":         round(t.pnl, 4),
                "pnl_pct":     round(t.pnl_pct * 100, 3),
            })
        return pd.DataFrame(rows)


class TradeSimulator:
    """
    Bar-by-bar trade simulator.

    Parameters
    ----------
    initial_capital : starting equity in account currency
    position_size_pct : fraction of equity to risk per trade
    commission_pct  : round-trip commission as fraction of trade value
    allow_short     : whether SELL signals open short positions
    stop_loss_pct   : optional stop loss as fraction of entry price
    take_profit_pct : optional take profit as fraction of entry price
    """

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        position_size_pct: float = 0.10,
        commission_pct: float = 0.001,
        allow_short: bool = True,
        stop_loss_pct: Optional[float] = 0.02,
        take_profit_pct: Optional[float] = 0.04,
    ):
        self.initial_capital    = initial_capital
        self.position_size_pct  = position_size_pct
        self.commission_pct     = commission_pct
        self.allow_short        = allow_short
        self.stop_loss_pct      = stop_loss_pct
        self.take_profit_pct    = take_profit_pct

        self._prereqs = Prerequisites()
        self._rules   = Rules()
        self._quality = QualityChecks()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(self, df: pd.DataFrame, verbose: bool = False) -> SimulationResult:
        """
        Run the full simulation over the supplied OHLC DataFrame.
        Returns a SimulationResult with all trades and metrics.
        """
        prereq_result = self._prereqs.check(df)
        if not prereq_result.passed:
            raise ValueError(f"Prerequisites failed:\n{prereq_result}")

        signals_df = self._rules.evaluate(df)

        equity           = self.initial_capital
        equity_curve: List[float] = [equity]
        trades: List[Trade]       = []
        open_trade: Optional[Trade] = None
        consecutive_losses = 0
        bars_since_trade   = 999

        for i in range(len(df)):
            bar       = df.iloc[i]
            signal    = int(signals_df["signal"].iloc[i])
            timestamp = df.index[i]

            # ---- manage open position -------------------------------- #
            if open_trade is not None:
                close_reason = self._check_exit(open_trade, bar)
                if close_reason or self._signal_flips(open_trade, signal):
                    price = bar["open"]   # exit at next open (conservative)
                    open_trade.close(i, timestamp, price)
                    equity += open_trade.pnl - self._commission(open_trade)
                    equity_curve.append(round(equity, 4))
                    if (open_trade.pnl or 0) < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0
                    bars_since_trade = 0
                    if verbose:
                        print(f"[{timestamp}] CLOSE {open_trade.direction} "
                              f"@ {price:.4f}  PnL={open_trade.pnl:+.2f}")
                    open_trade = None

            bars_since_trade += 1

            # ---- try to open new position ---------------------------- #
            if open_trade is None:
                qc = self._quality.check(
                    signal, df, i, equity_curve, consecutive_losses, bars_since_trade
                )
                if qc.approved:
                    direction = "LONG" if signal == SIGNAL_BUY else "SHORT"
                    if direction == "SHORT" and not self.allow_short:
                        continue
                    size  = (equity * self.position_size_pct) / bar["close"]
                    trade = Trade(
                        entry_bar=i,
                        entry_time=timestamp,
                        direction=direction,
                        entry_price=bar["close"],
                        size=round(size, 6),
                    )
                    trades.append(trade)
                    open_trade   = trade
                    bars_since_trade = 0
                    if verbose:
                        print(f"[{timestamp}] OPEN  {direction} @ {bar['close']:.4f}  "
                              f"size={size:.4f}")

        # close any remaining open position at last bar
        if open_trade is not None:
            last_bar = df.iloc[-1]
            open_trade.close(len(df) - 1, df.index[-1], last_bar["close"])
            equity += open_trade.pnl - self._commission(open_trade)
            equity_curve.append(round(equity, 4))

        return SimulationResult(
            trades=trades,
            equity_curve=equity_curve,
            signals_df=signals_df,
            initial_capital=self.initial_capital,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_exit(self, trade: Trade, bar: pd.Series) -> bool:
        """Return True if stop-loss or take-profit is hit."""
        price = bar["close"]
        if trade.direction == "LONG":
            if self.stop_loss_pct and price <= trade.entry_price * (1 - self.stop_loss_pct):
                return True
            if self.take_profit_pct and price >= trade.entry_price * (1 + self.take_profit_pct):
                return True
        else:  # SHORT
            if self.stop_loss_pct and price >= trade.entry_price * (1 + self.stop_loss_pct):
                return True
            if self.take_profit_pct and price <= trade.entry_price * (1 - self.take_profit_pct):
                return True
        return False

    @staticmethod
    def _signal_flips(trade: Trade, signal: int) -> bool:
        """True if the new signal is the opposite of the current position."""
        return (trade.direction == "LONG" and signal == SIGNAL_SELL) or \
               (trade.direction == "SHORT" and signal == SIGNAL_BUY)

    def _commission(self, trade: Trade) -> float:
        return trade.entry_price * trade.size * self.commission_pct
