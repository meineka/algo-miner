"""
Python shadow of the Aziz_NQ.mq5 EA.

Mirrors the MQL5 signal + risk logic in vectorised pandas so we can
validate behaviour on the XAUUSD M1 dataset BEFORE running a real MT5
strategy-tester pass. Strategy is symbol-agnostic — XAUUSD is the
validation harness, NQ is the live target.

Outputs (relative to repo root):
  collab/jobs/results/shadow_<TS>/
    trades.csv        one row per closed trade
    summary.json      headline metrics
    equity_curve.csv  per-bar equity / cash

Usage:
  python scripts/aziz_ea_shadow.py
  python scripts/aziz_ea_shadow.py --csv data/xauusd_m1_sample.csv \
                                   --session-open 09:30 --session-close 16:00
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, time, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator.ohlc_data import OHLCData  # noqa: E402


# ─── EA defaults — mirror Inp_* in Aziz_NQ.mq5 ─────────────────────────
@dataclass
class EAConfig:
    session_open: time = time(9, 30)
    session_close: time = time(16, 0)
    blackout_close_min: int = 30
    orb_window_min: int = 15
    auto_flat_min: int = 5
    max_trades_per_day: int = 4

    use_orb: bool = True
    use_vwap_reclaim: bool = True
    vwap_confirm_bars: int = 2

    use_vwap_filter: bool = True
    use_ema_trend_filter: bool = True
    ema_fast: int = 9
    ema_slow: int = 20
    breakout_vol_mult: float = 1.3

    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 2.0
    max_consecutive_loss: int = 3
    cooldown_bars: int = 5
    max_drawdown_pct: float = 6.0
    atr_period: int = 14
    atr_stop_mult: float = 1.5
    tp1_r_multiple: float = 1.0
    tp2_r_multiple: float = 2.0
    partial1_pct: float = 50.0

    initial_equity: float = 10_000.0
    point_value: float = 1.0   # $1 per 1.0 lot per price point (NQ-ish default)
    min_lot: float = 0.01
    lot_step: float = 0.01


# ─── Trade data ────────────────────────────────────────────────────────
@dataclass
class Trade:
    open_bar: int
    open_time: pd.Timestamp
    direction: int            # +1 long, -1 short
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    lots_initial: float
    sl_current: float = 0.0
    tp1_filled: bool = False
    close_bar: Optional[int] = None
    close_time: Optional[pd.Timestamp] = None
    close_reason: Optional[str] = None
    realised_pnl: float = 0.0
    partial_pnl: float = 0.0
    runner_pnl: float = 0.0
    lots_remaining: float = 0.0


# ─── Helpers ──────────────────────────────────────────────────────────
def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]; low = df["low"]; close = df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def session_vwap_and_streaks(df: pd.DataFrame, sopen: time, sclose: time) -> pd.DataFrame:
    """Cumulative session VWAP + below/above streak counters (intra-day)."""
    out = pd.DataFrame(index=df.index)
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = tp * df["volume"]

    # Per-day cumulative VWAP, but only inside session window
    in_window = is_in_session(df.index, sopen, sclose)
    pv_in = pv.where(in_window, 0.0)
    vol_in = df["volume"].where(in_window, 0.0)

    day = df.index.date
    cum_pv = pv_in.groupby(day).cumsum()
    cum_vol = vol_in.groupby(day).cumsum()
    out["vwap"] = (cum_pv / cum_vol.replace(0, np.nan)).where(in_window)

    above = (df["close"] > out["vwap"]).fillna(False)
    below = (df["close"] < out["vwap"]).fillna(False)

    # Track streaks per day (reset on session-open boundary)
    streak_below = np.zeros(len(df), dtype=int)
    streak_above = np.zeros(len(df), dtype=int)
    streak_below_at_prev = np.zeros(len(df), dtype=int)
    streak_above_at_prev = np.zeros(len(df), dtype=int)

    sb = 0; sa = 0; current_day = None
    for i, (ts, a, b) in enumerate(zip(df.index, above.values, below.values)):
        if not in_window.iloc[i]:
            sb = 0; sa = 0
            streak_below_at_prev[i] = 0
            streak_above_at_prev[i] = 0
            continue
        if current_day != ts.date():
            sb = 0; sa = 0
            current_day = ts.date()
        # snapshot before updating
        streak_below_at_prev[i] = sb
        streak_above_at_prev[i] = sa
        if a:
            sa += 1; sb = 0
        elif b:
            sb += 1; sa = 0
        streak_below[i] = sb
        streak_above[i] = sa

    out["streak_below_cur"] = streak_below
    out["streak_above_cur"] = streak_above
    out["streak_below_at_prev"] = streak_below_at_prev
    out["streak_above_at_prev"] = streak_above_at_prev
    return out


def is_in_session(ts: pd.DatetimeIndex, sopen: time, sclose: time) -> pd.Series:
    """Boolean: timestamp is inside [sopen, sclose] inclusive."""
    minutes = ts.hour * 60 + ts.minute
    o = sopen.hour * 60 + sopen.minute
    c = sclose.hour * 60 + sclose.minute
    return pd.Series((minutes >= o) & (minutes <= c), index=ts)


def opening_range(df: pd.DataFrame, sopen: time, window_min: int) -> pd.DataFrame:
    """Per-day opening-range high/low/avg-volume, frozen after the window."""
    out = pd.DataFrame(index=df.index)
    day = df.index.date

    # session_minute relative to sopen on that day
    sopen_min = sopen.hour * 60 + sopen.minute
    bar_min = df.index.hour * 60 + df.index.minute
    sm = bar_min - sopen_min
    in_window = (sm >= 0) & (sm < window_min)

    high_in = df["high"].where(in_window)
    low_in = df["low"].where(in_window)
    vol_in = df["volume"].where(in_window)

    out["range_high"] = high_in.groupby(day).cummax().groupby(day).ffill()
    out["range_low"] = low_in.groupby(day).cummin().groupby(day).ffill()
    out["range_vol_avg"] = vol_in.groupby(day).transform(lambda s: s.dropna().mean())
    return out


# ─── Core simulator ──────────────────────────────────────────────────
def run_shadow(df: pd.DataFrame, cfg: EAConfig) -> dict:
    df = df.copy()

    # Pre-compute indicators
    df["ema_fast"] = ema(df["close"], cfg.ema_fast)
    df["ema_slow"] = ema(df["close"], cfg.ema_slow)
    df["atr"] = atr(df, cfg.atr_period)

    vstreaks = session_vwap_and_streaks(df, cfg.session_open, cfg.session_close)
    orng = opening_range(df, cfg.session_open, cfg.orb_window_min)
    df = pd.concat([df, vstreaks, orng], axis=1)
    df["in_session"] = is_in_session(df.index, cfg.session_open, cfg.session_close)

    # State
    equity = cfg.initial_equity
    cash = cfg.initial_equity
    peak_equity = equity
    closed: List[Trade] = []
    open_trade: Optional[Trade] = None
    equity_curve = []

    current_day = None
    day_start_equity = equity
    day_realised_pnl = 0.0
    halted_for_day = False
    halted_for_dd = False
    consecutive_losses = 0
    bars_since_trade = 9999
    trades_today = 0
    orb_traded_long = False
    orb_traded_short = False
    vwap_reclaim_done = False

    sopen_min = cfg.session_open.hour * 60 + cfg.session_open.minute
    sclose_min = cfg.session_close.hour * 60 + cfg.session_close.minute
    flat_min = sclose_min - cfg.auto_flat_min
    orb_done_min = sopen_min + cfg.orb_window_min
    blackout_min = sclose_min - cfg.blackout_close_min

    for i, ts in enumerate(df.index):
        row = df.iloc[i]

        # Day rollover
        d = ts.date()
        if current_day != d:
            current_day = d
            day_start_equity = equity
            day_realised_pnl = 0.0
            halted_for_day = False
            trades_today = 0
            orb_traded_long = False
            orb_traded_short = False
            vwap_reclaim_done = False

        bar_min = ts.hour * 60 + ts.minute

        # Drawdown kill (permanent)
        if equity > peak_equity: peak_equity = equity
        if not halted_for_dd and peak_equity > 0:
            dd_pct = 100.0 * (peak_equity - equity) / peak_equity
            if dd_pct >= cfg.max_drawdown_pct:
                halted_for_dd = True
                if open_trade is not None:
                    close_position(open_trade, i, ts, row["close"], "dd_kill", df, cfg)
                    realized = open_trade.realised_pnl
                    cash += realized
                    equity = cash
                    day_realised_pnl += realized
                    if realized < 0: consecutive_losses += 1
                    elif realized > 0: consecutive_losses = 0
                    closed.append(open_trade)
                    open_trade = None

        if halted_for_dd:
            equity_curve.append((ts, equity))
            continue

        # Day-loss circuit
        if not halted_for_day and day_start_equity > 0:
            day_loss_pct = 100.0 * (-day_realised_pnl) / day_start_equity
            if day_loss_pct >= cfg.max_daily_loss_pct:
                halted_for_day = True
                if open_trade is not None:
                    close_position(open_trade, i, ts, row["close"], "day_stop", df, cfg)
                    realized = open_trade.realised_pnl
                    cash += realized
                    equity = cash
                    day_realised_pnl += realized
                    if realized < 0: consecutive_losses += 1
                    elif realized > 0: consecutive_losses = 0
                    closed.append(open_trade)
                    open_trade = None

        # Auto-flat before close
        if open_trade is not None and bar_min >= flat_min:
            close_position(open_trade, i, ts, row["close"], "auto_flat", df, cfg)
            realized = open_trade.realised_pnl
            cash += realized
            equity = cash
            day_realised_pnl += realized
            if realized < 0: consecutive_losses += 1
            elif realized > 0: consecutive_losses = 0
            closed.append(open_trade)
            open_trade = None

        # Manage open position: SL / TP1 partial / TP2
        if open_trade is not None:
            outcome = manage_position(open_trade, row, ts, i, cfg)
            if outcome == "closed":
                realized = open_trade.realised_pnl
                cash += realized
                equity = cash
                day_realised_pnl += realized
                if realized < 0: consecutive_losses += 1
                elif realized > 0: consecutive_losses = 0
                closed.append(open_trade)
                open_trade = None
                bars_since_trade = 0
            elif outcome == "partial":
                cash += open_trade.partial_pnl
                equity = cash + mark_to_market(open_trade, row["close"])
            else:
                equity = cash + mark_to_market(open_trade, row["close"])

        # Mark-to-market on bar close even without open trade
        if open_trade is None:
            equity = cash
        equity_curve.append((ts, equity))

        # Entry gating
        if open_trade is not None: continue
        if halted_for_day or halted_for_dd: continue
        if consecutive_losses >= cfg.max_consecutive_loss: continue
        if bars_since_trade < cfg.cooldown_bars:
            bars_since_trade += 1
            continue
        if trades_today >= cfg.max_trades_per_day: continue

        # Time gates
        if bar_min < orb_done_min: continue
        if bar_min > blackout_min: continue
        if not row["in_session"]: continue

        # Skip rows before indicators warm up
        if not np.isfinite(row.get("atr", np.nan)): continue
        if not np.isfinite(row.get("ema_fast", np.nan)): continue
        if not np.isfinite(row.get("ema_slow", np.nan)): continue

        # Signal
        sig, kind = compute_signal(row, cfg, orb_traded_long, orb_traded_short, vwap_reclaim_done)
        if sig == 0: continue

        # Open trade
        price = row["close"]
        a = row["atr"]
        if a <= 0 or not np.isfinite(a): continue
        stop_dist = a * cfg.atr_stop_mult
        if sig > 0:
            sl = price - stop_dist
            tp1 = price + stop_dist * cfg.tp1_r_multiple
            tp2 = price + stop_dist * cfg.tp2_r_multiple
        else:
            sl = price + stop_dist
            tp1 = price - stop_dist * cfg.tp1_r_multiple
            tp2 = price - stop_dist * cfg.tp2_r_multiple

        risk_money = equity * (cfg.risk_per_trade_pct / 100.0)
        loss_per_lot = stop_dist * cfg.point_value
        if loss_per_lot <= 0: continue
        lots = np.floor((risk_money / loss_per_lot) / cfg.lot_step) * cfg.lot_step
        if lots < cfg.min_lot: continue

        open_trade = Trade(
            open_bar=i, open_time=ts, direction=sig, entry_price=price,
            sl=sl, tp1=tp1, tp2=tp2, lots_initial=lots, sl_current=sl,
            lots_remaining=lots,
        )
        trades_today += 1
        bars_since_trade = 0
        if sig > 0: orb_traded_long = (kind == "orb") or orb_traded_long
        else:       orb_traded_short = (kind == "orb") or orb_traded_short
        if kind == "vwap": vwap_reclaim_done = True

    # Close anything left open at end of data
    if open_trade is not None:
        close_position(open_trade, len(df) - 1, df.index[-1], df["close"].iloc[-1], "end_of_data", df, cfg)
        cash += open_trade.realised_pnl
        equity = cash
        closed.append(open_trade)

    return summarize(closed, equity_curve, cfg)


def compute_signal(row, cfg: EAConfig,
                   orb_long_done, orb_short_done, vwap_reclaim_done) -> tuple:
    last_close = row["close"]; last_open = row["open"]; last_vol = row["volume"]
    bull = last_close > last_open
    bear = last_close < last_open
    vwap = row.get("vwap", np.nan)
    rh = row.get("range_high", np.nan); rl = row.get("range_low", np.nan)
    rv = row.get("range_vol_avg", np.nan)
    ema_f = row.get("ema_fast", np.nan); ema_s = row.get("ema_slow", np.nan)

    # ORB route
    if cfg.use_orb and np.isfinite(rh) and np.isfinite(rl) and np.isfinite(rv):
        vol_ok = last_vol > cfg.breakout_vol_mult * max(rv, 1.0)
        if not orb_long_done and last_close > rh and vol_ok:
            vwap_ok = (not cfg.use_vwap_filter) or (np.isfinite(vwap) and last_close > vwap)
            ema_ok = (not cfg.use_ema_trend_filter) or (np.isfinite(ema_f) and np.isfinite(ema_s) and ema_f > ema_s)
            if vwap_ok and ema_ok: return (+1, "orb")
        if not orb_short_done and last_close < rl and vol_ok:
            vwap_ok = (not cfg.use_vwap_filter) or (np.isfinite(vwap) and last_close < vwap)
            ema_ok = (not cfg.use_ema_trend_filter) or (np.isfinite(ema_f) and np.isfinite(ema_s) and ema_f < ema_s)
            if vwap_ok and ema_ok: return (-1, "orb")

    # VWAP reclaim route
    if cfg.use_vwap_reclaim and not vwap_reclaim_done:
        sb_prev = row.get("streak_below_at_prev", 0)
        sa_prev = row.get("streak_above_at_prev", 0)
        sa_cur = row.get("streak_above_cur", 0)
        sb_cur = row.get("streak_below_cur", 0)
        if sb_prev >= cfg.vwap_confirm_bars and sa_cur == 1 and bull:
            ema_ok = (not cfg.use_ema_trend_filter) or (np.isfinite(ema_f) and np.isfinite(ema_s) and ema_f > ema_s)
            if ema_ok: return (+1, "vwap")
        if sa_prev >= cfg.vwap_confirm_bars and sb_cur == 1 and bear:
            ema_ok = (not cfg.use_ema_trend_filter) or (np.isfinite(ema_f) and np.isfinite(ema_s) and ema_f < ema_s)
            if ema_ok: return (-1, "vwap")
    return (0, None)


def manage_position(tr: Trade, row, ts, i, cfg: EAConfig) -> str:
    """Returns 'open' / 'partial' / 'closed'."""
    high = row["high"]; low = row["low"]; close = row["close"]
    pv = cfg.point_value

    # Check SL hit first (conservative — worst-case fill)
    if tr.direction > 0 and low <= tr.sl_current:
        close_position(tr, i, ts, tr.sl_current, "stop_loss", None, cfg)
        return "closed"
    if tr.direction < 0 and high >= tr.sl_current:
        close_position(tr, i, ts, tr.sl_current, "stop_loss", None, cfg)
        return "closed"

    # Check TP1 partial
    if not tr.tp1_filled:
        hit_tp1 = (tr.direction > 0 and high >= tr.tp1) or (tr.direction < 0 and low <= tr.tp1)
        if hit_tp1:
            close_lots = round(tr.lots_initial * (cfg.partial1_pct / 100.0) / cfg.lot_step) * cfg.lot_step
            if close_lots >= cfg.min_lot and close_lots < tr.lots_remaining:
                sign = tr.direction
                partial_pnl = sign * (tr.tp1 - tr.entry_price) * close_lots * pv
                tr.partial_pnl = partial_pnl
                tr.lots_remaining -= close_lots
                tr.sl_current = tr.entry_price  # break-even on runner
                tr.tp1_filled = True
                return "partial"

    # Check TP2 hit on the runner
    hit_tp2 = (tr.direction > 0 and high >= tr.tp2) or (tr.direction < 0 and low <= tr.tp2)
    if hit_tp2:
        close_position(tr, i, ts, tr.tp2, "take_profit", None, cfg)
        return "closed"

    return "open"


def close_position(tr: Trade, i, ts, price, reason, df, cfg: EAConfig) -> None:
    sign = tr.direction
    pv = cfg.point_value
    tr.runner_pnl = sign * (price - tr.entry_price) * tr.lots_remaining * pv
    tr.realised_pnl = tr.partial_pnl + tr.runner_pnl
    tr.close_bar = i; tr.close_time = ts; tr.close_reason = reason
    tr.lots_remaining = 0.0


def mark_to_market(tr: Trade, price: float) -> float:
    return tr.direction * (price - tr.entry_price) * tr.lots_remaining


def summarize(trades: List[Trade], equity_curve, cfg: EAConfig) -> dict:
    total = len(trades)
    wins = sum(1 for t in trades if t.realised_pnl > 0)
    losses = sum(1 for t in trades if t.realised_pnl < 0)
    gross_win = sum(t.realised_pnl for t in trades if t.realised_pnl > 0)
    gross_loss = -sum(t.realised_pnl for t in trades if t.realised_pnl < 0)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    net = gross_win - gross_loss
    eq = pd.Series({ts: v for ts, v in equity_curve})
    max_dd = (eq.cummax() - eq).max() if len(eq) else 0.0
    max_dd_pct = (max_dd / eq.cummax().max()) * 100 if len(eq) else 0.0
    by_reason = {}
    for t in trades:
        by_reason[t.close_reason] = by_reason.get(t.close_reason, 0) + 1

    return {
        "config": asdict(cfg) | {
            "session_open": cfg.session_open.strftime("%H:%M"),
            "session_close": cfg.session_close.strftime("%H:%M"),
        },
        "trades_total": total,
        "trades_won": wins,
        "trades_lost": losses,
        "win_rate_pct": (100.0 * wins / total) if total else 0.0,
        "gross_win": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "net_pnl": round(net, 2),
        "profit_factor": round(pf, 3),
        "max_drawdown": round(float(max_dd), 2),
        "max_drawdown_pct": round(float(max_dd_pct), 2),
        "final_equity": round(float(eq.iloc[-1]) if len(eq) else cfg.initial_equity, 2),
        "close_reasons": by_reason,
        "trades": [
            {
                "open_time": str(t.open_time),
                "close_time": str(t.close_time),
                "direction": "LONG" if t.direction > 0 else "SHORT",
                "entry": round(t.entry_price, 4),
                "sl": round(t.sl, 4),
                "tp2": round(t.tp2, 4),
                "lots": round(t.lots_initial, 4),
                "pnl": round(t.realised_pnl, 2),
                "reason": t.close_reason,
            } for t in trades
        ],
        "equity_curve": [(str(ts), round(float(v), 2)) for ts, v in equity_curve[::max(len(equity_curve)//500, 1)]],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=str(ROOT / "data/xauusd_m1_sample.csv"))
    p.add_argument("--session-open", default="09:30")
    p.add_argument("--session-close", default="16:00")
    p.add_argument("--out-dir", default=None)
    args = p.parse_args()

    cfg = EAConfig(
        session_open=datetime.strptime(args.session_open, "%H:%M").time(),
        session_close=datetime.strptime(args.session_close, "%H:%M").time(),
    )

    print(f"[shadow] loading {args.csv}")
    df = OHLCData.from_csv(args.csv)
    print(f"[shadow] {len(df)} bars  {df.index[0]}  →  {df.index[-1]}")

    print(f"[shadow] running with session {cfg.session_open}–{cfg.session_close} (server time of CSV)")
    result = run_shadow(df, cfg)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
    out_dir = Path(args.out_dir) if args.out_dir else (ROOT / "collab/jobs/results" / f"shadow_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "summary.json").write_text(json.dumps(result, indent=2, default=str))
    pd.DataFrame(result["trades"]).to_csv(out_dir / "trades.csv", index=False)
    pd.DataFrame(result["equity_curve"], columns=["timestamp", "equity"]).to_csv(out_dir / "equity_curve.csv", index=False)

    print(f"[shadow] DONE → {out_dir}")
    print(f"[shadow] trades={result['trades_total']}  "
          f"win%={result['win_rate_pct']:.1f}  "
          f"net={result['net_pnl']:+.2f}  "
          f"PF={result['profit_factor']:.2f}  "
          f"maxDD%={result['max_drawdown_pct']:.2f}")


if __name__ == "__main__":
    main()
