"""
Smoke tests for the Aziz rule set.

These tests don't assert on PnL — they verify shape and integrity:
  - Each Aziz rule returns a Series aligned to the input index
  - Every value is one of {-1, 0, +1}
  - Rules don't crash on a DatetimeIndex DataFrame nor on integer-indexed
    synthetic data
  - The Rules registry assembles the 6 Aziz rules under style='aziz'
  - StrategyMiner.generate(style='aziz') produces valid genomes
  - TradeSimulator runs end-to-end with style='aziz' on real OHLC data
"""
from __future__ import annotations

import pandas as pd
import pytest

from brain.aziz_rules import (
    AZIZ_RULES,
    abcd_pattern_rule,
    bull_flag_rule,
    ma_trend_pullback_rule,
    opening_range_breakout_rule,
    red_to_green_rule,
    vwap_reclaim_rule,
)
from brain.config import AZIZ
from brain.rules import Rules, SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL
from brain.strategy_genome import AZIZ_SEEDS, StrategyMiner
from simulator.ohlc_data import OHLCData
from simulator.trade_simulator import TradeSimulator


def _intraday_df(n_days: int = 5, bars_per_day: int = 60) -> pd.DataFrame:
    """5 days of synthetic 1-minute bars with a DatetimeIndex (US market hours)."""
    frames = []
    for d in range(n_days):
        start = pd.Timestamp("2025-01-06") + pd.Timedelta(days=d)
        df = OHLCData.generate(
            n_bars=bars_per_day,
            start=start.replace(hour=9, minute=30).isoformat(),
            freq="1min",
            seed=42 + d,
        )
        frames.append(df)
    return pd.concat(frames)


@pytest.fixture(scope="module")
def df_intraday() -> pd.DataFrame:
    return _intraday_df()


@pytest.mark.parametrize("rule_fn", [fn for _, fn in AZIZ_RULES])
def test_rule_returns_aligned_int_signals(df_intraday, rule_fn):
    out = rule_fn(df_intraday)
    assert isinstance(out, pd.Series)
    assert len(out) == len(df_intraday)
    assert out.index.equals(df_intraday.index)
    assert set(out.unique()).issubset({SIGNAL_BUY, SIGNAL_HOLD, SIGNAL_SELL})


@pytest.mark.parametrize("rule_fn", [fn for _, fn in AZIZ_RULES])
def test_rule_handles_integer_index(rule_fn):
    df = OHLCData.generate(n_bars=200, seed=7).reset_index(drop=True)
    out = rule_fn(df)
    assert isinstance(out, pd.Series)
    assert len(out) == len(df)


def test_rules_registry_aziz_style(df_intraday):
    rules = Rules(style="aziz")
    assert len(rules.rule_names) == 6
    sig = rules.evaluate(df_intraday, regimes=[None] * len(df_intraday))
    assert "signal" in sig.columns
    assert set(sig["signal"].unique()).issubset({-1, 0, 1})


def test_rules_registry_hybrid_style(df_intraday):
    rules = Rules(style="hybrid")
    assert len(rules.rule_names) == 10  # 4 classic + 6 aziz


def test_rules_registry_rejects_unknown_style():
    with pytest.raises(ValueError):
        Rules(style="bogus")


def test_miner_generates_aziz_pool():
    miner = StrategyMiner(n_random=5, seed=42, style="aziz")
    pool = miner.generate()
    assert len(pool) == len(AZIZ_SEEDS) + 5
    for g in pool:
        assert g.style == "aziz"
        assert g.ma_fast_span < g.ma_slow_span
        assert 0 < g.orb_window_bars <= 60


def test_simulator_runs_aziz_on_real_data():
    df = OHLCData.from_csv("data/xauusd_m1_sample.csv").head(2000)
    sim = TradeSimulator(initial_capital=10_000.0, config=AZIZ, style="aziz")
    result = sim.run(df)
    # We don't assert PnL — only that the loop completed and equity is sane
    assert len(result.equity_curve) >= 1
    assert result.equity_curve[0] == 10_000.0
    assert result.equity_curve[-1] > 0
