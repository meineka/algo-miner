"""
Intraday helpers — session-aware derived series for Aziz-style rules.

The Aziz strategies (Opening Range Breakout, session VWAP, Red-to-Green,
moving-average pullback in the morning session) all need quantities that
reset every trading day:

  - session VWAP        : cumulative typical-price × volume per calendar day
  - session minute      : bar count since the session opened
  - prior-day close     : last close of the previous calendar day
  - opening range       : high/low of the first N bars of each day

Each helper returns a pandas Series aligned to df.index, so the rule
functions stay simple vectorised expressions.

For non-DatetimeIndex DataFrames (synthetic GBM with integer index),
the helpers degrade gracefully — they treat the whole series as a single
"day" with windowed approximations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _day_key(df: pd.DataFrame) -> pd.Series:
    """Return a Series mapping each bar to its calendar-day key."""
    if isinstance(df.index, pd.DatetimeIndex):
        return pd.Series(df.index.date, index=df.index)
    # No timestamp info — bucket into pseudo-days of 390 bars (a US equity session)
    return pd.Series((np.arange(len(df)) // 390), index=df.index)


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume-weighted average price, reset at the start of each calendar day."""
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv  = typical * df["volume"]
    day = _day_key(df)
    cum_pv = pv.groupby(day).cumsum()
    cum_v  = df["volume"].groupby(day).cumsum()
    return cum_pv / cum_v.replace(0, np.nan)


def session_minute(df: pd.DataFrame) -> pd.Series:
    """0 at the first bar of each day, then +1 for every subsequent bar that day."""
    day = _day_key(df)
    return df.groupby(day).cumcount()


def prior_day_close(df: pd.DataFrame) -> pd.Series:
    """Last close of the previous calendar day, broadcast to every bar of today."""
    day = _day_key(df)
    daily_close = df["close"].groupby(day).last()
    prior = daily_close.shift(1)
    return day.map(prior).astype(float)


def opening_range(
    df: pd.DataFrame,
    window_bars: int,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    For each bar, return (range_high, range_low, range_avg_volume) computed
    from the first `window_bars` of that bar's calendar day.

    Values for bars *inside* the range window equal the running max/min so
    far that day (range is still forming); from window_bars+1 onward they
    freeze at the final opening-range levels.
    """
    day = _day_key(df)
    sm  = session_minute(df)
    in_window = sm < window_bars

    # Build per-day rolling max/min/mean *within* the opening window only.
    high_in_window = df["high"].where(in_window)
    low_in_window  = df["low"].where(in_window)
    vol_in_window  = df["volume"].where(in_window)

    range_high = high_in_window.groupby(day).cummax().groupby(day).ffill()
    range_low  = low_in_window .groupby(day).cummin().groupby(day).ffill()
    # average volume of the opening window — use the *final* mean per day
    range_vol_mean = vol_in_window.groupby(day).transform(lambda s: s.dropna().mean())

    return range_high, range_low, range_vol_mean
