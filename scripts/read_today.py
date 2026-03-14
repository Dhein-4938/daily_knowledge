#!/usr/bin/env python3
"""Terminal reader for Daily Knowledge Digest.

Usage:
    python3 scripts/read_today.py
    python3 scripts/read_today.py --date 2026-03-10
"""

import argparse
import os
import re
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import VAULT_ROOT, DAILY_DIR, TOPICS_DIR, CATEGORY_DIRS

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[1;36m"
YELLOW = "\033[1;33m"
RED    = "\033[1;31m"
BLUE   = "\033[1;34m"
DIM    = "\033[2m"

WRAP_WIDTH = 60


def bold(s):   return f"{BOLD}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def blue(s):   return f"{BLUE}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_without_frontmatter).

    Only captures top-level scalar keys (first occurrence wins) so that nested
    YAML structures like sources[].title don't overwrite the note's own title.
    """
    fm: dict = {}
    if not text.startswith("---"):
        return fm, text
    end = text.find("\n---", 3)
    if end == -1:
        return fm, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    for line in fm_block.splitlines():
        # Only top-level keys (no leading whitespace) to skip nested YAML
        if ":" in line and not line[0].isspace():
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in fm:  # first occurrence wins
                fm[k] = v
    return fm, body


def strip_h1(body: str) -> str:
    """Remove the first H1 line if present."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            lines.pop(i)
            # Also remove any blank line immediately after
            if i < len(lines) and lines[i].strip() == "":
                lines.pop(i)
            break
    return "\n".join(lines)


def unwrap_code_fence(body: str) -> str:
    """Strip outer ```markdown ... ``` wrapper that Claude sometimes emits."""
    stripped = body.lstrip("\n")
    if not stripped.startswith("```"):
        return body
    lines = stripped.splitlines()
    # Remove opening fence line
    lines = lines[1:]
    # Remove trailing closing fence
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def strip_embedded_frontmatter(body: str) -> str:
    """Strip a second YAML frontmatter block embedded in the body (bug artifact)."""
    if not body.lstrip().startswith("---"):
        return body
    end = body.find("\n---", 3)
    if end == -1:
        return body
    return body[end + 4:].lstrip("\n")


def extract_topic_ids(daily_text: str) -> list[str]:
    """Extract topic IDs from [[wikilink]] entries in the daily note table rows."""
    # Match table rows with [[topic_id]] pattern
    return re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]", daily_text)


def find_topic_file(topic_id: str) -> Path | None:
    """Search all category dirs for {topic_id}.md."""
    for cat_dir in CATEGORY_DIRS.values():
        p = cat_dir / f"{topic_id}.md"
        if p.exists():
            return p
    # Fallback: recursive search
    for p in TOPICS_DIR.rglob(f"{topic_id}.md"):
        return p
    return None


# ---------------------------------------------------------------------------
# Inline rendering (wikilinks, bold, URLs)
# ---------------------------------------------------------------------------

def render_inline(text: str) -> str:
    # [[link|alias]] → alias
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    # [[link]] → link
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: bold(m.group(1)), text)
    # *italic* (just strip the asterisks)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text


def wrap_prose(text: str) -> str:
    """Wrap a paragraph of prose at WRAP_WIDTH, preserving leading indent."""
    indent = len(text) - len(text.lstrip())
    prefix = text[:indent]
    return textwrap.fill(text.strip(), width=WRAP_WIDTH,
                         initial_indent=prefix, subsequent_indent=prefix)


# ---------------------------------------------------------------------------
# Block-level rendering
# ---------------------------------------------------------------------------

def render_callout(label: str, title: str, body_lines: list[str]) -> str:
    label_up = label.upper()
    if label == "info":
        color = blue
    elif label == "tip":
        color = yellow
    else:
        color = red

    content_lines = [render_inline(ln.lstrip("> ").lstrip()) for ln in body_lines]
    content = " ".join(content_lines).strip()
    wrapped = textwrap.fill(content, width=WRAP_WIDTH - 4)

    header = color(f" ╔ {label_up}" + (f": {title}" if title else "") + " ╗ ")
    footer = color(" ╚" + "═" * (WRAP_WIDTH - 4) + "╝ ")
    inner_lines = []
    for ln in wrapped.splitlines():
        inner_lines.append(color("  ║ ") + ln)
    return "\n".join([header] + inner_lines + [footer])


