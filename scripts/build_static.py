#!/usr/bin/env python3
"""Static site generator for Daily Knowledge Digest.

Builds HTML files under site/ for GitHub Pages deployment.

Usage:
    python3 scripts/build_static.py
"""

import html
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DAILY_DIR
from read_today import extract_topic_ids, find_topic_file
from serve_web import PAGE_TEMPLATE, build_digest_page, build_topic_page

SITE_DIR = Path(__file__).parent.parent / "docs"

# GitHub Pages serves this repo at /knowledge/ — adjust if the repo is renamed.
SITE_BASE_PATH = "/daily_knowledge"


def _fix_paths(page_html: str) -> str:
    """Rewrite root-relative hrefs to include the GitHub Pages subpath."""
    return page_html.replace('href="/', f'href="{SITE_BASE_PATH}/')


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_digest_pages() -> list[date]:
    """Build one page per daily digest. Returns sorted list of built dates."""
    built: list[date] = []
    for daily_file in sorted(DAILY_DIR.glob("*.md")):
        try:
            run_date = date.fromisoformat(daily_file.stem)
        except ValueError:
            continue
        page_html, status = build_digest_page(run_date)
        if status == 200:
            _write(SITE_DIR / "digests" / daily_file.stem / "index.html",
                   _fix_paths(page_html))
            built.append(run_date)
            print(f"  digest {run_date.isoformat()} ✓")
        else:
            print(f"  digest {run_date.isoformat()} skipped (status {status})", file=sys.stderr)
    return built


def build_topic_pages() -> None:
    """Build one page per topic referenced in any daily note."""
    seen: set[str] = set()
    for daily_file in sorted(DAILY_DIR.glob("*.md")):
        try:
            run_date = date.fromisoformat(daily_file.stem)
        except ValueError:
            continue
        for tid in extract_topic_ids(daily_file.read_text(encoding="utf-8")):
            if tid in seen or find_topic_file(tid) is None:
                continue
            seen.add(tid)
            page_html, status = build_topic_page(tid, digest_date=run_date)
            if status == 200:
                _write(SITE_DIR / "topic" / tid / "index.html",
                       _fix_paths(page_html))
                print(f"  topic {tid} ✓")
            else:
                print(f"  topic {tid} skipped (status {status})", file=sys.stderr)


def build_archive_page(dates: list[date]) -> None:
    """Build site/digests/index.html listing all digests newest-first."""
    rows = "".join(
        f'<li><a href="{SITE_BASE_PATH}/digests/{d.isoformat()}/">'
        f'{html.escape(d.strftime("%B %-d, %Y"))}</a></li>\n'
        for d in reversed(dates)
    )
    body = (
        '<div class="digest-header">'
        '<h1>Daily Knowledge Digest — Archive</h1>'
        f'<div class="meta">{len(dates)} digests</div>'
        '</div>'
        f'<ul style="list-style:none;padding:0">{rows}</ul>'
    )
    _write(SITE_DIR / "digests" / "index.html",
           PAGE_TEMPLATE.format(title="Digest Archive", body=body))
    print("  archive ✓")


def build_home_redirect(latest: date) -> None:
    """Build site/index.html that meta-refreshes to the latest digest."""
    target = f"{SITE_BASE_PATH}/digests/{latest.isoformat()}/"
    body = (
        f'<meta http-equiv="refresh" content="0; url={target}">'
        f'<p><a href="{target}">Latest digest ({latest.isoformat()})</a></p>'
    )
    _write(SITE_DIR / "index.html",
           PAGE_TEMPLATE.format(title="Daily Knowledge Digest", body=body))
    print("  home redirect ✓")


def build_static() -> None:
    print("Building digests...")
    dates = build_digest_pages()
    if not dates:
        print("No digests found — nothing to build.", file=sys.stderr)
        sys.exit(1)

    print("Building topic pages...")
    build_topic_pages()

    print("Building archive...")
    build_archive_page(dates)

    print("Building home redirect...")
    build_home_redirect(dates[-1])

    print(f"Done. {len(dates)} digest(s) built → {SITE_DIR}")


if __name__ == "__main__":
    try:
        build_static()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
