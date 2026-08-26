import json
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


# ============================================================
# SNIPPET24 NEWS CURATOR
# ============================================================

OUTPUT_FILE = "articles.json"

# Keep at least 50 when available.
# 100 gives the website enough stories to work with.
MAX_PER_CATEGORY = 100

# FIFO:
# newest stories are inserted first and oldest stories are
# removed when the category exceeds MAX_PER_CATEGORY.
FIFO_LIMIT = MAX_PER_CATEGORY

REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Snippet24NewsBot/1.0; "
        "+https://snippet24.in)"
    )
}


# ============================================================
# RSS SOURCES
# ============================================================

RSS_SOURCES = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss",
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

    "Science": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.theguardian.com/science/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    ],

    "Sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.theguardian.com/sport/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
    ],

    "Lifestyle": [
        "https://feeds.bbci.co.uk/news/lifestyle_and_human_interest/rss.xml",
        "https://www.theguardian.com/lifeandstyle/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/FashionandStyle.xml",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "html.parser")
    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)
    text = text.replace("&nbsp;", " ")

    return text.strip()


def normalize_title(title):
    title = clean_text(title)

    # Remove common publisher suffixes.
    title = re.sub(
        r"\s*\|\s*(BBC|Hindustan Times|Firstpost|Reuters|CNN|"
        r"The Guardian|Business Standard|The Hindu|Indian Express).*$",
        "",
        title,
        flags=re.I,
    )

    title = re.sub(r"\s+-\s+(BBC|Reuters|CNN|The Guardian).*$", "", title)

    return title.strip()


def make_id(category, title, url):
    raw = f"{category}|{title}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


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
            dt = date_parser.parse(value)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except Exception:
            pass

    return datetime.now(timezone.utc)


def format_date(dt):
    return dt.isoformat()


def publisher_from_entry(entry):
    source = entry.get("source")

    if isinstance(source, dict):
        name = source.get("title")
        if name:
            return clean_text(name)

    publisher = entry.get("publisher")

    if publisher:
        return clean_text(publisher)

    return "Original publication"


def extract_summary(entry, title):
    possible = [
        entry.get("summary"),
        entry.get("description"),
        entry.get("content", [{}])[0].get("value")
        if entry.get("content")
        else "",
    ]

    for value in possible:
        text = clean_text(value)

        if not text:
            continue

        # Avoid using a duplicated headline as the summary.
        if text.lower().strip() == title.lower().strip():
            continue

        # Remove obvious HTML artifacts.
        text = re.sub(r"\s+", " ", text).strip()

        # Keep it short enough for the card.
        if len(text) > 420:
            text = text[:417].rsplit(" ", 1)[0] + "..."

        return text

    return ""


def create_fallback_summary(title, category):
    """
    We do NOT simply repeat the headline.

    If an RSS source doesn't provide a useful description,
    create a short neutral explanation from the headline.
    """

    title = title.strip()

    patterns = [
        (
            r"^(.*?)\s+says\s+(.*?)$",
            lambda m: (
                f"{m.group(2)} said {m.group(1).lower()} "
                f"during the latest development, highlighting "
                f"the key issues involved."
            ),
        ),
        (
            r"^(.*?)\s+to\s+(.*?)$",
            lambda m: (
                f"The latest development involves {m.group(1).lower()}, "
                f"with the next step being {m.group(2).lower()}."
            ),
        ),
    ]

    for pattern, builder in patterns:
        match = re.match(pattern, title, flags=re.I)

        if match:
            return builder(match)

    return (
        f"The latest {category.lower()} development concerns "
        f"{title.lower()}. The development is being reported as "
        f"part of the latest updates in this area."
    )


def create_ai_image_url(title, category):
    """
    Generates a relevant illustrative image using Pollinations.

    The image is AI-generated and should NOT be presented as a
    photograph of the actual event/person unless the prompt
    explicitly supports that distinction.
    """

    prompt = (
        f"Editorial news illustration for a {category} news story. "
        f"Subject: {title}. "
        f"Professional modern newsroom visual, realistic but clearly "
        f"illustrative, no text, no logos, no watermark, "
        f"wide composition, suitable for a news website."
    )

    encoded = quote(prompt)

    return (
        "https://image.pollinations.ai/prompt/"
        f"{encoded}"
        "?width=1200&height=675&nologo=true"
    )


