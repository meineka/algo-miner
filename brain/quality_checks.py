"""
Brain Quality Checks — post-signal sanity gates before an order is placed.

Checks run on the signal + the current portfolio state to prevent
over-trading, runaway losses, and regime mismatches.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd

from .rules import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD


@dataclass
class QualityResult:
    approved: bool
    reasons: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "✓ Signal approved" if self.approved else "✗ Signal blocked"
        if self.reasons:
            return status + ":\n" + "\n".join(f"  - {r}" for r in self.reasons)
        return status


class QualityChecks:
    """
    Gate that decides whether a raw signal should be acted upon.

    Parameters
    ----------
    max_drawdown_pct : float
        Kill-switch: block all BUY signals if portfolio drawdown exceeds this.
    min_atr_multiplier : float
        Minimum ATR-to-price ratio; skips signals in ultra-low-volatility regimes.
    max_consecutive_losses : int
        Pause after this many consecutive losing trades.
    cooldown_bars : int
        Minimum bars between two trades in the same direction.
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.10,
        min_atr_multiplier: float = 0.002,
        max_consecutive_losses: int = 3,
        cooldown_bars: int = 3,
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.min_atr_multiplier = min_atr_multiplier
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_bars = cooldown_bars

    def check(
        self,
        signal: int,
        df: pd.DataFrame,
        bar_index: int,
        equity_curve: List[float],
        consecutive_losses: int,
        bars_since_last_trade: int,
    ) -> QualityResult:
        """
        Approve or block the signal for the bar at `bar_index`.

        Parameters
        ----------
        signal            : SIGNAL_BUY, SIGNAL_SELL, or SIGNAL_HOLD
        df                : full OHLC DataFrame
        bar_index         : current bar position
        equity_curve      : list of equity values up to now
        consecutive_losses: count of losses in a row
        bars_since_last_trade: bars elapsed since last executed trade
        """
        if signal == SIGNAL_HOLD:
            return QualityResult(approved=False, reasons=["Signal is HOLD — nothing to do"])

        reasons: List[str] = []

        # 1. drawdown kill-switch
        if equity_curve and len(equity_curve) > 1:
            peak = max(equity_curve)
            current = equity_curve[-1]
            dd = (peak - current) / peak
            if dd >= self.max_drawdown_pct:
                reasons.append(
                    f"Drawdown {dd*100:.1f}% ≥ max {self.max_drawdown_pct*100:.1f}%"
                )

        # 2. consecutive-loss circuit-breaker
        if consecutive_losses >= self.max_consecutive_losses:
            reasons.append(
                f"Consecutive losses {consecutive_losses} ≥ limit {self.max_consecutive_losses}"
            )

        # 3. cooldown
        if bars_since_last_trade < self.cooldown_bars:
            reasons.append(
                f"Only {bars_since_last_trade} bars since last trade "
                f"(cooldown: {self.cooldown_bars})"
            )

        # 4. minimum volatility check via ATR
        atr = self._atr(df, bar_index)
        if atr is not None:
            close = df["close"].iloc[bar_index]
            if close > 0 and (atr / close) < self.min_atr_multiplier:
                reasons.append(
                    f"ATR/price {atr/close:.4f} < min {self.min_atr_multiplier} "
                    "(low-volatility regime)"
                )

        # 5. no short selling below zero (sanity)
        if signal == SIGNAL_SELL and equity_curve and equity_curve[-1] <= 0:
            reasons.append("Equity ≤ 0, cannot go short")

        return QualityResult(approved=len(reasons) == 0, reasons=reasons)

    # ------------------------------------------------------------------ #

    def _atr(self, df: pd.DataFrame, bar_index: int, period: int = 14) -> Optional[float]:
        """Average True Range up to bar_index."""
        start = max(0, bar_index - period * 2)
        window = df.iloc[start : bar_index + 1]
        if len(window) < 2:
            return None
        tr = pd.concat([
            window["high"] - window["low"],
            (window["high"] - window["close"].shift()).abs(),
            (window["low"]  - window["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])
