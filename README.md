# SoHelpMeBagrut

AI-powered Israeli Bagrut exam tutor. Paste a skill file URL into Claude (or any AI assistant) and it becomes a subject-specific tutor with access to real past exams.

**Site:** https://imnoammm.github.io/sohelpmebagurt/

---

## Available Subjects

| Subject | Variant | Skill URL | With MCP (image support) |
|---|---|---|---|
| מדעי המחשב | Java | `…/java/skill.md` | `…/java/skill_mcp.md` |
| מדעי המחשב | C# | `…/csharp/skill.md` | `…/csharp/skill_mcp.md` |

Base URL: `https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/`

Use `skill.md` with any AI assistant. Use `skill_mcp.md` only if you have the MCP server installed in Claude Desktop — it adds instructions that tell Claude to use the `get_pdf_page` tool when a question has a figure or diagram.

More subjects coming soon.

---

## MCP Server — PDF Page Viewer (for Claude Desktop)

Some exam questions include diagrams, graphs, or figures that can only be understood visually. The MCP server lets Claude fetch and view any page of a bagrut PDF as an image.

### What it does

When Claude encounters a question with a figure or diagram, it calls `get_pdf_page(url, page)` to fetch that page and see the image — no manual downloading needed.

### Installation

**1. Install dependencies**

```bash
pip install mcp pymupdf requests
```

**2. Download the server script**

Clone this repo or download [`mcp/pdf_page_server.py`](mcp/pdf_page_server.py) to a local folder.

**3. Add to Claude Desktop config**

Open your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the following (replace the path with wherever you saved the script):

```json
{
  "mcpServers": {
    "sohelpmebagurt-pdf-viewer": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp/pdf_page_server.py"]
    }
  }
}
```

**4. Restart Claude Desktop**

The tool `get_pdf_page` will now appear in Claude's tool list.

### Usage

Once installed, you don't need to do anything special — Claude will automatically call the tool when it detects a question that requires an image. You can also explicitly ask:

> "תביא לי את עמוד 3 מהבגרות הזו"

---

## How to use (without MCP)

1. Go to the [site](https://imnoammm.github.io/sohelpmebagurt/) and copy the skill URL for your subject
2. Paste it into Claude, ChatGPT, or any AI with web access
3. The AI loads the skill file and becomes your Bagrut tutor for that subject
