#!/usr/bin/env python3
"""
SoHelpMeBagrut — PDF Page Viewer MCP Server

Gives Claude the ability to fetch a single page from a bagrut PDF and see it as an image.
Use this when an exam question references a figure, diagram, or table that requires visual context.
"""

import asyncio
import base64
import subprocess
import sys


def ensure(pkg, import_as=None):
    try:
        return __import__(import_as or pkg)
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "--break-system-packages"],
            check=True, capture_output=True,
        )
        return __import__(import_as or pkg)


ensure("requests")
ensure("pymupdf", import_as="fitz")
ensure("mcp")

import requests
import fitz
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

MAX_BYTES = 999 * 1024  # 999 KB
DPI_STEPS = [150, 120, 96, 72]

server = Server("sohelpmebagurt-pdf-viewer")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="get_pdf_page",
            description=(
                "Fetch one page from a bagrut exam PDF and return it as an image. "
                "Use this whenever a question references a figure, graph, table, or diagram "
                "that you cannot read from the text alone. "
                "Pass the PDF URL from the Past Exam Files list and the 1-based page number."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Direct PDF URL from the Past Exam Files section of the skill file",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number to fetch (1-based)",
                        "minimum": 1,
                    },
                },
                "required": ["url", "page"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "get_pdf_page":
        raise ValueError(f"Unknown tool: {name}")

    url: str = arguments["url"]
    page_num: int = arguments["page"] - 1  # fitz is 0-indexed

    # Download PDF
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://meyda.education.gov.il/",
            },
            timeout=60,
        )
        resp.raise_for_status()
    except Exception as e:
        return [types.TextContent(type="text", text=f"Failed to download PDF: {e}")]

    # Open and render the page
    try:
        doc = fitz.open(stream=resp.content, filetype="pdf")
    except Exception as e:
        return [types.TextContent(type="text", text=f"Failed to open PDF: {e}")]

    total_pages = len(doc)
    if page_num >= total_pages:
        doc.close()
        return [
            types.TextContent(
                type="text",
                text=f"Page {page_num + 1} does not exist — this PDF has {total_pages} page(s).",
            )
        ]

    page = doc[page_num]
    png_bytes = None

    for dpi in DPI_STEPS:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        candidate = pix.tobytes("png")
        if len(candidate) <= MAX_BYTES:
            png_bytes = candidate
            break

    doc.close()

    if png_bytes is None:
        return [types.TextContent(type="text", text="Could not render page under 999 KB even at minimum resolution.")]

    b64 = base64.standard_b64encode(png_bytes).decode()
    return [types.ImageContent(type="image", data=b64, mimeType="image/png")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
