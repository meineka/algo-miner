<#
   aziz_remote_runner.ps1  — git-remote-execution daemon for Claude Code
   =====================================================================

   Polls the GitHub repo every $PollEverySec seconds for new job files in
   collab/jobs/incoming/. Each new *.job.json is executed locally on this
   Windows machine. Results (logs, reports, screenshots, zips) are placed
   in collab/jobs/results/ and pushed back to GitHub for Claude to read.

   SUPPORTED JOB KINDS
   -------------------
     mt5_backtest   Run MT5 Strategy Tester on a given EA + symbol +
                    date range, capture the HTML report.
     pytest         Run the algo-miner Python test suite.
     python_run     Run a one-shot Python script from the repo.
     shell          Run an arbitrary PowerShell command. ONLY enabled
                    when -AllowShell is passed on the command line.
                    Use with care.

   PERMISSION MODEL
   ----------------
   The user explicitly granted Claude execution permission on this
   machine. The daemon enforces the following gates:
     - Jobs are read only from <repo>/collab/jobs/incoming/.
     - Each job file is moved to .../processed/ after execution to
       prevent re-runs.
     - Shell jobs require the -AllowShell flag.
     - All outputs go to <repo>/collab/jobs/results/ and are pushed
       to the same branch.

   USAGE
   -----
     pwsh -ExecutionPolicy Bypass -File .\scripts\aziz_remote_runner.ps1 `
          -RepoPath C:\dev\algo-miner -MT5Path "C:\Program Files\MetaTrader 5" `
          [-AllowShell] [-PollSec 30] [-AutoCommit]

   STOP
   ----
     Ctrl+C in the running PowerShell.
#>

param(
    [string]$RepoPath    = "C:\dev\algo-miner",
    [string]$MT5Path     = "C:\Program Files\MetaTrader 5",
    [int]   $PollSec     = 30,
    [switch]$AllowShell  = $false,
    [switch]$AutoCommit  = $true,
    [string]$Branch      = "claude/review-ross-cameron-project-pb2ni"
)

$ErrorActionPreference = "Continue"
$RepoPath = (Resolve-Path $RepoPath).Path

if(-not (Test-Path $RepoPath)) { Write-Error "Repo not found: $RepoPath"; exit 1 }
Set-Location $RepoPath

