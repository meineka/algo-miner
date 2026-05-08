"""
Brain Prerequisites — checks that all conditions are met before the brain
can generate a trading signal.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import pandas as pd


@dataclass
class PrerequisiteResult:
    passed: bool
    failures: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.passed:
            return "✓ All prerequisites passed"
        return "✗ Prerequisites failed:\n" + "\n".join(f"  - {f}" for f in self.failures)


class Prerequisites:
    """
    Validates that incoming OHLC data satisfies minimum requirements
    before the brain evaluates any trading rule.
    """

    MIN_BARS = 50          # need enough history for indicators
    MAX_SPREAD_PCT = 0.10  # max allowed H-L spread as fraction of close
    MIN_VOLUME = 1         # non-zero volume required

    def check(self, df: pd.DataFrame) -> PrerequisiteResult:
        """Run all prerequisite checks and return a consolidated result."""
        failures: List[str] = []

        failures += self._check_columns(df)
        if failures:                     # no point going further without columns
            return PrerequisiteResult(passed=False, failures=failures)

        failures += self._check_min_bars(df)
        failures += self._check_no_nulls(df)
        failures += self._check_ohlc_integrity(df)
        failures += self._check_volume(df)
        failures += self._check_spread(df)

        return PrerequisiteResult(passed=len(failures) == 0, failures=failures)

    # ------------------------------------------------------------------ #
    # individual checks                                                    #
    # ------------------------------------------------------------------ #

    def _check_columns(self, df: pd.DataFrame) -> List[str]:
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns.str.lower())
        return [f"Missing columns: {missing}"] if missing else []

    def _check_min_bars(self, df: pd.DataFrame) -> List[str]:
        if len(df) < self.MIN_BARS:
            return [f"Need at least {self.MIN_BARS} bars, got {len(df)}"]
        return []

    def _check_no_nulls(self, df: pd.DataFrame) -> List[str]:
        cols = ["open", "high", "low", "close", "volume"]
        null_counts = df[cols].isnull().sum()
        bad = null_counts[null_counts > 0]
        if not bad.empty:
            return [f"Null values in columns: {bad.to_dict()}"]
        return []

    def _check_ohlc_integrity(self, df: pd.DataFrame) -> List[str]:
        errors = []
        if (df["high"] < df["low"]).any():
            errors.append("Found bars where high < low")
        if (df["high"] < df["open"]).any() or (df["high"] < df["close"]).any():
            errors.append("Found bars where high < open or close")
        if (df["low"] > df["open"]).any() or (df["low"] > df["close"]).any():
            errors.append("Found bars where low > open or close")
        return errors

    def _check_volume(self, df: pd.DataFrame) -> List[str]:
        zero_vol = (df["volume"] <= self.MIN_VOLUME).sum()
        if zero_vol > 0:
            return [f"{zero_vol} bars have zero/minimal volume"]
        return []

    def _check_spread(self, df: pd.DataFrame) -> List[str]:
        spread = (df["high"] - df["low"]) / df["close"]
        extreme = (spread > self.MAX_SPREAD_PCT).sum()
        if extreme > 0:
            return [f"{extreme} bars have spread > {self.MAX_SPREAD_PCT*100:.1f}% of close"]
        return []
