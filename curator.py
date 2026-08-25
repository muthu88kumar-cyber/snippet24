#!/usr/bin/env python3

"""
News Curator
------------

Features:
- Reads RSS/Atom feeds from sources.json
- Uses only Python standard library
- No feedparser dependency
- Deduplicates articles
- Maintains FIFO rolling storage
- Minimum target: 50 articles per category
- Maximum rolling storage: 200 articles per category
- Preserves old articles when feeds temporarily fail
- Generates articles.json
"""

import json
import os
import re
import sys
import time
import html
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
ARTICLES_FILE = os.path.join(BASE_DIR, "articles.json")

# Minimum number we want available for every category.
MIN_PER_CATEGORY = 50

# Rolling FIFO storage.
# We keep more than 50 so temporary RSS failures don't immediately
# destroy the feed.
MAX_PER_CATEGORY = 200

# Main/Home feed size.
MAIN_FEED_SIZE = 100

# Number of articles requested from each source.
MAX_ITEMS_PER_SOURCE = 100

# Network timeout.
REQUEST_TIMEOUT = 15

# User agent.
USER_AGENT = (
    "Mozilla/5.0 "
    "(NewsCurator/1.0; +https://example.com)"
)


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[curator] {message}", flush=True)


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log(f"Could not read {path}: {exc}")
        return default


def save_json(path, data):
    temp_path = path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp_path, path)


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    # Remove HTML.
    value = re.sub(r"<[^>]+>", " ", value)

    # Normalize whitespace.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_id(title, link):
    raw = f"{title}|{link}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:24]


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    # RSS usually uses RFC 2822.
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Atom / ISO dates.
    try:
        iso = value.replace("Z", "+00:00")

        dt = datetime.fromisoformat(iso)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return None


def date_to_iso(dt):
    if not dt:
        return ""

    return dt.astimezone(timezone.utc).isoformat()


def timestamp_now():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# XML HELPERS
# ============================================================

def local_name(tag):
    """
    Converts:

        {namespace}title

    into:

        title
    """

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def child_text(element, names):
    """
    Find the first matching child element.
    """

    names = set(names)

    for child in element.iter():

        if child is element:
            continue

        if local_name(child.tag) in names:

            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def find_link(element):
    """
    Supports RSS and Atom.
    """

    # RSS <link>
    for child in element.iter():

        if child is element:
            continue

        if local_name(child.tag) != "link":
            continue

        href = child.attrib.get("href")

        if href:
            return href.strip()

        text = "".join(child.itertext()).strip()

        if text:
            return text

    return ""


# ============================================================
# RSS / ATOM FETCHING
# ============================================================

def fetch_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/atom+xml, "
                "application/xml, "
                "text/xml, "
                "*/*"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            return response.read()

    except urllib.error.HTTPError as exc:
        log(f"HTTP {exc.code}: {url}")

    except urllib.error.URLError as exc:
        log(f"Network error: {url} -> {exc}")

    except Exception as exc:
        log(f"Fetch error: {url} -> {exc}")

    return None


def parse_feed(xml_data, source):
    """
    Parse RSS 2.0 / RSS 1.0 / Atom.
    """

    if not xml_data:
        return []

    try:
        root = ET.fromstring(xml_data)
    except Exception as exc:
        log(f"Invalid XML from {source.get('name', 'source')}: {exc}")
        return []

    items = []

    # RSS <item>
    rss_items = [
        element
        for element in root.iter()
        if local_name(element.tag) == "item"
    ]

    # Atom <entry>
    atom_entries = [
        element
        for element in root.iter()
        if local_name(element.tag) == "entry"
    ]

    elements = rss_items or atom_entries

    for element in elements[:MAX_ITEMS_PER_SOURCE]:

        title = child_text(
            element,
            ["title"]
        )

        link = find_link(element)

        description = child_text(
            element,
            [
                "description",
                "summary",
                "content",
                "encoded"
            ]
        )

        published_raw = child_text(
            element,
            [
                "pubDate",
                "published",
                "updated",
                "date"
            ]
        )

        author = child_text(
            element,
            [
                "author",
                "creator",
                "name"
            ]
        )

        guid = child_text(
            element,
            [
                "guid",
                "id"
            ]
        )

        title = clean_text(title)
        description = clean_text(description)
        author = clean_text(author)
        link = link.strip()
        guid = guid.strip()

        if not title:
            continue

        if not link:
            link = guid

        if not link:
            continue

        published_dt = parse_date(published_raw)

        article = {
            "id": make_id(title, link),

            "title": title,

            "link": link,

            "description": description,

            "source": source.get(
                "name",
                "Unknown"
            ),

            "website": source.get(
                "website",
                ""
            ),

            "category": source.get(
                "category",
                "General"
            ),

            "region": source.get(
                "region",
                ""
            ),

            "country": source.get(
                "country",
                ""
            ),

            "state": source.get(
                "state",
                ""
            ),

            "language": source.get(
                "language",
                "English"
            ),

            "author": author,

            "published_at": date_to_iso(
                published_dt
            ),

            "fetched_at": timestamp_now(),

            "guid": guid,

        }

        items.append(article)

    return items


