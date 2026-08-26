import json
import hashlib
import html
import re
import time
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests


BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = 0.25


USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Snippet24NewsBot/1.0; +https://snippet24.in)"
)


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_title(value):
    value = clean_text(value)

    # Google News sometimes adds " - Source"
    # We keep the title clean but do not aggressively modify it.
    return value


# ---------------------------------------------------------
# ID
# ---------------------------------------------------------

def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:24]


# ---------------------------------------------------------
# DATE
# ---------------------------------------------------------

def parse_date(entry):
    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created")
    ]

    for value in candidates:
        if not value:
            continue

        try:
            dt = parsedate_to_datetime(value)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).isoformat()

        except Exception:
            pass

    return now_iso()


# ---------------------------------------------------------
# GOOGLE NEWS RSS
# ---------------------------------------------------------

def google_news_url(query):
    encoded = quote_plus(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


# ---------------------------------------------------------
# RSS FETCH
# ---------------------------------------------------------

def fetch_feed(query):
    url = google_news_url(query)

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        return feed.entries

    except Exception as error:
        print(f"RSS ERROR: {query}")
        print(error)

        return []


# ---------------------------------------------------------
# SOURCE EXTRACTION
# ---------------------------------------------------------

def get_source(entry):
    source = entry.get("source")

    if isinstance(source, dict):
        return clean_text(source.get("title", ""))

    if source:
        return clean_text(source)

    # Google News sometimes includes source in title.
    title = clean_title(entry.get("title", ""))

    parts = title.split(" - ")

    if len(parts) >= 2:
        return parts[-1].strip()

    return "Google News"


# ---------------------------------------------------------
# URL
# ---------------------------------------------------------

def get_url(entry):
    url = entry.get("link")

    if not url:
        url = entry.get("id", "")

    return str(url).strip()


# ---------------------------------------------------------
# ARTICLE CONVERSION
# ---------------------------------------------------------

def entry_to_article(entry, category, query):
    title = clean_title(entry.get("title", ""))

    url = get_url(entry)

    if not title or not url:
        return None

    source = get_source(entry)

    published_at = parse_date(entry)

    description = clean_text(
        entry.get("summary")
        or entry.get("description")
        or title
    )

    # Keep descriptions short.
    if len(description) > 500:
        description = description[:497] + "..."

    article_id = make_id(title, url)

    return {
        "id": article_id,
        "title": title,
        "description": description,
        "url": url,
        "source": source,
        "category": category,
        "query": query,
        "published_at": published_at,
        "fetched_at": now_iso()
    }


# ---------------------------------------------------------
# LOAD OLD ARTICLES
# ---------------------------------------------------------

def load_existing():
    if not ARTICLES_FILE.exists():
        return {
            "version": 1,
            "updated_at": now_iso(),
            "minimum_per_category": MINIMUM_PER_CATEGORY,
            "maximum_per_category": MAXIMUM_PER_CATEGORY,
            "fifo": True,
            "categories": {}
        }

    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("articles.json is not an object")

        data.setdefault("categories", {})

        return data

    except Exception as error:
        print("Could not read existing articles.json:")
        print(error)

        return {
            "version": 1,
            "updated_at": now_iso(),
            "minimum_per_category": MINIMUM_PER_CATEGORY,
            "maximum_per_category": MAXIMUM_PER_CATEGORY,
            "fifo": True,
            "categories": {}
        }


# ---------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------

def deduplicate_articles(articles):
    result = []

    seen_ids = set()
    seen_urls = set()

    for article in articles:

        article_id = article.get("id", "")
        url = article.get("url", "")

        if not article_id or not url:
            continue

        if article_id in seen_ids:
            continue

        if url in seen_urls:
            continue

        seen_ids.add(article_id)
        seen_urls.add(url)

        result.append(article)

    return result


# ---------------------------------------------------------
# FETCH CATEGORY
# ---------------------------------------------------------

def fetch_category(category, queries):
    collected = []

    print()
    print("=" * 60)
    print(f"CATEGORY: {category}")
    print("=" * 60)

    for query in queries:

        print(f"Fetching: {query}")

        entries = fetch_feed(query)

        print(f"  Found: {len(entries)}")

        for entry in entries:

            article = entry_to_article(
                entry,
                category,
                query
            )

            if article:
                collected.append(article)

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    collected = deduplicate_articles(collected)

    # Newest first.
    collected.sort(
        key=lambda item: item.get("published_at", ""),
        reverse=True
    )

    print(
        f"{category}: {len(collected)} unique articles"
    )

    return collected


# ---------------------------------------------------------
# FIFO MERGE
# ---------------------------------------------------------

def merge_fifo(existing, fresh):
    """
    Keep old articles first and append new articles.

    When more than MAXIMUM_PER_CATEGORY exists,
    remove the oldest items from the beginning.

    This provides a FIFO-style rolling buffer.
    """

    existing = deduplicate_articles(existing)
    fresh = deduplicate_articles(fresh)

    existing_ids = {
        item.get("id")
        for item in existing
    }

    existing_urls = {
        item.get("url")
        for item in existing
    }

    new_articles = []

    for article in fresh:

        if article.get("id") in existing_ids:
            continue

        if article.get("url") in existing_urls:
            continue

        new_articles.append(article)

        existing_ids.add(article.get("id"))
        existing_urls.add(article.get("url"))

    combined = existing + new_articles

    # FIFO:
    # Oldest entries are removed when limit is exceeded.
    if len(combined) > MAXIMUM_PER_CATEGORY:
        combined = combined[-MAXIMUM_PER_CATEGORY:]

    return combined


# ---------------------------------------------------------
# ENSURE MINIMUM
# ---------------------------------------------------------

def ensure_minimum(category, articles, queries):
    """
    Try to guarantee at least 50 articles.

    Google News may return fewer articles for a query,
    so all configured queries are used.
    """

    if len(articles) >= MINIMUM_PER_CATEGORY:
        return articles

    print(
        f"{category}: only {len(articles)} articles. "
        f"Trying additional collection..."
    )

    additional = []

    for query in queries:

        entries = fetch_feed(query)

        for entry in entries:

            article = entry_to_article(
                entry,
                category,
                query
            )

            if article:
                additional.append(article)

        time.sleep(SLEEP_BETWEEN_REQUESTS)

        current = deduplicate_articles(
            articles + additional
        )

        if len(current) >= MINIMUM_PER_CATEGORY:
            break

    return deduplicate_articles(
        articles + additional
    )


# ---------------------------------------------------------
# BUILD DATABASE
# ---------------------------------------------------------

def build_database():

    print()
    print("==============================================")
    print("        SNIPPET24 NEWS CURATOR")
    print("==============================================")
    print()

    with open(
        SOURCES_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    minimum = int(
        config.get(
            "minimum_per_category",
            MINIMUM_PER_CATEGORY
        )
    )

    maximum = int(
        config.get(
            "maximum_per_category",
            MAXIMUM_PER_CATEGORY
        )
    )

    global MINIMUM_PER_CATEGORY
    global MAXIMUM_PER_CATEGORY

    MINIMUM_PER_CATEGORY = minimum
    MAXIMUM_PER_CATEGORY = maximum

    source_categories = config.get(
        "categories",
        {}
    )

    existing_database = load_existing()

    existing_categories = existing_database.get(
        "categories",
        {}
    )

    final_categories = {}

    for category, queries in source_categories.items():

        print()
        print(f"PROCESSING {category}")

        fresh = fetch_category(
            category,
            queries
        )

        old = existing_categories.get(
            category,
            []
        )

        # Existing + fresh using FIFO.
        merged = merge_fifo(
            old,
            fresh
        )

        # If still below 50, make another attempt.
        if len(merged) < minimum:

            merged = ensure_minimum(
                category,
                merged,
                queries
            )

            merged = merge_fifo(
                [],
                merged
            )

        # Maximum protection.
        merged = merged[-maximum:]

        final_categories[category] = merged

        print(
            f"{category}: FINAL = {len(merged)}"
        )

    # -----------------------------------------------------
    # TOP STORIES
    # -----------------------------------------------------

    all_articles = []

    for category, articles in final_categories.items():
        all_articles.extend(articles)

    all_articles = deduplicate_articles(
        all_articles
    )

    all_articles.sort(
        key=lambda item: item.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    # Top Stories = newest 100.
    top_stories = all_articles[:MAXIMUM_PER_CATEGORY]

    final_categories["Top Stories"] = top_stories

    # -----------------------------------------------------
    # FINAL JSON
    # -----------------------------------------------------

    output = {
        "version": 1,
        "provider": config.get(
            "provider",
            "Google News RSS"
        ),
        "language": config.get(
            "language",
            "en-IN"
        ),
        "country": config.get(
            "country",
            "IN"
        ),
        "updated_at": now_iso(),
        "minimum_per_category": minimum,
        "maximum_per_category": maximum,
        "fifo": True,
        "categories": final_categories
    }

    with open(
        ARTICLES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    # -----------------------------------------------------
    # REPORT
    # -----------------------------------------------------

    print()
    print("==============================================")
    print("FINAL ARTICLE COUNTS")
    print("==============================================")

    total = 0

    for category, articles in final_categories.items():

        count = len(articles)

        total += count

        status = (
            "OK"
            if count >= minimum
            else "WARNING"
        )

        print(
            f"{category}: {count} [{status}]"
        )

    print()
    print(f"TOTAL ARTICLES: {total}")
    print()
    print(
        f"articles.json written to: {ARTICLES_FILE}"
    )
    print()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    build_database()