import os
from pathlib import Path

VAULT_ROOT = Path("/home/dhein/projects/knowledge")

DAILY_DIR = VAULT_ROOT / "Daily"
TOPICS_DIR = VAULT_ROOT / "Topics"
META_DIR = VAULT_ROOT / "Meta"
SCRIPTS_DIR = VAULT_ROOT / "scripts"

TOPIC_QUEUE_FILE = META_DIR / "topic-queue.json"
TOPIC_HISTORY_FILE = META_DIR / "topic-history.json"
SYSTEM_LOG_FILE = META_DIR / "system-log.md"
CRON_LOG_FILE = META_DIR / "cron.log"

WOLFRAM_APP_ID = os.environ.get("WOLFRAM_APP_ID")

CLAUDE_MODEL = "claude-sonnet-4-6"
USER_AGENT = "DailyKnowledgeBot/1.0 (personal Obsidian vault; contact: dhein@localhost)"

TOPICS_PER_DAY = 4
COOLDOWN_DAYS = 60
MAX_WIKIPEDIA_CHARS = 3000
ARXIV_MAX_RESULTS = 3
RETRY_DELAY_SECONDS = 30

FAST_MOVING_FIELDS = {
    "Tech", "AI", "Machine Learning", "Quantum Computing",
    "Genomics", "Biotechnology", "Cryptography"
}

STALENESS_THRESHOLD_FAST_MONTHS = 18
STALENESS_THRESHOLD_SLOW_YEARS = 5

CATEGORY_DIRS = {
    "Science": TOPICS_DIR / "Science",
    "Tech": TOPICS_DIR / "Tech",
    "Math": TOPICS_DIR / "Math",
    "Logic": TOPICS_DIR / "Logic",
}
