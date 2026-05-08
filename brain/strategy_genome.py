"""
StrategyGenome — encodes one complete strategy configuration as a dict of
parameter values.  StrategyMiner generates N variants via random sampling
within validated ranges derived from trading literature and community practice.

Parameter ranges are intentionally conservative:
  - EMA spans come from classical technical analysis (9/21, 12/26, 5/20, etc.)
  - RSI thresholds from Wilder's original work + community adaptations
  - ATR multipliers from volatility-adjusted position sizing literature
  - Profit-factor targets from Van Tharp's position-sizing research
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np


# ══════════════════════════════════════════════════════════════════════
# Parameter space — community-validated ranges
# ══════════════════════════════════════════════════════════════════════

PARAM_SPACE: Dict[str, Any] = {
    # EMA crossover
    "ema_fast":           {"type": "int",   "low": 5,    "high": 15},
    "ema_slow":           {"type": "int",   "low": 15,   "high": 50},

    # RSI mean-reversion thresholds
    "rsi_period":         {"type": "int",   "low": 10,   "high": 21},
    "rsi_oversold":       {"type": "int",   "low": 20,   "high": 40},
    "rsi_overbought":     {"type": "int",   "low": 60,   "high": 80},

    # Donchian breakout window
    "donchian_window":    {"type": "int",   "low": 10,   "high": 40},

    # Volume spike multiplier
    "vol_spike_mult":     {"type": "float", "low": 1.5,  "high": 3.5},

    # Quality gates
    "min_agreement":      {"type": "int",   "low": 2,    "high": 4},
    "atr_stop_mult":      {"type": "float", "low": 1.0,  "high": 3.0},
    "take_profit_mult":   {"type": "float", "low": 1.5,  "high": 4.0},
    "max_risk_pct":       {"type": "float", "low": 0.005,"high": 0.025},
    "max_daily_loss_pct": {"type": "float", "low": 0.015,"high": 0.05},
    "cooldown_bars":      {"type": "int",   "low": 1,    "high": 5},
}

# Hand-seeded "community classics" — always included in the pool
COMMUNITY_SEEDS: List[Dict[str, Any]] = [
    # Classic EMA 9/21 + standard RSI
    dict(ema_fast=9,  ema_slow=21, rsi_period=14, rsi_oversold=30, rsi_overbought=70,
         donchian_window=20, vol_spike_mult=2.0, min_agreement=3,
         atr_stop_mult=2.0, take_profit_mult=2.0, max_risk_pct=0.01,
         max_daily_loss_pct=0.03, cooldown_bars=2),
    # MACD-inspired EMA 12/26
    dict(ema_fast=12, ema_slow=26, rsi_period=14, rsi_oversold=30, rsi_overbought=70,
         donchian_window=20, vol_spike_mult=2.0, min_agreement=2,
         atr_stop_mult=1.5, take_profit_mult=2.5, max_risk_pct=0.015,
         max_daily_loss_pct=0.025, cooldown_bars=2),
    # Conservative slow EMA + wide Donchian
    dict(ema_fast=10, ema_slow=40, rsi_period=21, rsi_oversold=25, rsi_overbought=75,
         donchian_window=30, vol_spike_mult=2.5, min_agreement=3,
         atr_stop_mult=2.5, take_profit_mult=3.0, max_risk_pct=0.01,
         max_daily_loss_pct=0.02, cooldown_bars=3),
    # Aggressive short-term scalp
    dict(ema_fast=5,  ema_slow=15, rsi_period=10, rsi_oversold=35, rsi_overbought=65,
         donchian_window=10, vol_spike_mult=1.5, min_agreement=2,
         atr_stop_mult=1.0, take_profit_mult=1.5, max_risk_pct=0.02,
         max_daily_loss_pct=0.04, cooldown_bars=1),
    # High-conviction, few trades (all 4 rules must agree)
    dict(ema_fast=9,  ema_slow=21, rsi_period=14, rsi_oversold=25, rsi_overbought=75,
         donchian_window=20, vol_spike_mult=3.0, min_agreement=4,
         atr_stop_mult=2.0, take_profit_mult=3.0, max_risk_pct=0.015,
         max_daily_loss_pct=0.03, cooldown_bars=3),
]


# ══════════════════════════════════════════════════════════════════════
# StrategyGenome
# ══════════════════════════════════════════════════════════════════════

@dataclass
class StrategyGenome:
    """One complete strategy configuration."""
    ema_fast:           int
    ema_slow:           int
    rsi_period:         int
    rsi_oversold:       int
    rsi_overbought:     int
    donchian_window:    int
    vol_spike_mult:     float
    min_agreement:      int
    atr_stop_mult:      float
    take_profit_mult:   float
    max_risk_pct:       float
    max_daily_loss_pct: float
    cooldown_bars:      int
    name:               str = ""
    source:             str = "random"   # 'community' | 'random' | 'llm'

    def __post_init__(self):
        # Enforce constraint: fast EMA must be < slow EMA
        if self.ema_fast >= self.ema_slow:
            self.ema_slow = self.ema_fast + random.randint(5, 20)
        # RSI: oversold < overbought
        if self.rsi_oversold >= self.rsi_overbought:
            self.rsi_overbought = min(self.rsi_oversold + 20, 80)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"[{self.source}] EMA({self.ema_fast}/{self.ema_slow}) "
            f"RSI({self.rsi_oversold}/{self.rsi_overbought},{self.rsi_period}) "
            f"Don({self.donchian_window}) Vol×{self.vol_spike_mult:.1f} "
            f"Agree={self.min_agreement} SL×{self.atr_stop_mult:.1f} "
            f"TP×{self.take_profit_mult:.1f} Risk={self.max_risk_pct*100:.1f}%"
        )


# ══════════════════════════════════════════════════════════════════════
# StrategyMiner
# ══════════════════════════════════════════════════════════════════════

class StrategyMiner:
    """
    Generates a diverse pool of StrategyGenome instances.

    Pool composition:
      - Community seeds  : known-good configurations from trading literature
      - Random variants  : sampled uniformly within validated parameter ranges
      - LLM variants     : Claude-suggested configurations (optional, requires API key)

    Parameters
    ----------
    n_random    : number of random variants to generate
    seed        : random seed for reproducibility
    llm_client  : optional anthropic.Anthropic client for LLM-assisted mining
    """

    def __init__(
        self,
        n_random:   int  = 50,
        seed:       int  = 42,
        llm_client  = None,
    ):
        self.n_random   = n_random
        self._rng       = random.Random(seed)
        self._np_rng    = np.random.default_rng(seed)
        self._llm       = llm_client

    def generate(self) -> List[StrategyGenome]:
        """Return full pool: community seeds + random variants + optional LLM variants."""
        pool: List[StrategyGenome] = []

        # 1. Community seeds
        for i, params in enumerate(COMMUNITY_SEEDS):
            g = StrategyGenome(**params, name=f"community_{i+1}", source="community")
            pool.append(g)

        # 2. Random variants
        for i in range(self.n_random):
            g = self._random_genome(name=f"random_{i+1}")
            pool.append(g)

        # 3. LLM variants (optional)
        if self._llm is not None:
            llm_genomes = self._llm_generate()
            pool.extend(llm_genomes)

        return pool

    def _random_genome(self, name: str = "") -> StrategyGenome:
        params: Dict[str, Any] = {}
        for key, spec in PARAM_SPACE.items():
            if spec["type"] == "int":
                params[key] = self._rng.randint(spec["low"], spec["high"])
            else:
                params[key] = round(
                    self._rng.uniform(spec["low"], spec["high"]), 3
                )
        return StrategyGenome(**params, name=name, source="random")

    def _llm_generate(self, n: int = 5) -> List[StrategyGenome]:
        """Ask Claude to suggest n strategy configurations based on trading knowledge."""
        try:
            import json
            prompt = f"""You are an expert algorithmic trader. Suggest {n} diverse trading strategy
parameter configurations. Each must be a JSON object with exactly these keys and value ranges:
  ema_fast (int 5-15), ema_slow (int 15-50), rsi_period (int 10-21),
  rsi_oversold (int 20-40), rsi_overbought (int 60-80),
  donchian_window (int 10-40), vol_spike_mult (float 1.5-3.5),
  min_agreement (int 2-4), atr_stop_mult (float 1.0-3.0),
  take_profit_mult (float 1.5-4.0), max_risk_pct (float 0.005-0.025),
  max_daily_loss_pct (float 0.015-0.05), cooldown_bars (int 1-5)

Make them diverse: some conservative, some aggressive, some trend-following, some mean-reversion focused.
Ensure ema_fast < ema_slow and rsi_oversold < rsi_overbought.
Return ONLY a JSON array of {n} objects, no explanation."""

            response = self._llm.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Extract JSON array even if wrapped in markdown
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json").strip()
            configs = json.loads(raw)
            genomes = []
            for i, cfg in enumerate(configs[:n]):
                try:
                    g = StrategyGenome(**cfg, name=f"llm_{i+1}", source="llm")
                    genomes.append(g)
                except Exception:
                    pass
            return genomes
        except Exception:
            return []
