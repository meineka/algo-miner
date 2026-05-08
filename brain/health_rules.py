"""
System Health Rules — walk-forward validation, regime coverage, logging.

DO:
  - Walk-Forward test: OOS performance >= 60% of IS performance
  - Strategy must be profitable in >= 2 different market phases (BULL + BEAR)
  - Minimum 30 closed trades for any rolling metric
  - Minimum 100 closed trades before parameter optimisation
  - Daily performance logging to detect live-vs-backtest drift
  - Parameter count guard: warn when free parameters > 3

DON'T:
  - Optimise on fewer than 100 trades
  - Use more than 3 free parameters
  - Go live when no BEAR-regime data was tested in the backtest
  - Change one parameter and re-optimise everything else
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Data containers
# ══════════════════════════════════════════════════════════════════════

@dataclass
class WalkForwardResult:
    is_pnl:       float    # in-sample total PnL
    oos_pnl:      float    # out-of-sample total PnL
    is_trades:    int
    oos_trades:   int
    ratio:        float    # oos_pnl / is_pnl  (NaN if is=0)
    passed:       bool     # oos >= min_ratio * is
    min_ratio:    float


@dataclass
class RegimeCoverageResult:
    regimes_seen:       List[str]        # distinct regime.trend values with trades
    profitable_regimes: List[str]        # regimes where total PnL > 0
    bear_tested:        bool
    passed:             bool
    min_profitable:     int


@dataclass
class HealthReport:
    walk_forward:     Optional[WalkForwardResult]
    regime_coverage:  Optional[RegimeCoverageResult]
    trade_count:      int
    param_count_ok:   bool
    param_count:      int
    max_free_params:  int
    reasons:          List[str] = field(default_factory=list)

    @property
    def go_live_approved(self) -> bool:
        return len(self.reasons) == 0

    def summary(self) -> str:
        lines = ["=" * 52, "  SYSTEM HEALTH REPORT", "=" * 52]
        status = "GO-LIVE ✓" if self.go_live_approved else "GO-LIVE BLOCKED ✗"
        lines.append(f"  Status             : {status}")
        lines.append(f"  Closed trades      : {self.trade_count}")
        lines.append(f"  Free params        : {self.param_count} / {self.max_free_params} allowed")
        if self.walk_forward:
            wf = self.walk_forward
            lines.append(
                f"  Walk-forward ratio : {wf.ratio:.2%}  "
                f"(IS={wf.is_pnl:+.2f}, OOS={wf.oos_pnl:+.2f})  "
                f"{'PASS' if wf.passed else 'FAIL'}"
            )
        if self.regime_coverage:
            rc = self.regime_coverage
            lines.append(
                f"  Regime coverage    : profitable={rc.profitable_regimes}  "
                f"bear_tested={rc.bear_tested}  "
                f"{'PASS' if rc.passed else 'FAIL'}"
            )
        if self.reasons:
            lines.append("  Issues:")
            for r in self.reasons:
                lines.append(f"    • {r}")
        lines.append("=" * 52)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# HealthRules
# ══════════════════════════════════════════════════════════════════════

class HealthRules:
    """
    Validates a completed simulation against the System Health rules.

    Parameters
    ----------
    walk_forward_split    : fraction of bars to treat as IS (rest = OOS)
    min_oos_ratio         : OOS PnL must be >= this fraction of IS PnL
    min_profitable_regimes: strategy must be profitable in this many regimes
    min_trades_metrics    : min closed trades for any quality metric
    min_trades_optimise   : min closed trades before parameter optimisation
    max_free_params       : warn above this many free parameters
    log_dir               : directory for daily performance log (None = off)
    """

    def __init__(
        self,
        walk_forward_split:     float = 0.70,
        min_oos_ratio:          float = 0.60,
        min_profitable_regimes: int   = 2,
        min_trades_metrics:     int   = 30,
        min_trades_optimise:    int   = 100,
        max_free_params:        int   = 3,
        log_dir:                Optional[str] = None,
    ):
        self.walk_forward_split     = walk_forward_split
        self.min_oos_ratio          = min_oos_ratio
        self.min_profitable_regimes = min_profitable_regimes
        self.min_trades_metrics     = min_trades_metrics
        self.min_trades_optimise    = min_trades_optimise
        self.max_free_params        = max_free_params
        self._log_dir               = Path(log_dir) if log_dir else None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def validate(
        self,
        trades:       list,           # List[Trade] — closed trades only
        df:           pd.DataFrame,   # full OHLC DataFrame used in simulation
        regimes:      list,           # List[RegimeState | None] — one per bar
        n_free_params: int  = 0,      # number of optimised parameters
    ) -> HealthReport:
        """Run all health checks and return a HealthReport."""
        reasons: List[str] = []

        trade_count = len(trades)

        # ── Parameter count guard ─────────────────────────────────────
        param_ok = n_free_params <= self.max_free_params
        if not param_ok:
            reasons.append(
                f"[Params] {n_free_params} free parameters > max {self.max_free_params} "
                f"— overfitting risk is high"
            )

        if n_free_params > 0 and trade_count < self.min_trades_optimise:
            reasons.append(
                f"[Params] Only {trade_count} trades — need {self.min_trades_optimise} "
                f"before optimising parameters"
            )

        # ── Minimum trade count ───────────────────────────────────────
        if trade_count < self.min_trades_metrics:
            reasons.append(
                f"[Trades] {trade_count} closed trades < minimum {self.min_trades_metrics} "
                f"— metrics are not statistically reliable"
            )

        # ── Walk-forward ──────────────────────────────────────────────
        wf_result: Optional[WalkForwardResult] = None
        if trade_count >= self.min_trades_metrics:
            wf_result = self._walk_forward(trades, df)
            if not wf_result.passed:
                reasons.append(
                    f"[WalkForward] OOS/IS ratio {wf_result.ratio:.2%} < "
                    f"minimum {self.min_oos_ratio:.0%} — strategy is overfit"
                )

        # ── Regime coverage ───────────────────────────────────────────
        rc_result: Optional[RegimeCoverageResult] = None
        if regimes and trade_count >= self.min_trades_metrics:
            rc_result = self._regime_coverage(trades, regimes)
            if not rc_result.bear_tested:
                reasons.append(
                    "[Regime] No BEAR-market trades in backtest — "
                    "do NOT go live without bear-market validation"
                )
            if not rc_result.passed:
                reasons.append(
                    f"[Regime] Strategy profitable in only {len(rc_result.profitable_regimes)} "
                    f"regime(s) {rc_result.profitable_regimes} — need {self.min_profitable_regimes}"
                )

        return HealthReport(
            walk_forward     = wf_result,
            regime_coverage  = rc_result,
            trade_count      = trade_count,
            param_count_ok   = param_ok,
            param_count      = n_free_params,
            max_free_params  = self.max_free_params,
            reasons          = reasons,
        )

    def log_daily(
        self,
        today_pnl:     float,
        today_trades:  int,
        equity:        float,
        backtest_avg_daily_pnl: Optional[float] = None,
    ) -> None:
        """
        Append one line to the daily performance log.
        Flags live drift if today's PnL is far below the backtest average.
        """
        if self._log_dir is None:
            return
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / "daily_performance.log"

        drift_flag = ""
        if backtest_avg_daily_pnl is not None and backtest_avg_daily_pnl > 0:
            ratio = today_pnl / backtest_avg_daily_pnl
            if ratio < 0.5:
                drift_flag = "  [DRIFT WARNING]"

        line = (
            f"{date.today().isoformat()}  "
            f"pnl={today_pnl:+.4f}  "
            f"trades={today_trades}  "
            f"equity={equity:.2f}"
            f"{drift_flag}\n"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
        if drift_flag:
            logger.warning("Daily PnL drift detected: %s", line.strip())

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _walk_forward(
        self, trades: list, df: pd.DataFrame
    ) -> WalkForwardResult:
        """Split trades at walk_forward_split by bar index, compare IS vs OOS PnL."""
        split_bar = int(len(df) * self.walk_forward_split)

        is_trades  = [t for t in trades if t.entry_bar <  split_bar]
        oos_trades = [t for t in trades if t.entry_bar >= split_bar]

        is_pnl  = sum(t.pnl for t in is_trades  if t.pnl is not None)
        oos_pnl = sum(t.pnl for t in oos_trades if t.pnl is not None)

        if is_pnl == 0:
            ratio = float("nan")
            passed = oos_pnl >= 0   # if IS broke even, OOS just needs to not lose
        elif is_pnl < 0:
            # IS was negative — OOS doing less-bad counts as improvement
            ratio = oos_pnl / abs(is_pnl)
            passed = oos_pnl > is_pnl
        else:
            ratio = oos_pnl / is_pnl
            passed = ratio >= self.min_oos_ratio

        return WalkForwardResult(
            is_pnl    = round(is_pnl, 4),
            oos_pnl   = round(oos_pnl, 4),
            is_trades = len(is_trades),
            oos_trades= len(oos_trades),
            ratio     = ratio,
            passed    = passed,
            min_ratio = self.min_oos_ratio,
        )

    def _regime_coverage(
        self, trades: list, regimes: list
    ) -> RegimeCoverageResult:
        """Check how many distinct regimes the strategy is profitable in."""
        # Map each trade to the regime at its entry bar
        regime_pnl: Dict[str, float] = {}
        for t in trades:
            if t.pnl is None:
                continue
            r = regimes[t.entry_bar] if t.entry_bar < len(regimes) else None
            regime_name = r.trend if r is not None else "UNKNOWN"
            regime_pnl[regime_name] = regime_pnl.get(regime_name, 0.0) + t.pnl

        regimes_seen       = list(regime_pnl.keys())
        profitable_regimes = [k for k, v in regime_pnl.items() if v > 0]
        bear_tested        = "BEAR" in regimes_seen

        passed = len(profitable_regimes) >= self.min_profitable_regimes

        return RegimeCoverageResult(
            regimes_seen       = regimes_seen,
            profitable_regimes = profitable_regimes,
            bear_tested        = bear_tested,
            passed             = passed,
            min_profitable     = self.min_profitable_regimes,
        )
