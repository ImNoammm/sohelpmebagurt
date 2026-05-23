#!/usr/bin/env python3
"""
Syncs Computer Science bagrut exam PDF URLs from the Ministry of Education API.
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
JAVA_SKILL = Path("subject/ComputerScience/java/skill.md")
CSHARP_SKILL = Path("subject/ComputerScience/csharp/skill.md")

KNOWN_CSRT = "3016677356254188609"  # static DNN token, extracted from the site


def fetch_all_exams():
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

    exams = []
    page_num = 1
    while True:
        url = (f"{API_URL}?search=1&sheelon=&miktzoa=899&safa=1"
               f"&pagesize=100&page={page_num}&csrt={KNOWN_CSRT}")
        print(f"  Fetching API page {page_num}...")
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
            print("  Empty response, stopping.")
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
        print(f"  Got {len(data)} exams (total: {total})")
        if len(exams) >= total:
            break
        page_num += 1

    return exams


def build_url_block(exams):
    by_sheelon: dict[str, list[tuple[str, str, str]]] = {}
    for exam in exams:
        pdf_url = exam.get("question")
        if not pdf_url:
            continue
        sheelon = exam["semel_sheelon"]
        year = exam["shana"]
        moed = exam["code_moed"]
        by_sheelon.setdefault(sheelon, []).append((year, moed, pdf_url))

    lines = []
    for sheelon in sorted(by_sheelon, reverse=True):
        lines.append(f"### {sheelon}")
        for year, moed, url in sorted(by_sheelon[sheelon], reverse=True):
            lines.append(f"{year} מועד {moed}: {url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_skill_files(url_block):
    new_section = (
        "## Past Exam Files\n\n"
        "Israeli CS Bagrut exam PDFs, direct from the Ministry of Education. "
        "Fetch the relevant PDF to read exam questions.\n\n"
        + (url_block if url_block else "_none yet — sync pending_")
    )

    for skill_file in (JAVA_SKILL, CSHARP_SKILL):
        text = skill_file.read_text(encoding="utf-8")
        text = re.sub(
            r"## Past Exam Files\b.*?(?=\n---|\n## |\Z)",
            new_section + "\n\n",
            text, flags=re.DOTALL,
        )
        skill_file.write_text(text, encoding="utf-8")
        print(f"  updated {skill_file}")


def main():
    print("=== Bagrut Sync ===")
    exams = fetch_all_exams()
    print(f"Found {len(exams)} exams in API")

    print("\nBuilding PDF URL list...")
    url_block = build_url_block(exams)
    exam_count = url_block.count(": http")
    print(f"  {exam_count} exams with PDF URLs")

    print("\nUpdating skill files...")
    update_skill_files(url_block)
    print("\nDone.")


if __name__ == "__main__":
    main()
