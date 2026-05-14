# MT5 Strategy-Tester via PowerShell — one-shot recipe

Run the Aziz NQ EA backtest from a single PowerShell command, no GUI.
Works on any Windows machine with MetaTrader 5 installed.

## TL;DR

```powershell
$MT5="C:\Program Files\MetaTrader 5"; $ID="aziz_$(Get-Date -Format yyyy-MM-ddTHH-mmZ)"
@"
[Tester]
Expert=Aziz_NQ.ex5
Symbol=NQ
Period=M1
Model=4
ExecutionMode=0
Optimization=0
FromDate=2024.04.01
ToDate=2026.05.14
ForwardMode=0
Report=$ID
ReplaceReport=1
ShutdownTerminal=1
Deposit=10000
Currency=USD
Leverage=1:100
UseLocal=1
Visual=0
"@ | Set-Content "$MT5\tester.ini"
& "$MT5\terminal64.exe" "/config:$MT5\tester.ini" /portable
```

After exit (~5–25 min depending on date range and PC), the HTML report
lives at `$MT5\Reports\$ID.htm` (or `$MT5\MQL5\Files\$ID.htm`).

## Prerequisites (one-time)

1. **MT5 installed** at `C:\Program Files\MetaTrader 5` (or adjust path)
2. **EA compiled**: open `mt5\Aziz_NQ.mq5` in MetaEditor → `F7` →
   compile. Expected output: `Aziz_NQ.ex5` in `MQL5\Experts\`.
3. **History data**: open MT5 → *View → Symbols → Symbols tab*. Select
   `NQ` (or your broker's alias), right-click → *Specification → Update
   Data*. Pull at least 2024-04-01 through today, M1.
4. **Real ticks** (for Model 4): MT5 → Tools → Options → Charts →
   *Max bars in window/chart* set high (~ unlimited).

## tester.ini reference

| Key | Value | Notes |
|---|---|---|
| `Expert` | `Aziz_NQ.ex5` | the compiled EA, must be in `MQL5\Experts\` |
| `Symbol` | `NQ` | broker symbol; can also be `US100`, `USTEC` etc. |
| `Period` | `M1` | EA is M1-only |
| `Model` | `4` | every-tick based on real ticks |
| `FromDate` | `2024.04.01` | inclusive |
| `ToDate` | `2026.05.14` | inclusive |
| `Deposit` | `10000` | starting equity in `Currency` |
| `Currency` | `USD` | account currency |
| `Leverage` | `1:100` | adjust per your account |
| `Report` | `aziz_<timestamp>` | output filename stem |
| `ShutdownTerminal` | `1` | MT5 closes after the backtest |
| `Visual` | `0` | headless |

## Doing it via the remote-runner daemon

Instead of typing the PowerShell, queue a job and let
`scripts\aziz_remote_runner.ps1` do everything:

1. Start the daemon (once):
   ```powershell
   cd C:\dev\algo-miner
   pwsh -ExecutionPolicy Bypass -File .\scripts\aziz_remote_runner.ps1 `
        -MT5Path "C:\Program Files\MetaTrader 5"
   ```
2. A job already sits in `collab\jobs\incoming\` — the daemon picks it
   up on its next poll cycle.
3. When done, the report is in `collab\jobs\results\<job-id>\` and
   automatically pushed to GitHub for Claude to read.

## Tuning the run time

Real-tick mode 4 on 2 years of NQ M1 takes ~20 minutes on a modern
desktop. To shorten:

- Use Model 1 (1-minute OHLC) instead of 4 — much faster, less realistic
- Shorten date range to 6 months for a quick sanity pass
- Disable Visual mode (already in the recipe above)

## Reading the HTML report

The HTML report has these sections useful for the Aziz rule book:

| Metric | What to look for |
|---|---|
| Total Net Profit | > 0 means strategy is at least nominally profitable |
| Profit Factor | Aziz target ≥ 1.20; >1.50 is good |
| Maximal Drawdown | Should be < 6 % (the EA's DD-kill); breach means risk model failed |
| Sharpe Ratio | Aim ≥ 0.7 (Aziz medium preset) |
| Trades / Won % | Loss % too high (>60 %) → review filters |
| Avg consecutive losses | Should be ≤ 3 (matches the cooldown threshold) |

If the report shows the EA blocked all signals, double-check:
1. Server-time offset (see `mt5/README.md` §"Server time vs. session time")
2. Symbol alias matches your broker's NQ instrument
3. History data actually covers the date range
