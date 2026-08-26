import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup
# ============================================================
# SNIPPET24 NEWS CURATOR
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"
MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100
CATEGORIES = [
    "World",
    "India",
    "Business",
    "Technology",
    "Lifestyle"
]
USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/2.0; "
    "+https://snippet24.in)"
)
HEADERS = {
    "User-Agent": USER_AGENT
}
# ============================================================
# HELPERS
# ============================================================
def clean_text(value):
    if not value:
        return ""
    value = html.unescape(str(value))
    soup = BeautifulSoup(value, "html.parser")
    value = soup.get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value).strip()
    return value
def normalize_text(value):
    value = clean_text(value).lower()
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]
def parse_date(entry):
    possible_dates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created")
    ]
    for value in possible_dates:
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()
def get_publisher(entry):
    publisher = entry.get("source")
    if isinstance(publisher, dict):
        publisher = publisher.get("title")
    if not publisher:
        publisher = entry.get("publisher")
    if not publisher:
        publisher = entry.get("author")
    if not publisher:
        return "Unknown source"
    return clean_text(publisher)
def get_url(entry):
    url = entry.get("link")
    if url:
        return url.strip()
    links = entry.get("links", [])
    for item in links:
        href = item.get("href")
        if href:
            return href.strip()
    return ""
def get_raw_description(entry):
    values = [
        entry.get("summary"),
        entry.get("description"),
        entry.get("content", [{}])[0].get("value")
        if entry.get("content")
        else ""
    ]
    for value in values:
        value = clean_text(value)
        if value:
            return value
    return ""
# ============================================================
# REMOVE RSS SUFFIXES FROM HEADLINES
# ============================================================
def clean_headline(title, publisher):
    title = clean_text(title)
    if not title:
        return ""
    # Remove common RSS suffixes.
    patterns = [
        r"\s*\|\s*" + re.escape(publisher) + r"\s*$",
        r"\s*-\s*" + re.escape(publisher) + r"\s*$",
        r"\s*\|\s*.*?\s*$"
    ]
    for pattern in patterns:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    # Remove accidental duplicate publisher names.
    title = re.sub(
        r"\s+(Hindustan Times|Business Standard|Firstpost|Reuters|"
        r"NDTV|The Hindu|Indian Express|News18|Times of India)\s*$",
        "",
        title,
        flags=re.IGNORECASE
    )
    return title.strip(" -|")
# ============================================================
# DETECT BAD / REPEATED RSS DESCRIPTIONS
# ============================================================
def description_is_bad(title, description):
    if not description:
        return True
    t = normalize_text(title)
    d = normalize_text(description)
    if not d:
        return True
    # Description is basically the headline.
    if t == d:
        return True
    # Description starts with the entire headline.
    if len(t) > 35 and d.startswith(t):
        remainder = d[len(t):].strip()
        if len(remainder) < 60:
            return True
    # Very short descriptions are generally useless.
    if len(d.split()) < 12:
        return True
    return False
# ============================================================
# CREATE A REAL SUMMARY
# ============================================================
def create_summary(title, description):
    """
    Prefer the RSS description when it contains actual information.
    Never return a description that merely repeats the headline.
    """
    title_clean = clean_text(title)
    description_clean = clean_text(description)
    if description_clean and not description_is_bad(
        title_clean,
        description_clean
    ):
        # Remove publisher repetition at the end.
        description_clean = re.sub(
            r"\s*(\||-)\s*[A-Za-z0-9 .&']+$",
            "",
            description_clean
        ).strip()
        # Limit excessive length.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            description_clean
        )
        sentences = [
            s.strip()
            for s in sentences
            if s.strip()
        ]
        if sentences:
            summary = " ".join(sentences[:3])
            if len(summary) > 500:
                summary = summary[:497].rsplit(" ", 1)[0] + "..."
            return summary
    # If RSS gives no useful summary, do NOT duplicate headline.
    return (
        "This story is being reported by the original publication. "
        "Read the original article for the latest details and full context."
    )
# ============================================================
# CATEGORY DETECTION
# ============================================================
def detect_category(title, description, source_category=""):
    text = normalize_text(
        f"{title} {description} {source_category}"
    )
    # India
    india_words = [
        "india",
        "indian",
        "new delhi",
        "mumbai",
        "chennai",
        "bengaluru",
        "hyderabad",
        "kolkata",
        "supreme court india",
        "parliament india",
        "modi",
        "sitharaman"
    ]
    # Technology
    technology_words = [
        "technology",
        "tech",
        "artificial intelligence",
        "ai",
        "openai",
        "google ai",
        "microsoft",
        "apple",
        "iphone",
        "cyber",
        "software",
        "chip",
        "semiconductor",
        "robot"
    ]
    # Business
    business_words = [
        "business",
        "economy",
        "economic",
        "market",
        "markets",
        "stocks",
        "stock",
        "investment",
        "investor",
        "company",
        "companies",
        "bank",
        "banking",
        "trade",
        "finance",
        "financial",
        "revenue",
        "profit",
        "ipo"
    ]
    # Lifestyle
    lifestyle_words = [
        "lifestyle",
        "health",
        "travel",
        "food",
        "fashion",
        "culture",
        "entertainment",
        "movie",
        "music",
        "celebrity",
        "wellness",
        "relationship"
    ]
    if any(word in text for word in technology_words):
        return "Technology"
    if any(word in text for word in business_words):
        return "Business"
    if any(word in text for word in lifestyle_words):
        return "Lifestyle"
    if any(word in text for word in india_words):
        return "India"
    return "World"