# ============================================================
# DEDUPLICATION
# ============================================================

def article_key(article):
    """
    Prefer URL/guid, then title.
    """

    link = str(article.get("link", "")).strip().lower()

    if link:
        return "url:" + link

    guid = str(article.get("guid", "")).strip().lower()

    if guid:
        return "guid:" + guid

    title = str(article.get("title", "")).strip().lower()

    return "title:" + title


def deduplicate(articles):
    result = []
    seen = set()

    for article in articles:

        key = article_key(article)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(article)

    return result


# ============================================================
# CATEGORY HELPERS
# ============================================================

def get_categories(sources):
    categories = []

    for source in sources:

        if not source.get("enabled", True):
            continue

        category = (
            source.get("category")
            or "General"
        ).strip()

        if category not in categories:
            categories.append(category)

    return categories


def normalize_existing_articles(data):
    """
    Handles both:

        {"articles": [...]}

    and:

        [...]
    """

    if isinstance(data, dict):
        articles = data.get("articles", [])

        if isinstance(articles, list):
            return articles

    if isinstance(data, list):
        return data

    return []


# ============================================================
# FIFO
# ============================================================

def fifo_category_update(
    existing,
    incoming,
    category
):
    """
    FIFO rolling queue.

    Existing articles are retained.
    New articles are appended.
    Duplicates are removed.
    Once MAX_PER_CATEGORY is exceeded,
    oldest entries are removed first.
    """

    existing_category = [
        a for a in existing
        if a.get("category") == category
    ]

    incoming_category = [
        a for a in incoming
        if a.get("category") == category
    ]

    # Existing first, new second.
    combined = (
        existing_category +
        incoming_category
    )

    combined = deduplicate(combined)

    # Sort by actual publication time when possible.
    # Articles without a date go toward the bottom.
    combined.sort(
        key=lambda a: (
            a.get("published_at") or
            a.get("fetched_at") or
            ""
        )
    )

    # FIFO:
    # Oldest articles are at the beginning.
    if len(combined) > MAX_PER_CATEGORY:
        combined = combined[
            -MAX_PER_CATEGORY:
        ]

    return combined


# ============================================================
# MAIN FEED
# ============================================================

def build_main_feed(all_articles):
    """
    Build a global newest-first feed.

    The application can display the first 50,
    100, etc.
    """

    articles = deduplicate(all_articles)

    articles.sort(
        key=lambda a: (
            a.get("published_at") or
            a.get("fetched_at") or
            ""
        ),
        reverse=True
    )

    return articles[:MAIN_FEED_SIZE]


# ============================================================
# CURATE
# ============================================================

