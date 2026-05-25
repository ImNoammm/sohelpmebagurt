#!/usr/bin/env python3
"""
Syncs CS and Math bagrut exam PDF URLs from the Ministry of Education API.
Writes direct PDF URLs into skill.md files — no downloading or text extraction needed.
"""

import re
import subprocess
import sys
from pathlib import Path

def ensure(pkg, import_as=None):
    try:
        return __import__(import_as or pkg)
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--break-system-packages'], check=True)
        return __import__(import_as or pkg)

BASE_URL   = "https://meyda.education.gov.il"
API_URL    = f"{BASE_URL}/bagmgr/Ajax.ashx"
KNOWN_CSRT = "3016677356254188609"  # static DNN token, extracted from the site

# ── Skill file paths ──────────────────────────────────────────────────────────
CS_FILES = [
    Path("subject/ComputerScience/java/skill.md"),
    Path("subject/ComputerScience/java/skill_mcp.md"),
    Path("subject/ComputerScience/csharp/skill.md"),
    Path("subject/ComputerScience/csharp/skill_mcp.md"),
]
MATH_FILES = [
    Path("subject/Math/skill_mcp.md"),
]
TANACH_FILES = [
    Path("subject/Tanach/skill_mcp.md"),
    Path("subject/Tanach/skill.md"),
]

# ── Math sheelon IDs (miktzoa=35) ─────────────────────────────────────────────
MATH_SHEELONIM = ["35572", "35571", "35581", "33582"]


def make_session():
    ensure('requests')
    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
        "Referer": f"{BASE_URL}/bagmgr/",
        "X-Requested-With": "XMLHttpRequest",
    })
    session.cookies.set("csrt", KNOWN_CSRT, domain="meyda.education.gov.il")
    return session


def fetch_pages(session, miktzoa, sheelon=""):
    """Fetch all paginated results for a given miktzoa (and optional sheelon)."""
    exams = []
    page_num = 1
    while True:
        url = (f"{API_URL}?search=1&sheelon={sheelon}&miktzoa={miktzoa}&safa=1"
               f"&pagesize=100&page={page_num}&csrt={KNOWN_CSRT}")
        try:
            resp = session.get(url, timeout=30)
        except Exception as e:
            print(f"  Request error: {e}")
            break
        if not resp.ok:
            print(f"  API returned {resp.status_code}, stopping.")
            break
        body = resp.text.strip()
        if not body:
            break
        try:
            data = resp.json()
        except Exception:
            print(f"  JSON parse error. Response (first 300 chars): {body[:300]}")
            break
        if not data:
            break
        exams.extend(data)
        total = data[0].get("total", 0)
        if len(exams) >= total:
            break
        page_num += 1
    return exams


def fetch_cs_exams(session):
    """Fetch all CS bagrut exams (miktzoa=899)."""
    exams = []
    page_num = 1
    while True:
        url = (f"{API_URL}?search=1&sheelon=&miktzoa=899&safa=1"
               f"&pagesize=100&page={page_num}&csrt={KNOWN_CSRT}")
        print(f"  Fetching CS API page {page_num}...")
        try:
            resp = session.get(url, timeout=30)
        except Exception as e:
            print(f"  Request error: {e}")
            break
        if not resp.ok:
            print(f"  API returned {resp.status_code}, stopping.")
            break
        body = resp.text.strip()
        if not body:
            break
        try:
            data = resp.json()
        except Exception:
            print(f"  JSON parse error: {body[:300]}")
            break
        if not data:
            break
        exams.extend(data)
        total = data[0].get("total", 0)
        print(f"  Got {len(data)} exams (total: {total})")
        if len(exams) >= total:
            break
        page_num += 1
    return exams


def fetch_math_exams(session):
    """Fetch math bagrut exams for the configured sheelonim."""
    all_exams = []
    for sh in MATH_SHEELONIM:
        print(f"  Fetching math sheelon {sh}...")
        exams = fetch_pages(session, miktzoa="35", sheelon=sh)
        print(f"    Got {len(exams)} exams")
        all_exams.extend(exams)
    return all_exams


