import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from config import TOPIC_QUEUE_FILE, COOLDOWN_DAYS


def load_queue() -> dict:
    if not TOPIC_QUEUE_FILE.exists():
        return _bootstrap_queue()
    with open(TOPIC_QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue: dict) -> None:
    TOPIC_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOPIC_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2, default=str)


def _bootstrap_queue() -> dict:
    seed_file = Path(__file__).parent / "seed_topics.json"
    with open(seed_file) as f:
        seed_topics = json.load(f)
    queue = {
        "version": "1.0",
        "last_run": None,
        "pointer": 0,
        "cooldown_days": COOLDOWN_DAYS,
        "topics": seed_topics,
    }
    save_queue(queue)
    return queue


def select_topics(n: int) -> list[dict]:
    queue = load_queue()
    today = date.today()
    cutoff = today - timedelta(days=queue["cooldown_days"])

    eligible = []
    for t in queue["topics"]:
        if t["last_covered"] is None:
            eligible.append(t)
        else:
            last = date.fromisoformat(t["last_covered"])
            if last <= cutoff:
                eligible.append(t)

    # Sort: priority ascending (1=high), then never-covered first, then oldest covered first
    def sort_key(t):
        if t["last_covered"] is None:
            recency = date.min.isoformat()
        else:
            recency = t["last_covered"]
        return (t["priority"], recency)

    eligible.sort(key=sort_key)
    return eligible[:n]


def mark_covered(topic_ids: list[str]) -> None:
    queue = load_queue()
    today = date.today().isoformat()
    for t in queue["topics"]:
        if t["id"] in topic_ids:
            t["last_covered"] = today
    queue["last_run"] = today
    save_queue(queue)


def add_topic(topic: dict) -> None:
    queue = load_queue()
    existing_ids = {t["id"] for t in queue["topics"]}
    if topic["id"] not in existing_ids:
        queue["topics"].append(topic)
        save_queue(queue)