def curate():
    log("Starting news curator...")

    sources_data = load_json(
        SOURCES_FILE,
        []
    )

    if isinstance(sources_data, dict):
        sources = sources_data.get(
            "sources",
            []
        )
    else:
        sources = sources_data

    if not isinstance(sources, list):
        log("sources.json must contain a list.")
        return 1

    enabled_sources = [
        source
        for source in sources
        if source.get("enabled", True)
    ]

    if not enabled_sources:
        log("No enabled news sources found.")
        return 1

    log(
        f"Enabled sources: "
        f"{len(enabled_sources)}"
    )

    # --------------------------------------------------------
    # Existing articles
    # --------------------------------------------------------

    old_data = load_json(
        ARTICLES_FILE,
        {"articles": []}
    )

    existing_articles = normalize_existing_articles(
        old_data
    )

    log(
        f"Existing stored articles: "
        f"{len(existing_articles)}"
    )

    # --------------------------------------------------------
    # Fetch sources
    # --------------------------------------------------------

    incoming_articles = []

    successful_sources = 0
    failed_sources = 0

    for source in enabled_sources:

        name = source.get(
            "name",
            "Unnamed source"
        )

        feed_url = source.get(
            "feed_url",
            ""
        ).strip()

        if not feed_url:
            log(
                f"Skipping {name}: "
                f"missing feed_url"
            )
            failed_sources += 1
            continue

        log(f"Fetching: {name}")

        xml_data = fetch_url(feed_url)

        if not xml_data:
            failed_sources += 1
            continue

        articles = parse_feed(
            xml_data,
            source
        )

        if articles:
            successful_sources += 1
            incoming_articles.extend(
                articles
            )

            log(
                f"  -> {len(articles)} articles"
            )
        else:
            failed_sources += 1
            log(
                "  -> no articles"
            )

    log(
        f"Sources successful: "
        f"{successful_sources}"
    )

    log(
        f"Sources failed: "
        f"{failed_sources}"
    )

    log(
        f"New articles fetched: "
        f"{len(incoming_articles)}"
    )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    categories = get_categories(
        enabled_sources
    )

    log(
        f"Categories: {len(categories)}"
    )

    # --------------------------------------------------------
    # FIFO update by category
    # --------------------------------------------------------

    final_articles = []

    category_stats = {}

    for category in categories:

        updated = fifo_category_update(
            existing_articles,
            incoming_articles,
            category
        )

        category_stats[category] = len(
            updated
        )

        final_articles.extend(updated)

    # --------------------------------------------------------
    # Preserve categories that existed previously
    # but no longer have active sources.
    # --------------------------------------------------------

    known_categories = set(categories)

    old_only_categories = set(
        article.get("category", "General")
        for article in existing_articles
    ) - known_categories

    for category in old_only_categories:

        old_category_articles = [
            a for a in existing_articles
            if a.get("category") == category
        ]

        old_category_articles = deduplicate(
            old_category_articles
        )

        old_category_articles.sort(
            key=lambda a: (
                a.get("published_at") or
                a.get("fetched_at") or
                ""
            )
        )

        old_category_articles = old_category_articles[
            -MAX_PER_CATEGORY:
        ]

        final_articles.extend(
            old_category_articles
        )

        category_stats[category] = len(
            old_category_articles
        )

    # --------------------------------------------------------
    # Final dedupe
    # --------------------------------------------------------

    final_articles = deduplicate(
        final_articles
    )

    # Newest first in JSON.
    final_articles.sort(
        key=lambda a: (
            a.get("published_at") or
            a.get("fetched_at") or
            ""
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # Main feed
    # --------------------------------------------------------

    main_articles = build_main_feed(
        final_articles
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output = {
        "generated_at": timestamp_now(),

        "version": 1,

        "settings": {
            "minimum_per_category":
                MIN_PER_CATEGORY,

            "maximum_per_category":
                MAX_PER_CATEGORY,

            "main_feed_size":
                MAIN_FEED_SIZE,

            "fifo":
                True
        },

        "stats": {
            "total_articles":
                len(final_articles),

            "main_articles":
                len(main_articles),

            "successful_sources":
                successful_sources,

            "failed_sources":
                failed_sources,

            "categories":
                category_stats
        },

        "main": main_articles,

        "articles": final_articles
    }

    save_json(
        ARTICLES_FILE,
        output
    )

    # --------------------------------------------------------
    # Print category status
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("NEWS CURATOR RESULT")
    print("=" * 60)

    print(
        f"Total articles: "
        f"{len(final_articles)}"
    )

    print(
        f"Main feed: "
        f"{len(main_articles)}"
    )

    print()

    for category in sorted(
        category_stats
    ):

        count = category_stats[category]

        status = (
            "OK"
            if count >= MIN_PER_CATEGORY
            else "LOW"
        )

        print(
            f"{status:4} "
            f"{category}: "
            f"{count}"
        )

    print("=" * 60)

    # --------------------------------------------------------
    # Important warning
    # --------------------------------------------------------

    low_categories = [
        category
        for category, count
        in category_stats.items()
        if count < MIN_PER_CATEGORY
    ]

    if low_categories:

        print()
        print(
            "WARNING: Some categories have "
            "fewer than "
            f"{MIN_PER_CATEGORY} articles:"
        )

        for category in low_categories:
            print(
                f"  - {category}"
            )

        print()
        print(
            "Add more RSS sources to those "
            "categories in sources.json."
        )

    else:

        print()
        print(
            f"SUCCESS: Every category has "
            f"at least {MIN_PER_CATEGORY} "
            "stored articles."
        )

    print()

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        sys.exit(curate())

    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)

    except Exception as exc:
        print(
            f"\nFATAL ERROR: {exc}",
            file=sys.stderr
        )
        sys.exit(1)