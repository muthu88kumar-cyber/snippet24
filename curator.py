import json
import os
import re
import hashlib
import html
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
ARTICLES_FILE = os.path.join(BASE_DIR, "articles.json")


# ============================================================
# CONFIGURATION
# ============================================================

MAX_ARTICLES = 300

MIN_ARTICLES = 50

MIN_PER_CATEGORY = 6

REQUEST_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Snippet24 News Aggregator/1.0)"
)

CATEGORIES = [
    "Indian & International",
    "Tech & AI",
    "Business & Economy",
    "Lifestyle & Health",
    "Entertainment & Living",
    "Earth & Environment",
    "Sports & Cultural"
]


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"Could not read {path}: {e}")
        return default


def save_json(path, data):
    temp = path + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp, path)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# DATE
# ============================================================

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

            return dt.astimezone(
                timezone.utc
            ).isoformat()

        except Exception:
            pass

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def extract_image(entry):

    # media_content
    media = entry.get("media_content")

    if media:
        for item in media:
            url = item.get("url")

            if url:
                return url

    # media_thumbnail
    thumbnails = entry.get("media_thumbnail")

    if thumbnails:
        for item in thumbnails:
            url = item.get("url")

            if url:
                return url

    # enclosure
    enclosures = entry.get("enclosures")

    if enclosures:
        for item in enclosures:

            url = item.get("href") or item.get("url")

            if url:
                mime = item.get("type", "")

                if (
                    "image" in mime
                    or url.lower().endswith(
                        (
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".webp"
                        )
                    )
                ):
                    return url

    # HTML image
    html_content = (
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)',
        html_content,
        re.I
    )

    if match:
        return html.unescape(
            match.group(1)
        )

    return ""


# ============================================================
# SUMMARY
# ============================================================

def make_summary(title, description):

    title = clean_text(title)
    description = clean_text(description)

    if description:

        description = re.sub(
            r"\s+",
            " ",
            description
        )

        if len(description) > 320:
            description = (
                description[:317].rsplit(
                    " ",
                    1
                )[0]
                + "..."
            )

        return description

    return (
        f"{title}. "
        "Read the key development and why it matters."
    )


# ============================================================
# UNIQUE ID
# ============================================================

def make_id(title, url):

    raw = (
        clean_text(title).lower()
        + "|"
        + url.strip().lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]


# ============================================================
# SOURCE NAME
# ============================================================

def source_name(entry, source):

    value = (
        entry.get("author")
        or entry.get("source", {}).get("title")
        or source.get("name")
        or "News Source"
    )

    value = clean_text(value)

    # Google News often produces ugly author strings.
    if value.lower().startswith("google news"):
        return source.get(
            "name",
            "News Source"
        )

    return value


# ============================================================
# FETCH RSS
# ============================================================

