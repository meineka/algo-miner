"""
algo-miner — entry point

Usage:
    python main.py                         synthetic data, DEFAULT config
    python main.py --preset strict         STRICT config (no garbage)
    python main.py --preset loose          LOOSE  config (research)
    python main.py --csv data/my.csv       your own OHLC CSV
    python main.py --preset strict --llm   strict + Layer 7 LLM validator
    python main.py --verbose               print every trade in real time
    python main.py --save-trades           export trades.csv
"""
import argparse
import os
import sys
from pathlib import Path

from simulator.ohlc_data import OHLCData
from simulator.trade_simulator import TradeSimulator
from brain.config import PRESETS, STRICT, DEFAULT, QualityConfig


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Algo-Miner trade simulator")

    # data
    p.add_argument("--csv",    type=str, default=None, help="Path to OHLC CSV file")
    p.add_argument("--bars",   type=int, default=500,  help="Bars to generate (synthetic)")
    p.add_argument("--seed",   type=int, default=42,   help="Random seed")

    # preset
    p.add_argument("--preset", type=str, default="default",
                   choices=["strict", "default", "loose"],
                   help="Quality gate preset (strict = no BS)")

    # overrides
    p.add_argument("--capital",  type=float, default=10_000, help="Initial capital")
    p.add_argument("--no-short", action="store_true",        help="Disable short trades")
    p.add_argument("--rr",       type=float, default=2.0,    help="Take-profit R:R multiplier")

    # LLM
    p.add_argument("--llm",    action="store_true", help="Enable Layer 7 LLM validation")
    p.add_argument("--llm-key", type=str, default=None,
                   help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")

    # output
    p.add_argument("--verbose",     action="store_true", help="Print each trade")
    p.add_argument("--save-trades", action="store_true", help="Save trades.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Data ─────────────────────────────────────────────────────────
    if args.csv:
        path = Path(args.csv)
        if not path.exists():
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)
        print(f"Loading OHLC data from {path} ...")
        df = OHLCData.from_csv(path)
    else:
        print(f"Generating {args.bars} synthetic OHLC bars (seed={args.seed}) ...")
        df = OHLCData.generate(n_bars=args.bars, seed=args.seed)
    print(OHLCData.summary(df))
    print()

    # ── Config ───────────────────────────────────────────────────────
    cfg: QualityConfig = PRESETS[args.preset]

    # Inject LLM flag if requested (keep rest of preset intact)
    if args.llm and not cfg.llm_enabled:
        from dataclasses import replace
        cfg = replace(cfg, llm_enabled=True)

    preset_label = args.preset.upper()
    llm_label    = " + LLM Layer 7" if cfg.llm_enabled else ""
    print(f"Quality preset : {preset_label}{llm_label}")
    print(f"  min_agreement={cfg.min_agreement}/4  "
          f"max_risk={cfg.max_risk_pct*100:.1f}%  "
          f"max_daily_loss={cfg.max_daily_loss_pct*100:.1f}%  "
          f"min_sharpe={cfg.min_sharpe}  "
          f"min_PF={cfg.min_profit_factor}  "
          f"max_DD={cfg.max_drawdown_pct*100:.0f}%")
    print()

    # ── Simulator ────────────────────────────────────────────────────
    api_key = args.llm_key or os.environ.get("ANTHROPIC_API_KEY")
    sim = TradeSimulator(
        initial_capital  = args.capital,
        allow_short      = not args.no_short,
        take_profit_mult = args.rr,
        config           = cfg,
        llm_api_key      = api_key if cfg.llm_enabled else None,
    )

    result = sim.run(df, verbose=args.verbose)
    print(result.summary())

    trades_df = result.trades_df()
    if not trades_df.empty:
        print(f"\nFirst 10 trades:\n{trades_df.head(10).to_string(index=False)}")

    if args.save_trades and not trades_df.empty:
        out = Path("trades.csv")
        trades_df.to_csv(out, index=False)
        print(f"\nTrades saved to {out}")


if __name__ == "__main__":
    main()
