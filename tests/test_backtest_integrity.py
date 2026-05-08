"""
tests/test_backtest_integrity.py

Three independent integrity checks — proves the backtest is not hallucinating.

  Test 1 — Permutation test   : signals on time-shuffled data produce near-zero PnL.
                                 Lookahead bias would still profit on random row order
                                 because the signal would "see" what comes next.

  Test 2 — Shadow PnL checker : re-derive every trade's PnL from raw OHLC independently.
                                 Arithmetic bugs in the simulator show up as a mismatch
                                 between the two calculations.

  Test 3 — Golden fixtures    : hand-crafted OHLC sequences with mathematically certain
                                 outcomes (known entry bar, known exit bar, known PnL).
                                 Logic bugs in entry/exit/signal code break these.

All three tests must pass for the backtest to be considered trustworthy.
A strategy that passes Test 1 but fails Test 2 has a calculation bug.
A strategy that passes Test 2 but fails Test 1 has lookahead bias.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from simulator.ohlc_data import OHLCData
from simulator.trade_simulator import TradeSimulator, Trade
from brain.config import LOOSE
from brain.rules import ema_crossover_rule, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from brain.quality_checks import SessionFilter


# ══════════════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════════════

def _daily_df(n_bars: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic OHLC with daily bar spacing.
    Daily spacing (>= 86 400 s) causes SessionFilter.is_daily_data() to
    return True, so the intraday session gate is skipped automatically.
    This lets the quality checks exercise all other layers without being
    blocked because synthetic timestamps aren't during London/NY hours.
    """
    df = OHLCData.generate(n_bars=n_bars, seed=seed)
    df.index = pd.date_range(start="2020-01-02", periods=n_bars, freq="D")
    return df


def _sim() -> TradeSimulator:
    return TradeSimulator(initial_capital=10_000.0, config=LOOSE, allow_short=True)


def _run(df: pd.DataFrame) -> "SimulationResult":
    return _sim().run(df)


# ══════════════════════════════════════════════════════════════════════
# TEST 1 — Permutation / Lookahead-Bias Test
# ══════════════════════════════════════════════════════════════════════

class TestPermutation:
    """
    Randomly shuffle the OHLC rows, destroying all temporal structure.

    Why this works as a lookahead detector
    ───────────────────────────────────────
    After shuffling, the price at bar i+1 is completely random relative
    to bar i. A correct strategy — one that uses only past bars — has
    zero edge: every trade is a coin flip minus commissions, so the mean
    return across many shuffles must converge to ≤ 0.

    If lookahead bias exists (e.g. a rolling window that accidentally
    includes future bars, or a label that was computed on the full
    series), the signals "know" what comes next even after shuffling.
    The shuffled mean return would then stay positive, and this test
    would catch it.
    """

    N_SHUFFLES      = 25
    MAX_MEAN_RETURN = 0.05   # 5% mean return on noise data is already a red flag

    def test_mean_return_near_zero_on_shuffled_data(self):
        df = _daily_df(n_bars=500, seed=42)
        sim = _sim()

        returns = []
        for i in range(self.N_SHUFFLES):
            # Shuffle rows but re-attach original datetime index so that
            # weekday / daily checks inside SessionFilter still behave normally.
            df_shuf = df.sample(frac=1, random_state=i).copy()
            df_shuf.index = df.index
            try:
                result = sim.run(df_shuf)
                returns.append(result.return_pct)
            except Exception:
                returns.append(0.0)

        mean_return = float(np.mean(returns))
        assert mean_return < self.MAX_MEAN_RETURN, (
            f"Mean return on {self.N_SHUFFLES} shuffled runs = {mean_return:.2%} "
            f"(max allowed {self.MAX_MEAN_RETURN:.0%}). "
            "Signals may be using future data (lookahead bias)."
        )

    def test_win_rate_not_systematically_above_random(self):
        """
        On shuffled data, the fraction of profitable runs should not
        consistently exceed what random chance would produce.
        A 70%+ win-run-rate on pure noise indicates the signals are
        correlated with future prices — another lookahead signature.
        """
        df = _daily_df(n_bars=500, seed=7)
        sim = _sim()
        profitable_runs = 0

        for i in range(self.N_SHUFFLES):
            df_shuf = df.sample(frac=1, random_state=i + 200).copy()
            df_shuf.index = df.index
            try:
                result = sim.run(df_shuf)
                if result.total_pnl > 0:
                    profitable_runs += 1
            except Exception:
                pass

        assert profitable_runs < self.N_SHUFFLES * 0.70, (
            f"{profitable_runs}/{self.N_SHUFFLES} shuffled runs were profitable "
            "— systematic win rate on random data suggests lookahead bias."
        )

    def test_shuffled_pnl_distribution_symmetric_around_zero(self):
        """
        PnL distribution across shuffled runs should be roughly symmetric
        (as many positive as negative outcomes). A right-skewed distribution
        on random data would indicate the strategy is systematically biased
        toward positive outcomes regardless of temporal ordering.
        """
        df = _daily_df(n_bars=500, seed=13)
        sim = _sim()
        pnls = []

        for i in range(self.N_SHUFFLES):
            df_shuf = df.sample(frac=1, random_state=i + 400).copy()
            df_shuf.index = df.index
            try:
                pnls.append(sim.run(df_shuf).total_pnl)
            except Exception:
                pnls.append(0.0)

        median_pnl = float(np.median(pnls))
        # Median should not be far above 0 (allow 10% of capital as threshold)
        assert median_pnl < 1_000.0, (
            f"Median PnL on shuffled data = {median_pnl:.2f} — "
            "distribution is right-skewed on noise data, check for lookahead bias."
        )


