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
from brain.config import PRESETS, MEDIUM, QualityConfig
from brain.health_rules import HealthRules
from brain.strategy_genome import StrategyMiner
from brain.tournament import Tournament


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Algo-Miner trade simulator")

    # data
    p.add_argument("--csv",    type=str, default=None, help="Path to OHLC CSV file")
    p.add_argument("--bars",   type=int, default=500,  help="Bars to generate (synthetic)")
    p.add_argument("--seed",   type=int, default=42,   help="Random seed")

    # preset
    p.add_argument("--preset", type=str, default="medium",
                   choices=["strict", "medium", "default", "loose", "aziz"],
                   help="Quality gate preset (strict = no BS, aziz = Bear Bull Traders defaults)")

    # rule set / style
    p.add_argument("--style", type=str, default="classic",
                   choices=["classic", "aziz", "hybrid"],
                   help="Rule set: classic (4 EMA/RSI/Donchian/Vol), "
                        "aziz (6 ORB/VWAP/Flag/ABCD/RtG/MA), or hybrid")

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
    p.add_argument("--save-trades",  action="store_true", help="Save trades.csv")
    p.add_argument("--health",       action="store_true", help="Run system health checks (walk-forward, regime coverage)")
    p.add_argument("--free-params",  type=int, default=0, help="Number of free parameters (for health check)")

    # Tournament / strategy mining
    p.add_argument("--mine",         action="store_true", help="Run walk-forward tournament to find best strategy")
    p.add_argument("--variants",     type=int, default=50, help="Random strategy variants to generate (default 50)")
    p.add_argument("--top-k",        type=int, default=10, help="Top-K IS survivors tested on OOS (default 10)")
    p.add_argument("--is-split",     type=float, default=0.70, help="IS fraction 0-1 (default 0.70)")
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
    cfg: QualityConfig = PRESETS.get(args.preset, MEDIUM)

    # Inject LLM flag if requested (keep rest of preset intact)
    if args.llm and not cfg.llm_enabled:
        from dataclasses import replace
        cfg = replace(cfg, llm_enabled=True)

    preset_label = args.preset.upper()
    llm_label    = " + LLM Layer 7" if cfg.llm_enabled else ""
    rule_total   = 6 if args.style == "aziz" else (10 if args.style == "hybrid" else 4)
    print(f"Quality preset : {preset_label}{llm_label}")
    print(f"  min_agreement={cfg.min_agreement}/{rule_total}  "
          f"max_risk={cfg.max_risk_pct*100:.1f}%  "
          f"max_daily_loss={cfg.max_daily_loss_pct*100:.1f}%  "
          f"min_sharpe={cfg.min_sharpe}  "
          f"min_PF={cfg.min_profit_factor}  "
          f"max_DD={cfg.max_drawdown_pct*100:.0f}%")
    print()

    # If the preset is 'aziz' and the user didn't pick a style explicitly,
    # default style to 'aziz' so the rule set matches the preset's intent.
    style = args.style
    if args.preset == "aziz" and style == "classic":
        style = "aziz"
    print(f"Rule style     : {style.upper()}")

    # ── Simulator ────────────────────────────────────────────────────
    api_key = args.llm_key or os.environ.get("ANTHROPIC_API_KEY")
    sim = TradeSimulator(
        initial_capital  = args.capital,
        allow_short      = not args.no_short,
        take_profit_mult = args.rr,
        config           = cfg,
        llm_api_key      = api_key if cfg.llm_enabled else None,
        style            = style,
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

    if args.health:
        from brain.quality_checks import RegimeFilter
        print("\nRunning System Health checks...")
        regimes = RegimeFilter().detect_all(df)
        health = HealthRules()
        report = health.validate(
            trades        = result.closed_trades,
            df            = df,
            regimes       = regimes,
            n_free_params = args.free_params,
        )
        print(report.summary())

    if args.mine:
        print(f"\nMining strategies: {args.variants} random + community seeds "
              f"(style={style}) ...")
        miner   = StrategyMiner(n_random=args.variants, seed=args.seed, style=style)
        genomes = miner.generate()
        print(f"  Pool size: {len(genomes)} genomes  "
              f"(IS={args.is_split*100:.0f}% / OOS={100-args.is_split*100:.0f}%)")

        tourney = Tournament(
            is_split        = args.is_split,
            top_k           = args.top_k,
            initial_capital = args.capital,
            allow_short     = not args.no_short,
            verbose         = args.verbose,
            style           = style,
        )
        t_result = tourney.run(df, genomes)
        print(t_result.summary())

        if t_result.champion:
            print("\nChampion parameters:")
            print(f"  {t_result.champion.genome}")
            if t_result.challengers:
                print(f"\nChallengers in standby ({len(t_result.challengers)}):")
                for i, c in enumerate(t_result.challengers[:5], 2):
                    print(f"  #{i}  {c.genome}")


if __name__ == "__main__":
    main()
