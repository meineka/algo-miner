"""
OHLC Data — synthetic generator and CSV loader.

Synthetic data uses geometric Brownian motion so price paths look realistic.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path


class OHLCData:
    """
    Factory for OHLC DataFrames.

    Columns produced: datetime, open, high, low, close, volume
    The DataFrame index is the datetime column (DatetimeIndex).
    """

    # ------------------------------------------------------------------
    # Public factory methods
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        n_bars: int = 500,
        start: str = "2023-01-01",
        freq: str = "1h",
        initial_price: float = 100.0,
        mu: float = 0.0001,        # drift per bar
        sigma: float = 0.012,      # volatility per bar
        seed: int | None = 42,
    ) -> pd.DataFrame:
        """
        Generate synthetic OHLC data using geometric Brownian motion.

        Parameters
        ----------
        n_bars        : number of bars to generate
        start         : start datetime string
        freq          : pandas frequency string (e.g. '1h', '1d', '15min')
        initial_price : starting close price
        mu            : per-bar drift
        sigma         : per-bar volatility (std of log-returns)
        seed          : random seed for reproducibility (None = random)
        """
        rng = np.random.default_rng(seed)
        index = pd.date_range(start=start, periods=n_bars, freq=freq)

        # close prices via GBM
        log_returns = rng.normal(mu, sigma, n_bars)
        closes = initial_price * np.exp(np.cumsum(log_returns))

        # intra-bar noise: open slightly offset from prev close
        opens = np.empty(n_bars)
        opens[0] = initial_price
        opens[1:] = closes[:-1] * (1 + rng.normal(0, sigma * 0.3, n_bars - 1))

        # high and low around the open/close range
        bar_range = np.abs(closes - opens)
        noise_h = rng.uniform(0.001, 0.015, n_bars) * closes
        noise_l = rng.uniform(0.001, 0.015, n_bars) * closes

        highs = np.maximum(opens, closes) + bar_range * 0.3 + noise_h
        lows  = np.minimum(opens, closes) - bar_range * 0.3 - noise_l

        # volume: log-normal with occasional spikes
        base_volume = rng.lognormal(mean=10, sigma=0.8, size=n_bars).astype(int)
        spike_mask  = rng.random(n_bars) < 0.05
        base_volume[spike_mask] = (base_volume[spike_mask] * rng.uniform(3, 8, spike_mask.sum())).astype(int)

        df = pd.DataFrame({
            "open":   np.round(opens, 4),
            "high":   np.round(highs, 4),
            "low":    np.round(lows, 4),
            "close":  np.round(closes, 4),
            "volume": base_volume,
        }, index=index)
        df.index.name = "datetime"
        return df

    @classmethod
    def from_csv(cls, path: str | Path, datetime_col: str = "datetime") -> pd.DataFrame:
        """
        Load OHLC data from a CSV file.

        The CSV must have columns: datetime, open, high, low, close, volume
        (case-insensitive).  datetime is parsed and set as the index.
        """
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower()

        if datetime_col not in df.columns:
            raise ValueError(f"Column '{datetime_col}' not found.  Available: {list(df.columns)}")

        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.set_index(datetime_col).sort_index()

        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        return df

    @classmethod
    def to_csv(cls, df: pd.DataFrame, path: str | Path) -> None:
        """Save an OHLC DataFrame to CSV."""
        df.to_csv(path)
        print(f"Saved {len(df)} bars to {path}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def summary(df: pd.DataFrame) -> str:
        return (
            f"Bars    : {len(df)}\n"
            f"From    : {df.index[0]}\n"
            f"To      : {df.index[-1]}\n"
            f"Close Hi : {df['close'].max():.4f}\n"
            f"Close Lo : {df['close'].min():.4f}\n"
            f"Avg Vol : {df['volume'].mean():.0f}"
        )
