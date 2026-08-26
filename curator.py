import json
import os
import re
import html
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
ARTICLES_FILE = os.path.join(BASE_DIR, "articles.json")

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Snippet24NewsBot/2.0; "
        "+https://snippet24.in)"
    )
}


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url):
    if not url:
        return ""

    return url.strip()


def parse_date(entry):
    for key in ["published", "updated", "created"]:
        value = entry.get(key)

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


def google_news_rss(query):
    encoded_query = requests.utils.quote(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


def get_source_name(entry):
    source = entry.get("source")

    if isinstance(source, dict):
        name = source.get("title")
        if name:
            return clean_text(name)

    title = clean_text(entry.get("title", ""))

    if " - " in title:
        parts = title.rsplit(" - ", 1)

        if len(parts) == 2:
            return parts[1].strip()

    return "News source"


def get_article_title(entry):
    title = clean_text(entry.get("title", ""))

    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()

    return title


def get_summary(entry):
    summary = (
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    summary = clean_text(summary)

    return summary[:500]


def fetch_feed(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        parsed = feedparser.parse(response.content)

        if parsed.bozo and not parsed.entries:
            return []

        return parsed.entries

    except Exception as exc:
        print(f"Feed error: {url}")
        print(f"Reason: {exc}")
        return []


def collect_category(category, queries):
    articles = []
    seen_urls = set()
    seen_titles = set()

    print("")
    print("=" * 60)
    print(f"COLLECTING: {category}")
    print("=" * 60)

    for query in queries:
        print(f"Query: {query}")

        url = google_news_rss(query)

        entries = fetch_feed(url)

        print(f"  Found: {len(entries)}")

        for entry in entries:

            title = get_article_title(entry)

            link = normalize_url(entry.get("link", ""))

            if not title or not link:
                continue

            title_key = re.sub(
                r"[^a-z0-9]+",
                " ",
                title.lower()
            ).strip()

            if link in seen_urls:
                continue

            if title_key in seen_titles:
                continue

            seen_urls.add(link)
            seen_titles.add(title_key)

            article = {
                "id": "",
                "category": category,
                "language": "en",
                "title": title,
                "summary": get_summary(entry),
                "source": get_source_name(entry),
                "url": link,
                "published_at": parse_date(entry)
            }

            articles.append(article)

        time.sleep(0.3)

    articles.sort(
        key=lambda item: item["published_at"],
        reverse=True
    )

    for index, article in enumerate(articles):
        article["id"] = f"{category.lower().replace(' ', '-')}-{index + 1}"

    articles = articles[:MAXIMUM_PER_CATEGORY]

    print(f"FINAL {category}: {len(articles)} articles")

    return articles


def load_previous_articles():
    if not os.path.exists(ARTICLES_FILE):
        return {}

    try:
        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data.get("categories", {})

    except Exception as exc:
        print(f"Could not read previous articles: {exc}")

    return {}


def merge_fifo(previous, fresh):
    """
    FIFO-style retention.

    New stories are added.
    Duplicate stories are removed.
    The newest 100 stories are retained.
    Oldest stories are discarded.
    """

    combined = []

    seen = set()

    for article in fresh + previous:

        url = article.get("url", "").strip()

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)

        combined.append(article)

    combined.sort(
        key=lambda item: item.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    return combined[:MAXIMUM_PER_CATEGORY]


def save_articles(categories):
    total = sum(
        len(items)
        for items in categories.values()
    )

    output = {
        "version": 2,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "minimum_per_category": MINIMUM_PER_CATEGORY,
        "maximum_per_category": MAXIMUM_PER_CATEGORY,
        "total": total,
        "categories": categories
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

    print("")
    print("=" * 60)
    print("ARTICLES.JSON CREATED")
    print("=" * 60)

    for category, items in categories.items():
        print(f"{category}: {len(items)}")

    print(f"TOTAL: {total}")


def validate(categories):

    print("")
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    failed = False

    for category, items in categories.items():

        count = len(items)

        print(f"{category}: {count}")

        if count < MINIMUM_PER_CATEGORY:
            print(
                f"ERROR: {category} has only "
                f"{count} articles"
            )
            failed = True

    total = sum(
        len(items)
        for items in categories.values()
    )

    print(f"TOTAL: {total}")

    if failed:
        raise SystemExit(1)

    print("VALIDATION PASSED")


def main():

    print("=" * 60)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 60)

    with open(
        SOURCES_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    category_queries = config["categories"]

    previous = load_previous_articles()

    categories = {}

    for category, queries in category_queries.items():

        fresh = collect_category(
            category,
            queries
        )

        old = previous.get(
            category,
            []
        )

        categories[category] = merge_fifo(
            old,
            fresh
        )

    save_articles(categories)

    validate(categories)

    print("")
    print("DONE")


if __name__ == "__main__":
    main()