def fetch_tanach_exams(session):
    """Fetch Tanach bagrut exams (miktzoa=1)."""
    print("  Fetching Tanach exams (miktzoa=1)...")
    exams = fetch_pages(session, miktzoa="1", sheelon="")
    print(f"    Got {len(exams)} exams")
    return exams


def url_exists(session, url):
    """Return True if the URL serves a non-HTML file (PDF or binary)."""
    try:
        resp = session.head(url, timeout=15, allow_redirects=True)
        if resp.ok:
            ct = resp.headers.get("Content-Type", "")
            if ct and "text/html" not in ct.lower():
                return True   # pdf, octet-stream, etc.
        # HEAD failed or returned HTML — try a real GET (stream, don't download body)
        resp = session.get(url, timeout=15, stream=True, allow_redirects=True)
        resp.close()
        if not resp.ok:
            return False
        ct = resp.headers.get("Content-Type", "")
        return not ct or "text/html" not in ct.lower()
    except Exception:
        return False


def build_url_block(exams, session):
    by_sheelon: dict[str, list[tuple[str, str, str]]] = {}
    seen_urls = 0
    for exam in exams:
        pdf_url = exam.get("question")
        if not pdf_url or "pitron" in pdf_url.lower():
            continue
        seen_urls += 1
        if seen_urls <= 3:
            print(f"  sample URL: {pdf_url}")
        if not url_exists(session, pdf_url):
            print(f"  skipping dead URL: {pdf_url}")
            continue
        sheelon = exam["semel_sheelon"]
        year    = exam["shana"]
        moed    = exam["code_moed"]
        by_sheelon.setdefault(sheelon, []).append((year, moed, pdf_url))

    lines = []
    for sheelon in sorted(by_sheelon, reverse=True):
        lines.append(f"### {sheelon}")
        for year, moed, url in sorted(by_sheelon[sheelon], reverse=True):
            lines.append(f"{year} מועד {moed}: {url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_skill_files(skill_files, url_block, subject_label):
    new_section = (
        "## Past Exam Files\n\n"
        f"Israeli {subject_label} Bagrut exam PDFs, direct from the Ministry of Education. "
        "Fetch the relevant PDF to read exam questions.\n\n"
        + (url_block if url_block else "_none yet — sync pending_")
    )
    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        text = re.sub(
            r"## Past Exam Files\b.*?(?=\n---|\n## |\Z)",
            new_section + "\n\n",
            text, flags=re.DOTALL,
        )
        skill_file.write_text(text, encoding="utf-8")
        print(f"  updated {skill_file}")


def main():
    session = make_session()

    # ── CS ────────────────────────────────────────────────────────────────────
    print("=== CS Bagrut Sync ===")
    cs_exams = fetch_cs_exams(session)
    print(f"Found {len(cs_exams)} CS exams")
    cs_block = build_url_block(cs_exams, session)
    print(f"  {cs_block.count(': http')} exams with PDF URLs")
    print("Updating CS skill files...")
    update_skill_files(CS_FILES, cs_block, "CS")

    # ── Math ──────────────────────────────────────────────────────────────────
    print("\n=== Math Bagrut Sync ===")
    math_exams = fetch_math_exams(session)
    print(f"Found {len(math_exams)} math exams")
    math_block = build_url_block(math_exams, session)
    print(f"  {math_block.count(': http')} exams with PDF URLs")
    print("Updating Math skill files...")
    update_skill_files(MATH_FILES, math_block, "Math")

    # ── Tanach ────────────────────────────────────────────────────────────────
    print("\n=== Tanach Bagrut Sync ===")
    tanach_exams = fetch_tanach_exams(session)
    print(f"Found {len(tanach_exams)} Tanach exams")
    tanach_block = build_url_block(tanach_exams, session)
    print(f"  {tanach_block.count(': http')} exams with PDF URLs")
    print("Updating Tanach skill files...")
    update_skill_files(TANACH_FILES, tanach_block, "Tanach")

    print("\nDone.")


if __name__ == "__main__":
    main()