$JobsRoot   = Join-Path $RepoPath "collab\jobs"
$Incoming   = Join-Path $JobsRoot  "incoming"
$Processed  = Join-Path $JobsRoot  "processed"
$Results    = Join-Path $JobsRoot  "results"
foreach($p in @($Incoming, $Processed, $Results)) {
    if(-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

$TerminalExe = Join-Path $MT5Path "terminal64.exe"
$MetaEditor  = Join-Path $MT5Path "metaeditor64.exe"

Write-Host "════════════════════════════════════════════════════════════════════"
Write-Host " aziz_remote_runner — Claude → Windows remote execution daemon"
Write-Host "════════════════════════════════════════════════════════════════════"
Write-Host "  Repo       : $RepoPath"
Write-Host "  Branch     : $Branch"
Write-Host "  MT5 path   : $MT5Path"
Write-Host "  Poll every : $PollSec s"
Write-Host "  AllowShell : $AllowShell"
Write-Host "  AutoCommit : $AutoCommit"
Write-Host "  Ctrl+C to stop"
Write-Host "════════════════════════════════════════════════════════════════════"

function Sync-FromRemote {
    git -C $RepoPath checkout $Branch 2>$null | Out-Null
    git -C $RepoPath pull --ff-only origin $Branch 2>&1 | Out-Null
}

function Push-Results([string]$msg) {
    if(-not $AutoCommit) { return }
    git -C $RepoPath add "collab/jobs/results" "collab/jobs/processed" 2>&1 | Out-Null
    git -C $RepoPath commit -m $msg 2>&1 | Out-Null
    git -C $RepoPath push origin $Branch 2>&1 | Out-Null
}

function Run-MT5Backtest($job, $resultsDir) {
    $p = $job.params

    if(-not (Test-Path $TerminalExe)) {
        return @{ ok=$false; error="MT5 terminal64.exe not found at $TerminalExe" }
    }

    # 1) Compile the EA via MetaEditor (in case the .mq5 changed)
    $eaPath  = Join-Path $RepoPath "mt5\$($p.expert).mq5"
    if(-not (Test-Path $eaPath)) {
        return @{ ok=$false; error="Expert source not found at $eaPath" }
    }
    if(Test-Path $MetaEditor) {
        $compileLog = Join-Path $resultsDir "compile.log"
        & $MetaEditor "/compile:$eaPath" "/log:$compileLog" 2>&1 | Out-Null
    }

    # 2) Build the tester.ini
    $reportName = "aziz_backtest_$($job.id)"
    $iniPath = Join-Path $resultsDir "tester.ini"
    @"
[Tester]
Expert=$($p.expert).ex5
Symbol=$($p.symbol)
Period=$($p.period)
Login=
Model=$($p.model)
ExecutionMode=0
Optimization=0
OptimizationCriterion=0
FromDate=$($p.from)
ToDate=$($p.to)
ForwardMode=0
ForwardDate=
Report=$reportName
ReplaceReport=1
ShutdownTerminal=1
Deposit=$($p.deposit)
Currency=USD
ProfitInPips=0
Leverage=$($p.leverage)
UseLocal=1
Visual=0
"@ | Out-File -FilePath $iniPath -Encoding ASCII

    # 3) Launch MT5 in tester mode and wait for it to shut itself down
    Write-Host "  [mt5] running Strategy Tester on $($p.symbol) $($p.from) → $($p.to) model=$($p.model)"
    $proc = Start-Process -FilePath $TerminalExe -ArgumentList "/config:$iniPath","/portable" -PassThru
    $proc | Wait-Process

    # 4) Capture report
    $reportSrc = Join-Path $MT5Path "Reports\$reportName.htm"
    $reportDst = Join-Path $resultsDir "$reportName.htm"
    if(Test-Path $reportSrc) {
        Copy-Item $reportSrc $reportDst
        return @{ ok=$true; report=$reportDst }
    }
    # MT5 sometimes saves to MQL5/Files instead
    $reportAlt = Join-Path $MT5Path "MQL5\Files\$reportName.htm"
    if(Test-Path $reportAlt) {
        Copy-Item $reportAlt $reportDst
        return @{ ok=$true; report=$reportDst }
    }
    return @{ ok=$false; error="MT5 report not found in Reports/ or MQL5/Files/" }
}

function Run-Pytest($job, $resultsDir) {
    $log = Join-Path $resultsDir "pytest.log"
    $cmd = if($job.params.expression) { "pytest tests/ $($job.params.expression)" } else { "pytest tests/ -v" }
    & cmd /c "$cmd > `"$log`" 2>&1"
    return @{ ok=$true; log=$log }
}

function Run-Python($job, $resultsDir) {
    $script = Join-Path $RepoPath $job.params.script
    if(-not (Test-Path $script)) { return @{ ok=$false; error="script not found: $script" } }
    $log = Join-Path $resultsDir "python.log"
    & python $script > $log 2>&1
    return @{ ok=$true; log=$log }
}

function Run-Shell($job, $resultsDir) {
    if(-not $AllowShell) { return @{ ok=$false; error="shell jobs disabled — pass -AllowShell to enable" } }
    $log = Join-Path $resultsDir "shell.log"
    Invoke-Expression $job.params.command *> $log
    return @{ ok=$true; log=$log }
}

function Process-Job($jobPath) {
    $jobName = [System.IO.Path]::GetFileNameWithoutExtension($jobPath)
    $resultsDir = Join-Path $Results $jobName
    if(-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir | Out-Null }

    $started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mmZ")
    Write-Host "[$started] processing job: $jobName"

    $job = Get-Content $jobPath -Raw | ConvertFrom-Json

    $outcome = switch ($job.kind) {
        "mt5_backtest" { Run-MT5Backtest $job $resultsDir }
        "pytest"       { Run-Pytest      $job $resultsDir }
        "python_run"   { Run-Python      $job $resultsDir }
        "shell"        { Run-Shell       $job $resultsDir }
        default        { @{ ok=$false; error="unknown job kind: $($job.kind)" } }
    }

    $finished = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mmZ")
    $resultJson = @{
        job_id   = $job.id
        kind     = $job.kind
        started  = $started
        finished = $finished
        ok       = $outcome.ok
        result   = $outcome
    } | ConvertTo-Json -Depth 6

    $resultPath = Join-Path $resultsDir "result.json"
    $resultJson | Out-File -FilePath $resultPath -Encoding utf8

    # Move job to processed/
    Move-Item $jobPath (Join-Path $Processed (Split-Path $jobPath -Leaf)) -Force

    Write-Host ("  → " + ($(if($outcome.ok){"OK"}else{"FAIL: "+$outcome.error})))

    Push-Results -msg "remote-runner: job $jobName done ($finished)"
}

# Main loop
while ($true) {
    Sync-FromRemote
    $pending = Get-ChildItem -Path $Incoming -Filter "*.job.json" -File -ErrorAction SilentlyContinue |
               Sort-Object Name
    foreach($f in $pending) {
        try   { Process-Job $f.FullName }
        catch { Write-Warning "job $($f.Name) crashed: $_" }
    }
    Start-Sleep -Seconds $PollSec
}
