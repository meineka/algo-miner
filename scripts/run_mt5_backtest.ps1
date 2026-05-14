<#
   run_mt5_backtest.ps1 — one-shot Aziz NQ backtest

   What it does, in order:
     1. Clones the algo-miner repo if not already present
     2. Pulls the latest claude/review-ross-cameron-project-pb2ni branch
     3. Copies Aziz_NQ.mq5 to MQL5\Experts\
     4. Compiles it with MetaEditor (skips if no MetaEditor found)
     5. Writes a tester.ini with the requested params
     6. Launches MT5 in headless tester mode with /config:tester.ini
     7. Waits for MT5 to shut itself down (ShutdownTerminal=1)
     8. Copies the HTML report into collab/jobs/results/<jobid>/
     9. Commits + pushes the report to GitHub

   Usage (single PowerShell command):
     pwsh -ExecutionPolicy Bypass -File .\scripts\run_mt5_backtest.ps1

   Override defaults via params:
     -MT5Path "D:\Apps\MetaTrader 5"
     -Symbol "US100"
     -From "2025.01.01"  -To "2026.05.14"
     -Model 1                    (faster: 1-min OHLC)
     -SkipPush                   (don't git push results)
#>

param(
    [string]$RepoPath  = "C:\dev\algo-miner",
    [string]$RepoUrl   = "https://github.com/meineka/algo-miner.git",
    [string]$Branch    = "claude/review-ross-cameron-project-pb2ni",
    [string]$MT5Path   = "C:\Program Files\MetaTrader 5",
    [string]$Symbol    = "NQ",
    [string]$Period    = "M1",
    [int]   $Model     = 4,
    [string]$From      = "2024.04.01",
    [string]$To        = "2026.05.14",
    [int]   $Deposit   = 10000,
    [string]$Leverage  = "1:100",
    [switch]$SkipPush  = $false
)

$ErrorActionPreference = "Stop"
$JobId = "$(Get-Date -Format 'yyyy-MM-ddTHH-mmZ' -AsUTC)_mt5_$Symbol"
Write-Host "════════════════════════════════════════════════════════════════"
Write-Host " Aziz NQ — one-shot MT5 backtest"
Write-Host " Job ID: $JobId"
Write-Host "════════════════════════════════════════════════════════════════"

# 1) Repo: clone or pull
if(-not (Test-Path $RepoPath)) {
    Write-Host "[1/8] cloning $RepoUrl → $RepoPath"
    git clone $RepoUrl $RepoPath
} else {
    Write-Host "[1/8] repo exists, pulling latest"
}
Set-Location $RepoPath
git checkout $Branch | Out-Null
git pull --ff-only origin $Branch | Out-Null

# 2) Locate MT5
$TerminalExe = Join-Path $MT5Path "terminal64.exe"
$MetaEditor  = Join-Path $MT5Path "metaeditor64.exe"
if(-not (Test-Path $TerminalExe)) {
    throw "MT5 not found at $MT5Path. Pass -MT5Path or install MetaTrader 5."
}
Write-Host "[2/8] MT5 found at $MT5Path"

# 3) Copy EA into MT5's MQL5\Experts
$EaSrc = Join-Path $RepoPath "mt5\Aziz_NQ.mq5"
if(-not (Test-Path $EaSrc)) { throw "EA source missing: $EaSrc" }
$EaDst = Join-Path $MT5Path "MQL5\Experts\Aziz_NQ.mq5"
Copy-Item $EaSrc $EaDst -Force
Write-Host "[3/8] EA copied → $EaDst"

# 4) Compile via MetaEditor (best-effort)
$ResultsDir = Join-Path $RepoPath "collab\jobs\results\$JobId"
New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
$CompileLog = Join-Path $ResultsDir "compile.log"
if(Test-Path $MetaEditor) {
    Write-Host "[4/8] compiling EA"
    & $MetaEditor "/compile:$EaDst" "/log:$CompileLog" | Out-Null
    if(Test-Path $CompileLog) {
        Get-Content $CompileLog | Select-Object -Last 10 | ForEach-Object { Write-Host "      $_" }
    }
} else {
    Write-Host "[4/8] MetaEditor not found at $MetaEditor — assuming Aziz_NQ.ex5 already compiled"
}

# 5) Write tester.ini
$ReportStem = "report_$JobId"
$IniPath = Join-Path $ResultsDir "tester.ini"
@"
[Tester]
Expert=Aziz_NQ.ex5
Symbol=$Symbol
Period=$Period
Login=
Model=$Model
ExecutionMode=0
Optimization=0
OptimizationCriterion=0
FromDate=$From
ToDate=$To
ForwardMode=0
ForwardDate=
Report=$ReportStem
ReplaceReport=1
ShutdownTerminal=1
Deposit=$Deposit
Currency=USD
ProfitInPips=0
Leverage=$Leverage
UseLocal=1
Visual=0
"@ | Out-File -FilePath $IniPath -Encoding ASCII
Write-Host "[5/8] tester.ini → $IniPath"
Write-Host "      Symbol=$Symbol  Period=$Period  Model=$Model  $From → $To"

# 6) Launch MT5
Write-Host "[6/8] launching MT5 strategy tester (this will take a while)"
$Started = Get-Date
$Proc = Start-Process -FilePath $TerminalExe -ArgumentList "/config:$IniPath","/portable" -PassThru
$Proc | Wait-Process
$Elapsed = (Get-Date) - $Started
Write-Host "      MT5 exited after $($Elapsed.TotalMinutes.ToString('F1')) min"

# 7) Collect report
$ReportCandidates = @(
    (Join-Path $MT5Path "Reports\$ReportStem.htm"),
    (Join-Path $MT5Path "MQL5\Files\$ReportStem.htm"),
    (Join-Path $MT5Path "Tester\$ReportStem.htm")
)
$ReportPath = $null
foreach($p in $ReportCandidates) {
    if(Test-Path $p) { $ReportPath = $p; break }
}
if($ReportPath) {
    Copy-Item $ReportPath (Join-Path $ResultsDir "$ReportStem.htm")
    Write-Host "[7/8] report captured → $ResultsDir\$ReportStem.htm"
} else {
    Write-Warning "[7/8] report NOT found. Checked:`n  $($ReportCandidates -join "`n  ")"
}

# 8) Push results to GitHub
if(-not $SkipPush) {
    Write-Host "[8/8] pushing results to GitHub"
    git add "collab/jobs/results/$JobId" 2>&1 | Out-Null
    git commit -m "mt5: backtest report $JobId" 2>&1 | Out-Null
    git push origin $Branch 2>&1 | Out-Null
    Write-Host "      pushed."
} else {
    Write-Host "[8/8] -SkipPush set, not pushing"
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════"
Write-Host " DONE.  Job: $JobId  Elapsed: $($Elapsed.TotalMinutes.ToString('F1')) min"
Write-Host " Result folder: $ResultsDir"
Write-Host "════════════════════════════════════════════════════════════════"