def render_body(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # --- HR ---
        if re.match(r"^---+\s*$", line):
            out.append(dim("─" * WRAP_WIDTH))
            i += 1
            continue

        # --- Callout block ---
        # > [!type] optional title
        callout_m = re.match(r"^>\s*\[!(info|tip|warning)\]\s*(.*)", line, re.IGNORECASE)
        if callout_m:
            label = callout_m.group(1).lower()
            title = callout_m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                body_lines.append(lines[i])
                i += 1
            out.append(render_callout(label, title, body_lines))
            continue

        # --- Plain blockquote (no callout) ---
        if line.startswith(">"):
            content = line.lstrip("> ").strip()
            out.append(dim("  │ " + render_inline(content)))
            i += 1
            continue

        # --- H2 ---
        if line.startswith("## "):
            heading = line[3:].strip().upper()
            out.append("")
            out.append(cyan(f" {heading} "))
            out.append("")
            i += 1
            continue

        # --- H3 ---
        if line.startswith("### "):
            heading = line[4:].strip()
            out.append("")
            out.append(bold(f" {heading} "))
            i += 1
            continue

        # --- Code fence (skip) ---
        if line.startswith("```"):
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                i += 1
            i += 1
            continue

        # --- Blank line ---
        if line.strip() == "":
            out.append("")
            i += 1
            continue

        # --- List item ---
        list_m = re.match(r"^(\s*[-*]\s+)(.*)", line)
        if list_m:
            prefix = list_m.group(1)
            content = render_inline(list_m.group(2))
            wrapped = textwrap.fill(content, width=WRAP_WIDTH - len(prefix),
                                    subsequent_indent=" " * len(prefix))
            out.append(prefix + wrapped)
            i += 1
            continue

        # --- Numbered list ---
        num_m = re.match(r"^(\s*\d+\.\s+)(.*)", line)
        if num_m:
            prefix = num_m.group(1)
            content = render_inline(num_m.group(2))
            wrapped = textwrap.fill(content, width=WRAP_WIDTH - len(prefix),
                                    subsequent_indent=" " * len(prefix))
            out.append(prefix + wrapped)
            i += 1
            continue

        # --- Prose ---
        rendered = render_inline(line)
        if rendered.strip():
            out.append(wrap_prose(rendered))
        else:
            out.append("")
        i += 1

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

W = WRAP_WIDTH + 2  # box width


def digest_header(run_date: date, n_topics: int, total_min: int) -> str:
    date_str = run_date.strftime("%B %-d, %Y")
    line1 = f"Daily Knowledge Digest — {date_str}"
    line2 = f"{n_topics} topics  ·  ~{total_min} min total"
    inner = W - 2
    top    = "╔" + "═" * inner + "╗"
    mid1   = "║  " + line1.ljust(inner - 2) + "║"
    mid2   = "║  " + line2.ljust(inner - 2) + "║"
    bot    = "╚" + "═" * inner + "╝"
    return cyan("\n".join([top, mid1, mid2, bot]))


def topic_header(idx: int, total: int, fm: dict) -> str:
    title     = fm.get("title", "Unknown").upper()
    category  = fm.get("category", "")
    subcat    = fm.get("subcategory", "")
    status    = fm.get("status", "unknown")
    read_time = fm.get("read_time_minutes", "?")
    cat_str   = f"{category} · {subcat}" if subcat else category
    sep       = "━" * (W + 2)
    counter   = f"[{idx}/{total}]  "
    line1     = counter + title.ljust(W - len(counter) - len(cat_str)) + cat_str
    line2     = "       " + f"Status: {status}  ·  ~{read_time} min read"
    return bold("\n".join([sep, line1, line2, sep]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Terminal reader for Daily Knowledge Digest")
    parser.add_argument("--date", help="Date to read (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    if args.date:
        try:
            run_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date: {args.date}", file=sys.stderr)
            sys.exit(1)
    else:
        run_date = date.today()

    daily_path = DAILY_DIR / f"{run_date.isoformat()}.md"
    if not daily_path.exists():
        print(f"No digest found for {run_date.isoformat()}: {daily_path}", file=sys.stderr)
        sys.exit(1)

    daily_text = daily_path.read_text(encoding="utf-8")
    topic_ids = extract_topic_ids(daily_text)

    if not topic_ids:
        print("No topics found in daily note.", file=sys.stderr)
        sys.exit(1)

    # Load topic files
    topics: list[tuple[dict, str]] = []  # (frontmatter, rendered_body)
    total_min = 0
    for tid in topic_ids:
        path = find_topic_file(tid)
        if path is None:
            print(f"Warning: topic file not found for '{tid}'", file=sys.stderr)
            continue
        raw = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        body = strip_h1(body)
        body = unwrap_code_fence(body)
        body = strip_embedded_frontmatter(body)
        total_min += int(fm.get("read_time_minutes", 0))
        topics.append((fm, body))

    if not topics:
        print("No topic files could be loaded.", file=sys.stderr)
        sys.exit(1)

    # Build full output
    sections: list[str] = []
    sections.append(digest_header(run_date, len(topics), total_min))
    sections.append("")

    for i, (fm, body) in enumerate(topics, 1):
        sections.append(topic_header(i, len(topics), fm))
        sections.append("")
        sections.append(render_body(body))
        sections.append("")

    full_output = "\n".join(sections)

    # Pipe through less -R
    try:
        proc = subprocess.Popen(
            ["less", "-R"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=full_output.encode("utf-8"))
    except FileNotFoundError:
        # less not available — just print
        print(full_output)


if __name__ == "__main__":
    main()