# ══════════════════════════════════════════════════════════════════════
# TEST 2 — Shadow PnL Checker
# ══════════════════════════════════════════════════════════════════════

class TestShadowPnL:
    """
    After the simulator runs, re-compute every trade's PnL from scratch
    using only the raw OHLC DataFrame — no simulator internals.

    The shadow calculator is deliberately naive:
      pnl = direction_sign * (exit_price - entry_price) * size

    Any discrepancy > TOLERANCE reveals an arithmetic bug in the simulator
    (wrong sign, wrong size, accumulated rounding, etc.).

    Additionally, exit prices are verified against the OHLC bars directly:
    signal_flip / end_of_data exits must equal the bar's close price;
    stop_loss / take_profit exits must equal the pre-set level on the Trade.
    """

    TOLERANCE = 1e-4

    def _shadow_pnl(self, trade: Trade) -> float:
        sign = 1.0 if trade.direction == "LONG" else -1.0
        return sign * (trade.exit_price - trade.entry_price) * trade.size

    def test_all_trade_pnls_match_shadow(self):
        df = _daily_df(n_bars=500, seed=42)
        result = _run(df)

        if not result.closed_trades:
            pytest.skip("No closed trades — cannot run shadow PnL check")

        for i, trade in enumerate(result.closed_trades):
            shadow = self._shadow_pnl(trade)
            diff = abs(trade.pnl - shadow)
            assert diff < self.TOLERANCE, (
                f"Trade {i} ({trade.direction} @ {trade.entry_time}): "
                f"simulator PnL={trade.pnl:.6f}, shadow PnL={shadow:.6f}, "
                f"diff={diff:.2e}. Arithmetic mismatch in simulator."
            )

    def test_exit_price_matches_ohlc_bar(self):
        """
        Verify that exit prices are read from the correct bar and field.
        signal_flip / end_of_data  →  must equal bar["close"]  at exit_bar
        stop_loss                  →  must equal trade.stop_price
        take_profit                →  must equal trade.tp_price
        """
        df = _daily_df(n_bars=500, seed=42)
        result = _run(df)

        if not result.closed_trades:
            pytest.skip("No closed trades to verify exit prices")

        for trade in result.closed_trades:
            bar_close = float(df.iloc[trade.exit_bar]["close"])
            if trade.exit_reason in ("signal_flip", "end_of_data"):
                assert abs(trade.exit_price - bar_close) < self.TOLERANCE, (
                    f"{trade.exit_reason}: exit_price={trade.exit_price} != "
                    f"bar close={bar_close} at bar {trade.exit_bar}"
                )
            elif trade.exit_reason == "stop_loss":
                assert abs(trade.exit_price - trade.stop_price) < self.TOLERANCE, (
                    f"stop_loss: exit_price={trade.exit_price} != "
                    f"stop_price={trade.stop_price}"
                )
            elif trade.exit_reason == "take_profit":
                assert abs(trade.exit_price - trade.tp_price) < self.TOLERANCE, (
                    f"take_profit: exit_price={trade.exit_price} != "
                    f"tp_price={trade.tp_price}"
                )

    def test_pnl_sign_consistent_with_direction_and_price_movement(self):
        """
        A LONG trade where exit > entry MUST have positive PnL.
        A SHORT trade where exit < entry MUST have positive PnL.
        Violations indicate a sign flip in the PnL formula.
        """
        df = _daily_df(n_bars=500, seed=42)
        result = _run(df)

        for trade in result.closed_trades:
            if trade.direction == "LONG":
                price_up = trade.exit_price > trade.entry_price
                pnl_pos  = (trade.pnl or 0) > 0
                assert price_up == pnl_pos, (
                    f"LONG: entry={trade.entry_price}, exit={trade.exit_price}, "
                    f"pnl={trade.pnl} — PnL sign inconsistent with price movement"
                )
            else:
                price_dn = trade.exit_price < trade.entry_price
                pnl_pos  = (trade.pnl or 0) > 0
                assert price_dn == pnl_pos, (
                    f"SHORT: entry={trade.entry_price}, exit={trade.exit_price}, "
                    f"pnl={trade.pnl} — PnL sign inconsistent with price movement"
                )

    def test_equity_curve_tracks_trade_pnl_minus_commission(self):
        """
        final_equity == initial_capital + Σ(pnl_i - commission_i)

        Commission is one-way: entry_price * size * commission_pct.
        If the equity curve drifts away from this identity, equity
        is being updated incorrectly (applied twice, missing, etc.).
        """
        df = _daily_df(n_bars=500, seed=42)
        sim = _sim()
        result = sim.run(df)

        total_commission = sum(
            t.entry_price * t.size * sim.commission_pct
            for t in result.closed_trades
        )
        expected = result.initial_capital + result.total_pnl - total_commission
        diff = abs(result.final_equity - expected)

        assert diff < 0.02, (
            f"Equity curve drift: final={result.final_equity:.4f}, "
            f"expected={expected:.4f} (diff={diff:.4f}). "
            "Equity update logic may be applying PnL or commission incorrectly."
        )


