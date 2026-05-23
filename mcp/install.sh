#!/bin/bash
# SoHelpMeBagrut — MCP Auto-Installer (macOS / Linux)
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
G='\033[0;32m'  # green
DG='\033[0;90m' # dark gray
CY='\033[0;36m' # cyan
YL='\033[0;33m' # yellow
RD='\033[0;31m' # red
W='\033[0;37m'  # white
B='\033[1m'     # bold
R='\033[0m'     # reset

step() { printf "\n  ${DG}[${CY}$1${DG}]${R} ${B}$2${R}\n"; }
ok()   { printf "  ${G} OK ${R}  $1\n"; }
info() { printf "  ${DG}-->${R}  $1\n"; }
warn() { printf "  ${YL}[!]${R}  $1\n"; }
fail() { printf "  ${RD}[x]${R}  $1\n"; exit 1; }
rule() { printf "  ${DG}──────────────────────────────────────────────────${R}\n"; }

# ── Banner ────────────────────────────────────────────────────────────────────
printf "\n"
printf "  ${DG}╔══════════════════════════════════════════════════╗${R}\n"
printf "  ${G}║       SoHelpMeBagrut — MCP Installer            ║${R}\n"
printf "  ${G}║       תמיכה בתמונות ל-Claude Desktop            ║${R}\n"
printf "  ${DG}╚══════════════════════════════════════════════════╝${R}\n"
printf "\n"

# ── [1] Install location ──────────────────────────────────────────────────────
step 1 "Install location"
DEFAULT_DIR="$HOME/Documents/ClaudeMCPs"
info "Default: $DEFAULT_DIR"
printf "  ${DG}-->${R}  Press ${CY}Enter${R} to use default, or type a custom path: "
read -r ANSWER
if [ -z "$ANSWER" ]; then DIR="$DEFAULT_DIR"; else DIR="$ANSWER"; fi
mkdir -p "$DIR"
ok "Installing to: $DIR"

# ── [2] Download server ───────────────────────────────────────────────────────
step 2 "Downloading pdf_page_server.py"
curl -fsSL "https://raw.githubusercontent.com/ImNoammm/sohelpmebagurt/main/mcp/pdf_page_server.py" -o "$DIR/pdf_page_server.py" \
  || fail "Download failed. Check your internet connection."
ok "Saved to $DIR/pdf_page_server.py"

# ── [3] Install dependencies ──────────────────────────────────────────────────
step 3 "Installing Python packages"
info "mcp  pymupdf  requests"
printf "\n"
pip3 install mcp pymupdf requests --break-system-packages -q 2>/dev/null \
  || pip3 install mcp pymupdf requests -q
printf "\n"
ok "Packages installed"

# ── [4] Find Claude Desktop config ───────────────────────────────────────────
step 4 "Locating Claude Desktop config"
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
        warn "Config not found — will create at default location"
        CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
        mkdir -p "$(dirname "$CONFIG_PATH")"
    else
        warn "Config not found — will create at default location"
        CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
        mkdir -p "$(dirname "$CONFIG_PATH")"
    fi
fi
ok "Config: $CONFIG_PATH"

# ── [5] Update config ─────────────────────────────────────────────────────────
step 5 "Writing MCP server entry to config"
python3 - "$CONFIG_PATH" "$DIR/pdf_page_server.py" <<'PYEOF'
import json, sys
config_path, server_path = sys.argv[1], sys.argv[2]
try:
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
except Exception:
    config = {}
config.setdefault("mcpServers", {})["sohelpmebagurt-pdf-viewer"] = {
    "command": "python3",
    "args": [server_path]
}
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
PYEOF
ok "Config updated"

# ── Done ──────────────────────────────────────────────────────────────────────
SKILL_URL="https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/csharp/skill_mcp.md?v=1"

# Copy to clipboard
COPIED=0
if command -v pbcopy &>/dev/null; then
    printf '%s' "$SKILL_URL" | pbcopy && COPIED=1
elif command -v xclip &>/dev/null; then
    printf '%s' "$SKILL_URL" | xclip -selection clipboard && COPIED=1
elif command -v xsel &>/dev/null; then
    printf '%s' "$SKILL_URL" | xsel --clipboard --input && COPIED=1
fi

printf "\n"
printf "  ${DG}╔══════════════════════════════════════════════════╗${R}\n"
printf "  ${G}║               הכל מוכן!                         ║${R}\n"
printf "  ${DG}╚══════════════════════════════════════════════════╝${R}\n"
printf "\n"
printf "  ${W}Next steps:${R}\n\n"
printf "   ${DG}1.${R}  ${YL}Restart Claude Desktop${R}\n"
printf "   ${DG}2.${R}  ${CY}Paste the URL below into Claude${R}\n\n"
rule
printf "  ${G}${SKILL_URL}${R}\n"
rule
if [ "$COPIED" = "1" ]; then
    printf "\n  ${DG}(URL copied to clipboard automatically)${R}\n"
else
    printf "\n  ${DG}(copy the URL above and paste it into Claude)${R}\n"
fi
printf "\n"
