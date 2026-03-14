import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Optional
import requests
import feedparser
from config import WOLFRAM_APP_ID, STALENESS_THRESHOLD_FAST_MONTHS, STALENESS_THRESHOLD_SLOW_YEARS, FAST_MOVING_FIELDS

USER_AGENT = "DailyKnowledgeBot/1.0 (personal Obsidian vault; contact: dhein@localhost)"

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
ARXIV_API = "http://export.arxiv.org/api/query"
WOLFRAM_API = "http://api.wolframalpha.com/v1/result"


def fetch_wikipedia(title: str) -> Optional[dict]:
    try:
        params = {
            "action": "query",
            "prop": "extracts|revisions",
            "exintro": True,
            "explaintext": True,
            "rvprop": "timestamp",
            "rvlimit": 1,
            "titles": title,
            "format": "json",
        }
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(WIKIPEDIA_API, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        if "missing" in page:
            return None
        extract = page.get("extract", "")
        revisions = page.get("revisions", [{}])
        last_edited = revisions[0].get("timestamp", "") if revisions else ""
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        categories = [c.get("title", "").replace("Category:", "") for c in page.get("categories", [])]
        # Parse last_edited date
        last_edited_date = None
        if last_edited:
            try:
                last_edited_date = datetime.fromisoformat(last_edited.rstrip("Z")).date().isoformat()
            except ValueError:
                pass
        return {
            "title": page.get("title", title),
            "extract": extract,
            "url": url,
            "last_edited_date": last_edited_date,
            "categories": categories,
        }
    except Exception:
        return None


def fetch_arxiv(query: str, max_results: int = 3) -> Optional[list[dict]]:
    try:
        params = {
            "search_query": f"all:{query}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
        resp = requests.get(ARXIV_API, params=params, timeout=15)
        resp.raise_for_status()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)
        results = []
        for entry in root.findall("atom:entry", ns):
            arxiv_id_url = entry.findtext("atom:id", default="", namespaces=ns)
            arxiv_id = arxiv_id_url.split("/abs/")[-1] if "/abs/" in arxiv_id_url else arxiv_id_url
            published_raw = entry.findtext("atom:published", default="", namespaces=ns)
            published_date = None
            if published_raw:
                try:
                    published_date = datetime.fromisoformat(published_raw.rstrip("Z")).date().isoformat()
                except ValueError:
                    pass
            authors = [
                a.findtext("atom:name", default="", namespaces=ns)
                for a in entry.findall("atom:author", ns)
            ]
            results.append({
                "title": (entry.findtext("atom:title", default="", namespaces=ns) or "").strip().replace("\n", " "),
                "abstract": (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip().replace("\n", " "),
                "authors": authors[:5],
                "published_date": published_date,
                "arxiv_id": arxiv_id,
                "url": arxiv_id_url,
            })
        return results if results else None
    except Exception:
        return None


def fetch_rss_feed(url: str, max_items: int = 5) -> Optional[list[dict]]:
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return None
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return items if items else None
    except Exception:
        return None


def fetch_wolfram_short(query: str) -> Optional[str]:
    if not WOLFRAM_APP_ID:
        return None
    try:
        params = {"i": query, "appid": WOLFRAM_APP_ID}
        resp = requests.get(WOLFRAM_API, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.text.strip()
        return None
    except Exception:
        return None


def assess_staleness(source_date_str: Optional[str], category: str, pace: str) -> str:
    if not source_date_str:
        return "uncertain"
    try:
        source_date = date.fromisoformat(source_date_str)
    except ValueError:
        return "uncertain"
    today = date.today()
    age_months = (today.year - source_date.year) * 12 + (today.month - source_date.month)

    is_fast = pace == "fast" or category in FAST_MOVING_FIELDS
    if is_fast:
        threshold_months = STALENESS_THRESHOLD_FAST_MONTHS
        if age_months > threshold_months:
            return "outdated"
    else:
        threshold_months = STALENESS_THRESHOLD_SLOW_YEARS * 12
        if age_months > threshold_months:
            return "outdated"
    return "current"
