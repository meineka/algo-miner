"""
Brain LLM Validator — Layer 7: AI-powered signal gate ("GPT time").

Runs AFTER all 6 deterministic quality layers pass.
Sends full trading context to Claude and requires an APPROVE with
confidence >= min_confidence before the trade is executed.

Fail-safe: any error (timeout, parse failure, API down) → REJECT.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

try:
    import anthropic as _anthropic_module
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

from .rules import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD
from .quality_checks import RegimeState


# ══════════════════════════════════════════════════════════════════════
# Result
# ══════════════════════════════════════════════════════════════════════

@dataclass
class LLMValidation:
    approved:    bool
    confidence:  int           # 0–100
    reasoning:   str
    flags:       List[str]     = field(default_factory=list)
    model:       str           = ""
    raw:         str           = ""

    def __str__(self) -> str:
        status = "✓ LLM APPROVED" if self.approved else "✗ LLM REJECTED"
        flag_lines = "\n".join(f"    [!] {f}" for f in self.flags)
        base = f"  {status} (confidence={self.confidence}%)  {self.reasoning}"
        return f"{base}\n{flag_lines}" if flag_lines else base


# ══════════════════════════════════════════════════════════════════════
# Validator
# ══════════════════════════════════════════════════════════════════════

class LLMValidator:
    """
    Uses Claude Haiku (fast + cheap) to act as a final, strict risk manager.

    Parameters
    ----------
    model          : Claude model ID
    api_key        : Anthropic key — falls back to ANTHROPIC_API_KEY env var
    min_confidence : LLM must be at least this confident to approve (0–100)
    """

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        model:          str           = DEFAULT_MODEL,
        api_key:        Optional[str] = None,
        min_confidence: int           = 75,
    ):
        if not _AVAILABLE:
            raise ImportError("Run: pip install anthropic")

        self.model          = model
        self.min_confidence = min_confidence
        self._client        = _anthropic_module.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def validate(
        self,
        signal:             int,
        rule_votes:         pd.Series,
        entry_price:        float,
        stop_price:         float,
        tp_price:           float,
        size:               float,
        equity:             float,
        initial_capital:    float,
        daily_pnl:          float,
        equity_curve:       List[float],
        closed_trades:      list,
        consecutive_losses: int,
        regime:             Optional[RegimeState],
    ) -> LLMValidation:

        prompt = self._build_prompt(
            signal, rule_votes, entry_price, stop_price, tp_price,
            size, equity, initial_capital, daily_pnl,
            equity_curve, closed_trades, consecutive_losses, regime,
        )

        try:
            resp = self._client.messages.create(
                model      = self.model,
                max_tokens = 512,
                system     = (
                    "You are a strict quantitative trading risk manager. "
                    "Your default is REJECT — only approve when all criteria are "
                    "clearly met. Respond ONLY with valid JSON, no markdown, no text."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            return self._parse(raw)

        except Exception as exc:
            return LLMValidation(
                approved   = False,
                confidence = 0,
                reasoning  = f"API error — fail-safe REJECT ({type(exc).__name__}: {exc})",
                model      = self.model,
            )

    # ------------------------------------------------------------------ #
    # Prompt building                                                      #
    # ------------------------------------------------------------------ #

    def _build_prompt(
        self, signal, rule_votes, entry_price, stop_price, tp_price,
        size, equity, initial_capital, daily_pnl,
        equity_curve, closed_trades, consecutive_losses, regime,
    ) -> str:

        direction  = "LONG" if signal == SIGNAL_BUY else "SHORT"
        stop_dist  = abs(entry_price - stop_price)
        tp_dist    = abs(tp_price - entry_price)
        rr         = tp_dist / stop_dist if stop_dist > 0 else 0

        # Regime block
        if regime:
            regime_txt = (
                f"Trend={regime.trend}  ADX={regime.adx:.1f}  "
                f"DI+={regime.di_plus:.1f}  DI-={regime.di_minus:.1f}  "
                f"Volatility={regime.volatility}  ATR-ratio={regime.atr_ratio:.2f}"
            )
        else:
            regime_txt = "Not available (insufficient history)"

        # Rule votes block
        _name = {SIGNAL_BUY: "BUY", SIGNAL_SELL: "SELL", SIGNAL_HOLD: "HOLD"}
        vote_lines = "\n".join(
            f"  {'agree' if v == signal else 'disagree':8s}  {k}: {_name.get(int(v), str(v))}"
            for k, v in rule_votes.items()
        )
        n_agree = int((rule_votes == signal).sum())

        # Performance block
        ct   = [t for t in closed_trades if t.pnl is not None]
        n_ct = len(ct)
        if n_ct > 0:
            pnls      = [t.pnl for t in ct]
            wins      = sum(1 for p in pnls if p > 0)
            gw        = sum(p for p in pnls if p > 0)
            gl        = abs(sum(p for p in pnls if p < 0))
            pf        = gw / gl if gl > 0 else float("inf")
            wr        = wins / n_ct * 100
            recent10  = ", ".join(f"{t.pnl:+.1f}" for t in ct[-10:])
            perf_txt  = (
                f"Closed trades={n_ct}  Win rate={wr:.1f}%  PF={pf:.2f}  "
                f"Consecutive losses={consecutive_losses}\n"
                f"Last 10 PnLs: [{recent10}]"
            )
        else:
            perf_txt = "No closed trades yet."

        # Account block
        peak = max(equity_curve) if equity_curve else equity
        dd   = (peak - equity) / peak * 100 if peak > 0 else 0.0
        ret  = (equity - initial_capital) / initial_capital * 100

        return f"""Evaluate this {direction} signal. Default is REJECT unless all criteria are met.

