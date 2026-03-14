#!/usr/bin/env python3
"""Web reader for Daily Knowledge Digest.

Serves a local HTTP server accessible from Windows at http://localhost:8080.
MathJax renders LaTeX; callout boxes and wikilinks are fully styled.

Usage:
    python3 scripts/serve_web.py
    python3 scripts/serve_web.py --port 9000
"""

import argparse
import html
import re
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from config import DAILY_DIR
from read_today import (
    extract_topic_ids,
    find_topic_file,
    parse_frontmatter,
    strip_embedded_frontmatter,
    strip_h1,
    unwrap_code_fence,
)

# ---------------------------------------------------------------------------
# HTML page template
# ---------------------------------------------------------------------------

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script>
MathJax = {{
  tex: {{
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']],
    processEscapes: true
  }},
  options: {{ skipHtmlTags: ['script','noscript','style','textarea','pre'] }}
}};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>document.addEventListener('DOMContentLoaded', () => hljs.highlightAll());</script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #1a1a2e;
    color: #e0e0f0;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 17px;
    line-height: 1.7;
    padding: 2rem 1rem;
  }}
  .page {{ max-width: 820px; margin: 0 auto; }}
  /* Header */
  .digest-header {{
    border: 2px solid #4a9eff;
    border-radius: 8px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.8rem;
    background: #0d1b35;
  }}
  .digest-header h1 {{
    font-size: 1.4rem;
    color: #4a9eff;
    margin-bottom: 0.3rem;
  }}
  .digest-header .meta {{ color: #8898bb; font-size: 0.95rem; }}
  /* Topic nav */
  .topic-nav {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 2rem;
  }}
  .topic-nav a {{
    background: #1e2a45;
    color: #7ec8ff;
    text-decoration: none;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.88rem;
    border: 1px solid #2e4a6e;
    transition: background 0.15s;
  }}
  .topic-nav a:hover {{ background: #2a3d5e; }}
  /* Topic article */
  article {{
    margin-bottom: 3.5rem;
    scroll-margin-top: 1rem;
  }}
  .topic-header {{
    border-left: 4px solid #4a9eff;
    padding: 0.8rem 1rem;
    background: #111828;
    border-radius: 0 6px 6px 0;
    margin-bottom: 1.4rem;
  }}
  .topic-header h2 {{
    color: #7ec8ff;
    font-size: 1.3rem;
    margin-bottom: 0.25rem;
  }}
  .topic-header .topic-meta {{ color: #7a8db0; font-size: 0.88rem; }}
  /* Back link */
  .back-link {{
    display: inline-block;
    margin-bottom: 1.5rem;
    color: #7ec8ff;
    text-decoration: none;
    font-size: 0.92rem;
  }}
  .back-link:hover {{ text-decoration: underline; }}
  /* Body typography */
  .body h2 {{
    color: #4a9eff;
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 1.6rem 0 0.6rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid #2a3d5e;
  }}
  .body h3 {{
    color: #c5d8f5;
    font-size: 1.05rem;
    margin: 1.2rem 0 0.4rem;
  }}
  .body p {{ margin: 0.7rem 0; }}
  .body strong {{ color: #fff; }}
  .body em {{ color: #c9d8f0; font-style: italic; }}
  .body a {{ color: #7ec8ff; text-decoration: none; }}
  .body a:hover {{ text-decoration: underline; }}
  .body hr {{ border: none; border-top: 1px solid #2a3d5e; margin: 1.4rem 0; }}
  .body ul, .body ol {{ margin: 0.6rem 0 0.6rem 1.6rem; }}
  .body li {{ margin: 0.25rem 0; }}
  .body blockquote {{
    border-left: 3px solid #3a5070;
    padding: 0.4rem 1rem;
    color: #8898bb;
    margin: 0.8rem 0;
    font-style: italic;
  }}
  /* Callouts */
  .callout {{
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin: 1rem 0;
  }}
  .callout .callout-title {{
    font-weight: bold;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }}
  .callout.info  {{ background: #0a1f3a; border-left: 4px solid #4a9eff; }}
  .callout.info  .callout-title {{ color: #4a9eff; }}
  .callout.tip   {{ background: #1e1a00; border-left: 4px solid #f0d060; }}
  .callout.tip   .callout-title {{ color: #f0d060; }}
  .callout.warning {{ background: #2a0a0a; border-left: 4px solid #ff6060; }}
  .callout.warning .callout-title {{ color: #ff6060; }}
  /* Code */
  .body pre {{
    border-radius: 6px;
    overflow-x: auto;
    margin: 1rem 0;
    font-size: 0.9rem;
  }}
  .body code:not(pre code) {{
    background: #1e2a45;
    color: #a8cfff;
    padding: 0.1em 0.35em;
    border-radius: 3px;
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 0.88em;
  }}
  /* Single topic page */
  .single-topic article {{ margin-bottom: 0; }}
</style>
</head>
<body>
<div class="page">
{body}
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Markdown → HTML renderer
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    """HTML-escape while preserving LaTeX delimiters."""
    return html.escape(s, quote=False)


def render_inline_html(text: str) -> str:
    """Convert inline Markdown to HTML, keeping LaTeX intact."""
    # Protect LaTeX from further processing by temporarily replacing $ spans
    # We do substitutions in order: display math, inline math, then Markdown.

    placeholders: list[str] = []

    def stash(match_text: str) -> str:
        key = f"\x00MATH{len(placeholders)}\x00"
        placeholders.append(match_text)
        return key

    # Stash display math $$...$$
    text = re.sub(r'\$\$(.+?)\$\$', lambda m: stash(m.group(0)), text, flags=re.DOTALL)
    # Stash inline math $...$
    text = re.sub(r'\$([^$\n]+?)\$', lambda m: stash(m.group(0)), text)

    # [[link|alias]] → internal link
    text = re.sub(
        r'\[\[([^\]|]+)\|([^\]]+)\]\]',
        lambda m: f'<a href="/topic/{_esc(m.group(1).strip())}">{_esc(m.group(2).strip())}</a>',
        text,
    )
    # [[link]] → internal link
    text = re.sub(
        r'\[\[([^\]]+)\]\]',
        lambda m: f'<a href="/topic/{_esc(m.group(1).strip())}">{_esc(m.group(1).strip())}</a>',
        text,
    )
    # [text](url) → external link
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        lambda m: f'<a href="{_esc(m.group(2))}" target="_blank" rel="noopener">{_esc(m.group(1))}</a>',
        text,
    )
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<strong>{_esc(m.group(1))}</strong>', text)
    # *italic*
    text = re.sub(r'\*(.+?)\*', lambda m: f'<em>{_esc(m.group(1))}</em>', text)
    # `inline code`
    text = re.sub(r'`([^`]+)`', lambda m: f'<code>{_esc(m.group(1))}</code>', text)

    # Restore LaTeX placeholders (un-escaped, passed through for MathJax)
    for i, orig in enumerate(placeholders):
        text = text.replace(f"\x00MATH{i}\x00", orig)

    return text


def render_body_html(body: str) -> str:
    """Convert full Markdown body to an HTML string."""
    lines = body.splitlines()
    out: list[str] = []
    i = 0

    # State for open list tags
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]

        # --- HR ---
        if re.match(r'^---+\s*$', line):
            close_lists()
            out.append('<hr>')
            i += 1
            continue

        # --- Display math block $$...$$ on its own line ---
        if line.strip().startswith('$$') and not line.strip() == '$$':
            close_lists()
            out.append(f'<p>{line.strip()}</p>')
            i += 1
            continue
        if line.strip() == '$$':
            close_lists()
            math_lines = ['$$']
            i += 1
            while i < len(lines) and lines[i].strip() != '$$':
                math_lines.append(lines[i])
                i += 1
            math_lines.append('$$')
            i += 1  # consume closing $$
            out.append('<p>' + '\n'.join(math_lines) + '</p>')
            continue

        # --- Code fence ---
        if line.startswith('```'):
            close_lists()
            lang = line[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            lang_attr = f' class="language-{html.escape(lang)}"' if lang else ''
            out.append(f'<pre><code{lang_attr}>{html.escape(chr(10).join(code_lines))}</code></pre>')
            continue

        # --- Callout block > [!type] title ---
        callout_m = re.match(r'^>\s*\[!(info|tip|warning)\]\s*(.*)', line, re.IGNORECASE)
        if callout_m:
            close_lists()
            label = callout_m.group(1).lower()
            title = callout_m.group(2).strip()
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith('>'):
                body_lines.append(lines[i].lstrip('> ').lstrip())
                i += 1
            title_html = f'<div class="callout-title">{_esc(label.upper())}{": " + _esc(title) if title else ""}</div>'
            content_html = render_inline_html(' '.join(body_lines))
            out.append(f'<div class="callout {label}">{title_html}<div>{content_html}</div></div>')
            continue

        # --- Plain blockquote ---
        if line.startswith('>'):
            close_lists()
            content = line.lstrip('> ').lstrip()
            out.append(f'<blockquote><p>{render_inline_html(content)}</p></blockquote>')
            i += 1
            continue

        # --- H2 ---
        if line.startswith('## '):
            close_lists()
            out.append(f'<h2>{_esc(line[3:].strip())}</h2>')
            i += 1
            continue

        # --- H3 ---
        if line.startswith('### '):
            close_lists()
            out.append(f'<h3>{_esc(line[4:].strip())}</h3>')
            i += 1
            continue

        # --- Unordered list ---
        ul_m = re.match(r'^(\s*)[-*]\s+(.*)', line)
        if ul_m:
            if not in_ul:
                if in_ol:
                    out.append('</ol>')
                    in_ol = False
                out.append('<ul>')
                in_ul = True
            out.append(f'<li>{render_inline_html(ul_m.group(2))}</li>')
            i += 1
            continue

        # --- Ordered list ---
        ol_m = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if ol_m:
            if not in_ol:
                if in_ul:
                    out.append('</ul>')
                    in_ul = False
                out.append('<ol>')
                in_ol = True
            out.append(f'<li>{render_inline_html(ol_m.group(2))}</li>')
            i += 1
            continue

        # --- Blank line ---
        if line.strip() == '':
            close_lists()
            out.append('')
            i += 1
            continue

        # --- Prose paragraph ---
        close_lists()
        out.append(f'<p>{render_inline_html(line)}</p>')
        i += 1

    close_lists()
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def _read_time_str(fm: dict) -> str:
    rt = fm.get('read_time_minutes', '?')
    return f'~{rt} min read'


def build_digest_page(run_date: date) -> tuple[str, int]:
    """Return (html_string, status_code)."""
    daily_path = DAILY_DIR / f'{run_date.isoformat()}.md'
    if not daily_path.exists():
        body = f'<p style="color:#ff6060">No digest found for {run_date.isoformat()}.</p>'
        return PAGE_TEMPLATE.format(title='Not Found', body=body), 404

    daily_text = daily_path.read_text(encoding='utf-8')
    topic_ids = extract_topic_ids(daily_text)

    topics: list[tuple[str, dict, str]] = []  # (id, fm, body)
    total_min = 0
    for tid in topic_ids:
        path = find_topic_file(tid)
        if path is None:
            continue
        raw = path.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(raw)
        body = strip_h1(body)
        body = unwrap_code_fence(body)
        body = strip_embedded_frontmatter(body)
        total_min += int(fm.get('read_time_minutes', 0))
        topics.append((tid, fm, body))

    if not topics:
        body = '<p style="color:#ff6060">No topics could be loaded.</p>'
        return PAGE_TEMPLATE.format(title='Empty Digest', body=body), 200

    date_str = run_date.strftime('%B %-d, %Y')
    n = len(topics)

    sections: list[str] = []

    # Header
    sections.append(
        f'<div class="digest-header">'
        f'<h1>Daily Knowledge Digest</h1>'
        f'<div class="meta">{html.escape(date_str)} &nbsp;·&nbsp; {n} topics &nbsp;·&nbsp; ~{total_min} min</div>'
        f'</div>'
    )

    # Nav pills
    nav_items = ''.join(
        f'<a href="#{html.escape(tid)}">{html.escape(fm.get("title", tid))}</a>'
        for tid, fm, _ in topics
    )
    sections.append(f'<nav class="topic-nav">{nav_items}</nav>')

    # Articles
    for idx, (tid, fm, body) in enumerate(topics, 1):
        title = fm.get('title', tid)
        category = fm.get('category', '')
        subcat = fm.get('subcategory', '')
        cat_str = f'{category} · {subcat}' if subcat else category
        rt = _read_time_str(fm)

        meta_parts = [html.escape(cat_str)] if cat_str else []
        meta_parts.append(html.escape(rt))
        meta_html = ' &nbsp;·&nbsp; '.join(meta_parts)

        sections.append(
            f'<article id="{html.escape(tid)}">'
            f'<div class="topic-header">'
            f'<h2>{html.escape(title)}</h2>'
            f'<div class="topic-meta">{meta_html}</div>'
            f'</div>'
            f'<div class="body">{render_body_html(body)}</div>'
            f'</article>'
        )

    page_body = '\n'.join(sections)
    page_title = f'Daily Digest — {date_str}'
    return PAGE_TEMPLATE.format(title=page_title, body=page_body), 200


def build_topic_page(topic_id: str, digest_date: date | None = None) -> tuple[str, int]:
    """Return (html_string, status_code)."""
    path = find_topic_file(topic_id)
    if path is None:
        body = f'<p style="color:#ff6060">Topic not found: {html.escape(topic_id)}</p>'
        return PAGE_TEMPLATE.format(title='Not Found', body=body), 404

    raw = path.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(raw)
    body = strip_h1(body)
    body = unwrap_code_fence(body)
    body = strip_embedded_frontmatter(body)

    title = fm.get('title', topic_id)
    category = fm.get('category', '')
    subcat = fm.get('subcategory', '')
    cat_str = f'{category} · {subcat}' if subcat else category
    rt = _read_time_str(fm)

    meta_parts = [html.escape(cat_str)] if cat_str else []
    meta_parts.append(html.escape(rt))
    meta_html = ' &nbsp;·&nbsp; '.join(meta_parts)

    back_href = f'/digests/{digest_date.isoformat()}/' if digest_date else '/'
    sections = [
        '<div class="single-topic">',
        f'<a class="back-link" href="{back_href}">← Back to digest</a>',
        f'<article>',
        f'<div class="topic-header">',
        f'<h2>{html.escape(title)}</h2>',
        f'<div class="topic-meta">{meta_html}</div>',
        f'</div>',
        f'<div class="body">{render_body_html(body)}</div>',
        f'</article>',
        '</div>',
    ]

    page_body = '\n'.join(sections)
    return PAGE_TEMPLATE.format(title=html.escape(title), body=page_body), 200


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class DigestHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # noqa: N802
        print(f'  {self.address_string()} — {fmt % args}')

    def send_html(self, content: str, status: int = 200):
        encoded = content.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # --- Digest page ---
        if path == '/':
            date_param = qs.get('date', [None])[0]
            if date_param:
                try:
                    run_date = date.fromisoformat(date_param)
                except ValueError:
                    self.send_html('<p>Invalid date format. Use ?date=YYYY-MM-DD</p>', 400)
                    return
            else:
                run_date = date.today()
            content, status = build_digest_page(run_date)
            self.send_html(content, status)
            return

        # --- Single topic page ---
        topic_m = re.match(r'^/topic/([^/]+)$', path)
        if topic_m:
            topic_id = topic_m.group(1)
            content, status = build_topic_page(topic_id)
            self.send_html(content, status)
            return

        # --- 404 ---
        self.send_html('<p>Not found.</p>', 404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Web reader for Daily Knowledge Digest')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    args = parser.parse_args()

    server = HTTPServer(('0.0.0.0', args.port), DigestHandler)
    print(f'Serving Daily Knowledge Digest at http://localhost:{args.port}')
    print('Press Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
        server.server_close()


if __name__ == '__main__':
    main()
