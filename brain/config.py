"""
Quality Gate Presets.

STRICT  — zero tolerance, institutional grade. Default for live/paper trading.
DEFAULT — balanced, suitable for backtesting and development.
LOOSE   — relaxed, for research and strategy exploration only.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class QualityConfig:
    # Layer 1 — Regime
    block_counter_trend:    bool  = True

    # Layer 2 — Rule Agreement
    min_agreement:          int   = 3      # rules that must agree (out of 4)

    # Layer 3 — Daily Loss Limit
    max_daily_loss_pct:     float = 0.020  # fraction of equity

    # Layer 4 — Portfolio Heat
    max_portfolio_heat_pct: float = 0.060  # fraction of equity

    # Layer 5 — Rolling Health (last N closed trades)
    health_window:          int   = 30
    min_sharpe:             float = 0.5
    min_profit_factor:      float = 1.10

    # Layer 6 — Classic checks
    max_drawdown_pct:       float = 0.100
    max_consecutive_losses: int   = 4
    cooldown_bars:          int   = 2
    min_atr_multiplier:     float = 0.001

    # Position sizing
    max_risk_pct:           float = 0.020  # hard cap per trade
    atr_stop_multiplier:    float = 2.0

    # Layer 7 — LLM Validator
    llm_enabled:            bool  = False
    llm_min_confidence:     int   = 75

    # Session filter — disable during strategy mining / backtesting on historical data
    # (session filter is designed for live intraday trading, not batch backtests)
    disable_session_filter: bool  = False


# ──────────────────────────────────────────────────────────────────────
# STRICT — what we use. No garbage in.
#
# Gate                    Value     Reasoning
# ─────────────────────── ───────── ──────────────────────────────────────
# min_agreement           4 / 4     ALL rules must agree — no split votes
# max_risk_pct            1%        Institutional standard (CFA: ≤ 2%)
# max_daily_loss          1.5%      Hard stop for the day
# max_portfolio_heat      4%        Max total open risk
# min_sharpe (rolling)    1.0       Below 1.0 = not worth the risk
# min_profit_factor       1.3       30% more winning than losing PnL
# max_drawdown            8%        Kill-switch before real damage
# max_consecutive_losses  3         3 in a row = forced pause
# cooldown_bars           3         No churning
# LLM min_confidence      75%       LLM must be clearly confident
# ──────────────────────────────────────────────────────────────────────
STRICT = QualityConfig(
    block_counter_trend    = True,
    min_agreement          = 4,       # ALL 4 rules must agree
    max_daily_loss_pct     = 0.015,   # 1.5%
    max_portfolio_heat_pct = 0.040,   # 4%
    health_window          = 30,
    min_sharpe             = 1.0,     # rolling Sharpe floor
    min_profit_factor      = 1.30,    # rolling PF floor
    max_drawdown_pct       = 0.080,   # 8% kill-switch
    max_consecutive_losses = 3,
    cooldown_bars          = 3,
    min_atr_multiplier     = 0.002,   # stricter dead-market floor
    max_risk_pct           = 0.010,   # 1% hard cap
    atr_stop_multiplier    = 2.0,
    llm_enabled            = False,   # enable explicitly with --llm
    llm_min_confidence     = 75,
)

# ──────────────────────────────────────────────────────────────────────
# DEFAULT — for backtesting and development
# ──────────────────────────────────────────────────────────────────────
DEFAULT = QualityConfig(
    block_counter_trend    = True,
    min_agreement          = 3,
    max_daily_loss_pct     = 0.020,
    max_portfolio_heat_pct = 0.060,
    health_window          = 30,
    min_sharpe             = 0.5,
    min_profit_factor      = 1.10,
    max_drawdown_pct       = 0.100,
    max_consecutive_losses = 4,
    cooldown_bars          = 2,
    min_atr_multiplier     = 0.001,
    max_risk_pct           = 0.020,
    atr_stop_multiplier    = 2.0,
    llm_enabled            = False,
    llm_min_confidence     = 75,
)

# ──────────────────────────────────────────────────────────────────────
# LOOSE — research only, no guardrails
# ──────────────────────────────────────────────────────────────────────
LOOSE = QualityConfig(
    block_counter_trend    = False,
    min_agreement          = 2,
    max_daily_loss_pct     = 0.050,
    max_portfolio_heat_pct = 0.150,
    health_window          = 50,
    min_sharpe             = 0.0,
    min_profit_factor      = 1.00,
    max_drawdown_pct       = 0.200,
    max_consecutive_losses = 10,
    cooldown_bars          = 1,
    min_atr_multiplier     = 0.0,
    max_risk_pct           = 0.050,
    atr_stop_multiplier    = 2.0,
    llm_enabled            = False,
    llm_min_confidence     = 50,
)

# ──────────────────────────────────────────────────────────────────────
# MEDIUM — balanced for live/paper trading. Default preset.
#
# Gate                    Value     Reasoning
# ─────────────────────── ───────── ──────────────────────────────────────
# min_agreement           3 / 4     Solid majority, not unanimous
# max_risk_pct            1.5%      Hurts but does not ruin
# max_daily_loss          2.5%      Realistic intraday limit
# max_portfolio_heat      6%        Standard retail algo threshold
# min_sharpe (rolling)    0.7       Meaningful floor, not paralysing
# min_profit_factor       1.15      Slightly above break-even
# max_drawdown            12%       Painful but survivable
# max_consecutive_losses  4         Gives system room to recover
# cooldown_bars           2         No churning, not crippling
# LLM min_confidence      75%       Clearly convinced, not vague
# ──────────────────────────────────────────────────────────────────────
MEDIUM = QualityConfig(
    block_counter_trend    = True,
    min_agreement          = 3,
    max_daily_loss_pct     = 0.025,   # 2.5%
    max_portfolio_heat_pct = 0.060,   # 6%
    health_window          = 30,
    min_sharpe             = 0.7,
    min_profit_factor      = 1.15,
    max_drawdown_pct       = 0.120,   # 12%
    max_consecutive_losses = 4,
    cooldown_bars          = 2,
    min_atr_multiplier     = 0.001,
    max_risk_pct           = 0.015,   # 1.5%
    atr_stop_multiplier    = 2.0,
    llm_enabled            = False,   # enable explicitly with --llm
    llm_min_confidence     = 75,
)

# ──────────────────────────────────────────────────────────────────────
# AZIZ — Andrew Aziz day-trader profile (Bear Bull Traders rule book)
#
# Gate                    Value     Reasoning (Aziz / BBT)
# ─────────────────────── ───────── ──────────────────────────────────────
# min_agreement           2 / 6     Confluence — 2 strategies need to align
# max_risk_pct            1.0%      Aziz: ≤ 1 % per trade
# max_daily_loss          2.0%      Aziz: hard stop, walk away
# max_consecutive_losses  3         "Three strikes, you're done for the day"
# cooldown_bars           5         No revenge trading
# max_drawdown            6%        BBT classroom kill-switch
# atr_stop_multiplier     1.5       Aziz uses tight intraday stops
# block_counter_trend     True      "Don't fight the morning trend"
# ──────────────────────────────────────────────────────────────────────
AZIZ = QualityConfig(
    block_counter_trend    = True,
    min_agreement          = 2,       # 2 of 6 Aziz strategies must agree
    max_daily_loss_pct     = 0.020,   # 2 %
    max_portfolio_heat_pct = 0.040,   # 4 %
    health_window          = 30,
    min_sharpe             = 0.7,
    min_profit_factor      = 1.20,
    max_drawdown_pct       = 0.060,   # 6 %
    max_consecutive_losses = 3,
    cooldown_bars          = 5,
    min_atr_multiplier     = 0.0005,
    max_risk_pct           = 0.010,   # 1 %
    atr_stop_multiplier    = 1.5,
    llm_enabled            = False,
    llm_min_confidence     = 75,
)

PRESETS = {"strict": STRICT, "medium": MEDIUM, "default": DEFAULT, "loose": LOOSE, "aziz": AZIZ}