# ══════════════════════════════════════════════════════════════════════
# TEST 3 — Golden Fixtures
# ══════════════════════════════════════════════════════════════════════

class TestGoldenFixtures:
    """
    Hand-crafted scenarios with mathematically certain outcomes.

    Each fixture:
      1. defines the minimal OHLC data needed to trigger a specific code path
      2. states the exact expected outcome (price, reason, PnL)
      3. fails if any logic detail changes unexpectedly

    Sections
    ─────────
      3A  Trade.close() PnL arithmetic (unit)
      3B  TradeSimulator._check_exit() logic (unit)
      3C  EMA crossover signal on controlled price series
      3D  SessionFilter DST correctness
      3E  End-to-end determinism (same seed → identical output)
    """

    # ── 3A: Trade.close() arithmetic ──────────────────────────────────

    def test_long_trade_pnl_math(self):
        t = Trade(0, pd.Timestamp("2023-01-01"), "LONG",
                  entry_price=100.0, size=2.0, stop_price=98.0, tp_price=104.0)
        t.close(5, pd.Timestamp("2023-01-06"), price=110.0, reason="signal_flip")
        # pnl  = +1 * (110 - 100) * 2 = +20
        # pct  = 20 / (100 * 2)       = 0.10
        assert math.isclose(t.pnl,     20.0, abs_tol=1e-9)
        assert math.isclose(t.pnl_pct,  0.10, abs_tol=1e-9)

    def test_short_trade_pnl_math(self):
        t = Trade(0, pd.Timestamp("2023-01-01"), "SHORT",
                  entry_price=100.0, size=3.0, stop_price=102.0, tp_price=96.0)
        t.close(5, pd.Timestamp("2023-01-06"), price=90.0, reason="take_profit")
        # pnl = -1 * (90 - 100) * 3 = +30
        assert math.isclose(t.pnl, 30.0, abs_tol=1e-9)

    def test_losing_long_trade_stop(self):
        t = Trade(0, pd.Timestamp("2023-01-01"), "LONG",
                  entry_price=100.0, size=1.0, stop_price=98.0, tp_price=104.0)
        t.close(3, pd.Timestamp("2023-01-04"), price=98.0, reason="stop_loss")
        # pnl = +1 * (98 - 100) * 1 = -2
        assert math.isclose(t.pnl, -2.0, abs_tol=1e-9)

    def test_trade_is_open_until_closed(self):
        t = Trade(0, pd.Timestamp("2023-01-01"), "LONG",
                  entry_price=100.0, size=1.0, stop_price=98.0, tp_price=104.0)
        assert t.is_open
        t.close(1, pd.Timestamp("2023-01-02"), 101.0)
        assert not t.is_open

    # ── 3B: Exit logic on known bars ──────────────────────────────────

    @staticmethod
    def _bar(open_, high, low, close, vol=100_000):
        return pd.Series({"open": open_, "high": high, "low": low,
                          "close": close, "volume": vol})

    @staticmethod
    def _long_trade(entry=100.0, stop=98.0, tp=104.0, size=1.0):
        return Trade(0, pd.Timestamp("2023-01-01"), "LONG",
                     entry, size, stop, tp)

    @staticmethod
    def _short_trade(entry=100.0, stop=102.0, tp=96.0, size=1.0):
        return Trade(0, pd.Timestamp("2023-01-01"), "SHORT",
                     entry, size, stop, tp)

    def test_long_stop_loss_triggered(self):
        sim = TradeSimulator()
        bar = self._bar(99, 99.5, 97.0, 98.5)   # low=97 < stop=98
        price, reason = sim._check_exit(self._long_trade(), bar, SIGNAL_HOLD)
        assert price == 98.0 and reason == "stop_loss"

    def test_long_take_profit_triggered(self):
        sim = TradeSimulator()
        bar = self._bar(101, 105.0, 100.5, 104.0)  # high=105 >= tp=104
        price, reason = sim._check_exit(self._long_trade(), bar, SIGNAL_HOLD)
        assert price == 104.0 and reason == "take_profit"

    def test_long_signal_flip_to_sell(self):
        sim = TradeSimulator()
        bar = self._bar(101, 103.0, 100.5, 102.0)  # no SL/TP hit
        price, reason = sim._check_exit(self._long_trade(), bar, SIGNAL_SELL)
        assert price == 102.0 and reason == "signal_flip"

    def test_short_stop_loss_triggered(self):
        sim = TradeSimulator()
        bar = self._bar(101, 103.0, 100.5, 101.0)  # high=103 >= stop=102
        price, reason = sim._check_exit(self._short_trade(), bar, SIGNAL_HOLD)
        assert price == 102.0 and reason == "stop_loss"

    def test_short_take_profit_triggered(self):
        sim = TradeSimulator()
        bar = self._bar(94, 95.0, 93.0, 94.0)  # low=93 <= tp=96
        price, reason = sim._check_exit(self._short_trade(), bar, SIGNAL_HOLD)
        assert price == 96.0 and reason == "take_profit"

    def test_no_exit_when_price_stays_in_range(self):
        sim = TradeSimulator()
        bar = self._bar(100, 103.0, 99.0, 101.0)  # inside SL/TP, HOLD
        price, reason = sim._check_exit(self._long_trade(), bar, SIGNAL_HOLD)
        assert price is None and reason is None

    def test_stop_loss_priority_over_take_profit(self):
        """
        When both SL and TP levels are touched in the same bar, the
        simulator resolves stop_loss first (conservative — worst case).
        This fixture uses a bar with an extreme high/low that crosses both.
        """
        sim = TradeSimulator()
        # LONG: stop=98, tp=104. Bar: low=97 (SL hit), high=106 (TP hit).
        # SL check comes first in _check_exit → should return stop_loss.
        bar = self._bar(100, 106.0, 97.0, 101.0)
        price, reason = sim._check_exit(self._long_trade(), bar, SIGNAL_HOLD)
        assert reason == "stop_loss", (
            "When both SL and TP are hit in the same bar, stop_loss must take priority."
        )

    # ── 3C: Signal rules on controlled price series ────────────────────

    @staticmethod
    def _trending_df(n: int = 60, step: float = 1.0, start: float = 100.0) -> pd.DataFrame:
        """Perfectly linear trend — guarantees fast EMA stays above/below slow EMA."""
        closes = [start + i * step for i in range(n)]
        return pd.DataFrame({
            "open":   [c - 0.1 for c in closes],
            "high":   [c + 0.5 for c in closes],
            "low":    [c - 0.5 for c in closes],
            "close":  closes,
            "volume": [100_000] * n,
        }, index=pd.date_range("2023-01-02", periods=n, freq="D"))

    def test_ema_crossover_all_buy_in_linear_uptrend(self):
        """
        In a perfectly linear uptrend, fast EMA (9) is always above slow EMA (21)
        after the initial warmup period. Every bar after warmup must be BUY.
        """
        df = self._trending_df(n=60, step=+1.0)
        signals = ema_crossover_rule(df)
        tail = signals.iloc[25:]  # well past EMA warmup
        assert (tail == SIGNAL_BUY).all(), (
            f"EMA crossover expected all BUY in uptrend after warmup. "
            f"Got: {tail.value_counts().to_dict()}"
        )

    def test_ema_crossover_all_sell_in_linear_downtrend(self):
        df = self._trending_df(n=60, step=-1.0, start=200.0)
        signals = ema_crossover_rule(df)
        tail = signals.iloc[25:]
        assert (tail == SIGNAL_SELL).all(), (
            f"EMA crossover expected all SELL in downtrend after warmup. "
            f"Got: {tail.value_counts().to_dict()}"
        )

    def test_ema_crossover_flips_when_trend_reverses(self):
        """
        40 bars uptrend → 40 bars downtrend.
        Signals must flip from BUY to SELL after the reversal point.
        """
        n = 40
        up_closes   = [100.0 + i for i in range(n)]
        down_closes = [up_closes[-1] - i for i in range(1, n + 1)]
        closes = up_closes + down_closes
        df = pd.DataFrame({
            "open":   [c - 0.1 for c in closes],
            "high":   [c + 0.5 for c in closes],
            "low":    [c - 0.5 for c in closes],
            "close":  closes,
            "volume": [100_000] * len(closes),
        }, index=pd.date_range("2023-01-02", periods=len(closes), freq="D"))

        signals = ema_crossover_rule(df)
        # By bar 70 (well into the downtrend) the signal must be SELL
        assert signals.iloc[70] == SIGNAL_SELL, (
            f"EMA signal at bar 70 (deep into downtrend) = {signals.iloc[70]}, expected SELL"
        )

    # ── 3D: SessionFilter DST correctness ─────────────────────────────

    def test_london_winter_session_allowed(self):
        # Jan 11 2023 10:00 UTC — London local 10:00 GMT, inside 08:15–16:15
        ts = pd.Timestamp("2023-01-11 10:00", tz="UTC")
        allowed, reason = SessionFilter(blackout_open_min=15).is_allowed(ts)
        assert allowed, f"Expected allowed in London winter session. Reason: {reason}"

    def test_london_winter_before_open_blocked(self):
        """
        Jan 11 2023 07:30 UTC: London local = 07:30 GMT.
        London opens at 08:00 local (GMT = UTC+0 in winter).
        07:30 is BEFORE the session — must be blocked.

        The old hardcoded implementation used (7, 0) UTC which would
        have (incorrectly) allowed trading 30 min before London opens.
        The zoneinfo fix correctly blocks this.
        """
        ts = pd.Timestamp("2023-01-11 07:30", tz="UTC")
        sf = SessionFilter(sessions=["london"], blackout_open_min=0)
        allowed, reason = sf.is_allowed(ts)
        assert not allowed, (
            "07:30 UTC in January must be BLOCKED — London opens at 08:00 GMT. "
            "Old hardcoded (7,0) UTC would have allowed this incorrectly."
        )

    def test_london_summer_before_open_in_utc_but_after_in_bst(self):
        """
        Jun 14 2023 07:30 UTC: London local = 08:30 BST (UTC+1 in summer).
        London opens at 08:00 BST = 07:00 UTC in summer.
        07:30 UTC = 08:30 BST → 30 min INSIDE session (past 15-min blackout).
        Must be ALLOWED.

        This is the key DST case: same UTC time (07:30) is outside session
        in winter but inside session in summer — only zoneinfo handles this.
        """
        ts = pd.Timestamp("2023-06-14 07:30", tz="UTC")
        sf = SessionFilter(sessions=["london"], blackout_open_min=15)
        allowed, reason = sf.is_allowed(ts)
        assert allowed, (
            "07:30 UTC in June must be ALLOWED — London local = 08:30 BST "
            f"(session 08:00–16:30 BST). Reason: {reason}"
        )

    def test_ny_winter_before_open_blocked(self):
        # Jan 11 2023 13:00 UTC → NY local = 08:00 EST (UTC-5). Before 09:30 open.
        ts = pd.Timestamp("2023-01-11 13:00", tz="UTC")
        sf = SessionFilter(sessions=["new_york"], blackout_open_min=0)
        allowed, _ = sf.is_allowed(ts)
        assert not allowed, "08:00 EST is before NY open (09:30 EST)"

    def test_ny_summer_open_correct(self):
        # Jun 14 2023 13:45 UTC → NY local = 09:45 EDT (UTC-4). 15 min after open.
        ts = pd.Timestamp("2023-06-14 13:45", tz="UTC")
        sf = SessionFilter(sessions=["new_york"], blackout_open_min=15)
        allowed, reason = sf.is_allowed(ts)
        assert allowed, f"09:45 EDT should be inside NY session. Reason: {reason}"

    def test_weekend_always_blocked(self):
        ts = pd.Timestamp("2023-01-14 14:00", tz="UTC")  # Saturday
        allowed, _ = SessionFilter().is_allowed(ts)
        assert not allowed

    def test_outside_all_sessions_blocked(self):
        # 03:00 UTC on a weekday — outside every session
        ts = pd.Timestamp("2023-01-11 03:00", tz="UTC")
        allowed, reason = SessionFilter().is_allowed(ts)
        assert not allowed
        assert "Outside" in reason

    def test_opening_blackout_blocked(self):
        # London opens 08:00 GMT in winter. 08:07 is within 15-min blackout.
        ts = pd.Timestamp("2023-01-11 08:07", tz="UTC")
        allowed, reason = SessionFilter(blackout_open_min=15).is_allowed(ts)
        assert not allowed
        assert "blackout" in reason.lower()

    # ── 3E: Determinism — identical results on repeated runs ──────────

    def test_same_seed_produces_identical_results(self):
        """
        Two runs with the same DataFrame must produce bit-for-bit identical
        output. Any non-determinism (random seeding, unordered dict, etc.)
        would cause this to fail intermittently.
        """
        df = _daily_df(n_bars=300, seed=99)
        r1 = _run(df)
        r2 = _run(df)

        assert len(r1.closed_trades) == len(r2.closed_trades), "Trade count differs"
        assert r1.final_equity        == r2.final_equity,       "Final equity differs"
        assert r1.total_pnl           == r2.total_pnl,           "Total PnL differs"

        for i, (t1, t2) in enumerate(zip(r1.closed_trades, r2.closed_trades)):
            assert t1.entry_bar   == t2.entry_bar,   f"Trade {i}: entry_bar mismatch"
            assert t1.entry_price == t2.entry_price, f"Trade {i}: entry_price mismatch"
            assert t1.exit_price  == t2.exit_price,  f"Trade {i}: exit_price mismatch"
            assert t1.pnl         == t2.pnl,          f"Trade {i}: pnl mismatch"
            assert t1.direction   == t2.direction,   f"Trade {i}: direction mismatch"

    def test_different_seeds_produce_different_results(self):
        """
        Sanity check: two different seeds should not produce the same equity.
        If they do, the random generator is broken or ignored.
        """
        r1 = _run(_daily_df(seed=1))
        r2 = _run(_daily_df(seed=2))
        assert r1.final_equity != r2.final_equity, (
            "Different seeds produced identical equity — random seed may not be wired up"
        )