def fetch_feed(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        if getattr(feed, "bozo", False) and not feed.entries:
            return []

        return feed.entries

    except Exception as exc:
        print(f"WARNING: RSS failed: {url}")
        print(f"         {exc}")
        return []


# ============================================================
# LOAD EXISTING DATA
# ============================================================

def load_articles():
    if not os.path.exists(OUTPUT_FILE):
        return {
            "version": 1,
            "generated_at": None,
            "articles": [],
        }

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Support both old formats.
        if isinstance(data, list):
            articles = data

        elif isinstance(data, dict):
            articles = data.get("articles", [])

        else:
            articles = []

        if not isinstance(articles, list):
            articles = []

        return {
            "version": 1,
            "generated_at": data.get("generated_at")
            if isinstance(data, dict)
            else None,
            "articles": articles,
        }

    except Exception as exc:
        print(f"WARNING: Could not read {OUTPUT_FILE}: {exc}")

        return {
            "version": 1,
            "generated_at": None,
            "articles": [],
        }


# ============================================================
# CURATION
# ============================================================

def curate_category(category, feeds):
    collected = []

    print(f"\n[{category}]")

    for feed_url in feeds:
        print(f"Fetching: {feed_url}")

        entries = fetch_feed(feed_url)

        print(f"  Found {len(entries)} entries")

        for entry in entries:
            title = normalize_title(entry.get("title"))

            if not title:
                continue

            url = (
                entry.get("link")
                or entry.get("url")
                or ""
            ).strip()

            if not url:
                continue

            published = parse_date(entry)

            publisher = publisher_from_entry(entry)

            summary = extract_summary(entry, title)

            if not summary:
                summary = create_fallback_summary(
                    title,
                    category,
                )

            article = {
                "id": make_id(category, title, url),
                "category": category,
                "headline": title,
                "summary": summary,
                "publisher": publisher,
                "published_at": format_date(published),
                "url": url,

                # AI generated eye-catcher.
                "image_url": create_ai_image_url(
                    title,
                    category,
                ),

                "source_language": "en",

                # Translation fields.
                "translations": {
                    "ta": None,
                    "hi": None,
                    "te": None,
                    "ml": None,
                    "kn": None,
                    "bn": None,
                    "mr": None,
                },

                "image_type": "ai_generated_illustration",
            }

            collected.append(article)

    # Newest first.
    collected.sort(
        key=lambda item: item.get("published_at", ""),
        reverse=True,
    )

    # Remove duplicate URLs/headlines.
    unique = []
    seen = set()

    for article in collected:
        key = (
            article["url"].lower().strip()
            or article["headline"].lower().strip()
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(article)

    # FIFO limit.
    return unique[:FIFO_LIMIT]


def merge_categories(existing_articles, fresh_by_category):
    """
    Preserve old articles if RSS temporarily fails.

    New stories replace/update matching IDs.
    Old stories remain until the FIFO limit is reached.
    """

    by_id = {}

    for article in existing_articles:
        if not isinstance(article, dict):
            continue

        article_id = article.get("id")

        if article_id:
            by_id[article_id] = article

    # Add/update fresh articles.
    for category, fresh_articles in fresh_by_category.items():

        for article in fresh_articles:
            by_id[article["id"]] = article

    # Group by category.
    grouped = {}

    for article in by_id.values():
        category = article.get("category", "World")

        grouped.setdefault(category, []).append(article)

    final_articles = []

    for category in RSS_SOURCES.keys():

        items = grouped.get(category, [])

        items.sort(
            key=lambda item: item.get("published_at", ""),
            reverse=True,
        )

        # FIFO per category.
        items = items[:FIFO_LIMIT]

        final_articles.extend(items)

    return final_articles


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("SNIPPET24 AI NEWS CURATOR")
    print("=" * 60)

    existing = load_articles()

    fresh_by_category = {}

    total_new = 0

    for category, feeds in RSS_SOURCES.items():

        articles = curate_category(
            category,
            feeds,
        )

        fresh_by_category[category] = articles

        total_new += len(articles)

        print(
            f"{category}: {len(articles)} usable stories"
        )

    final_articles = merge_categories(
        existing["articles"],
        fresh_by_category,
    )

    # Final newest-first order.
    final_articles.sort(
        key=lambda item: item.get("published_at", ""),
        reverse=True,
    )

    output = {
        "version": 1,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "article_count": len(final_articles),

        "categories": {
            category: sum(
                1
                for article in final_articles
                if article.get("category") == category
            )
            for category in RSS_SOURCES.keys()
        },

        "articles": final_articles,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + "=" * 60)
    print("CURATION COMPLETE")
    print("=" * 60)

    print(f"Total articles: {len(final_articles)}")

    for category, count in output["categories"].items():
        print(f"{category}: {count}")

    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()