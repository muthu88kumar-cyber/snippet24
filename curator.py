import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime

import feedparser
import requests


BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Snippet24News/1.0; "
        "+https://snippet24.in)"
    )
}


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    # Remove HTML
    value = re.sub(r"<[^>]+>", " ", value)

    # Remove excessive whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def shorten_text(text, limit=500):
    text = clean_text(text)

    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + "..."


# ---------------------------------------------------------
# DATE
# ---------------------------------------------------------

def parse_date(entry):
    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
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

    return utc_now()


# ---------------------------------------------------------
# ID
# ---------------------------------------------------------

def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:24]


# ---------------------------------------------------------
# LOAD JSON
# ---------------------------------------------------------

def load_sources():
    if not SOURCES_FILE.exists():
        raise FileNotFoundError("sources.json not found")

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_articles():
    if not ARTICLES_FILE.exists():
        return {
            "version": 1,
            "updated_at": utc_now(),
            "minimum_per_category": MINIMUM_PER_CATEGORY,
            "maximum_per_category": MAXIMUM_PER_CATEGORY,
            "fifo": True,
            "categories": {},
        }

    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception:
        print("WARNING: articles.json is invalid. Starting fresh.")

        return {
            "version": 1,
            "updated_at": utc_now(),
            "minimum_per_category": MINIMUM_PER_CATEGORY,
            "maximum_per_category": MAXIMUM_PER_CATEGORY,
            "fifo": True,
            "categories": {},
        }

    # Expected format
    if isinstance(data, dict) and isinstance(data.get("categories"), dict):
        return data

    # Safety for older format
    if isinstance(data, dict):
        return {
            "version": 1,
            "updated_at": utc_now(),
            "minimum_per_category": MINIMUM_PER_CATEGORY,
            "maximum_per_category": MAXIMUM_PER_CATEGORY,
            "fifo": True,
            "categories": data,
        }

    return {
        "version": 1,
        "updated_at": utc_now(),
        "minimum_per_category": MINIMUM_PER_CATEGORY,
        "maximum_per_category": MAXIMUM_PER_CATEGORY,
        "fifo": True,
        "categories": {},
    }


# ---------------------------------------------------------
# RSS FETCH
# ---------------------------------------------------------

def fetch_feed(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return feedparser.parse(response.content)

    except Exception as e:
        print(f"RSS ERROR: {url}")
        print(f"          {e}")

        return None


# ---------------------------------------------------------
# ENTRY
# ---------------------------------------------------------

def entry_to_article(entry, category, source_name):
    title = clean_text(entry.get("title", ""))

    if not title:
        return None

    url = (
        entry.get("link")
        or entry.get("url")
        or ""
    ).strip()

    if not url:
        return None

    description = (
        entry.get("summary")
        or entry.get("description")
        or title
    )

    description = shorten_text(description)

    published_at = parse_date(entry)

    return {
        "id": make_id(title, url),
        "title": title,
        "description": description,
        "url": url,
        "source": source_name,
        "category": category,
        "published_at": published_at,
        "fetched_at": utc_now(),
    }


# ---------------------------------------------------------
# FETCH CATEGORY
# ---------------------------------------------------------

def fetch_category(category, feed_list):
    results = []

    seen_ids = set()

    for source in feed_list:

        if isinstance(source, str):
            feed_url = source
            source_name = "Google News"
        else:
            feed_url = source.get("url", "")
            source_name = source.get("name", "Google News")

        if not feed_url:
            continue

        print(f"[{category}] Fetching: {source_name}")

        feed = fetch_feed(feed_url)

        if feed is None:
            continue

        entries = getattr(feed, "entries", [])

        print(
            f"[{category}] {source_name}: "
            f"{len(entries)} entries"
        )

        for entry in entries:

            article = entry_to_article(
                entry,
                category,
                source_name,
            )

            if not article:
                continue

            if article["id"] in seen_ids:
                continue

            seen_ids.add(article["id"])

            results.append(article)

        # Small pause between feeds
        time.sleep(0.2)

    return results


# ---------------------------------------------------------
# SORT
# ---------------------------------------------------------

def article_timestamp(article):
    try:
        return datetime.fromisoformat(
            article["published_at"].replace("Z", "+00:00")
        ).timestamp()

    except Exception:
        return 0


def sort_articles(articles):
    return sorted(
        articles,
        key=article_timestamp,
        reverse=True,
    )


# ---------------------------------------------------------
# MERGE + FIFO
# ---------------------------------------------------------

def merge_category(old_articles, new_articles):
    combined = []

    # Newest first
    combined.extend(new_articles)

    # Keep previous articles that were not fetched this time
    existing_ids = {
        article.get("id")
        for article in new_articles
        if article.get("id")
    }

    for article in old_articles:
        article_id = article.get("id")

        if article_id and article_id not in existing_ids:
            combined.append(article)

    # Final deduplication
    unique = {}

    for article in combined:
        article_id = article.get("id")

        if not article_id:
            continue

        if article_id not in unique:
            unique[article_id] = article

    combined = list(unique.values())

    # Newest first
    combined = sort_articles(combined)

    # FIFO:
    # keep only newest MAXIMUM_PER_CATEGORY articles
    return combined[:MAXIMUM_PER_CATEGORY]


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("========================================")
    print("Snippet24 News Curator")
    print("========================================")

    sources = load_sources()
    existing = load_articles()

    categories_config = sources.get("categories", {})

    if not categories_config:
        raise RuntimeError(
            "sources.json contains no categories"
        )

    old_categories = existing.get("categories", {})

    final_categories = {}

    total_articles = 0

    for category, feeds in categories_config.items():

        print()
        print("----------------------------------------")
        print(f"CATEGORY: {category}")
        print("----------------------------------------")

        if not isinstance(feeds, list):
            print(
                f"WARNING: {category} has no valid feed list"
            )
            feeds = []

        new_articles = fetch_category(
            category,
            feeds,
        )

        old_articles = old_categories.get(
            category,
            [],
        )

        merged = merge_category(
            old_articles,
            new_articles,
        )

        final_categories[category] = merged

        total_articles += len(merged)

        print(
            f"{category}: "
            f"{len(new_articles)} new / "
            f"{len(merged)} stored"
        )

        if len(merged) < MINIMUM_PER_CATEGORY:
            print(
                f"WARNING: {category} has only "
                f"{len(merged)} articles. "
                f"Target is {MINIMUM_PER_CATEGORY}."
            )

    # -----------------------------------------------------
    # WRITE JSON
    # -----------------------------------------------------

    output = {
        "version": 1,
        "provider": "Google News RSS",
        "language": "en-IN",
        "country": "IN",
        "minimum_per_category": MINIMUM_PER_CATEGORY,
        "maximum_per_category": MAXIMUM_PER_CATEGORY,
        "fifo": True,
        "updated_at": utc_now(),
        "categories": final_categories,
    }

    temporary_file = ARTICLES_FILE.with_suffix(
        ".json.tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    temporary_file.replace(ARTICLES_FILE)

    # -----------------------------------------------------
    # REPORT
    # -----------------------------------------------------

    print()
    print("========================================")
    print(f"TOTAL ARTICLES: {total_articles}")
    print("========================================")

    for category, articles in final_categories.items():
        print(
            f"{category}: {len(articles)}"
        )

    if total_articles == 0:
        raise RuntimeError(
            "No articles were fetched. "
            "Check RSS sources/network."
        )

    print()
    print("articles.json updated successfully.")


if __name__ == "__main__":
    main()