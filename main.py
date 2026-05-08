"""
algo-miner — entry point

Usage:
    python main.py                        run on synthetic OHLC data
    python main.py --csv data/my.csv      run on your own CSV file
    python main.py --verbose              print every trade in real time
    python main.py --save-trades          export trades to CSV
    python main.py --min-agreement 2      relax rule agreement (default 3)
    python main.py --max-risk 0.01        1% max risk per trade (default 2%)
"""
import argparse
import sys
from pathlib import Path

from simulator.ohlc_data import OHLCData
from simulator.trade_simulator import TradeSimulator


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Algo-Miner trade simulator")
    # data
    p.add_argument("--csv",           type=str,   default=None,   help="Path to OHLC CSV")
    p.add_argument("--bars",          type=int,   default=500,    help="Bars (synthetic mode)")
    p.add_argument("--seed",          type=int,   default=42,     help="Random seed")
    # core sim
    p.add_argument("--capital",       type=float, default=10_000, help="Initial capital")
    p.add_argument("--commission",    type=float, default=0.001,  help="Commission fraction")
    p.add_argument("--no-short",      action="store_true",        help="Disable short trades")
    p.add_argument("--sl-atr",        type=float, default=2.0,    help="Stop-loss ATR multiplier")
    p.add_argument("--rr",            type=float, default=2.0,    help="Take-profit R:R ratio")
    # quality checks
    p.add_argument("--max-risk",      type=float, default=0.02,   help="Max risk per trade (fraction)")
    p.add_argument("--min-agreement", type=int,   default=3,      help="Min rules that must agree")
    p.add_argument("--max-daily-loss",type=float, default=0.02,   help="Daily loss limit (fraction)")
    p.add_argument("--max-heat",      type=float, default=0.06,   help="Portfolio heat limit (fraction)")
    p.add_argument("--max-dd",        type=float, default=0.10,   help="Max drawdown kill-switch")
    p.add_argument("--no-regime",     action="store_true",        help="Disable regime filter")
    # output
    p.add_argument("--verbose",       action="store_true",        help="Print each trade")
    p.add_argument("--save-trades",   action="store_true",        help="Save trades to CSV")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Load or generate data
    if args.csv:
        path = Path(args.csv)
        if not path.exists():
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)
        print(f"Loading OHLC data from {path} …")
        df = OHLCData.from_csv(path)
    else:
        print(f"Generating {args.bars} synthetic OHLC bars (seed={args.seed}) …")
        df = OHLCData.generate(n_bars=args.bars, seed=args.seed)

    print(OHLCData.summary(df))
    print()

    sim = TradeSimulator(
        initial_capital        = args.capital,
        commission_pct         = args.commission,
        allow_short            = not args.no_short,
        stop_loss_atr_mult     = args.sl_atr,
        take_profit_mult       = args.rr,
        max_risk_pct           = args.max_risk,
        block_counter_trend    = not args.no_regime,
        min_agreement          = args.min_agreement,
        max_daily_loss_pct     = args.max_daily_loss,
        max_portfolio_heat_pct = args.max_heat,
        max_drawdown_pct       = args.max_dd,
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
