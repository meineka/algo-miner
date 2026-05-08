"""
Trade Simulator — event-driven bar-by-bar backtester.

Pipeline per bar:
  1. Prerequisites.check()       data valid?
  2. Rules.evaluate()            raw signal + individual rule votes
  3. QualityChecks.check()       6-layer deterministic gate + position sizing
  4. LLMValidator.validate()     Layer 7 — AI sanity check ("GPT time")
  5. Execute trade / update state
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from brain.prerequisites import Prerequisites
from brain.rules import Rules, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from brain.quality_checks import QualityChecks, RegimeFilter, SessionFilter
from brain.config import QualityConfig, DEFAULT, MEDIUM
from brain.llm_validator import LLMValidator, LLMValidation


# ══════════════════════════════════════════════════════════════════════
# Trade & Result data classes
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    entry_bar:   int
    entry_time:  pd.Timestamp
    direction:   str
    entry_price: float
    size:        float
    stop_price:  float
    tp_price:    float
    exit_bar:    Optional[int]           = None
    exit_time:   Optional[pd.Timestamp]  = None
    exit_price:  Optional[float]         = None
    exit_reason: Optional[str]           = None
    pnl:         Optional[float]         = None
    pnl_pct:     Optional[float]         = None
    llm_confidence: Optional[int]        = None   # LLM confidence when approved

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
    llm_enabled:     bool = False

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
        wins = sum(t.pnl for t in self.closed_trades if (t.pnl or 0) > 0)
        loss = abs(sum(t.pnl for t in self.closed_trades if (t.pnl or 0) < 0))
        return wins / loss if loss > 0 else float("inf")

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else self.initial_capital

    @property
    def return_pct(self) -> float:
        return (self.final_equity - self.initial_capital) / self.initial_capital

    def summary(self) -> str:
        ct  = self.closed_trades
        wins = sum(1 for t in ct if (t.pnl or 0) > 0)
        by_reason = {}
        for t in ct:
            by_reason[t.exit_reason] = by_reason.get(t.exit_reason, 0) + 1
        reason_str = "  ".join(f"{k}:{v}" for k, v in sorted(by_reason.items()))
        llm_avg = ""
        if self.llm_enabled:
            confidences = [t.llm_confidence for t in ct if t.llm_confidence is not None]
            if confidences:
                llm_avg = f"\n  Avg LLM confidence : {sum(confidences)/len(confidences):.0f}%"
        return "\n".join([
            "=" * 52,
            "  SIMULATION RESULTS",
            "=" * 52,
            f"  Initial capital    : {self.initial_capital:>12,.2f}",
            f"  Final equity       : {self.final_equity:>12,.2f}",
            f"  Total PnL          : {self.total_pnl:>+12,.2f}",
            f"  Return             : {self.return_pct*100:>11.2f}%",
            f"  Max Drawdown       : {self.max_drawdown*100:>11.2f}%",
            f"  Profit Factor      : {self.profit_factor:>12.2f}",
            f"  Total trades       : {len(ct):>12}",
            f"  Win / Loss         : {wins:>5} / {len(ct)-wins:<5}",
            f"  Win rate           : {self.win_rate*100:>11.2f}%",
            f"  Exit reasons       : {reason_str}" + llm_avg,
            "=" * 52,
        ])

    def trades_df(self) -> pd.DataFrame:
        if not self.closed_trades:
            return pd.DataFrame()
        return pd.DataFrame([{
            "entry_time":     t.entry_time,
            "exit_time":      t.exit_time,
            "direction":      t.direction,
            "entry_price":    t.entry_price,
            "exit_price":     t.exit_price,
            "size":           t.size,
            "pnl":            round(t.pnl, 4),
            "pnl_pct":        round(t.pnl_pct * 100, 3),
            "exit_reason":    t.exit_reason,
            "llm_confidence": t.llm_confidence,
        } for t in self.closed_trades])


# ══════════════════════════════════════════════════════════════════════
# TradeSimulator
# ══════════════════════════════════════════════════════════════════════

class TradeSimulator:
    """
    Bar-by-bar trade simulator with a 7-layer quality gate.

    Parameters
    ----------
    initial_capital    : starting equity
    commission_pct     : one-way commission as fraction of trade value
    allow_short        : whether SELL signals open short positions
    take_profit_mult   : TP = SL distance × this (R:R ratio)
    config             : QualityConfig preset (use brain.STRICT for production)
    llm_api_key        : Anthropic API key for Layer 7 (or set ANTHROPIC_API_KEY)
    """

    def __init__(
        self,
        initial_capital:  float          = 10_000.0,
        commission_pct:   float          = 0.001,
        allow_short:      bool           = True,
        take_profit_mult: float          = 2.0,
        config:           QualityConfig  = DEFAULT,
        llm_api_key:      Optional[str]  = None,
        genome           = None,         # optional StrategyGenome — overrides rule params
    ):
        self.initial_capital  = initial_capital
        self.commission_pct   = commission_pct
        self.allow_short      = allow_short
        self.take_profit_mult = take_profit_mult
        self._cfg             = config

        self._prereqs       = Prerequisites()
        self._rules         = Rules(genome=genome)   # genome wires rule parameters
        self._regime_filter = RegimeFilter()
        self._quality = QualityChecks(
            block_counter_trend    = config.block_counter_trend,
            min_agreement          = config.min_agreement,
            max_daily_loss_pct     = config.max_daily_loss_pct,
            max_portfolio_heat_pct = config.max_portfolio_heat_pct,
            health_window          = config.health_window,
            min_sharpe             = config.min_sharpe,
            min_profit_factor      = config.min_profit_factor,
            max_drawdown_pct       = config.max_drawdown_pct,
            max_consecutive_losses = config.max_consecutive_losses,
            cooldown_bars          = config.cooldown_bars,
            min_atr_multiplier     = config.min_atr_multiplier,
            max_risk_pct           = config.max_risk_pct,
            atr_stop_multiplier    = config.atr_stop_multiplier,
            session_filter         = None if config.disable_session_filter else SessionFilter(),
        )
        self._llm: Optional[LLMValidator] = None
        if config.llm_enabled:
            self._llm = LLMValidator(
                min_confidence=config.llm_min_confidence,
                api_key=llm_api_key,
            )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(self, df: pd.DataFrame, verbose: bool = False) -> SimulationResult:
        prereq = self._prereqs.check(df)
        if not prereq.passed:
            raise ValueError(f"Prerequisites failed:\n{prereq}")

        # Pre-compute regimes once — reused by regime-aware rules AND quality checks
        if verbose:
            print("  Computing regimes for all bars...")
        regimes   = self._regime_filter.detect_all(df)

        signals_df = self._rules.evaluate(df, regimes=regimes)
        rule_cols  = [c for c in signals_df.columns if c not in ("vote_sum", "signal")]

        equity           = self.initial_capital
        equity_curve     = [equity]
        all_trades:    List[Trade] = []
        closed_trades: List[Trade] = []
        open_trade:    Optional[Trade] = None

        consecutive_losses = 0
        bars_since_trade   = 999
        daily_pnl          = 0.0
        llm_rejected       = 0
        current_date       = df.index[0].date() if len(df) > 0 else None

        for i in range(len(df)):
            bar      = df.iloc[i]
            signal   = int(signals_df["signal"].iloc[i])
            ts       = df.index[i]
            bar_date = ts.date()

            if bar_date != current_date:
                daily_pnl    = 0.0
                current_date = bar_date

            # ── Manage open position ──────────────────────────────────
            if open_trade is not None:
                exit_price, exit_reason = self._check_exit(open_trade, bar, signal)
                if exit_price is not None:
                    open_trade.close(i, ts, exit_price, exit_reason)
                    comm    = self._commission(open_trade)
                    equity += open_trade.pnl - comm
                    daily_pnl += open_trade.pnl - comm
                    equity_curve.append(round(equity, 4))
                    closed_trades.append(open_trade)
                    consecutive_losses = (
                        consecutive_losses + 1 if (open_trade.pnl or 0) < 0 else 0
                    )
                    bars_since_trade = 0
                    if verbose:
                        print(f"[{ts}] CLOSE {open_trade.direction} "
                              f"@ {exit_price:.4f}  PnL={open_trade.pnl:+.2f} ({exit_reason})")
                    open_trade = None

            bars_since_trade += 1

            # ── Try to open new position ──────────────────────────────
            if open_trade is not None:
                continue

            rule_votes = signals_df[rule_cols].iloc[i]
            qc = self._quality.check(
                signal                = signal,
                rule_votes            = rule_votes,
                df                    = df,
                bar_index             = i,
                equity                = equity,
                equity_curve          = equity_curve,
                closed_trades         = closed_trades,
                consecutive_losses    = consecutive_losses,
                bars_since_last_trade = bars_since_trade,
                daily_pnl             = daily_pnl,
                portfolio_heat        = 0.0,
                precomputed_regime    = regimes[i],   # no re-computation of ADX
            )

            if not qc.approved:
                continue

            # ── Layer 7: LLM Validator ("GPT time") ───────────────────
            llm_result: Optional[LLMValidation] = None
            if self._llm is not None:
                atr      = self._quality._atr(df, i)
                entry_px = float(bar["close"])
                atr_val  = atr or entry_px * 0.01
                stop_d   = atr_val * self._cfg.atr_stop_multiplier
                direction = "LONG" if signal == SIGNAL_BUY else "SHORT"
                stop_px = (entry_px - stop_d) if direction == "LONG" else (entry_px + stop_d)
                tp_px   = (entry_px + stop_d * self.take_profit_mult) if direction == "LONG" \
                          else (entry_px - stop_d * self.take_profit_mult)

                llm_result = self._llm.validate(
                    signal             = signal,
                    rule_votes         = rule_votes,
                    entry_price        = entry_px,
                    stop_price         = stop_px,
                    tp_price           = tp_px,
                    size               = qc.size,
                    equity             = equity,
                    initial_capital    = self.initial_capital,
                    daily_pnl          = daily_pnl,
                    equity_curve       = equity_curve,
                    closed_trades      = closed_trades,
                    consecutive_losses = consecutive_losses,
                    regime             = qc.regime,
                )
                if not llm_result.approved:
                    llm_rejected += 1
                    if verbose:
                        print(f"[{ts}] LLM REJECTED  {llm_result}")
                    continue

            # ── Open trade ────────────────────────────────────────────
            direction = "LONG" if signal == SIGNAL_BUY else "SHORT"
            if direction == "SHORT" and not self.allow_short:
                continue

            entry_px = float(bar["close"])
            atr_val  = self._quality._atr(df, i) or entry_px * 0.01
            stop_d   = atr_val * self._cfg.atr_stop_multiplier
            stop_px  = (entry_px - stop_d) if direction == "LONG" else (entry_px + stop_d)
            tp_px    = (entry_px + stop_d * self.take_profit_mult) if direction == "LONG" \
                       else (entry_px - stop_d * self.take_profit_mult)

            trade = Trade(
                entry_bar      = i,
                entry_time     = ts,
                direction      = direction,
                entry_price    = entry_px,
                size           = qc.size,
                stop_price     = round(stop_px, 4),
                tp_price       = round(tp_px, 4),
                llm_confidence = llm_result.confidence if llm_result else None,
            )
            all_trades.append(trade)
            open_trade       = trade
            bars_since_trade = 0

            if verbose:
                regime_str = f"  [{qc.regime}]" if qc.regime else ""
                llm_str    = f"  LLM={llm_result.confidence}%" if llm_result else ""
                print(f"[{ts}] OPEN {direction} @ {entry_px:.4f}  "
                      f"size={qc.size:.4f}  SL={stop_px:.4f}  TP={tp_px:.4f}"
                      f"{regime_str}{llm_str}")

        # Close leftover open position
        if open_trade is not None:
            last = df.iloc[-1]
            open_trade.close(len(df)-1, df.index[-1], float(last["close"]), "end_of_data")
            equity += open_trade.pnl - self._commission(open_trade)
            equity_curve.append(round(equity, 4))
            closed_trades.append(open_trade)

        if verbose and self._llm is not None:
            print(f"\n  [LLM] Total rejections by Layer 7: {llm_rejected}")

        return SimulationResult(
            trades          = all_trades,
            equity_curve    = equity_curve,
            signals_df      = signals_df,
            initial_capital = self.initial_capital,
            llm_enabled     = self._llm is not None,
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _check_exit(
        self, trade: Trade, bar: pd.Series, new_signal: int
    ) -> tuple[Optional[float], Optional[str]]:
        low  = float(bar["low"])
        high = float(bar["high"])
        if trade.direction == "LONG":
            if low  <= trade.stop_price: return trade.stop_price, "stop_loss"
            if high >= trade.tp_price:   return trade.tp_price,   "take_profit"
            if new_signal == SIGNAL_SELL: return float(bar["close"]), "signal_flip"
        else:
            if high >= trade.stop_price: return trade.stop_price, "stop_loss"
            if low  <= trade.tp_price:   return trade.tp_price,   "take_profit"
            if new_signal == SIGNAL_BUY:  return float(bar["close"]), "signal_flip"
        return None, None

    def _commission(self, trade: Trade) -> float:
        return trade.entry_price * trade.size * self.commission_pct
