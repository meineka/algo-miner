<#
   install_claude_desktop_mcp.ps1
   ==============================
   One-shot installer that wires Claude Desktop's filesystem MCP server
   to your Aziz collab folder.

   Run from PowerShell (no admin required):
     pwsh -ExecutionPolicy Bypass -File .\install_claude_desktop_mcp.ps1

   What it does
     1. Checks that Node + npx are available; tries `winget install`
        for Node LTS if not.
     2. Creates the target folder if it doesn't exist.
     3. Patches %APPDATA%\Claude\claude_desktop_config.json to add a
        `filesystem-aziz` MCP server pointed at the target folder.
        Existing mcpServers entries are preserved.
     4. Tells you to restart Claude Desktop.
#>

$TargetFolder = "C:\Users\Szymon\ross-cameron\99_2 Aziz claude chatgpt"
$ConfigPath   = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

Write-Host "== Aziz collab — Claude Desktop MCP installer =="

# 1) Node check
$node = Get-Command node -ErrorAction SilentlyContinue
if(-not $node) {
   Write-Host "[1/4] Node.js not found — attempting winget install ..."
   try { winget install --silent --accept-source-agreements --accept-package-agreements OpenJS.NodeJS.LTS }
   catch { Write-Error "winget install failed. Please install Node.js LTS manually from https://nodejs.org/"; exit 1 }
   # refresh PATH for this shell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
               [System.Environment]::GetEnvironmentVariable("Path","User")
   if(-not (Get-Command node -ErrorAction SilentlyContinue)) {
      Write-Error "Node still not on PATH. Restart PowerShell after install and re-run."; exit 1
   }
}
Write-Host "[1/4] Node OK ($(node --version))"

# 2) Target folder
if(-not (Test-Path $TargetFolder)) {
   New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
   Write-Host "[2/4] Created $TargetFolder"
} else {
   Write-Host "[2/4] $TargetFolder already exists"
}

# 3) Patch claude_desktop_config.json
$claudeDir = Split-Path $ConfigPath -Parent
if(-not (Test-Path $claudeDir)) {
   Write-Error "Claude Desktop config dir not found at $claudeDir — install Claude Desktop first from https://claude.ai/download"; exit 1
}

$config = @{}
if(Test-Path $ConfigPath) {
   try {
      $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json -AsHashtable
   } catch {
      Write-Warning "Existing config is not valid JSON — backing up and rewriting"
      Copy-Item $ConfigPath ($ConfigPath + ".bak.$(Get-Date -Format 'yyyyMMddHHmmss')")
      $config = @{}
   }
}
if(-not $config.ContainsKey("mcpServers")) { $config["mcpServers"] = @{} }
$config["mcpServers"]["filesystem-aziz"] = @{
   command = "npx"
   args    = @("-y", "@modelcontextprotocol/server-filesystem", $TargetFolder)
}

$json = ($config | ConvertTo-Json -Depth 10)
$json | Out-File -FilePath $ConfigPath -Encoding utf8
Write-Host "[3/4] Patched $ConfigPath"
Write-Host "      Added MCP server 'filesystem-aziz' → $TargetFolder"

# 4) Restart hint
Write-Host "[4/4] Done. Now:"
Write-Host "      a) Right-click the Claude Desktop tray icon → Quit"
Write-Host "      b) Re-launch Claude Desktop"
Write-Host "      c) In a new chat, ask: 'List the files you can see in your filesystem.'"
Write-Host "      Expected: Claude lists the contents of $TargetFolder (initially empty)."
