#!/bin/bash
# SoHelpMeBagrut — MCP Auto-Installer (macOS / Linux)
set -e

# ── Install location ──────────────────────────────────────────────────────────
DEFAULT_DIR="$HOME/Documents/ClaudeMCPs"
echo ""
echo "Install location"
echo "  Default: $DEFAULT_DIR"
printf "Press Enter to use default, or type a custom path: "
read -r ANSWER
if [ -z "$ANSWER" ]; then
    DIR="$DEFAULT_DIR"
else
    DIR="$ANSWER"
fi
mkdir -p "$DIR"
echo "Installing to: $DIR"
echo ""

# ── Download server ───────────────────────────────────────────────────────────
echo "Downloading pdf_page_server.py..."
curl -fsSL "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -o "$DIR/pdf_page_server.py"

# ── Install dependencies ──────────────────────────────────────────────────────
echo "Installing Python dependencies..."
pip3 install mcp pymupdf requests --break-system-packages 2>/dev/null || pip3 install mcp pymupdf requests

# ── Find Claude Desktop config ────────────────────────────────────────────────
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

# ── Update config ─────────────────────────────────────────────────────────────
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

# ── Done ──────────────────────────────────────────────────────────────────────
SKILL_URL="https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/csharp/skill_mcp.md?v=1"

# Copy to clipboard
if command -v pbcopy &>/dev/null; then
    echo -n "$SKILL_URL" | pbcopy
    COPIED=1
elif command -v xclip &>/dev/null; then
    echo -n "$SKILL_URL" | xclip -selection clipboard
    COPIED=1
elif command -v xsel &>/dev/null; then
    echo -n "$SKILL_URL" | xsel --clipboard --input
    COPIED=1
else
    COPIED=0
fi

echo ""
echo "Done! Restart Claude Desktop to activate."
echo ""
if [ "$COPIED" = "1" ]; then
    echo "The skill URL has been copied to your clipboard."
else
    echo "Copy this URL and paste it into Claude:"
fi
echo "  $SKILL_URL"
echo ""
echo "Server : $DIR/pdf_page_server.py"
echo "Config : $CONFIG_PATH"
