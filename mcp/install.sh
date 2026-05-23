#!/bin/bash
# SoHelpMeBagrut — MCP Auto-Installer (macOS / Linux)
set -e

DIR="$HOME/Documents/ClaudeMCPs"
mkdir -p "$DIR"

echo "Downloading pdf_page_server.py..."
curl -fsSL "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -o "$DIR/pdf_page_server.py"

echo "Installing Python dependencies..."
pip3 install mcp pymupdf requests --break-system-packages 2>/dev/null || pip3 install mcp pymupdf requests

# Search for Claude Desktop config
echo "Locating Claude Desktop config..."
CANDIDATES=(
    "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    "$HOME/.config/Claude/claude_desktop_config.json"
    "$HOME/.config/claude/claude_desktop_config.json"
    "$HOME/.config/Anthropic/Claude/claude_desktop_config.json"
)

CONFIG_PATH=""
for c in "${CANDIDATES[@]}"; do
    if [ -f "$c" ]; then CONFIG_PATH="$c"; break; fi
done

if [ -z "$CONFIG_PATH" ]; then
    FOUND=$(find "$HOME" -maxdepth 8 -name "claude_desktop_config.json" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        CONFIG_PATH="$FOUND"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
        mkdir -p "$(dirname "$CONFIG_PATH")"
    else
        CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
        mkdir -p "$(dirname "$CONFIG_PATH")"
    fi
fi

echo "Config: $CONFIG_PATH"

python3 - "$CONFIG_PATH" "$DIR/pdf_page_server.py" <<'PYEOF'
import json, sys
config_path, server_path = sys.argv[1], sys.argv[2]
try:
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}
config.setdefault("mcpServers", {})["sohelpmebagurt-pdf-viewer"] = {
    "command": "python3",
    "args": [server_path]
}
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
PYEOF

echo ""
echo "Done! Restart Claude Desktop to activate."
echo "Server : $DIR/pdf_page_server.py"
echo "Config : $CONFIG_PATH"
