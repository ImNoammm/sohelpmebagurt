# SoHelpMeBagrut — MCP Auto-Installer (Windows PowerShell)
$ErrorActionPreference = "Stop"

$dir = Join-Path $HOME "Documents\ClaudeMCPs"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "Downloading pdf_page_server.py..."
Invoke-WebRequest "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -OutFile "$dir\pdf_page_server.py"

# Detect Python command (py launcher > python > python3)
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

Write-Host "Installing Python dependencies..."
& $py -m pip install mcp pymupdf requests

# Search for Claude Desktop config in common locations
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

# Read or create config
if (Test-Path $configPath) {
    try { $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { $config = [PSCustomObject]@{} }
} else {
    $config = [PSCustomObject]@{}
}

if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
}

$config.mcpServers | Add-Member -MemberType NoteProperty -Name "sohelpmebagurt-pdf-viewer" -Value (
    [PSCustomObject]@{ command = $py; args = @("$dir\pdf_page_server.py") }
) -Force

# ConvertTo-Json automatically escapes backslashes correctly (\ becomes \\)
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8

Write-Host ""
Write-Host "Done! Restart Claude Desktop to activate."
Write-Host "Python  : $py"
Write-Host "Server  : $dir\pdf_page_server.py"
Write-Host "Config  : $configPath"
