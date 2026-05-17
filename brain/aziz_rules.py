"""
Aziz Rules — six day-trading strategies distilled from Andrew Aziz's books
("How to Day Trade for a Living", "Advanced Techniques in Day Trading") and
the Bear Bull Traders course material.

Strategies modelled here
────────────────────────
  vwap_reclaim         : reclaim / loss of session VWAP with confirming bar
  opening_range_breakout: break of the first N-bar range, volume-confirmed
  bull_flag            : flagpole → tight consolidation → breakout w/ volume
  abcd_pattern         : impulse → 38–62 % pullback → re-entry above swing
  red_to_green         : cross of the prior-day close in the morning window
  ma_trend_pullback    : 9 EMA over 20 EMA pullback bounce (rides until 20 EMA break)

All rules return a pandas Series of {-1, 0, +1} aligned to df.index and accept
the same `regimes` argument the classic rules use, so they slot into the
existing Rules registry without further plumbing.

Time-of-day filters use brain.intraday helpers, so they work on any
DataFrame with a DatetimeIndex (real MT5 data) and degrade gracefully on
synthetic data with an integer index.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from .intraday import (
    opening_range,
    prior_day_close,
    session_minute,
    session_vwap,
)
from .rules import SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL


# ══════════════════════════════════════════════════════════════════════
# 1. VWAP reclaim / loss
# ══════════════════════════════════════════════════════════════════════

def vwap_reclaim_rule(
    df:      pd.DataFrame,
    regimes: Optional[List] = None,
    confirm_bars: int = 1,
) -> pd.Series:
    """
    Aziz: "VWAP is my favourite indicator." Long when price climbs back
    above session VWAP after trading below it; short when it loses VWAP
    from above. The confirming bar must close in the trade direction.
    """
    vwap = session_vwap(df)
    above = df["close"] > vwap
    below = df["close"] < vwap
    bull_bar = df["close"] > df["open"]
    bear_bar = df["close"] < df["open"]

    # Reclaim: previous N bars were below, current bar closes above
    was_below = below.shift(1).fillna(False)
    was_above = above.shift(1).fillna(False)
    for k in range(2, confirm_bars + 1):
        was_below = was_below & below.shift(k).fillna(False)
        was_above = was_above & above.shift(k).fillna(False)

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[above & was_below & bull_bar] = SIGNAL_BUY
    signal[below & was_above & bear_bar] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 2. Opening Range Breakout (ORB)
# ══════════════════════════════════════════════════════════════════════

def opening_range_breakout_rule(
    df:                 pd.DataFrame,
    regimes:            Optional[List] = None,
    window_bars:        int   = 15,
    volume_mult:        float = 1.3,
    session_max_minute: int   = 180,
) -> pd.Series:
    """
    Aziz/Zarattini ORB on "Stocks in Play". Once the first `window_bars` of
    the session have printed, take longs on closes above the range high and
    shorts on closes below the range low, with volume above the average of
    the opening window. Stops trading after `session_max_minute` bars.
    """
    range_high, range_low, opening_avg_vol = opening_range(df, window_bars)
    sm = session_minute(df)

    after_window = sm > window_bars
    in_session   = sm < session_max_minute
    vol_ok       = df["volume"] > volume_mult * opening_avg_vol

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    long_break  = (df["close"] > range_high) & vol_ok & after_window & in_session
    short_break = (df["close"] < range_low)  & vol_ok & after_window & in_session
    signal[long_break]  = SIGNAL_BUY
    signal[short_break] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 3. Bull / Bear Flag Momentum
# ══════════════════════════════════════════════════════════════════════

def bull_flag_rule(
    df:           pd.DataFrame,
    regimes:      Optional[List] = None,
    pole_bars:    int   = 5,
    flag_bars:    int   = 3,
    pole_min_pct: float = 0.004,
    retrace_max:  float = 0.50,
    volume_mult:  float = 1.5,
) -> pd.Series:
    """
    Aziz Bull-Flag Momentum (mirrored for bear flags).

      flagpole : strong move over `pole_bars` (>= pole_min_pct)
      flag     : `flag_bars` of consolidation retracing <= retrace_max of pole
      trigger  : current close breaks the flag high (low) with volume.
    """
    pole_start = df["close"].shift(pole_bars + flag_bars)
    pole_end   = df["close"].shift(flag_bars)
    pole_size  = pole_end - pole_start
    pole_gain  = pole_size / pole_start.replace(0, np.nan)

    flag_high    = df["high"].shift(1).rolling(flag_bars).max()
    flag_low     = df["low"].shift(1).rolling(flag_bars).min()
    flag_avg_vol = df["volume"].shift(1).rolling(flag_bars).mean()

    # Retrace: how far did the flag pull back relative to the pole
    bull_retrace = (pole_end - flag_low) / pole_size.replace(0, np.nan)
    bear_retrace = (flag_high - pole_end) / (-pole_size).replace(0, np.nan)

    bull_pole = pole_gain >=  pole_min_pct
    bear_pole = pole_gain <= -pole_min_pct
    vol_ok    = df["volume"] > volume_mult * flag_avg_vol

    bull_break = (df["close"] > flag_high) & bull_pole & (bull_retrace <= retrace_max) & vol_ok
    bear_break = (df["close"] < flag_low ) & bear_pole & (bear_retrace <= retrace_max) & vol_ok

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[bull_break] = SIGNAL_BUY
    signal[bear_break] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 4. ABCD Pattern
# ══════════════════════════════════════════════════════════════════════

def abcd_pattern_rule(
    df:           pd.DataFrame,
    regimes:      Optional[List] = None,
    lookback:     int   = 20,
    swing_bars:   int   = 5,
    retrace_min:  float = 0.382,
    retrace_max:  float = 0.618,
) -> pd.Series:
    """
    ABCD continuation pattern.

      A : highest high over the lookback window
      B : the pullback low established after A
      C : consolidation roughly at the B level (low of last `swing_bars`)
      D : current close breaks above the recent `swing_bars` high while
          B still respects a 38.2–61.8 % retracement of the A-impulse.

    Mirrored for the bearish ABCD.
    """
    a_high = df["high"].shift(1).rolling(lookback).max()
    a_low  = df["low"] .shift(1).rolling(lookback).min()
    impulse_start = df["close"].shift(lookback)

    pullback_low  = df["low"].shift(1).rolling(swing_bars).min()
    pullback_high = df["high"].shift(1).rolling(swing_bars).max()

    impulse_up   = (a_high - impulse_start).replace(0, np.nan)
    impulse_down = (impulse_start - a_low).replace(0, np.nan)

    bull_retrace = (a_high - pullback_low) / impulse_up
    bear_retrace = (pullback_high - a_low) / impulse_down

    swing_high = df["close"].shift(1).rolling(swing_bars).max()
    swing_low  = df["close"].shift(1).rolling(swing_bars).min()

    bull_ok = (
        (bull_retrace >= retrace_min) & (bull_retrace <= retrace_max)
        & (df["close"] > swing_high) & (df["close"] > pullback_low)
    )
    bear_ok = (
        (bear_retrace >= retrace_min) & (bear_retrace <= retrace_max)
        & (df["close"] < swing_low)   & (df["close"] < pullback_high)
    )

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[bull_ok] = SIGNAL_BUY
    signal[bear_ok] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 5. Red-to-Green
# ══════════════════════════════════════════════════════════════════════

def red_to_green_rule(
    df:                 pd.DataFrame,
    regimes:            Optional[List] = None,
    session_max_minute: int   = 180,
    volume_mult:        float = 1.3,
) -> pd.Series:
    """
    Stock that opens below the prior session close (red) reclaims it (green)
    on rising volume — Aziz's classic morning reversal. Mirrored to "green-to-red".
    Active only inside the first `session_max_minute` minutes of the day.
    """
    pdc = prior_day_close(df)
    sm  = session_minute(df)

    crossed_up   = (df["close"] > pdc) & (df["close"].shift(1) <= pdc)
    crossed_down = (df["close"] < pdc) & (df["close"].shift(1) >= pdc)

    avg_vol = df["volume"].rolling(20).mean()
    vol_ok  = df["volume"] > volume_mult * avg_vol
    in_win  = sm < session_max_minute
    has_pdc = pdc.notna()

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[crossed_up   & vol_ok & in_win & has_pdc] = SIGNAL_BUY
    signal[crossed_down & vol_ok & in_win & has_pdc] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 6. Moving-Average Trend Pullback (9 EMA / 20 EMA)
# ══════════════════════════════════════════════════════════════════════

def ma_trend_pullback_rule(
    df:           pd.DataFrame,
    regimes:      Optional[List] = None,
    fast_span:    int   = 9,
    slow_span:    int   = 20,
    pullback_pct: float = 0.003,
) -> pd.Series:
    """
    Aziz Moving-Average Trend trade:
      uptrend  : 9 EMA > 20 EMA, both rising, price above both
      pullback : low touches the band between 9 and 20 EMA (± pullback_pct)
      trigger  : bar closes back up (bullish bar) → BUY
      exit hint: trend ends when 20 EMA breaks (handled by signal_flip).

    Mirrored for downtrend.
    """
    ema_f = df["close"].ewm(span=fast_span, adjust=False).mean()
    ema_s = df["close"].ewm(span=slow_span, adjust=False).mean()

    uptrend   = (ema_f > ema_s) & (df["close"] > ema_s)
    downtrend = (ema_f < ema_s) & (df["close"] < ema_s)

    upper = ema_f * (1 + pullback_pct)
    lower = ema_s * (1 - pullback_pct)
    pulled_long = (df["low"]  <= upper) & (df["low"]  >= lower)

    upper_s = ema_s * (1 + pullback_pct)
    lower_f = ema_f * (1 - pullback_pct)
    pulled_short = (df["high"] >= lower_f) & (df["high"] <= upper_s)

    bull_bar = df["close"] > df["open"]
    bear_bar = df["close"] < df["open"]

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    signal[uptrend   & pulled_long  & bull_bar] = SIGNAL_BUY
    signal[downtrend & pulled_short & bear_bar] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# 7. Intraday-Momentum Boundary (Zarattini × Aziz × Barbon — "Beat the Market")
#    SSRN 4824172 / SFI Research Paper 24-97
# ══════════════════════════════════════════════════════════════════════

def intraday_momentum_boundary_rule(
    df:                 pd.DataFrame,
    regimes:            Optional[List] = None,
    lookback_days:      int = 14,
    decision_clock_min: tuple = (0, 30),
    session_open_min:   int = 0,
    session_close_min:  int = 390,
    use_gap_adjustment: bool = True,
) -> pd.Series:
    """
    "Beat the Market" intraday momentum boundary breakout for index ETFs
    (target: SPY; works on any liquid intraday instrument).

    For each minute m of day d, build noise boundaries from the last
    `lookback_days` of cumulative returns at minute m, adjusted for the
    prior overnight gap. At HH:00 / HH:30 ticks, if the price has
    crossed above the upper band → LONG; below the lower band → SHORT.

    Reference: Zarattini, Aziz, Barbon 2024.
    Sharpe 1.33, +19.6 % p.a., +1 985 % cumulative (2007–Q1 2024) on SPY.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        # Pure mechanism degrades to no-signal on integer-indexed data.
        return pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)

    # Per-bar session-minute (0 at session open)
    sm = session_minute(df)
    in_session = (sm >= session_open_min) & (sm < session_close_min)

    # Daily anchors
    day = pd.Series(df.index.date, index=df.index)
    daily_open  = df["open"].groupby(day).transform("first")
    daily_close = df["close"].groupby(day).last()
    prev_close  = day.map(daily_close.shift(1))

    # Per-(day, minute) cumulative return from session open
    bar_ret_to_open = (df["close"] - daily_open) / daily_open

    # For each minute m, mean of bar_ret_to_open over last `lookback_days`
    # at the same session minute. We pivot day×minute and apply a rolling
    # mean along the day axis, then flatten back.
    df_internal = pd.DataFrame({"day": day, "sm": sm, "r": bar_ret_to_open})
    pivot = (
        df_internal.pivot_table(index="day", columns="sm", values="r", aggfunc="last")
                   .sort_index()
    )
    mean_pivot = pivot.shift(1).rolling(lookback_days, min_periods=max(1, lookback_days // 2)).mean()

    # Map mean back onto the original bar timeline
    pair = list(zip(day.values, sm.values))
    mean_ret = pd.Series(
        [mean_pivot.at[d, m] if (d in mean_pivot.index and m in mean_pivot.columns) else np.nan
         for d, m in pair],
        index=df.index,
    )

    # Gap adjustments (only widen the bound on the side OPPOSITE the gap)
    if use_gap_adjustment and not prev_close.isna().all():
        gap_up_adj   = ((daily_open - prev_close) / prev_close).clip(lower=0).fillna(0)
        gap_down_adj = ((prev_close - daily_open) / prev_close).clip(lower=0).fillna(0)
    else:
        gap_up_adj   = pd.Series(0.0, index=df.index)
        gap_down_adj = pd.Series(0.0, index=df.index)

    upper = daily_open * (1.0 + mean_ret.abs() + gap_down_adj)
    lower = daily_open * (1.0 - mean_ret.abs() - gap_up_adj)

    # Decision clock — only fire at HH:00 / HH:30 (or whatever minutes given)
    minute_of_hour = df.index.minute
    clock_ok = pd.Series(np.isin(minute_of_hour, list(decision_clock_min)), index=df.index)

    signal = pd.Series(SIGNAL_HOLD, index=df.index, dtype=int)
    long_break  = clock_ok & in_session & (df["close"] > upper) & upper.notna()
    short_break = clock_ok & in_session & (df["close"] < lower) & lower.notna()
    signal[long_break]  = SIGNAL_BUY
    signal[short_break] = SIGNAL_SELL
    return signal


# ══════════════════════════════════════════════════════════════════════
# Registry of names (used by Rules.__init__ when style='aziz')
# ══════════════════════════════════════════════════════════════════════

AZIZ_RULES = (
    ("vwap_reclaim",                vwap_reclaim_rule),
    ("opening_range_breakout",      opening_range_breakout_rule),
    ("bull_flag",                   bull_flag_rule),
    ("abcd_pattern",                abcd_pattern_rule),
    ("red_to_green",                red_to_green_rule),
    ("ma_trend_pullback",           ma_trend_pullback_rule),
    ("intraday_momentum_boundary",  intraday_momentum_boundary_rule),
)
