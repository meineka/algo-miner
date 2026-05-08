"""
tests/test_csv_loading.py

Validates that a new chat instance can correctly load and use the
committed real-data CSV (data/xauusd_m1_sample.csv).

These tests serve as a "new-chat health check" — if they all pass,
the environment is correctly set up and the data is usable.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from simulator.ohlc_data import OHLCData
from brain.prerequisites import Prerequisites

DATA_DIR  = Path(__file__).parent.parent / "data"
SAMPLE    = DATA_DIR / "xauusd_m1_sample.csv"


# ══════════════════════════════════════════════════════════════════════
# Availability guard — skip gracefully if file is missing
# ══════════════════════════════════════════════════════════════════════

def _require_sample():
    if not SAMPLE.exists():
        pytest.skip(
            f"Sample CSV not found at {SAMPLE}. "
            "Run: git pull  (the file is committed in data/)"
        )


# ══════════════════════════════════════════════════════════════════════
# Test 1 — File can be loaded
# ══════════════════════════════════════════════════════════════════════

class TestCSVLoad:

    def test_file_exists(self):
        _require_sample()
        assert SAMPLE.exists(), f"Missing: {SAMPLE}"

    def test_loads_without_error(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert df is not None

    def test_has_correct_columns(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert set(df.columns) == {"open", "high", "low", "close", "volume"}, (
            f"Expected 5 canonical columns, got: {list(df.columns)}"
        )

    def test_index_is_datetime(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert isinstance(df.index, pd.DatetimeIndex), (
            f"Index must be DatetimeIndex, got {type(df.index)}"
        )

    def test_index_is_sorted(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert df.index.is_monotonic_increasing, "DatetimeIndex must be sorted ascending"

    def test_no_nulls(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        nulls = df.isnull().sum().sum()
        assert nulls == 0, f"Found {nulls} null values in loaded DataFrame"

    def test_minimum_row_count(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert len(df) >= 10_000, (
            f"Expected >= 10 000 rows in sample, got {len(df)}"
        )

    def test_prices_are_positive(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        for col in ("open", "high", "low", "close"):
            assert (df[col] > 0).all(), f"Column '{col}' contains non-positive prices"

    def test_ohlc_consistency(self):
        """high >= max(open, close) and low <= min(open, close) for every bar."""
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        bad_high = (df["high"] < df[["open", "close"]].max(axis=1)).sum()
        bad_low  = (df["low"]  > df[["open", "close"]].min(axis=1)).sum()
        assert bad_high == 0, f"{bad_high} bars where high < max(open, close)"
        assert bad_low  == 0, f"{bad_low} bars where low > min(open, close)"

    def test_volume_is_non_negative(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert (df["volume"] >= 0).all(), "volume column contains negative values"


# ══════════════════════════════════════════════════════════════════════
# Test 2 — Data passes Prerequisites gate
# ══════════════════════════════════════════════════════════════════════

class TestPrerequisites:
    """
    The 50 000-bar M1 sample must pass the Prerequisites check so it can
    actually be used by the simulator.  If this fails, the data is unusable
    regardless of strategy parameters.
    """

    def test_prerequisites_pass(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        prereq = Prerequisites()
        result = prereq.check(df)
        assert result.passed, (
            f"Prerequisites failed on sample data:\n{result}"
        )


# ══════════════════════════════════════════════════════════════════════
# Test 3 — Instrument / date sanity
# ══════════════════════════════════════════════════════════════════════

class TestDataSanity:
    """Spot-checks that this is actually XAUUSD M1 data in the right range."""

    def test_price_range_plausible_for_xauusd(self):
        """XAUUSD 2025 traded between ~2 500 and ~3 500 USD/oz."""
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        mid = df["close"].median()
        assert 2_000 < mid < 6_000, (
            f"Median close {mid:.2f} is outside expected XAUUSD range 2000-6000. "
            "Wrong instrument or wrong CSV?"
        )

    def test_date_range_starts_2025(self):
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        assert df.index[0].year == 2025, (
            f"Expected data starting in 2025, got {df.index[0]}"
        )

    def test_bar_frequency_is_1_minute(self):
        """Consecutive bars should be ~60 seconds apart (M1 data)."""
        _require_sample()
        df = OHLCData.from_csv(SAMPLE)
        # Use most common delta to ignore gaps (weekends, holidays)
        deltas = df.index.to_series().diff().dropna()
        mode_seconds = deltas.mode()[0].total_seconds()
        assert mode_seconds == 60.0, (
            f"Expected 60s bar spacing (M1), got modal delta = {mode_seconds}s"
        )


# ══════════════════════════════════════════════════════════════════════
# Test 4 — Simulator can run on real data end-to-end
# ══════════════════════════════════════════════════════════════════════

class TestSimulatorOnRealData:
    """
    Smoke test: the simulator must complete a full run on the sample
    without errors.  Uses LOOSE config + session filter disabled so
    trades are actually generated despite M1 intraday timing.
    """

    def test_simulator_runs_without_error(self):
        _require_sample()
        from simulator.trade_simulator import TradeSimulator
        from brain.config import LOOSE
        from dataclasses import replace

        df = OHLCData.from_csv(SAMPLE)
        # Use first 5 000 bars for speed; disable session filter for M1 data
        df_small = df.head(5_000)
        cfg = replace(LOOSE, disable_session_filter=True)
        sim = TradeSimulator(initial_capital=10_000, config=cfg)
        result = sim.run(df_small)

        assert result is not None
        assert result.initial_capital == 10_000
        assert len(result.equity_curve) > 0

    def test_equity_curve_starts_at_initial_capital(self):
        _require_sample()
        from simulator.trade_simulator import TradeSimulator
        from brain.config import LOOSE
        from dataclasses import replace

        df  = OHLCData.from_csv(SAMPLE).head(5_000)
        cfg = replace(LOOSE, disable_session_filter=True)
        result = TradeSimulator(initial_capital=10_000, config=cfg).run(df)

        assert result.equity_curve[0] == 10_000.0, (
            f"Equity curve must start at initial_capital=10000, "
            f"got {result.equity_curve[0]}"
        )