SIGNAL
  Direction   : {direction}
  Entry price : {entry_price:.4f}
  Stop-loss   : {stop_price:.4f}  ({stop_dist/entry_price*100:.2f}% away)
  Take-profit : {tp_price:.4f}  ({tp_dist/entry_price*100:.2f}% away)
  R:R ratio   : {rr:.2f}
  Size        : {size:.6f} units

REGIME
  {regime_txt}

RULE VOTES  ({n_agree}/{len(rule_votes)} agree with {direction})
{vote_lines}

ACCOUNT
  Equity      : {equity:,.2f}  (return={ret:+.2f}%  drawdown={dd:.2f}%)
  Daily PnL   : {daily_pnl:+.2f}

PERFORMANCE
  {perf_txt}

APPROVAL CRITERIA  (ALL must be satisfied):
  1. R:R >= 1.5
  2. Regime does NOT strongly contradict the signal direction
  3. At least 3 rules agree with the signal direction
  4. Drawdown < 10%
  5. If >= 20 closed trades: Profit Factor > 1.0 and win rate > 35%
  6. No alarming pattern in last 10 PnLs (e.g. 5+ consecutive losses)

Return ONLY this JSON (no code block, no extra text):
{{"decision":"APPROVE or REJECT","confidence":0-100,"reasoning":"one sentence","flags":["concern1","concern2"]}}"""

    # ------------------------------------------------------------------ #
    # Parse                                                                #
    # ------------------------------------------------------------------ #

    def _parse(self, raw: str) -> LLMValidation:
        try:
            txt = raw.strip()
            # strip accidental markdown fences
            if txt.startswith("```"):
                parts = txt.split("```")
                txt = parts[1].lstrip("json").strip() if len(parts) > 1 else txt
            data       = json.loads(txt)
            decision   = str(data.get("decision", "REJECT")).upper().strip()
            confidence = max(0, min(100, int(data.get("confidence", 0))))
            reasoning  = str(data.get("reasoning", ""))
            flags      = [str(f) for f in data.get("flags", [])]
            approved   = (decision == "APPROVE") and (confidence >= self.min_confidence)
            return LLMValidation(
                approved=approved, confidence=confidence,
                reasoning=reasoning, flags=flags,
                model=self.model, raw=raw,
            )
        except Exception as exc:
            return LLMValidation(
                approved=False, confidence=0,
                reasoning=f"Parse error — fail-safe REJECT ({exc})",
                raw=raw, model=self.model,
            )