def fetch_feed(source):

    url = source.get("feed_url")

    if not url:
        return []

    print(
        f"Fetching: {source.get('name', url)}"
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        results = []

        for entry in feed.entries:

            title = clean_text(
                entry.get("title", "")
            )

            link = (
                entry.get("link")
                or entry.get("id")
                or ""
            )

            if not title or not link:
                continue

            description = clean_text(
                entry.get("summary")
                or entry.get("description")
                or ""
            )

            article = {
                "id": make_id(
                    title,
                    link
                ),

                "title": title,

                "summary": make_summary(
                    title,
                    description
                ),

                "description": description,

                "url": link,

                "source": source_name(
                    entry,
                    source
                ),

                "source_feed": source.get(
                    "name",
                    ""
                ),

                "image_url": extract_image(
                    entry
                ),

                "published_at": parse_date(
                    entry
                ),

                "category": source.get(
                    "category",
                    "Indian & International"
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

                "ai_image": False,

                "created_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            results.append(article)

        print(
            f"  → {len(results)} articles"
        )

        return results

    except Exception as e:

        print(
            f"  ERROR: {e}"
        )

        return []


# ============================================================
# DUPLICATES
# ============================================================

def deduplicate(articles):

    seen_ids = set()

    output = []

    for article in articles:

        article_id = article.get("id")

        if not article_id:
            continue

        if article_id in seen_ids:
            continue

        seen_ids.add(article_id)

        output.append(article)

    return output


# ============================================================
# CATEGORY BALANCING
# ============================================================

def category_balance(articles):

    selected = []

    remaining = []

    used = set()

    # First guarantee minimum per category.
    for category in CATEGORIES:

        count = 0

        for article in articles:

            if article.get(
                "category"
            ) != category:
                continue

            if article["id"] in used:
                continue

            selected.append(article)

            used.add(article["id"])

            count += 1

            if count >= MIN_PER_CATEGORY:
                break

    # Then add newest remaining articles.
    for article in articles:

        if article["id"] in used:
            continue

        remaining.append(article)

    selected.extend(
        remaining
    )

    return selected


# ============================================================
# FIFO
# ============================================================

def fifo_limit(articles):

    # Newest first.
    articles.sort(
        key=lambda x: x.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    # Keep only newest MAX_ARTICLES.
    #
    # Therefore:
    #
    # NEW ARTICLE
    #      ↓
    # TOP
    #      ↓
    # ...
    #      ↓
    # OLDEST
    #      ↓
    # REMOVE
    #

    if len(articles) > MAX_ARTICLES:

        articles = articles[
            :MAX_ARTICLES
        ]

    return articles


# ============================================================
# ENSURE MINIMUM
# ============================================================

def enough_news(articles):

    if len(articles) < MIN_ARTICLES:
        return False

    counts = {}

    for category in CATEGORIES:

        counts[category] = 0

    for article in articles:

        category = article.get(
            "category"
        )

        if category in counts:
            counts[category] += 1

    missing = [
        category
        for category, count
        in counts.items()
        if count < MIN_PER_CATEGORY
    ]

    return len(missing) == 0


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n=============================="
    )

    print(
        "       SNIPPET24 CURATOR"
    )

    print(
        "==============================\n"
    )

    # --------------------------------------------------------
    # Load existing articles FIRST.
    # --------------------------------------------------------

    old_articles = load_json(
        ARTICLES_FILE,
        []
    )

    if not isinstance(old_articles, list):
        old_articles = []

    print(
        f"Existing articles: "
        f"{len(old_articles)}"
    )

    # --------------------------------------------------------
    # Load sources
    # --------------------------------------------------------

    config = load_json(
        SOURCES_FILE,
        {"sources": []}
    )

    sources = config.get(
        "sources",
        []
    )

    enabled_sources = [
        source
        for source in sources
        if source.get(
            "enabled",
            True
        )
    ]

    print(
        f"Enabled sources: "
        f"{len(enabled_sources)}"
    )

    # --------------------------------------------------------
    # Fetch new articles
    # --------------------------------------------------------

    new_articles = []

    for source in enabled_sources:

        fetched = fetch_feed(
            source
        )

        new_articles.extend(
            fetched
        )

        time.sleep(0.2)

    print(
        f"\nNew articles: "
        f"{len(new_articles)}"
    )

    # --------------------------------------------------------
    # Combine OLD + NEW
    #
    # This is critical.
    #
    # A failed RSS feed does NOT destroy
    # previously collected stories.
    # --------------------------------------------------------

    combined = (
        old_articles
        + new_articles
    )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    combined = deduplicate(
        combined
    )

    print(
        f"After deduplication: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # Sort newest
    # --------------------------------------------------------

    combined.sort(
        key=lambda x: x.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # Balance categories
    # --------------------------------------------------------

    combined = category_balance(
        combined
    )

    # --------------------------------------------------------
    # FIFO
    # --------------------------------------------------------

    combined = fifo_limit(
        combined
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_json(
        ARTICLES_FILE,
        combined
    )

    print(
        f"\nSaved articles: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # Category report
    # --------------------------------------------------------

    print(
        "\nCATEGORY REPORT"
    )

    for category in CATEGORIES:

        count = sum(
            1
            for article in combined
            if article.get(
                "category"
            ) == category
        )

        print(
            f"{category}: {count}"
        )

    # --------------------------------------------------------
    # Warning
    # --------------------------------------------------------

    if len(combined) < MIN_ARTICLES:

        print(
            "\nWARNING:"
        )

        print(
            f"Only {len(combined)} "
            f"articles available."
        )

        print(
            "Existing stories were preserved."
        )

    else:

        print(
            "\n✓ Minimum news requirement met."
        )

    print(
        "\n==============================\n"
    )


if __name__ == "__main__":
    main()