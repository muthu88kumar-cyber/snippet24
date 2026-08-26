import json
import os
import re
import html
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "articles.json"

# ============================================================
# SNIPPET24 RSS SOURCES
# No RSS_SOURCES environment variable is required.
# ============================================================

RSS_SOURCES = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
        "https://feeds.reuters.com/reuters/worldNews",
    ],

    "India": [
        "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://indianexpress.com/section/india/feed/",
    ],

    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/business/rss",
        "https://www.moneycontrol.com/rss/business.xml",
    ],

    "Technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theguardian.com/technology/rss",
        "https://techcrunch.com/feed/",
    ],

    "Lifestyle": [
        "https://feeds.bbci.co.uk/news/lifestyle/rss.xml",
        "https://www.theguardian.com/lifeandstyle/rss",
    ],
}

CATEGORY_LIMIT = 100


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    soup = BeautifulSoup(value, "html.parser")
    value = soup.get_text(" ", strip=True)

    value = re.sub(r"\s+", " ", value)
    value = value.replace("&nbsp;", " ")

    return value.strip()


def make_id(url, title):
    raw = f"{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def get_source_name(entry, feed_url):
    source = ""

    if hasattr(entry, "source") and entry.source:
        source = entry.source.get("title", "")

    if not source:
        source = entry.get("author", "")

    if not source:
        source = urlparse(feed_url).netloc

    source = clean_text(source)

    source = re.sub(
        r"^(www\.|feeds\.|rss\.)",
        "",
        source,
        flags=re.IGNORECASE
    )

    return source or "Original publisher"


def parse_date(entry):
    try:
        if entry.get("published_parsed"):
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()

        if entry.get("updated_parsed"):
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()

        if entry.get("published"):
            dt = parsedate_to_datetime(entry["published"])
            return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        pass

    return datetime.now(timezone.utc).isoformat()


def extract_summary(entry):
    text = ""

    if entry.get("summary"):
        text = entry.get("summary")

    elif entry.get("description"):
        text = entry.get("description")

    elif entry.get("content"):
        try:
            text = entry.content[0].value
        except Exception:
            pass

    text = clean_text(text)

    return text


def shorten_summary(text, max_chars=360):
    text = clean_text(text)

    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    shortened = text[:max_chars]

    # Try to stop at a sentence.
    last_stop = max(
        shortened.rfind(". "),
        shortened.rfind("! "),
        shortened.rfind("? ")
    )

    if last_stop > 160:
        return shortened[:last_stop + 1]

    return shortened.rstrip() + "..."


# ============================================================
# IMAGE DISCOVERY
# ============================================================

def get_feed_image(entry):
    # media:content
    media_content = entry.get("media_content")

    if media_content:
        for media in media_content:
            url = media.get("url")
            if url:
                return url

    # media:thumbnail
    media_thumbnail = entry.get("media_thumbnail")

    if media_thumbnail:
        for media in media_thumbnail:
            url = media.get("url")
            if url:
                return url

    # enclosure
    enclosures = entry.get("enclosures")

    if enclosures:
        for enclosure in enclosures:
            url = enclosure.get("href") or enclosure.get("url")
            if url:
                media_type = enclosure.get("type", "")
                if media_type.startswith("image/") or not media_type:
                    return url

    return ""


# ============================================================
# FETCH RSS
# ============================================================

def fetch_feed(category, feed_url):
    print(f"Fetching [{category}] {feed_url}")

    try:
        response = requests.get(
            feed_url,
            timeout=20,
            headers={
                "User-Agent": "Snippet24-NewsBot/1.0"
            }
        )

        response.raise_for_status()

        parsed = feedparser.parse(response.content)

        if parsed.bozo and not parsed.entries:
            print(f"  RSS parse failed: {feed_url}")
            return []

        articles = []

        for entry in parsed.entries:

            title = clean_text(entry.get("title", ""))

            link = (
                entry.get("link")
                or entry.get("id")
                or ""
            )

            if not title or not link:
                continue

            summary = extract_summary(entry)

            publisher = get_source_name(entry, feed_url)

            image = get_feed_image(entry)

            published_at = parse_date(entry)

            article = {
                "id": make_id(link, title),
                "category": category,
                "original_title": title,
                "headline": title,
                "summary": shorten_summary(summary),
                "publisher": publisher,
                "url": link,
                "image": image,
                "published_at": published_at,
                "source_type": "rss",
                "ai_generated": False
            }

            articles.append(article)

        print(f"  Found {len(articles)} articles")

        return articles

    except Exception as e:
        print(f"  Feed error: {e}")
        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(articles):
    seen = set()
    output = []

    for article in articles:

        key = (
            article.get("url")
            or article.get("original_title")
            or article.get("headline")
        ).strip().lower()

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        output.append(article)

    return output


# ============================================================
# AI-READY HEADLINE/SUMMARY
# ============================================================

def prepare_for_ai(article):
    """
    Keeps original facts while creating fields that can later
    be processed by an AI provider.

    Do NOT fabricate facts.
    """

    original_title = clean_text(article.get("original_title", ""))
    summary = clean_text(article.get("summary", ""))

    if not summary:
        summary = original_title

    article["headline"] = original_title
    article["summary"] = shorten_summary(summary)

    return article


# ============================================================
# LOAD EXISTING ARTICLES
# ============================================================

def load_existing():

    if not os.path.exists(OUTPUT_FILE):
        return []

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("articles", [])

    except Exception as e:
        print(f"Could not read {OUTPUT_FILE}: {e}")

    return []


# ============================================================
# FIFO STORAGE
# ============================================================

def merge_fifo(existing, new_articles):

    combined = existing + new_articles

    combined = deduplicate(combined)

    # Newest first.
    combined.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    # Exactly 100 maximum per category.
    final = []

    categories = [
        "World",
        "India",
        "Business",
        "Technology",
        "Lifestyle"
    ]

    for category in categories:

        category_articles = [
            article
            for article in combined
            if article.get("category") == category
        ]

        category_articles = category_articles[:CATEGORY_LIMIT]

        final.extend(category_articles)

    return final


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 60)

    all_new_articles = []

    for category, feeds in RSS_SOURCES.items():

        print(f"\nCATEGORY: {category}")

        category_articles = []

        for feed_url in feeds:
            articles = fetch_feed(category, feed_url)
            category_articles.extend(articles)

        category_articles = deduplicate(category_articles)

        for article in category_articles:
            article = prepare_for_ai(article)
            all_new_articles.append(article)

        print(
            f"TOTAL {category}: "
            f"{len(category_articles)}"
        )

    if not all_new_articles:
        print("\nERROR: All RSS feeds returned 0 articles.")
        print("The website will keep the existing articles.")
        return 1

    existing = load_existing()

    print(f"\nExisting articles: {len(existing)}")
    print(f"New articles:      {len(all_new_articles)}")

    final_articles = merge_fifo(
        existing,
        all_new_articles
    )

    # Final validation.
    final_articles = [
        article
        for article in final_articles
        if article.get("headline")
        and article.get("url")
        and article.get("category")
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            final_articles,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 60)
    print("SNIPPET24 UPDATE COMPLETE")
    print("=" * 60)

    for category in RSS_SOURCES:

        count = sum(
            1
            for article in final_articles
            if article.get("category") == category
        )

        print(f"{category}: {count}")

    print(f"TOTAL: {len(final_articles)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())