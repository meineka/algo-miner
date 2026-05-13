"""
Walk-Forward Tournament — mines strategy variants on IS data, validates on OOS.

Pipeline
────────
  1. Split df  →  IS window (train)  +  OOS window (forward test)
  2. Run all genomes on IS  →  score each, filter by HealthRules
  3. Take top_k survivors
  4. Run survivors on OOS  →  final ranking on never-seen data
  5. Champion  = #1 on OOS
     Challengers = #2..top_k, waiting for next rotation

Score formula (both IS and OOS):
  score = Sharpe × ProfitFactor × (1 - MaxDrawdown) × log(1 + n_trades)
  → rewards risk-adjusted returns, punishes drawdown, requires volume
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

from .strategy_genome import StrategyGenome
from .health_rules import HealthRules


# ══════════════════════════════════════════════════════════════════════
# Result containers
# ══════════════════════════════════════════════════════════════════════

@dataclass
class GenomeScore:
    genome:       StrategyGenome
    n_trades:     int
    sharpe:       float
    profit_factor: float
    max_drawdown: float
    win_rate:     float
    total_pnl:    float
    score:        float         # composite — higher is better
    health_ok:    bool
    health_notes: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        health = "✓" if self.health_ok else "✗"
        return (
            f"{health} score={self.score:7.3f}  "
            f"PnL={self.total_pnl:+8.2f}  "
            f"Sharpe={self.sharpe:.2f}  "
            f"PF={self.profit_factor:.2f}  "
            f"DD={self.max_drawdown*100:.1f}%  "
            f"trades={self.n_trades}  "
            f"| {self.genome}"
        )


@dataclass
class TournamentResult:
    champion:     Optional[GenomeScore]
    challengers:  List[GenomeScore]     # ranked 2..top_k
    all_is:       List[GenomeScore]     # full IS ranking (for analysis)
    all_oos:      List[GenomeScore]     # full OOS ranking
    is_bars:      int
    oos_bars:     int
    n_genomes:    int
    elapsed_sec:  float

    def summary(self) -> str:
        lines = ["=" * 70, "  TOURNAMENT RESULTS", "=" * 70]
        lines.append(f"  Genomes tested : {self.n_genomes}")
        lines.append(f"  IS bars        : {self.is_bars}  |  OOS bars: {self.oos_bars}")
        lines.append(f"  Runtime        : {self.elapsed_sec:.1f}s")
        lines.append("")

        if self.champion:
            lines.append("  CHAMPION (OOS):")
            lines.append(f"    {self.champion}")
        else:
            lines.append("  NO CHAMPION — no genome passed health checks on OOS")

        if self.challengers:
            lines.append(f"\n  CHALLENGERS ({len(self.challengers)}):")
            for i, c in enumerate(self.challengers, 1):
                lines.append(f"    #{i+1}  {c}")

        # IS vs OOS consistency check for champion
        if self.champion and self.all_is:
            champ_is = next(
                (s for s in self.all_is
                 if s.genome.name == self.champion.genome.name), None
            )
            if champ_is:
                ratio = (self.champion.total_pnl / champ_is.total_pnl
                         if champ_is.total_pnl > 0 else float("nan"))
                lines.append(
                    f"\n  Champion IS PnL={champ_is.total_pnl:+.2f}  "
                    f"OOS PnL={self.champion.total_pnl:+.2f}  "
                    f"OOS/IS ratio={ratio:.2%}"
                )
        lines.append("=" * 70)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# Tournament
# ══════════════════════════════════════════════════════════════════════

class Tournament:
    """
    Walk-forward tournament runner.

    Parameters
    ----------
    is_split      : fraction of bars used as in-sample training window
    top_k         : how many IS survivors are tested on OOS
    initial_capital
    commission_pct
    allow_short
    min_trades    : genome must produce at least this many trades to qualify
    verbose       : print progress
    """

    def __init__(
        self,
        is_split:        float = 0.70,
        top_k:           int   = 10,
        initial_capital: float = 10_000.0,
        commission_pct:  float = 0.001,
        allow_short:     bool  = True,
        min_trades:      int   = 5,
        verbose:         bool  = False,
        style:           str   = "classic",
    ):
        self.is_split        = is_split
        self.top_k           = top_k
        self.initial_capital = initial_capital
        self.commission_pct  = commission_pct
        self.allow_short     = allow_short
        self.min_trades      = min_trades
        self.verbose         = verbose
        self.style           = style
        self._health         = HealthRules(min_trades_metrics=self.min_trades)

    # ------------------------------------------------------------------ #

    def run(
        self,
        df:      pd.DataFrame,
        genomes: List[StrategyGenome],
    ) -> TournamentResult:
        t0 = time.time()
        split = int(len(df) * self.is_split)
        df_is  = df.iloc[:split].copy()
        df_oos = df.iloc[split:].copy()

        if self.verbose:
            print(f"  IS:  {len(df_is)} bars  |  OOS: {len(df_oos)} bars")
            print(f"  Testing {len(genomes)} genomes on IS...")

        # ── Phase 1: IS run ──────────────────────────────────────────
        is_scores: List[GenomeScore] = []
        for i, genome in enumerate(genomes):
            score = self._evaluate(genome, df_is)
            is_scores.append(score)
            if self.verbose and (i + 1) % 10 == 0:
                print(f"    {i+1}/{len(genomes)} done  "
                      f"best so far: {max(s.score for s in is_scores):.3f}")

        is_scores.sort(key=lambda s: s.score, reverse=True)

        # Keep only healthy survivors for OOS
        survivors = [s for s in is_scores if s.health_ok and s.n_trades >= self.min_trades]
        survivors = survivors[:self.top_k]

        if self.verbose:
            print(f"\n  IS survivors (health_ok, min {self.min_trades} trades): "
                  f"{len(survivors)}/{len(is_scores)}")
            print(f"  Running top {len(survivors)} on OOS...")

        # ── Phase 2: OOS run ─────────────────────────────────────────
        oos_scores: List[GenomeScore] = []
        for gs in survivors:
            score = self._evaluate(gs.genome, df_oos)
            oos_scores.append(score)

        oos_scores.sort(key=lambda s: s.score, reverse=True)

        champion    = oos_scores[0]  if oos_scores else None
        challengers = oos_scores[1:] if len(oos_scores) > 1 else []

        return TournamentResult(
            champion     = champion,
            challengers  = challengers,
            all_is       = is_scores,
            all_oos      = oos_scores,
            is_bars      = len(df_is),
            oos_bars     = len(df_oos),
            n_genomes    = len(genomes),
            elapsed_sec  = time.time() - t0,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _evaluate(self, genome: StrategyGenome, df: pd.DataFrame) -> GenomeScore:
        """Run one genome on one data window and compute composite score."""
        from .config import QualityConfig
        from .quality_checks import RegimeFilter
        from simulator.trade_simulator import TradeSimulator

        cfg = self._genome_to_config(genome)
        sim = TradeSimulator(
            initial_capital  = self.initial_capital,
            commission_pct   = self.commission_pct,
            allow_short      = self.allow_short,
            take_profit_mult = genome.take_profit_mult,
            config           = cfg,
            genome           = genome,
            style            = self.style,
        )
        try:
            result = sim.run(df)
        except Exception:
            return self._zero_score(genome)

        ct = result.closed_trades
        if len(ct) < self.min_trades:
            return self._zero_score(genome)

        # Health check
        regimes = RegimeFilter().detect_all(df)
        health  = self._health.validate(ct, df, regimes, n_free_params=0)

        sharpe = self._sharpe(ct)
        pf     = result.profit_factor
        mdd    = result.max_drawdown
        n      = len(ct)

        score = self._composite(sharpe, pf, mdd, n)

        return GenomeScore(
            genome        = genome,
            n_trades      = n,
            sharpe        = round(sharpe, 3),
            profit_factor = round(pf, 3),
            max_drawdown  = round(mdd, 4),
            win_rate      = round(result.win_rate, 3),
            total_pnl     = round(result.total_pnl, 2),
            score         = round(score, 4),
            health_ok     = health.go_live_approved,
            health_notes  = health.reasons,
        )

    @staticmethod
    def _composite(sharpe: float, pf: float, mdd: float, n: int) -> float:
        """
        Composite score — rewards risk-adjusted edge, punishes drawdown,
        requires sufficient trade volume.
          score = Sharpe × PF_capped × (1 - DD) × volume_bonus
        """
        if sharpe <= 0 or pf <= 1.0:
            return 0.0
        pf_cap      = min(pf, 5.0)                    # cap outliers
        dd_penalty  = max(0.0, 1.0 - mdd)
        vol_bonus   = math.log1p(n)                    # log(1+trades)
        return sharpe * pf_cap * dd_penalty * vol_bonus

    @staticmethod
    def _sharpe(closed_trades) -> float:
        import numpy as np
        pnls = [t.pnl for t in closed_trades if t.pnl is not None]
        if len(pnls) < 2:
            return 0.0
        arr = np.array(pnls, dtype=float)
        std = arr.std(ddof=1)
        return float((arr.mean() / std) * math.sqrt(252)) if std > 0 else 0.0

    @staticmethod
    def _zero_score(genome: StrategyGenome) -> GenomeScore:
        return GenomeScore(
            genome=genome, n_trades=0, sharpe=0.0, profit_factor=0.0,
            max_drawdown=0.0, win_rate=0.0, total_pnl=0.0, score=0.0,
            health_ok=False, health_notes=["too few trades"],
        )

    def _genome_to_config(self, genome: StrategyGenome):
        """Convert genome parameters to a QualityConfig for backtesting."""
        from dataclasses import replace
        from .config import LOOSE

        return replace(
            LOOSE,
            min_agreement          = genome.min_agreement,
            atr_stop_multiplier    = genome.atr_stop_mult,
            max_risk_pct           = genome.max_risk_pct,
            max_daily_loss_pct     = genome.max_daily_loss_pct,
            cooldown_bars          = genome.cooldown_bars,
            llm_enabled            = False,
            # Session filter disabled for mining — it's designed for live intraday
            # trading.  Backtesting on historical OHLC spans all hours.
            disable_session_filter = True,
        )
