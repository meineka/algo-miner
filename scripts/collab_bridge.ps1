<#
   collab_bridge.ps1
   =================
   Bidirectional sync between the GitHub collab/ folder and your local
   Windows folder for the Claude × ChatGPT review loop.

   What it does
     1. Every 30 seconds: `git pull` to fetch new Claude exports.
        Any new files in collab/ are copied to $LocalCollab.
     2. Watches $LocalCollab for new *_chatgpt_answer.* files.
        When one appears it's copied into the repo, committed, pushed.

   Setup (one-time)
     - Clone the repo to a local folder, e.g. C:\dev\algo-miner:
         git clone https://github.com/meineka/algo-miner.git
         cd algo-miner
         git checkout claude/review-ross-cameron-project-pb2ni
     - Configure git credentials so push works headlessly
       (recommended: GitHub CLI `gh auth login` or a credential helper)
     - Edit the two paths below.
     - Run from PowerShell (Admin not required):
         pwsh -ExecutionPolicy Bypass -File .\collab_bridge.ps1

   Stop with Ctrl+C.
#>

# ── EDIT THESE TWO PATHS ──────────────────────────────────────────────
$RepoPath    = "C:\dev\algo-miner"
$LocalCollab = "C:\Users\Szymon\ross-cameron\99_2 Aziz claude chatgpt"
# ──────────────────────────────────────────────────────────────────────

$Branch        = "claude/review-ross-cameron-project-pb2ni"
$PullEverySec  = 30
$CollabSubdir  = "collab"

if(-not (Test-Path $RepoPath))    { Write-Error "Repo path not found: $RepoPath";    exit 1 }
if(-not (Test-Path $LocalCollab)) { New-Item -ItemType Directory -Path $LocalCollab | Out-Null }

Set-Location $RepoPath
git checkout $Branch 2>$null
git pull --ff-only origin $Branch 2>$null

Write-Host "[collab_bridge] watching $LocalCollab and syncing with $RepoPath/$CollabSubdir on branch $Branch"
Write-Host "[collab_bridge] Ctrl+C to stop"

while ($true) {
   # ── 1. Pull from GitHub and mirror NEW Claude exports to local folder ─
   Set-Location $RepoPath
   git pull --ff-only origin $Branch 2>&1 | Out-Null

   $repoCollabPath = Join-Path $RepoPath $CollabSubdir
   if(Test-Path $repoCollabPath) {
      Get-ChildItem -Path $repoCollabPath -Filter "*_claude_export.*" -File | ForEach-Object {
         $dst = Join-Path $LocalCollab $_.Name
         if(-not (Test-Path $dst)) {
            Copy-Item $_.FullName $dst
            Write-Host ("[collab_bridge] {0} ← claude export {1}" -f (Get-Date -Format 'HH:mm:ss'), $_.Name)
         }
      }
   }

   # ── 2. Mirror NEW ChatGPT answers back into the repo + push ──────────
   $newAnswers = Get-ChildItem -Path $LocalCollab -Filter "*_chatgpt_answer*" -File |
                 Where-Object {
                    $dst = Join-Path $repoCollabPath $_.Name
                    -not (Test-Path $dst)
                 }
   if($newAnswers) {
      foreach($f in $newAnswers) {
         $dst = Join-Path $repoCollabPath $f.Name
         Copy-Item $f.FullName $dst
         git add $dst | Out-Null
         Write-Host ("[collab_bridge] {0} → repo  chatgpt answer {1}" -f (Get-Date -Format 'HH:mm:ss'), $f.Name)
      }
      git commit -m ("collab: ChatGPT answers {0:yyyy-MM-ddTHH-mmZ}" -f (Get-Date).ToUniversalTime()) 2>&1 | Out-Null
      git push origin $Branch 2>&1 | Out-Null
      Write-Host "[collab_bridge] pushed."
   }

   Start-Sleep -Seconds $PullEverySec
}
