# SoHelpMeBagrut — MCP Auto-Installer (Windows PowerShell)
$ErrorActionPreference = "Stop"

# ── Install location ──────────────────────────────────────────────────────────
$defaultDir = Join-Path $HOME "Documents\ClaudeMCPs"
Write-Host ""
Write-Host "Install location"
Write-Host "  Default: $defaultDir"
$answer = Read-Host "Press Enter to use default, or type a custom path"
if ($answer.Trim() -eq "") {
    $dir = $defaultDir
} else {
    $dir = $answer.Trim()
}
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Write-Host "Installing to: $dir"
Write-Host ""

# ── Download server ───────────────────────────────────────────────────────────
Write-Host "Downloading pdf_page_server.py..."
Invoke-WebRequest "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -OutFile "$dir\pdf_page_server.py"

# ── Detect Python ─────────────────────────────────────────────────────────────
Write-Host "Detecting Python..."
$py = $null
foreach ($cmd in @("py", "python", "python3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) { $py = $cmd; break }
}
if (-not $py) {
    Write-Error "Python not found. Install it from https://python.org and re-run."
    exit 1
}
Write-Host "Using: $py"

# ── Install dependencies ──────────────────────────────────────────────────────
Write-Host "Installing Python dependencies..."
& $py -m pip install mcp pymupdf requests

# ── Find Claude Desktop config ────────────────────────────────────────────────
Write-Host "Locating Claude Desktop config..."
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
        $configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
        New-Item -ItemType Directory -Force -Path (Split-Path $configPath) | Out-Null
    }
}

Write-Host "Config: $configPath"

# ── Update config via Python (avoids ConvertTo-Json bugs) ────────────────────
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

# ── Done ──────────────────────────────────────────────────────────────────────
$skillUrl = "https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/csharp/skill_mcp.md?v=1"
Set-Clipboard -Value $skillUrl

Write-Host ""
Write-Host "Done! Restart Claude Desktop to activate."
Write-Host ""
Write-Host "The skill URL has been copied to your clipboard."
Write-Host "Paste it into Claude to start studying:"
Write-Host "  $skillUrl"
Write-Host ""
Write-Host "Python  : $py"
Write-Host "Server  : $dir\pdf_page_server.py"
Write-Host "Config  : $configPath"
