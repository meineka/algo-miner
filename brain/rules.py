"""
Brain Rules — generates BUY / SELL / HOLD signals from OHLC data.

Each rule is regime-aware: it returns HOLD when the current market
condition does not suit its logic, instead of firing blindly.

  EMA Crossover      → trend markets only   (ADX >= 20)
  RSI Mean Reversion → sideways only        (ADX <  25)
  Donchian Breakout  → trending + volume    (ADX >= 20, volume confirmed)
  Volume Spike       → any, but direction-filtered and min 2× avg vol

The Brain combines all active signals via a configurable agreement threshold.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

SIGNAL_BUY  =  1
SIGNAL_SELL = -1
SIGNAL_HOLD =  0


class Rules:
    """
    Registry of trading rules.

    evaluate(df, regimes) pre-computes regimes for every bar so each rule
    function can gate itself without re-running ADX.
    """

    def __init__(self, genome=None, style: str = "classic"):
        """
        genome : optional StrategyGenome — when provided, rule parameters
                 (EMA spans, RSI thresholds, etc.) are taken from the genome
                 instead of the hard-coded defaults.
        style  : 'classic'  — the original 4 regime-aware rules
                 'aziz'     — the 6 Andrew-Aziz day-trading strategies
                 'hybrid'   — both rule sets combined (10 rules)
        """
        self._rules: Dict[str, Callable] = {}
        self._genome = genome
        self._style  = style

        if style in ("classic", "hybrid"):
            self._register_classic(genome)
        if style in ("aziz", "hybrid"):
            self._register_aziz(genome)
        if not self._rules:
            raise ValueError(f"Unknown style '{style}' (expected 'classic'|'aziz'|'hybrid')")

    def _register_classic(self, genome) -> None:
        import functools
        if genome is not None:
            self.register("ema_crossover")(
                functools.partial(ema_crossover_rule,
                                  fast_span=genome.ema_fast,
                                  slow_span=genome.ema_slow))
            self.register("rsi_mean_reversion")(
                functools.partial(rsi_mean_reversion_rule,
                                  period=genome.rsi_period,
                                  oversold=genome.rsi_oversold,
                                  overbought=genome.rsi_overbought))
            self.register("donchian_breakout")(
                functools.partial(donchian_breakout_rule,
                                  window=genome.donchian_window))
            self.register("volume_spike")(
                functools.partial(volume_spike_rule,
                                  multiplier=genome.vol_spike_mult))
        else:
            self.register("ema_crossover")(ema_crossover_rule)
            self.register("rsi_mean_reversion")(rsi_mean_reversion_rule)
            self.register("donchian_breakout")(donchian_breakout_rule)
            self.register("volume_spike")(volume_spike_rule)

    def _register_aziz(self, genome) -> None:
        import functools
        from .aziz_rules import (
            AZIZ_RULES,
            opening_range_breakout_rule,
            bull_flag_rule,
            ma_trend_pullback_rule,
            red_to_green_rule,
        )

        # Pull Aziz-tunable knobs off the genome when present; fall back to
        # the function defaults otherwise.
        def g(attr, default):
            return getattr(genome, attr, default) if genome is not None else default

        overrides = {
            "opening_range_breakout": functools.partial(
                opening_range_breakout_rule,
                window_bars        = g("orb_window_bars", 15),
                volume_mult        = g("orb_volume_mult", 1.3),
                session_max_minute = g("orb_session_max_min", 180),
            ),
            "bull_flag": functools.partial(
                bull_flag_rule,
                pole_bars    = g("flag_pole_bars", 5),
                flag_bars    = g("flag_consol_bars", 3),
                pole_min_pct = g("flag_pole_min_pct", 0.004),
                retrace_max  = g("flag_retrace_max", 0.50),
                volume_mult  = g("flag_volume_mult", 1.5),
            ),
            "ma_trend_pullback": functools.partial(
                ma_trend_pullback_rule,
                fast_span    = g("ma_fast_span", 9),
                slow_span    = g("ma_slow_span", 20),
                pullback_pct = g("ma_pullback_pct", 0.003),
            ),
            "red_to_green": functools.partial(
                red_to_green_rule,
                session_max_minute = g("rtg_session_max_min", 180),
                volume_mult        = g("rtg_volume_mult", 1.3),
            ),
        }
        for name, fn in AZIZ_RULES:
            self.register(name)(overrides.get(name, fn))

    def register(self, name: str):
        def decorator(fn: Callable):
            self._rules[name] = fn
            return fn
        return decorator

    def evaluate(
        self,
        df: pd.DataFrame,
        regimes: Optional[List] = None,   # list[RegimeState | None], one per bar
    ) -> pd.DataFrame:
        """
        Run all rules and return a DataFrame with one column per rule
        plus a 'signal' column (majority-vote of active rules).

        regimes : pre-computed list from RegimeFilter.detect_all(df).
                  If None, rules run without regime gating.
        """
        signals = pd.DataFrame(index=df.index)
        for name, fn in self._rules.items():
            signals[name] = fn(df, regimes)

        rule_cols = list(self._rules.keys())
        buy_count  = (signals[rule_cols] == SIGNAL_BUY).sum(axis=1)
        sell_count = (signals[rule_cols] == SIGNAL_SELL).sum(axis=1)
        total      = len(rule_cols)

        signals["vote_sum"] = buy_count - sell_count
        # majority vote: more buys than sells → BUY, vice versa → SELL
        signals["signal"] = SIGNAL_HOLD
        signals.loc[buy_count  > sell_count, "signal"] = SIGNAL_BUY
        signals.loc[sell_count > buy_count,  "signal"] = SIGNAL_SELL

        return signals

    @property
    def rule_names(self) -> List[str]:
        return list(self._rules.keys())


# ══════════════════════════════════════════════════════════════════════
# Regime helpers
# ══════════════════════════════════════════════════════════════════════

def _trend_mask(regimes, index: pd.Index, min_adx: float = 20.0) -> pd.Series:
    """True where regime is trending (ADX >= min_adx)."""
    return pd.Series(
        [r is not None and r.adx >= min_adx and r.trend in ("BULL", "BEAR", "TRANSITIONING")
         for r in regimes],
        index=index, dtype=bool,
    )

def _sideways_mask(regimes, index: pd.Index, max_adx: float = 25.0) -> pd.Series:
    """True where regime is sideways (ADX < max_adx or SIDEWAYS)."""
    return pd.Series(
        [r is None or r.adx < max_adx or r.trend == "SIDEWAYS"
         for r in regimes],
        index=index, dtype=bool,
    )


# ══════════════════════════════════════════════════════════════════════
# Rule implementations
# ══════════════════════════════════════════════════════════════════════

def ema_crossover_rule(
    df: pd.DataFrame,
    regimes:   Optional[List] = None,
    fast_span: int = 9,
    slow_span: int = 21,
) -> pd.Series:
    """
    Fast/slow EMA crossover.
    Active only in trending regimes (ADX >= 20) — fires HOLD in sideways markets
    where crossovers produce whipsaws.
    """
    fast = df["close"].ewm(span=fast_span, adjust=False).mean()
    slow = df["close"].ewm(span=slow_span, adjust=False).mean()
    diff = fast - slow

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[diff > 0] = SIGNAL_BUY
    signal[diff < 0] = SIGNAL_SELL

    # Silence in sideways — crossovers here are noise
    if regimes is not None:
        sideways = _sideways_mask(regimes, df.index, max_adx=20.0)
        signal[sideways] = SIGNAL_HOLD

    return signal


def rsi_mean_reversion_rule(
    df: pd.DataFrame,
    regimes:    Optional[List] = None,
    period:     int = 14,
    oversold:   int = 30,
    overbought: int = 70,
) -> pd.Series:
    """
    Oversold/Overbought RSI reversion.
    Active only in sideways / low-trend regimes (ADX < 25) — in a strong trend,
    RSI stays overbought/oversold for a long time and the signal is useless.
    """
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = 100 - 100 / (1 + rs)

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[rsi < oversold]   = SIGNAL_BUY
    signal[rsi > overbought] = SIGNAL_SELL

    # Silence in strong trends — RSI mean-reversion fails there
    if regimes is not None:
        trending = _trend_mask(regimes, df.index, min_adx=25.0)
        signal[trending] = SIGNAL_HOLD

    return signal


def donchian_breakout_rule(
    df: pd.DataFrame,
    regimes: Optional[List] = None,
    window:  int = 20,
) -> pd.Series:
    """
    Donchian channel breakout with volume confirmation.
    Active only in trending regimes (ADX >= 20) — breakouts in sideways
    markets are almost always fakeouts.
    Volume confirmation: current volume must exceed the 20-bar average.
    """
    rolling_high = df["close"].shift(1).rolling(window).max()
    rolling_low  = df["close"].shift(1).rolling(window).min()
    avg_vol      = df["volume"].rolling(window).mean()
    vol_confirm  = df["volume"] > avg_vol   # volume must be above average

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[(df["close"] > rolling_high) & vol_confirm] = SIGNAL_BUY
    signal[(df["close"] < rolling_low)  & vol_confirm] = SIGNAL_SELL

    # Silence in sideways — breakouts without trend are fakeouts
    if regimes is not None:
        sideways = ~_trend_mask(regimes, df.index, min_adx=20.0)
        signal[sideways] = SIGNAL_HOLD

    return signal


def volume_spike_rule(
    df: pd.DataFrame,
    regimes:    Optional[List] = None,
    multiplier: float = 2.0,
) -> pd.Series:
    """
    Directional volume spike.
    Requires volume > 2× rolling average AND close > open (bullish bar) or
    close < open (bearish bar). Works in all regimes but requires a
    significant volume threshold — weak spikes are ignored.
    """
    avg_vol  = df["volume"].rolling(20).mean()
    spike    = df["volume"] > multiplier * avg_vol
    up_bar   = df["close"] > df["open"]
    dn_bar   = df["close"] < df["open"]

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[spike & up_bar] = SIGNAL_BUY
    signal[spike & dn_bar] = SIGNAL_SELL

    # In HIGH-volatility regimes, require even stronger spike (3×) to reduce noise
    if regimes is not None:
        high_vol = pd.Series(
            [r is not None and r.volatility == "HIGH" for r in regimes],
            index=df.index, dtype=bool,
        )
        strong_spike = df["volume"] > multiplier * 1.5 * avg_vol
        # downgrade weak spikes during HIGH-vol to HOLD
        signal[high_vol & spike & ~strong_spike] = SIGNAL_HOLD

    return signal
