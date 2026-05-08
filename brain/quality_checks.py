"""
Brain Quality Checks — six-layer pre-trade gate.

Execution order per bar:
  1. Regime Filter         ADX trend + ATR-ratio volatility detection
  2. Rule Agreement        minimum consensus across individual rule votes
  3. Daily Loss Limit      intraday circuit-breaker (% of equity)
  4. Portfolio Heat        total open-risk cap across all positions
  5. Rolling Health        Sharpe + Profit Factor on last N closed trades
  6. Classic Micro-checks  drawdown kill-switch, consecutive losses, cooldown

Position sizing (ATR-based + Half-Kelly) runs only when all layers pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # type: ignore

from .rules import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD


# ══════════════════════════════════════════════════════════════════════
# Layer 1 — Regime Filter
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RegimeState:
    trend:      str    # 'BULL' | 'BEAR' | 'SIDEWAYS' | 'TRANSITIONING'
    volatility: str    # 'LOW'  | 'NORMAL' | 'HIGH'
    adx:        float
    di_plus:    float
    di_minus:   float
    atr_ratio:  float  # short_atr / long_atr

    @property
    def vol_multiplier(self) -> float:
        """Scale position size down in high-vol regime."""
        return 0.5 if self.volatility == "HIGH" else 1.0

    def blocks_signal(self, signal: int) -> Optional[str]:
        """
        Return a reason string if the signal strongly contradicts the regime.
        Only blocks on ADX > 30 (strong trend) to avoid over-filtering.
        """
        if signal == SIGNAL_BUY  and self.trend == "BEAR" and self.adx > 30:
            return f"Counter-trend BUY blocked — BEAR regime (ADX={self.adx:.1f}, DI-={self.di_minus:.1f})"
        if signal == SIGNAL_SELL and self.trend == "BULL" and self.adx > 30:
            return f"Counter-trend SELL blocked — BULL regime (ADX={self.adx:.1f}, DI+={self.di_plus:.1f})"
        return None

    def __str__(self) -> str:
        return (f"Regime({self.trend}, vol={self.volatility}, "
                f"ADX={self.adx:.1f}, DI+={self.di_plus:.1f}, DI-={self.di_minus:.1f}, "
                f"ATR-ratio={self.atr_ratio:.2f})")


class RegimeFilter:
    """
    Detects the current market regime using:
    - ADX (14) for trend strength and direction (via DI+/DI-)
    - ATR-ratio (short ATR / long ATR) for volatility regime
    """

    ADX_PERIOD        = 14
    ADX_TREND_THRESH  = 25   # ADX above this → trending
    ADX_STRONG_THRESH = 30   # ADX above this → strong trend (block counter-trend)
    VOL_SHORT         = 14
    VOL_LONG          = 50
    HIGH_VOL_RATIO    = 1.5  # short_atr / long_atr > this → HIGH
    LOW_VOL_RATIO     = 0.7

    def detect(self, df: pd.DataFrame, bar_index: int) -> Optional[RegimeState]:
        """Return RegimeState at bar_index, or None if not enough history."""
        min_bars = self.VOL_LONG + self.ADX_PERIOD * 3
        if bar_index < min_bars:
            return None

        window = df.iloc[max(0, bar_index - min_bars * 2): bar_index + 1].copy()

        adx, di_plus, di_minus = self._compute_adx(window)
        if adx is None:
            return None

        atr_ratio = self._compute_vol_ratio(window)

        # Trend classification
        if adx > self.ADX_TREND_THRESH:
            trend = "BULL" if di_plus > di_minus else "BEAR"
        elif adx < 20:
            trend = "SIDEWAYS"
        else:
            trend = "TRANSITIONING"

        # Volatility classification
        if atr_ratio > self.HIGH_VOL_RATIO:
            volatility = "HIGH"
        elif atr_ratio < self.LOW_VOL_RATIO:
            volatility = "LOW"
        else:
            volatility = "NORMAL"

        return RegimeState(
            trend=trend, volatility=volatility,
            adx=round(adx, 2), di_plus=round(di_plus, 2),
            di_minus=round(di_minus, 2), atr_ratio=round(atr_ratio, 3),
        )

    def _compute_adx(self, df: pd.DataFrame) -> Tuple[Optional[float], float, float]:
        p    = self.ADX_PERIOD
        high = df["high"]
        low  = df["low"]
        close= df["close"]

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        up   = high.diff()
        down = -low.diff()
        dm_p = np.where((up > down) & (up > 0),   up,   0.0)
        dm_m = np.where((down > up) & (down > 0), down,  0.0)

        atr14  = pd.Series(tr.values).ewm(span=p, adjust=False).mean()
        di_p   = 100 * pd.Series(dm_p).ewm(span=p, adjust=False).mean() / atr14.replace(0, np.nan)
        di_m   = 100 * pd.Series(dm_m).ewm(span=p, adjust=False).mean() / atr14.replace(0, np.nan)

        denom  = (di_p + di_m).replace(0, np.nan)
        dx     = 100 * (di_p - di_m).abs() / denom
        adx_s  = dx.ewm(span=p, adjust=False).mean()

        vals = (float(adx_s.iloc[-1]), float(di_p.iloc[-1]), float(di_m.iloc[-1]))
        if any(math.isnan(v) for v in vals):
            return None, 0.0, 0.0
        return vals

    def _compute_vol_ratio(self, df: pd.DataFrame) -> float:
        close = df["close"]
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - close.shift(1)).abs(),
            (df["low"]  - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        short_atr = float(tr.rolling(self.VOL_SHORT).mean().iloc[-1])
        long_atr  = float(tr.rolling(self.VOL_LONG).mean().iloc[-1])

        if long_atr <= 0 or math.isnan(long_atr) or math.isnan(short_atr):
            return 1.0
        return short_atr / long_atr

    def detect_all(self, df: pd.DataFrame) -> List[Optional[RegimeState]]:
        """Pre-compute regime for every bar. Called once before the main loop."""
        return [self.detect(df, i) for i in range(len(df))]


# ══════════════════════════════════════════════════════════════════════
# Session / Timezone Filter
# ══════════════════════════════════════════════════════════════════════

class SessionFilter:
    """
    Blocks trades outside active trading sessions and during blackout windows.

    Session boundaries are defined in their LOCAL timezone so DST is handled
    automatically by the OS/Python timezone database (tzdata on Windows).
    All comparisons happen after converting the bar timestamp to the session's
    local time — no hardcoded UTC offsets that would drift when clocks change.

    Supported sessions:
      new_york  09:30 – 16:00  America/New_York   (EDT = UTC-4, EST = UTC-5)
      london    08:00 – 16:30  Europe/London       (BST = UTC+1, GMT = UTC+0)
      sydney    10:00 – 16:00  Australia/Sydney    (AEST/AEDT — opposite hemisphere)
      tokyo     09:00 – 15:30  Asia/Tokyo          (JST = UTC+9, no DST)

    Blackout windows (configurable):
      - First N minutes after session open   (wide spread, erratic fills)
      - Last  N minutes before session close (illiquid, gap risk)
      - Weekends (Saturday + Sunday in UTC)
    """

    # (iana_timezone, (open_h, open_m), (close_h, close_m)) — all LOCAL times
    _SESSION_DEFS: dict = {
        "new_york": ("America/New_York", (9,  30), (16,  0)),
        "london":   ("Europe/London",    (8,   0), (16, 30)),
        "sydney":   ("Australia/Sydney", (10,  0), (16,  0)),
        "tokyo":    ("Asia/Tokyo",       (9,   0), (15, 30)),
    }

    def __init__(
        self,
        sessions:           List[str] = None,   # ['london', 'new_york'] by default
        blackout_open_min:  int  = 15,
        blackout_close_min: int  = 15,
        block_weekends:     bool = True,
    ):
        self.sessions           = sessions or ["london", "new_york"]
        self.blackout_open_min  = blackout_open_min
        self.blackout_close_min = blackout_close_min
        self.block_weekends     = block_weekends

        # Pre-build ZoneInfo objects; fall back gracefully if tzdata is missing
        self._zones: List[Tuple] = []
        for name in self.sessions:
            if name not in self._SESSION_DEFS:
                raise ValueError(f"Unknown session '{name}'. "
                                 f"Valid: {list(self._SESSION_DEFS)}")
            tz_name, (oh, om), (ch, cm) = self._SESSION_DEFS[name]
            try:
                tz = ZoneInfo(tz_name)
            except (ZoneInfoNotFoundError, KeyError):
                # tzdata package not installed — fall back to UTC window
                tz = None
            open_min  = oh * 60 + om
            close_min = ch * 60 + cm
            self._zones.append((name, tz, tz_name, open_min, close_min))

    def is_allowed(self, ts: pd.Timestamp) -> tuple:
        """Return (allowed: bool, reason: str)."""
        # Normalise to UTC-aware
        if ts.tzinfo is not None:
            ts_utc = ts.tz_convert("UTC")
        else:
            ts_utc = ts.tz_localize("UTC")

        # Weekend check (UTC calendar day)
        if self.block_weekends and ts_utc.weekday() >= 5:
            return False, f"[Session] Weekend — no trading ({ts_utc.day_name()})"

        for name, tz, tz_name, open_min, close_min in self._zones:
            if tz is not None:
                # Convert to session-local time — DST handled by zoneinfo
                ts_local = ts_utc.tz_convert(tz)
            else:
                # tzdata unavailable: operate in UTC (degraded mode)
                ts_local = ts_utc

            local_min = ts_local.hour * 60 + ts_local.minute

            if local_min < open_min or local_min > close_min:
                continue  # not in this session window

            # Inside session — apply blackout zones
            if local_min < open_min + self.blackout_open_min:
                local_str = ts_local.strftime("%H:%M")
                return False, (
                    f"[Session] {name} opening blackout "
                    f"({local_str} {tz_name}, first {self.blackout_open_min} min)"
                )
            if local_min > close_min - self.blackout_close_min:
                local_str = ts_local.strftime("%H:%M")
                return False, (
                    f"[Session] {name} closing blackout "
                    f"({local_str} {tz_name}, last {self.blackout_close_min} min)"
                )
            return True, ""  # in session and outside blackout

        hhmm = f"{ts_utc.hour:02d}:{ts_utc.minute:02d} UTC"
        return False, f"[Session] Outside active sessions ({hhmm})"

    def is_daily_data(self, df: pd.DataFrame) -> bool:
        """Infer whether the DataFrame contains daily (or coarser) bars."""
        if len(df) < 2:
            return False
        delta = (df.index[1] - df.index[0]).total_seconds()
        return delta >= 86_400  # >= 1 day


# ══════════════════════════════════════════════════════════════════════
# Position Sizer  (runs after all gates pass)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SizingResult:
    size:        float
    risk_amount: float
    method:      str   # 'half_kelly' | 'atr' | 'fallback'
    capped:      bool  # True if the hard-cap had to trim the size


class PositionSizer:
    """
    Computes position size in two steps:
    1. ATR-based size  →  risk exactly max_risk_pct of equity per 1 stop-distance
    2. Half-Kelly size →  activated after min_trades closed trades
    Final size = min(half_kelly, atr_size), then hard-capped at max_risk_pct.

    ATR-based is the safety net — Kelly is never allowed to exceed it.
    """

    def __init__(
        self,
        max_risk_pct:    float = 0.02,   # 2% hard cap per trade
        atr_multiplier:  float = 2.0,    # stop distance = 2 × ATR
        kelly_min_trades: int  = 20,     # trades needed before Kelly activates
    ):
        self.max_risk_pct     = max_risk_pct
        self.atr_multiplier   = atr_multiplier
        self.kelly_min_trades = kelly_min_trades

    def compute(
        self,
        equity:       float,
        entry_price:  float,
        atr:          float,
        closed_trades: list,
        vol_multiplier: float = 1.0,
    ) -> SizingResult:
        cap_risk   = equity * self.max_risk_pct * vol_multiplier
        stop_dist  = atr * self.atr_multiplier if atr > 0 else entry_price * 0.02
        per_unit   = stop_dist  # loss per unit if stop is hit

        # ATR-based: size that risks exactly cap_risk at 1×stop
        atr_size = cap_risk / per_unit if per_unit > 0 else cap_risk / entry_price

        # Half-Kelly (only when history is available)
        kelly_size, method = None, "atr"
        if len(closed_trades) >= self.kelly_min_trades:
            k_pct = self._half_kelly_pct(closed_trades)
            if k_pct > 0:
                kelly_risk = equity * k_pct * vol_multiplier
                kelly_size = kelly_risk / per_unit if per_unit > 0 else kelly_risk / entry_price
                method = "half_kelly"

        raw_size = min(kelly_size, atr_size) if kelly_size else atr_size

        # Hard cap
        actual_risk = raw_size * per_unit
        capped = actual_risk > cap_risk
        if capped:
            raw_size = atr_size   # fall back to ATR-based

        return SizingResult(
            size=max(round(raw_size, 6), 0.0),
            risk_amount=min(actual_risk, cap_risk),
            method=method,
            capped=capped,
        )

    def _half_kelly_pct(self, closed_trades: list) -> float:
        pnls   = [t.pnl for t in closed_trades if t.pnl is not None]
        wins   = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        if not wins or not losses:
            return 0.0
        W = len(wins) / len(pnls)
        R = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
        kelly = W - (1 - W) / R
        # half-Kelly, clamped
        return max(0.0, min(kelly / 2, self.max_risk_pct))


# ══════════════════════════════════════════════════════════════════════
# QualityResult + QualityChecks
# ══════════════════════════════════════════════════════════════════════

@dataclass
class QualityResult:
    approved: bool
    size:     float                   = 0.0
    regime:   Optional[RegimeState]   = None
    reasons:  List[str]               = field(default_factory=list)

    def __str__(self) -> str:
        status = "✓ Approved" if self.approved else "✗ Blocked"
        regime_str = f"  {self.regime}" if self.regime else ""
        if self.reasons:
            detail = "\n".join(f"  • {r}" for r in self.reasons)
            return f"{status}{regime_str}\n{detail}"
        return f"{status}  size={self.size:.6f}{regime_str}"


class QualityChecks:
    """
    Six-layer quality gate + session filter.  Instantiate once, call .check() per bar.

    Parameters
    ----------
    block_counter_trend   : Block signals against a strong trend (ADX > 30)
    min_agreement         : Min rules that must agree on the direction
    max_daily_loss_pct    : Stop trading for the day after this equity loss
    max_portfolio_heat_pct: Max total open-risk as fraction of equity
    health_window         : Recent closed trades for rolling metrics
    min_sharpe            : Rolling Sharpe threshold
    min_profit_factor     : Rolling Profit Factor threshold
    max_drawdown_pct      : Equity drawdown kill-switch
    max_consecutive_losses: Consecutive-loss circuit-breaker
    cooldown_bars         : Minimum bars between two trades
    min_atr_multiplier    : Block signals in dead markets
    max_risk_pct          : Hard cap on equity at risk per trade
    atr_stop_multiplier   : ATR multiples used as effective stop distance
    session_filter        : SessionFilter instance (None = disable, daily data auto-skips)
    """

    def __init__(
        self,
        # Layer 1
        block_counter_trend:    bool  = True,
        # Layer 2
        min_agreement:          int   = 3,
        # Layer 3
        max_daily_loss_pct:     float = 0.02,
        # Layer 4
        max_portfolio_heat_pct: float = 0.06,
        # Layer 5
        health_window:          int   = 30,
        min_sharpe:             float = 0.5,
        min_profit_factor:      float = 1.1,
        # Layer 6
        max_drawdown_pct:       float = 0.10,
        max_consecutive_losses: int   = 4,
        cooldown_bars:          int   = 2,
        min_atr_multiplier:     float = 0.001,
        # Sizing
        max_risk_pct:           float = 0.02,
        atr_stop_multiplier:    float = 2.0,
        # Session / timezone
        session_filter:         Optional[SessionFilter] = None,
    ):
        self.block_counter_trend    = block_counter_trend
        self.min_agreement          = min_agreement
        self.max_daily_loss_pct     = max_daily_loss_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.health_window          = health_window
        self.min_sharpe             = min_sharpe
        self.min_profit_factor      = min_profit_factor
        self.max_drawdown_pct       = max_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_bars          = cooldown_bars
        self.min_atr_multiplier     = min_atr_multiplier
        self._session               = session_filter

        self._regime  = RegimeFilter()
        self._sizer   = PositionSizer(
            max_risk_pct=max_risk_pct,
            atr_multiplier=atr_stop_multiplier,
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def check(
        self,
        signal:               int,
        rule_votes:           pd.Series,
        df:                   pd.DataFrame,
        bar_index:            int,
        equity:               float,
        equity_curve:         List[float],
        closed_trades:        list,
        consecutive_losses:   int,
        bars_since_last_trade: int,
        daily_pnl:            float,
        portfolio_heat:       float,
        precomputed_regime:   Optional[RegimeState] = None,  # avoids duplicate ADX computation
    ) -> QualityResult:

        if signal == SIGNAL_HOLD:
            return QualityResult(approved=False, reasons=["Signal is HOLD — nothing to do"])

        reasons: List[str] = []

        # ── Layer 1: Regime ───────────────────────────────────────────
        regime = precomputed_regime if precomputed_regime is not None \
                 else self._regime.detect(df, bar_index)
        vol_multiplier = 1.0
        if regime is not None:
            vol_multiplier = regime.vol_multiplier
            if self.block_counter_trend:
                block_msg = regime.blocks_signal(signal)
                if block_msg:
                    reasons.append(f"[Regime] {block_msg}")

        # ── Layer 2: Rule agreement ───────────────────────────────────
        n_rules = len(rule_votes)
        n_agree = int((rule_votes == signal).sum())
        if n_agree < self.min_agreement:
            reasons.append(
                f"[Agreement] {n_agree}/{n_rules} rules agree "
                f"— need {self.min_agreement} (signal={_signal_name(signal)})"
            )

        # ── Layer 3: Daily loss limit ─────────────────────────────────
        if equity > 0 and daily_pnl < 0:
            daily_loss_frac = abs(daily_pnl) / equity
            if daily_loss_frac >= self.max_daily_loss_pct:
                reasons.append(
                    f"[DailyLimit] Loss today {daily_loss_frac*100:.2f}% "
                    f"≥ limit {self.max_daily_loss_pct*100:.1f}% — paused for the day"
                )

        # ── Layer 4: Portfolio heat ───────────────────────────────────
        max_heat = equity * self.max_portfolio_heat_pct
        if portfolio_heat >= max_heat:
            reasons.append(
                f"[Heat] Open risk {portfolio_heat:.0f} ≥ max {max_heat:.0f} "
                f"({self.max_portfolio_heat_pct*100:.0f}% of equity)"
            )

        # ── Layer 5: Rolling health metrics ──────────────────────────
        if len(closed_trades) >= self.health_window:
            reasons += self._rolling_health(closed_trades)

        # ── Layer 6: Classic micro-checks ─────────────────────────────
        reasons += self._classic_checks(
            df, bar_index, equity, equity_curve,
            consecutive_losses, bars_since_last_trade
        )

        if reasons:
            return QualityResult(approved=False, regime=regime, reasons=reasons)

        # ── Sizing (only when all layers pass) ────────────────────────
        atr        = self._atr(df, bar_index)
        entry_px   = float(df["close"].iloc[bar_index])
        sizing     = self._sizer.compute(
            equity=equity,
            entry_price=entry_px,
            atr=atr or entry_px * 0.01,
            closed_trades=closed_trades,
            vol_multiplier=vol_multiplier,
        )
        return QualityResult(approved=True, size=sizing.size, regime=regime)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _rolling_health(self, closed_trades: list) -> List[str]:
        recent = closed_trades[-self.health_window:]
        pnls   = [t.pnl for t in recent if t.pnl is not None]
        if len(pnls) < 2:
            return []

        reasons = []
        arr = np.array(pnls, dtype=float)

        # Profit Factor
        gross_win  = float(arr[arr > 0].sum())
        gross_loss = float(abs(arr[arr < 0].sum()))
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        if pf < self.min_profit_factor:
            reasons.append(
                f"[Health] Profit Factor {pf:.2f} < min {self.min_profit_factor} "
                f"(last {self.health_window} trades)"
            )

        # Annualised Sharpe (assumes each PnL is one bar → ×√252 proxy)
        std = arr.std(ddof=1)
        if std > 0:
            sharpe = (arr.mean() / std) * math.sqrt(252)
            if sharpe < self.min_sharpe:
                reasons.append(
                    f"[Health] Rolling Sharpe {sharpe:.2f} < min {self.min_sharpe} "
                    f"(last {self.health_window} trades)"
                )

        return reasons

    def _classic_checks(
        self,
        df: pd.DataFrame,
        bar_index: int,
        equity: float,
        equity_curve: List[float],
        consecutive_losses: int,
        bars_since_last_trade: int,
    ) -> List[str]:
        reasons = []

        # Session / timezone gate (skip for daily data — no intraday time info)
        if self._session is not None and not self._session.is_daily_data(df):
            ts = df.index[bar_index]
            allowed, reason = self._session.is_allowed(ts)
            if not allowed:
                reasons.append(reason)

        # Drawdown kill-switch
        if len(equity_curve) > 1:
            peak = max(equity_curve)
            dd   = (peak - equity_curve[-1]) / peak if peak > 0 else 0.0
            if dd >= self.max_drawdown_pct:
                reasons.append(
                    f"[Drawdown] {dd*100:.1f}% ≥ kill-switch "
                    f"{self.max_drawdown_pct*100:.1f}%"
                )

        # Consecutive-loss circuit-breaker
        if consecutive_losses >= self.max_consecutive_losses:
            reasons.append(
                f"[Losses] {consecutive_losses} consecutive losses "
                f"≥ limit {self.max_consecutive_losses}"
            )

        # Cooldown
        if bars_since_last_trade < self.cooldown_bars:
            reasons.append(
                f"[Cooldown] {bars_since_last_trade} bars since last trade "
                f"(min {self.cooldown_bars})"
            )

        # Dead-market ATR floor
        atr = self._atr(df, bar_index)
        if atr is not None:
            close = float(df["close"].iloc[bar_index])
            if close > 0 and (atr / close) < self.min_atr_multiplier:
                reasons.append(
                    f"[Volatility] ATR/price {atr/close:.5f} < floor "
                    f"{self.min_atr_multiplier} — dead market"
                )

        return reasons

    def _atr(self, df: pd.DataFrame, bar_index: int, period: int = 14) -> Optional[float]:
        start  = max(0, bar_index - period * 3)
        window = df.iloc[start: bar_index + 1]
        if len(window) < 2:
            return None
        tr = pd.concat([
            window["high"] - window["low"],
            (window["high"] - window["close"].shift(1)).abs(),
            (window["low"]  - window["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        val = float(tr.rolling(period).mean().iloc[-1])
        return val if not math.isnan(val) else None


# ── Utility ──────────────────────────────────────────────────────────

def _signal_name(signal: int) -> str:
    return {SIGNAL_BUY: "BUY", SIGNAL_SELL: "SELL", SIGNAL_HOLD: "HOLD"}.get(signal, str(signal))