# ============================================================
# LOAD SOURCES
# ============================================================
def load_sources():
    if not SOURCES_FILE.exists():
        print("ERROR: sources.json not found")
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("sources", [])
    except Exception as e:
        print("ERROR loading sources.json:", e)
    return []
# ============================================================
# LOAD EXISTING ARTICLES
# ============================================================
def load_articles():
    if not ARTICLES_FILE.exists():
        return {
            "version": 2,
            "updated_at": "",
            "categories": {
                category: []
                for category in CATEGORIES
            }
        }
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "categories" not in data:
            data["categories"] = {}
        for category in CATEGORIES:
            if category not in data["categories"]:
                data["categories"][category] = []
        return data
    except Exception as e:
        print("ERROR loading articles.json:", e)
        return {
            "version": 2,
            "updated_at": "",
            "categories": {
                category: []
                for category in CATEGORIES
            }
        }
# ============================================================
# FETCH RSS
# ============================================================
def fetch_feed(source):
    if isinstance(source, str):
        url = source
        source_name = "Unknown source"
        source_category = ""
    else:
        url = (
            source.get("url")
            or source.get("rss")
            or source.get("feed")
            or ""
        )
        source_name = (
            source.get("name")
            or source.get("publisher")
            or source.get("title")
            or "Unknown source"
        )
        source_category = source.get("category", "")
    if not url:
        return []
    print(f"Fetching: {source_name}")
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        articles = []
        for entry in feed.entries:
            title = clean_headline(
                entry.get("title", ""),
                source_name
            )
            if not title:
                continue
            url = get_url(entry)
            if not url:
                continue
            raw_description = get_raw_description(entry)
            summary = create_summary(
                title,
                raw_description
            )
            category = detect_category(
                title,
                raw_description,
                source_category
            )
            publisher = get_publisher(entry)
            if publisher == "Unknown source":
                publisher = clean_text(source_name)
            article = {
                "id": make_id(title, url),
                "category": category,
                "title": title,
                "summary": summary,
                "publisher": publisher,
                "published_at": parse_date(entry),
                "url": url,
                "language": "en-IN"
            }
            articles.append(article)
        return articles
    except Exception as e:
        print(f"ERROR fetching {source_name}: {e}")
        return []
# ============================================================
# ADD ARTICLES
# ============================================================
def add_articles(data, new_articles):
    existing_ids = set()
    for category in CATEGORIES:
        for article in data["categories"].get(category, []):
            if article.get("id"):
                existing_ids.add(article["id"])
    added = 0
    for article in new_articles:
        article_id = article["id"]
        if article_id in existing_ids:
            continue
        category = article["category"]
        if category not in CATEGORIES:
            category = "World"
        article["category"] = category
        data["categories"][category].append(article)
        existing_ids.add(article_id)
        added += 1
    return added
# ============================================================
# SORT + FIFO
# ============================================================
def sort_and_fifo(data):
    for category in CATEGORIES:
        articles = data["categories"].get(category, [])
        # Newest first.
        articles.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True
        )
        # Keep maximum 100.
        data["categories"][category] = articles[
            :MAXIMUM_PER_CATEGORY
        ]
# ============================================================
# SAVE
# ============================================================
def save_articles(data):
    data["version"] = 2
    data["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    temp_file = ARTICLES_FILE.with_suffix(".tmp")
    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
    temp_file.replace(ARTICLES_FILE)
# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 60)
    sources = load_sources()
    if not sources:
        print("ERROR: No RSS sources found.")
        return 1
    data = load_articles()
    all_new_articles = []
    for source in sources:
        articles = fetch_feed(source)
        all_new_articles.extend(articles)
        time.sleep(0.25)
    print()
    print(f"Fetched articles: {len(all_new_articles)}")
    added = add_articles(
        data,
        all_new_articles
    )
    print(f"New articles added: {added}")
    sort_and_fifo(data)
    save_articles(data)
    print()
    print("=" * 60)
    print("FINAL ARTICLE COUNTS")
    print("=" * 60)
    total = 0
    for category in CATEGORIES:
        count = len(
            data["categories"].get(category, [])
        )
        total += count
        print(
            f"{category}: {count}"
        )
        if count < MINIMUM_PER_CATEGORY:
            print(
                f"WARNING: {category} has fewer than "
                f"{MINIMUM_PER_CATEGORY} articles"
            )
    print()
    print(f"TOTAL: {total}")
    print(f"Saved: {ARTICLES_FILE}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())