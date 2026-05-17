# Jobs folder — Claude → Windows remote execution

This is the channel through which Claude (Code, in a Linux sandbox)
asks your Windows PC to do work — primarily MT5 strategy-tester runs
that need the Windows MetaTrader 5 installation.

## Topology

```
   Claude Code (sandbox)             Your Windows PC
   ────────────────────              ───────────────
   commits *.job.json                aziz_remote_runner.ps1
        │                             ↑   (polls every 30 s)
        ▼                             │
   GitHub origin   ────── git pull ──┘
        ▲
        │  git push results back
        │
   Claude reads at next heartbeat
```

## Folder layout

```
collab/jobs/
├── incoming/          jobs Claude wants executed; pick up + remove
├── processed/         jobs already executed (audit trail)
└── results/<job_id>/  output files: result.json + logs + reports
```

## Job file format — `*.job.json`

```json
{
  "id": "2026-05-14T20-30Z_mt5_first_backtest",
  "kind": "mt5_backtest",
  "params": {
    "expert": "Aziz_NQ",
    "symbol": "NQ",
    "period": "M1",
    "from":   "2024.04.01",
    "to":     "2026.05.14",
    "model":  4,
    "deposit": 10000,
    "leverage": "1:100"
  }
}
```

`id` is free-form but should start with a UTC timestamp so files sort
chronologically. `kind` is one of:

| Kind             | Params                                       | What happens |
|------------------|----------------------------------------------|--------------|
| `mt5_backtest`   | expert, symbol, period, from, to, model, deposit, leverage | Compile EA, run Strategy Tester with the given tester.ini, save HTML report |
| `pytest`         | (optional) expression                        | Run `pytest tests/` in the repo, capture log |
| `python_run`     | script (path inside repo)                    | Run a single Python script, capture stdout/stderr |
| `shell`          | command                                      | Run an arbitrary PowerShell command (REQUIRES `-AllowShell`) |

`model` for `mt5_backtest`:
- 0 = Every tick (slow)
- 1 = 1-minute OHLC
- 2 = Open prices only
- 3 = Math calculations
- **4 = Every tick based on real ticks** ← this is what we use

## Daemon — `scripts/aziz_remote_runner.ps1`

Start once on your Windows PC:

```powershell
cd C:\dev\algo-miner
git checkout claude/review-ross-cameron-project-pb2ni
pwsh -ExecutionPolicy Bypass `
     -File .\scripts\aziz_remote_runner.ps1 `
     -RepoPath C:\dev\algo-miner `
     -MT5Path  "C:\Program Files\MetaTrader 5"
```

Leave the window open. The daemon:

1. Pulls every 30 s
2. Picks up new `incoming/*.job.json` files
3. Executes them locally
4. Writes `results/<job_id>/result.json` + logs + report
5. Moves the job to `processed/`
6. Commits + pushes

Stop with `Ctrl+C`.

## Result file format — `results/<job_id>/result.json`

```json
{
  "job_id":   "2026-05-14T20-30Z_mt5_first_backtest",
  "kind":     "mt5_backtest",
  "started":  "2026-05-14T20-32Z",
  "finished": "2026-05-14T20-39Z",
  "ok":       true,
  "result": {
    "ok":     true,
    "report": "C:\\dev\\algo-miner\\collab\\jobs\\results\\…\\aziz_backtest_….htm"
  }
}
```

Alongside `result.json` the daemon places the MT5 HTML report, the
tester.ini that was used, compile.log (if MetaEditor ran), and any
attached output files.

## Permission model — what Claude can do on your PC

After you start the daemon, the daemon executes anything Claude pushes
to `collab/jobs/incoming/`. That's effectively remote execution within
the **whitelist of job kinds** above.

To allow arbitrary shell commands too, add `-AllowShell` to the daemon
command line. Without that flag, shell jobs are rejected.

To revoke at any time: stop the daemon with `Ctrl+C`. The next time
Claude pushes a job it just sits in the `incoming/` folder until you
restart the daemon (or you delete the file).
