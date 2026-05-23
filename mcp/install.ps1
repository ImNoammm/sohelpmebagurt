# SoHelpMeBagrut — MCP Auto-Installer (Windows PowerShell)
$ErrorActionPreference = "Stop"

function Write-Step  { param($n,$text) Write-Host "  [$n] " -NoNewline -ForegroundColor DarkGray; Write-Host $text -ForegroundColor Cyan }
function Write-OK    { param($text)    Write-Host "   OK  " -NoNewline -ForegroundColor Green;    Write-Host $text -ForegroundColor Gray }
function Write-Info  { param($text)    Write-Host "  --> " -NoNewline -ForegroundColor DarkGray;  Write-Host $text -ForegroundColor Gray }
function Write-Warn  { param($text)    Write-Host "  [!] " -NoNewline -ForegroundColor Yellow;    Write-Host $text -ForegroundColor Yellow }
function Write-Fail  { param($text)    Write-Host "  [x] " -NoNewline -ForegroundColor Red;       Write-Host $text -ForegroundColor Red }
function Write-Rule  {                 Write-Host ("  " + ("─" * 50)) -ForegroundColor DarkGray }

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor DarkGreen
Write-Host "  ║       SoHelpMeBagrut — MCP Installer            ║" -ForegroundColor Green
Write-Host "  ║       תמיכה בתמונות ל-Claude Desktop            ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor DarkGreen
Write-Host ""

# ── [1] Install location ──────────────────────────────────────────────────────
Write-Step 1 "Install location"
$defaultDir = Join-Path $HOME "Documents\ClaudeMCPs"
Write-Info "Default: $defaultDir"
Write-Host "  --> " -NoNewline -ForegroundColor DarkGray
Write-Host "Press " -NoNewline -ForegroundColor Gray
Write-Host "Enter" -NoNewline -ForegroundColor Cyan
Write-Host " to use default, or type a custom path: " -NoNewline -ForegroundColor Gray
$answer = Read-Host
if ($answer.Trim() -eq "") { $dir = $defaultDir } else { $dir = $answer.Trim() }
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Write-OK "Installing to: $dir"
Write-Host ""

# ── [2] Download server ───────────────────────────────────────────────────────
Write-Step 2 "Downloading pdf_page_server.py"
try {
    Invoke-WebRequest "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -OutFile "$dir\pdf_page_server.py"
    Write-OK "Saved to $dir\pdf_page_server.py"
} catch {
    Write-Fail "Download failed: $_"
    exit 1
}
Write-Host ""

# ── [3] Detect Python ─────────────────────────────────────────────────────────
Write-Step 3 "Detecting Python"
$py = $null
foreach ($cmd in @("py", "python", "python3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) { $py = $cmd; break }
}
if (-not $py) {
    Write-Fail "Python not found. Install it from https://python.org and re-run."
    exit 1
}
$pyVer = (& $py --version 2>&1)
Write-OK "Found: $py  ($pyVer)"
Write-Host ""

# ── [4] Install dependencies ──────────────────────────────────────────────────
Write-Step 4 "Installing Python packages"
Write-Info "mcp  pymupdf  requests"
Write-Host ""
& $py -m pip install mcp pymupdf requests --quiet
Write-Host ""
Write-OK "Packages installed"
Write-Host ""

# ── [5] Find Claude Desktop config ───────────────────────────────────────────
Write-Step 5 "Locating Claude Desktop config"
$candidates = @(
    "$env:APPDATA\Claude\claude_desktop_config.json",
    "$env:LOCALAPPDATA\Claude\claude_desktop_config.json",
    "$env:APPDATA\Anthropic\Claude\claude_desktop_config.json",
    "$env:LOCALAPPDATA\Anthropic\Claude\claude_desktop_config.json"
)
$configPath = $null
foreach ($c in $candidates) {
    if (Test-Path $c) { $configPath = $c; break }
}
if (-not $configPath) {
    $found = Get-ChildItem -Path $env:APPDATA -Filter "claude_desktop_config.json" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $found) {
        $found = Get-ChildItem -Path $env:LOCALAPPDATA -Filter "claude_desktop_config.json" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if ($found) {
        $configPath = $found.FullName
    } else {
        Write-Warn "Config not found — will create it at default location"
        $configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
        New-Item -ItemType Directory -Force -Path (Split-Path $configPath) | Out-Null
    }
}
Write-OK "Config: $configPath"
Write-Host ""

# ── [6] Update config ─────────────────────────────────────────────────────────
Write-Step 6 "Writing MCP server entry to config"
$pyScript = @"
import json, sys
config_path, server_path, py_cmd = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
except Exception:
    config = {}
config.setdefault('mcpServers', {})['sohelpmebagurt-pdf-viewer'] = {
    'command': py_cmd,
    'args': [server_path]
}
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
"@
& $py -c $pyScript $configPath "$dir\pdf_page_server.py" $py
Write-OK "Config updated"
Write-Host ""

# ── Done ──────────────────────────────────────────────────────────────────────
$skillUrl = "https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/csharp/skill_mcp.md?v=1"
Set-Clipboard -Value $skillUrl

Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor DarkGreen
Write-Host "  ║               הכל מוכן!                         ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor DarkGreen
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "   1. " -NoNewline -ForegroundColor DarkGray
Write-Host "Restart Claude Desktop" -ForegroundColor Yellow
Write-Host "   2. " -NoNewline -ForegroundColor DarkGray
Write-Host "Paste the URL below into Claude" -ForegroundColor Cyan
Write-Host ""
Write-Rule
Write-Host "  " -NoNewline
Write-Host $skillUrl -ForegroundColor Green
Write-Rule
Write-Host ""
Write-Host "  (URL copied to clipboard automatically)" -ForegroundColor DarkGray
Write-Host ""
