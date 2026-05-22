#!/usr/bin/env python3
"""
Syncs Computer Science bagrut exams from the Ministry of Education.
Downloads new PDFs, extracts text, saves to subject/ComputerScience/bagrut/.
Also regenerates the URL lists in base.md and java/skill.md.
"""

import json
import re
import sys
import tempfile
from pathlib import Path

import requests

try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pdfplumber', '--break-system-packages'], check=True)
    import pdfplumber

BASE_URL      = "https://meyda.education.gov.il"
API_URL       = f"{BASE_URL}/bagmgr/Ajax.ashx"
BAGRUT_DIR    = Path("subject/ComputerScience/bagrut")
BASE_MD       = Path("subject/ComputerScience/shared/base.md")
JAVA_SKILL    = Path("subject/ComputerScience/java/skill.md")
GITHUB_BASE   = "https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/bagrut"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def get_session_and_csrt():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.get(f"{BASE_URL}/bagmgr/", timeout=15)
        print(f"  Main page status: {resp.status_code}, size: {len(resp.text)}")
        # Try multiple patterns for DotNetNuke's csrt token
        for pattern in [r'csrt[="\s:\']+(\d+)', r'"csrt"\s*:\s*"?(\d+)', r'csrt=(\d+)']:
            match = re.search(pattern, resp.text)
            if match:
                csrt = match.group(1)
                print(f"  Found CSRF token: {csrt[:6]}...")
                return session, csrt
        print(f"  CSRF token not found. Page snippet: {resp.text[:300]}")
        csrt = None
    except Exception as e:
        print(f"  Error fetching main page: {e}")
        csrt = None
    return session, csrt


def fetch_all_exams(session, csrt):
    exams, page = [], 1
    while True:
        params = {"search": "1", "sheelon": "", "miktzoa": "899",
                  "safa": "1", "pagesize": "100", "page": str(page)}
        if csrt:
            params["csrt"] = csrt
        resp = session.get(API_URL, params=params,
                           headers={**HEADERS, "Referer": f"{BASE_URL}/bagmgr/"}, timeout=15)
        if not resp.ok or not resp.text.strip():
            print(f"  ERROR: API returned {resp.status_code}. Response: {resp.text[:200]}")
            break
        try:
            data = resp.json()
        except Exception as e:
            print(f"  ERROR: Could not parse JSON: {e}\n  Response: {resp.text[:200]}")
            break
        if not data:
            break
        exams.extend(data)
        total = data[0].get("total", 0)
        if len(exams) >= total:
            break
        page += 1
    return exams


def extract_text(pdf_bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp = Path(f.name)
    try:
        pages = []
        with pdfplumber.open(tmp) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n\n".join(pages)
    finally:
        tmp.unlink(missing_ok=True)


def sync_exams(session, exams):
    new_count = 0
    for exam in exams:
        sheelon   = exam["semel_sheelon"]
        year      = exam["shana"]
        code_moed = exam["code_moed"]
        pdf_url   = exam.get("question")

        if not pdf_url:
            continue

        folder = BAGRUT_DIR / sheelon
        folder.mkdir(parents=True, exist_ok=True)

        out_path = folder / f"{year}_{code_moed}_exam.txt"
        if out_path.exists():
            print(f"  skip  {sheelon}/{out_path.name}")
            continue

        print(f"  fetch {sheelon}/{out_path.name} ...")
        try:
            pdf_resp = session.get(pdf_url, timeout=30)
            pdf_resp.raise_for_status()
        except Exception as e:
            print(f"    ERROR downloading: {e}")
            continue

        text = extract_text(pdf_resp.content)
        if not text.strip():
            print(f"    WARNING: no text extracted, skipping")
            continue

        out_path.write_text(text, encoding="utf-8")
        print(f"    saved {len(text):,} chars")
        new_count += 1

    return new_count


def regenerate_url_lists():
    """Rebuild the URL sections in base.md and java/skill.md from actual files."""
    by_sheelon: dict[str, list[str]] = {}
    for txt in sorted(BAGRUT_DIR.rglob("*.txt")):
        sheelon = txt.parent.name
        url = f"{GITHUB_BASE}/{sheelon}/{txt.name}"
        by_sheelon.setdefault(sheelon, []).append(url)

    lines = []
    for sheelon in sorted(by_sheelon, reverse=True):
        lines.append(f"### {sheelon}")
        for url in sorted(by_sheelon[sheelon], reverse=True):
            lines.append(url)
        lines.append("")
    url_block = "\n".join(lines).rstrip()

    # --- Update base.md ---
    text = BASE_MD.read_text(encoding="utf-8")
    new_section = (
        "## Bagruyot Files\n\n"
        "**Note:** Hebrew text may appear with reversed word order per line "
        "(PDF extraction artifact) — parse accordingly. "
        "Each question has both Java and C# signatures; "
        "your language-specific file tells you which to show.\n\n"
        + url_block
    )
    text = re.sub(
        r"## Bagruyot Files\b.*?(?=\n## |\Z)",
        new_section + "\n\n",
        text,
        flags=re.DOTALL,
    )
    BASE_MD.write_text(text, encoding="utf-8")
    print("  updated base.md")

    # --- Update java/skill.md (old 899205 / 899222 section) ---
    java_text = JAVA_SKILL.read_text(encoding="utf-8")
    old_extra = {s: by_sheelon.get(s, []) for s in ("899205", "899222")}
    extra_lines = []
    for sheelon, urls in old_extra.items():
        if urls:
            extra_lines.append(f"**{sheelon}**")
            for url in sorted(urls, reverse=True):
                extra_lines.append(url)
            extra_lines.append("")
    extra_block = "\n".join(extra_lines).rstrip()

    new_extra = (
        "### Additional exam files (older Java-era exams)\n\n"
        + (extra_block if extra_block else "_none available_")
    )
    java_text = re.sub(
        r"### Additional exam files.*?(?=\n---|\n## |\Z)",
        new_extra + "\n\n",
        java_text,
        flags=re.DOTALL,
    )
    JAVA_SKILL.write_text(java_text, encoding="utf-8")
    print("  updated java/skill.md")


def main():
    print("=== Bagrut Sync ===")
    session, csrt = get_session_and_csrt()
    print(f"CSRF token: {csrt or 'not found (continuing anyway)'}")

    exams = fetch_all_exams(session, csrt)
    print(f"Found {len(exams)} exams in API")

    new_count = sync_exams(session, exams)
    print(f"\n{new_count} new exam(s) downloaded")

    print("\nRegenerating URL lists...")
    regenerate_url_lists()

    print("\nDone.")


if __name__ == "__main__":
    main()
