"""
algo-miner — entry point

Usage:
    python main.py                   # run on synthetic OHLC data
    python main.py --csv data/my.csv # run on your own CSV file
    python main.py --verbose         # print every trade in real time
    python main.py --save-trades     # export trades to CSV
"""
import argparse
import sys
from pathlib import Path

from simulator.ohlc_data import OHLCData
from simulator.trade_simulator import TradeSimulator


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Algo-Miner trade simulator")
    p.add_argument("--csv",         type=str,   default=None,  help="Path to OHLC CSV file")
    p.add_argument("--bars",        type=int,   default=500,   help="Bars to generate (synthetic mode)")
    p.add_argument("--capital",     type=float, default=10000, help="Initial capital")
    p.add_argument("--risk",        type=float, default=0.10,  help="Position size as fraction of equity")
    p.add_argument("--stop",        type=float, default=0.02,  help="Stop-loss fraction (0 = disabled)")
    p.add_argument("--tp",          type=float, default=0.04,  help="Take-profit fraction (0 = disabled)")
    p.add_argument("--no-short",    action="store_true",       help="Disable short trades")
    p.add_argument("--verbose",     action="store_true",       help="Print each trade as it happens")
    p.add_argument("--save-trades", action="store_true",       help="Save trade list to trades.csv")
    p.add_argument("--seed",        type=int,   default=42,    help="Random seed for synthetic data")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ---- load or generate data ---- #
    if args.csv:
        path = Path(args.csv)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        print(f"Loading OHLC data from {path} …")
        df = OHLCData.from_csv(path)
    else:
        print(f"Generating {args.bars} synthetic OHLC bars (seed={args.seed}) …")
        df = OHLCData.generate(n_bars=args.bars, seed=args.seed)

    print(OHLCData.summary(df))
    print()

    # ---- configure and run simulator ---- #
    sim = TradeSimulator(
        initial_capital   = args.capital,
        position_size_pct = args.risk,
        stop_loss_pct     = args.stop if args.stop > 0 else None,
        take_profit_pct   = args.tp   if args.tp   > 0 else None,
        allow_short       = not args.no_short,
    )

    result = sim.run(df, verbose=args.verbose)

    # ---- output ---- #
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
