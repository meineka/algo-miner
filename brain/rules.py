"""
Brain Rules — generates BUY / SELL / HOLD signals from OHLC data.

Each rule is self-contained and returns a pd.Series of signals.
The Brain combines them via a majority vote.
"""
from __future__ import annotations
from typing import Callable, Dict, List
import pandas as pd


SIGNAL_BUY  =  1
SIGNAL_SELL = -1
SIGNAL_HOLD =  0


class Rules:
    """
    Registry of trading rules. Add custom rules with @rules.register().
    """

    def __init__(self):
        self._rules: Dict[str, Callable[[pd.DataFrame], pd.Series]] = {}
        # register built-in rules
        self.register("ema_crossover")(ema_crossover_rule)
        self.register("rsi_mean_reversion")(rsi_mean_reversion_rule)
        self.register("breakout")(breakout_rule)
        self.register("volume_spike")(volume_spike_rule)

    def register(self, name: str):
        """Decorator to add a new rule."""
        def decorator(fn: Callable[[pd.DataFrame], pd.Series]):
            self._rules[name] = fn
            return fn
        return decorator

    def evaluate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run all rules and return a DataFrame where each column is one rule's
        signal series.  Final column 'signal' = majority vote.
        """
        signals = pd.DataFrame(index=df.index)
        for name, fn in self._rules.items():
            signals[name] = fn(df)

        # majority vote: sum of signals, then sign
        signals["vote_sum"] = signals.sum(axis=1)
        signals["signal"] = signals["vote_sum"].apply(
            lambda v: SIGNAL_BUY if v > 0 else (SIGNAL_SELL if v < 0 else SIGNAL_HOLD)
        )
        return signals

    @property
    def rule_names(self) -> List[str]:
        return list(self._rules.keys())


# ------------------------------------------------------------------ #
# Built-in rule implementations                                        #
# ------------------------------------------------------------------ #

def ema_crossover_rule(df: pd.DataFrame) -> pd.Series:
    """
    Classic fast/slow EMA crossover.
    BUY  when fast EMA crosses above slow EMA.
    SELL when fast EMA crosses below slow EMA.
    """
    fast = df["close"].ewm(span=9, adjust=False).mean()
    slow = df["close"].ewm(span=21, adjust=False).mean()
    diff = fast - slow
    prev_diff = diff.shift(1)

    signal = pd.Series(SIGNAL_HOLD, index=df.index)
    signal[diff > 0] = SIGNAL_BUY
    signal[diff < 0] = SIGNAL_SELL
    # crossing bars get stronger conviction
    signal[(diff > 0) & (prev_diff <= 0)] = SIGNAL_BUY
    signal[(diff < 0) & (prev_diff >= 0)] = SIGNAL_SELL
    return signal


def rsi_mean_reversion_rule(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Oversold RSI < 30 → BUY, Overbought RSI > 70 → SELL.
    """
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - 100 / (1 + rs)

    signal = pd.Series(SIGNAL_HOLD, index=df.index)
    signal[rsi < 30] = SIGNAL_BUY
    signal[rsi > 70] = SIGNAL_SELL
    return signal


def breakout_rule(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Donchian channel breakout:
    BUY  when close > rolling high (prev window bars).
    SELL when close < rolling low  (prev window bars).
    """
    rolling_high = df["close"].shift(1).rolling(window).max()
    rolling_low  = df["close"].shift(1).rolling(window).min()

    signal = pd.Series(SIGNAL_HOLD, index=df.index)
    signal[df["close"] > rolling_high] = SIGNAL_BUY
    signal[df["close"] < rolling_low]  = SIGNAL_SELL
    return signal


def volume_spike_rule(df: pd.DataFrame, multiplier: float = 2.0) -> pd.Series:
    """
    Volume spike with price direction:
    If volume > multiplier * avg AND close > open → BUY
    If volume > multiplier * avg AND close < open → SELL
    """
    avg_vol = df["volume"].rolling(20).mean()
    spike   = df["volume"] > multiplier * avg_vol
    up_bar  = df["close"] > df["open"]
    dn_bar  = df["close"] < df["open"]

    signal = pd.Series(SIGNAL_HOLD, index=df.index)
    signal[spike & up_bar] = SIGNAL_BUY
    signal[spike & dn_bar] = SIGNAL_SELL
    return signal
