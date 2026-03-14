#!/usr/bin/env python3
"""Daily Knowledge Research — Obsidian Vault Automation

Fetches content from Wikipedia + arXiv for selected topics, synthesizes with
Claude, and writes structured Obsidian markdown notes.
"""

import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

# Allow running from the scripts dir
sys.path.insert(0, str(Path(__file__).parent))

import config
from config import (
    TOPICS_PER_DAY,
    MAX_WIKIPEDIA_CHARS,
    RETRY_DELAY_SECONDS,
    VAULT_ROOT,
    META_DIR,
    DAILY_DIR,
    TOPICS_DIR,
    CATEGORY_DIRS,
    SYSTEM_LOG_FILE,
)
from topics import select_topics, mark_covered, load_queue, save_queue
from fetchers import fetch_wikipedia, fetch_arxiv, assess_staleness
from writer import build_frontmatter, build_note_body, write_topic_note, write_daily_note


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        META_DIR.mkdir(parents=True, exist_ok=True)
        with open(SYSTEM_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[LOG ERROR] {e}", flush=True)


# ---------------------------------------------------------------------------
# Synthesis via Anthropic API
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = (
    "You write personal Obsidian knowledge notes for a technical reader who enjoys "
    "rigorous depth. Use Obsidian-flavored markdown: [[wikilinks]] for See Also, "
    "callout blocks ([!info], [!tip], [!warning]), and LaTeX math ($$...$$) where appropriate. "
    "Be precise, insightful, and avoid unnecessary padding. Target ~700 words."
)

SYNTHESIS_USER_TEMPLATE = """\
Write a structured Obsidian knowledge note for: **{title}**

## Source Material

### Wikipedia Extract
{wikipedia_extract}

### Recent arXiv Papers
{arxiv_section}

## Required Sections
1. **Core Concept** — Clear definition with key formalism or LaTeX where appropriate
2. **Why It Matters** — Significance, applications, connections to other fields
3. **Key Details** — 3-5 important technical points or subtleties
4. **Current State** — What's actively being researched or recently resolved
5. **See Also** — 4-6 [[wikilinks]] to related Obsidian topics
6. **Discussion Prompts** — 3 thoughtful questions to explore in conversation

## Callout Rules
- Use `[!info]` for important definitions
- Use `[!tip]` for non-obvious insights or connections
- Use `[!warning]` with text "Note: this information may be dated" for any content \
that seems potentially outdated (technology, active research, etc.)

Do not include the title as a heading (it's in the frontmatter). Start directly with ## Core Concept.
"""


def call_anthropic(topic: dict, wikipedia_data: dict | None, arxiv_papers: list | None) -> str | None:
    wiki_extract = "(Wikipedia data unavailable)"
    if wikipedia_data and wikipedia_data.get("extract"):
        wiki_extract = wikipedia_data["extract"][:MAX_WIKIPEDIA_CHARS]
        if len(wikipedia_data["extract"]) > MAX_WIKIPEDIA_CHARS:
            wiki_extract += "\n[...truncated...]"

    arxiv_section = "(No recent arXiv papers found)"
    if arxiv_papers:
        parts = []
        for p in arxiv_papers:
            parts.append(
                f"**{p['title']}** ({p.get('published_date', 'n.d.')})\n"
                f"Authors: {', '.join(p.get('authors', []))}\n"
                f"{p.get('abstract', '')}"
            )
        arxiv_section = "\n\n---\n".join(parts)

    user_msg = SYNTHESIS_USER_TEMPLATE.format(
        title=topic["title"],
        wikipedia_extract=wiki_extract,
        arxiv_section=arxiv_section,
    )

    for attempt in range(2):
        try:
            result = subprocess.run(
                ["claude", "-p", user_msg, "--system-prompt", SYNTHESIS_SYSTEM],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                synthesis = result.stdout.strip()
                # Strip ```markdown ... ``` wrapper if Claude emitted one
                if synthesis.startswith("```"):
                    lines = synthesis.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    synthesis = "\n".join(lines).strip()
                return synthesis
            log(f"claude -p error (attempt {attempt + 1}): {result.stderr.strip()}")
        except Exception as e:
            log(f"claude -p error (attempt {attempt + 1}): {e}")
        if attempt == 0:
            log(f"Retrying in {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
    return None


# ---------------------------------------------------------------------------
# Per-topic processing
# ---------------------------------------------------------------------------

def process_topic(topic: dict) -> dict | None:
    log(f"Processing: {topic['title']} [{topic['category']}]")

    wikipedia_data = fetch_wikipedia(topic["wikipedia_title"])
    if wikipedia_data:
        log(f"  Wikipedia OK (last edited: {wikipedia_data.get('last_edited_date', 'unknown')})")
    else:
        log(f"  Wikipedia FAILED for '{topic['wikipedia_title']}'")

    arxiv_papers = fetch_arxiv(topic["arxiv_query"])
    if arxiv_papers:
        log(f"  arXiv OK ({len(arxiv_papers)} papers)")
    else:
        log(f"  arXiv FAILED for query '{topic['arxiv_query']}'")

    if not wikipedia_data and not arxiv_papers:
        log(f"  All sources failed for '{topic['title']}' — skipping")
        return None

    # Staleness assessment
    wiki_date = wikipedia_data.get("last_edited_date") if wikipedia_data else None
    arxiv_date = arxiv_papers[0].get("published_date") if arxiv_papers else None
    best_date = arxiv_date or wiki_date
    staleness = assess_staleness(best_date, topic["category"], topic["pace"])
    log(f"  Staleness: {staleness} (best source date: {best_date})")

    # Call Claude
    synthesis = call_anthropic(topic, wikipedia_data, arxiv_papers)
    if synthesis is None:
        log(f"  Synthesis FAILED for '{topic['title']}' — skipping")
        return None

    # Build source metadata list
    sources = []
    today = date.today().isoformat()
    if wikipedia_data:
        sources.append({
            "type": "wikipedia",
            "url": wikipedia_data["url"],
            "retrieved": today,
            "last_edited": wikipedia_data.get("last_edited_date"),
        })
    if arxiv_papers:
        for p in arxiv_papers:
            year = p.get("published_date", "")[:4] if p.get("published_date") else None
            sources.append({
                "type": "arxiv",
                "id": p["arxiv_id"],
                "title": p["title"],
                "year": int(year) if year and year.isdigit() else None,
            })

    # Estimate read time (~200 words/min)
    word_count = len(synthesis.split())
    read_time = max(3, round(word_count / 200))

    confidence = "high" if (wikipedia_data and arxiv_papers) else "medium"
    frontmatter = build_frontmatter(topic, sources, staleness, confidence, read_time)
    body = build_note_body(topic, synthesis, sources)
    full_note = frontmatter + "\n" + body

    note_path = write_topic_note(topic, full_note)
    log(f"  Written: {note_path.relative_to(VAULT_ROOT)}")

    return {
        "topic": topic,
        "status": staleness,
        "read_time": read_time,
        "note_path": note_path,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ensure_vault_dirs():
    for d in [META_DIR, DAILY_DIR, TOPICS_DIR] + list(CATEGORY_DIRS.values()):
        d.mkdir(parents=True, exist_ok=True)


def write_failure_daily_note(run_date: date, reason: str):
    from writer import write_daily_note as _write
    daily_dir = VAULT_ROOT / "Daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    note_path = daily_dir / f"{run_date.isoformat()}.md"
    content = (
        f"# Daily Knowledge Digest — {run_date.strftime('%B %d, %Y')}\n\n"
        f"> [!warning] Generation Failed\n"
        f"> {reason}\n\n"
        f"*Check `Meta/system-log.md` for details.*\n"
    )
    note_path.write_text(content, encoding="utf-8")
    log(f"Failure note written: {note_path.relative_to(VAULT_ROOT)}")


def main():
    today = date.today()
    log(f"=== daily_research.py START ({today.isoformat()}) ===")

    # 1. Ensure directories
    ensure_vault_dirs()

    # 2. Bootstrap queue
    load_queue()  # triggers bootstrap if missing

    # 3. Idempotency check
    daily_note_path = DAILY_DIR / f"{today.isoformat()}.md"
    if daily_note_path.exists():
        log(f"Already ran today ({today.isoformat()}). Exiting. (idempotent)")
        sys.exit(0)

    # 4. Select topics
    selected = select_topics(TOPICS_PER_DAY)
    if not selected:
        log("No eligible topics found (all on cooldown?). Aborting.")
        write_failure_daily_note(today, "No eligible topics available — all may be on cooldown.")
        sys.exit(1)
    log(f"Selected {len(selected)} topics: {[t['title'] for t in selected]}")

    # 5. Process each topic
    topic_notes = []
    covered_ids = []
    skipped_ids = []

    for topic in selected:
        result = process_topic(topic)
        if result:
            topic_notes.append(result)
            covered_ids.append(topic["id"])
        else:
            skipped_ids.append(topic["id"])

    if skipped_ids:
        log(f"Skipped topics (will not mark covered): {skipped_ids}")

    # 6. Write daily note
    if topic_notes:
        daily_path = write_daily_note(today, topic_notes)
        log(f"Daily note written: {daily_path.relative_to(VAULT_ROOT)}")
    else:
        log("All topics failed — writing failure daily note.")
        write_failure_daily_note(today, "All selected topics failed to fetch or synthesize.")
        sys.exit(1)

    # 7. Mark covered
    if covered_ids:
        mark_covered(covered_ids)
        log(f"Marked covered: {covered_ids}")

    log(f"=== daily_research.py DONE — {len(topic_notes)} notes written ===")


if __name__ == "__main__":
    main()
