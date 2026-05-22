#!/usr/bin/env python3
"""
Syncs Computer Science bagrut exams from the Ministry of Education.
Uses Playwright (headless Chromium) to bypass CloudFront bot detection.
Downloads new PDFs, extracts text, saves to subject/ComputerScience/bagrut/.
Also regenerates the URL lists in base.md and java/skill.md.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

def ensure(pkg, import_as=None):
    try:
        return __import__(import_as or pkg)
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--break-system-packages'], check=True)
        return __import__(import_as or pkg)

ensure('pdfplumber')
import pdfplumber

BASE_URL    = "https://meyda.education.gov.il"
API_URL     = f"{BASE_URL}/bagmgr/Ajax.ashx"
BAGRUT_DIR  = Path("subject/ComputerScience/bagrut")
BASE_MD     = Path("subject/ComputerScience/shared/base.md")
JAVA_SKILL  = Path("subject/ComputerScience/java/skill.md")
GITHUB_BASE = "https://imnoammm.github.io/sohelpmebagurt/subject/ComputerScience/bagrut"


def fetch_all_exams():
    """Use a headless Chromium browser to fetch all exam metadata from the API."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright', '--break-system-packages'], check=True)
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium', '--with-deps'], check=True)
        from playwright.sync_api import sync_playwright

    exams = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL",
        )
        page = context.new_page()

        print("  Opening ministry site to get session...")
        page.goto(f"{BASE_URL}/bagmgr/", wait_until="networkidle", timeout=60000)
        print(f"  Page loaded: {page.title()}")

        # Extract DotNetNuke CSRF token from the page
        csrt = ""
        try:
            # Try hidden input field first
            el = page.query_selector('input[name="__RequestVerificationToken"]')
            if el:
                csrt = el.get_attribute("value") or ""
            # Try cookies
            if not csrt:
                for cookie in context.cookies():
                    if "csrt" in cookie["name"].lower() or "requestverification" in cookie["name"].lower():
                        csrt = cookie["value"]
                        break
            # Try extracting from page source via regex
            if not csrt:
                src = page.content()
                m = re.search(r'csrt["\s:=]+([0-9]{10,})', src)
                if m:
                    csrt = m.group(1)
        except Exception as e:
            print(f"  Could not extract csrt: {e}")
        print(f"  csrt: {csrt[:30] if csrt else 'not found — proceeding without'}")

        page_num = 1
        while True:
            url = (f"{API_URL}?search=1&sheelon=&miktzoa=899&safa=1"
                   f"&pagesize=100&page={page_num}"
                   + (f"&csrt={csrt}" if csrt else ""))
            print(f"  Fetching API page {page_num}...")
            resp = page.request.get(url)
            if not resp.ok:
                print(f"  API returned {resp.status}, stopping.")
                break
            body = resp.text()
            if not body.strip():
                print(f"  Empty response — likely missing session/csrt. Stopping.")
                break
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                print(f"  JSON parse error. Response (first 300 chars): {body[:300]}")
                break
            if not data:
                break
            exams.extend(data)
            total = data[0].get("total", 0)
            print(f"  Got {len(data)} exams (total: {total})")
            if len(exams) >= total:
                break
            page_num += 1

        browser.close()
    return exams


def download_pdf(url):
    """Use Playwright to download a PDF as bytes."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        resp = page.request.get(url)
        data = resp.body()
        browser.close()
    return data


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


def sync_exams(exams):
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
            pdf_bytes = download_pdf(pdf_url)
        except Exception as e:
            print(f"    ERROR downloading: {e}")
            continue

        try:
            text = extract_text(pdf_bytes)
        except Exception as e:
            print(f"    WARNING: could not extract text ({e}), skipping")
            continue
        if not text.strip():
            print(f"    WARNING: no text extracted, skipping")
            continue

        out_path.write_text(text, encoding="utf-8")
        print(f"    saved {len(text):,} chars")
        new_count += 1

    return new_count


def regenerate_url_lists():
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
        text, flags=re.DOTALL,
    )
    BASE_MD.write_text(text, encoding="utf-8")
    print("  updated base.md")

    java_text = JAVA_SKILL.read_text(encoding="utf-8")
    new_java_section = (
        "## Bagruyot Files\n\n"
        + (url_block if url_block else "_none available_")
    )
    java_text = re.sub(
        r"## Bagruyot Files\b.*?(?=\n---|\n## |\Z)",
        new_java_section + "\n\n",
        java_text, flags=re.DOTALL,
    )
    JAVA_SKILL.write_text(java_text, encoding="utf-8")
    print("  updated java/skill.md")


def main():
    print("=== Bagrut Sync ===")
    exams = fetch_all_exams()
    print(f"Found {len(exams)} exams in API")

    new_count = sync_exams(exams)
    print(f"\n{new_count} new exam(s) downloaded")

    print("\nRegenerating URL lists...")
    regenerate_url_lists()
    print("\nDone.")


if __name__ == "__main__":
    main()
