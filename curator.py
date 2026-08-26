import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests


ROOT = Path(__file__).resolve().parent

SOURCES_FILE = ROOT / "sources.json"
OUTPUT_FILE = ROOT / "articles.json"

MIN_PER_CATEGORY = 50
MAX_PER_CATEGORY = 100

REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Snippet24News/1.0; "
        "+https://snippet24.in)"
    )
}


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    if url.startswith("//"):
        url = "https:" + url

    return url


def article_id(title, url):
    raw = f"{title.strip().lower()}|{normalize_url(url).lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def parse_date(entry):
    for key in (
        "published_parsed",
        "updated_parsed",
        "created_parsed",
    ):
        value = entry.get(key)

        if value:
            try:
                return datetime(
                    value.tm_year,
                    value.tm_mon,
                    value.tm_mday,
                    value.tm_hour,
                    value.tm_min,
                    value.tm_sec,
                    tzinfo=timezone.utc,
                ).isoformat()
            except Exception:
                pass

    return datetime.now(timezone.utc).isoformat()


def get_description(entry):
    description = (
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    description = clean_text(description)

    if len(description) > 700:
        description = description[:697] + "..."

    return description


def get_image(entry):
    media = entry.get("media_content")

    if media and isinstance(media, list):
        for item in media:
            if isinstance(item, dict):
                url = item.get("url")
                if url:
                    return normalize_url(url)

    media = entry.get("media_thumbnail")

    if media and isinstance(media, list):
        for item in media:
            if isinstance(item, dict):
                url = item.get("url")
                if url:
                    return normalize_url(url)

    for enclosure in entry.get("enclosures", []):
        if isinstance(enclosure, dict):
            url = enclosure.get("href") or enclosure.get("url")
            mime = enclosure.get("type", "")

            if url and (
                mime.startswith("image/")
                or re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", url, re.I)
            ):
                return normalize_url(url)

    return ""


def load_sources():
    if not SOURCES_FILE.exists():
        raise RuntimeError("sources.json not found")

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        sources = data.get("sources", data)
    elif isinstance(data, list):
        sources = data
    else:
        sources = []

    return sources


def source_name(source):
    if isinstance(source, dict):
        return (
            source.get("name")
            or source.get("source")
            or source.get("publisher")
            or "Unknown Source"
        )

    return "Unknown Source"


def source_url(source):
    if isinstance(source, dict):
        return (
            source.get("url")
            or source.get("feed")
            or source.get("rss")
            or ""
        )

    return str(source)


def source_categories(source):
    if not isinstance(source, dict):
        return []

    categories = (
        source.get("categories")
        or source.get("category")
        or []
    )

    if isinstance(categories, str):
        return [categories]

    if isinstance(categories, list):
        return [str(x) for x in categories if x]

    return []


def fetch_feed(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        parsed = feedparser.parse(response.content)

        return parsed

    except Exception as exc:
        print(f"Feed failed: {url} -> {exc}")
        return None


def make_article(entry, source, category):
    title = clean_text(entry.get("title", ""))
    url = normalize_url(
        entry.get("link")
        or entry.get("guid")
        or ""
    )

    if not title or not url:
        return None

    publisher = source_name(source)

    article = {
        "id": article_id(title, url),
        "title": title,
        "description": get_description(entry),
        "url": url,
        "source": publisher,
        "category": category,
        "published_at": parse_date(entry),
        "image": get_image(entry),
        "language": "en",
        "country": "IN",
        "domain": urlparse(url).netloc,
    }

    return article


def load_existing():
    if not OUTPUT_FILE.exists():
        return []

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            articles = data.get("articles", [])
        elif isinstance(data, list):
            articles = data
        else:
            articles = []

        if not isinstance(articles, list):
            return []

        return articles

    except Exception as exc:
        print(f"Existing articles.json could not be read: {exc}")
        return []


def unique_articles(items):
    seen = set()
    result = []

    for article in items:
        if not isinstance(article, dict):
            continue

        title = clean_text(article.get("title", ""))
        url = normalize_url(article.get("url", ""))

        if not title or not url:
            continue

        key = (
            article.get("id")
            or article_id(title, url)
        )

        if key in seen:
            continue

        seen.add(key)

        article["id"] = key
        article["title"] = title
        article["url"] = url

        result.append(article)

    return result


def fetch_new_articles():
    sources = load_sources()

    all_new = []

    for source in sources:
        feed_url = source_url(source)

        if not feed_url:
            continue

        categories = source_categories(source)

        if not categories:
            categories = ["Top Stories"]

        print(f"Fetching: {source_name(source)}")

        feed = fetch_feed(feed_url)

        if not feed:
            continue

        entries = feed.entries[:150]

        for entry in entries:
            for category in categories:
                article = make_article(
                    entry,
                    source,
                    category,
                )

                if article:
                    all_new.append(article)

        time.sleep(0.2)

    return unique_articles(all_new)


def normalize_categories(articles):
    result = []

    for article in articles:
        if not isinstance(article, dict):
            continue

        category = clean_text(
            article.get("category")
            or "Top Stories"
        )

        article["category"] = category

        result.append(article)

    return result


def group_by_category(articles):
    groups = {}

    for article in articles:
        category = article.get("category", "Top Stories")

        if category not in groups:
            groups[category] = []

        groups[category].append(article)

    return groups


def fifo_merge(existing, new):
    """
    FIFO strategy:
    Existing articles are retained first.
    New articles are added after them.
    The oldest entries are removed when a category exceeds
    MAX_PER_CATEGORY.

    New articles are then moved to the front for display.
    """

    existing = unique_articles(existing)
    new = unique_articles(new)

    combined = existing + new

    combined = unique_articles(combined)

    groups = group_by_category(combined)

    final = []

    for category, items in groups.items():

        # Newest first
        items.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True,
        )

        # Keep maximum
        items = items[:MAX_PER_CATEGORY]

        final.extend(items)

    return unique_articles(final)


def ensure_minimum_categories(articles):
    """
    We never manufacture fake news.

    If a category has fewer than 50 real RSS articles,
    we keep every valid article available from its feeds.
    """

    groups = group_by_category(articles)

    for category in sorted(groups):
        count = len(groups[category])

        if count < MIN_PER_CATEGORY:
            print(
                f"WARNING: {category} has only "
                f"{count} real articles; "
                f"target is {MIN_PER_CATEGORY}."
            )

    return articles


def sort_articles(articles):
    return sorted(
        articles,
        key=lambda x: x.get("published_at", ""),
        reverse=True,
    )


def build_output(articles):
    articles = normalize_categories(articles)
    articles = unique_articles(articles)
    articles = sort_articles(articles)

    categories = {}

    for article in articles:
        category = article["category"]

        if category not in categories:
            categories[category] = 0

        categories[category] += 1

    output = {
        "version": 1,
        "site": "Snippet24 News",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "language": "en-IN",
        "country": "IN",
        "minimum_per_category": MIN_PER_CATEGORY,
        "maximum_per_category": MAX_PER_CATEGORY,
        "fifo": True,
        "total_articles": len(articles),
        "category_counts": categories,
        "articles": articles,
    }

    return output


def validate_output(data):
    if not isinstance(data, dict):
        raise ValueError("Root must be a JSON object")

    required = [
        "version",
        "site",
        "generated_at",
        "articles",
    ]

    for field in required:
        if field not in data:
            raise ValueError(
                f"Missing required field: {field}"
            )

    if not isinstance(data["articles"], list):
        raise ValueError(
            "'articles' must be an array"
        )

    seen = set()

    for index, article in enumerate(data["articles"]):

        if not isinstance(article, dict):
            raise ValueError(
                f"Article {index} is not an object"
            )

        for field in (
            "id",
            "title",
            "url",
            "source",
            "category",
            "published_at",
        ):
            if not article.get(field):
                raise ValueError(
                    f"Article {index} missing '{field}'"
                )

        article_id_value = article["id"]

        if article_id_value in seen:
            raise ValueError(
                f"Duplicate article id: {article_id_value}"
            )

        seen.add(article_id_value)

    return True


def save_output(data):
    temporary = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # Validate the exact bytes we are going to publish
    with open(
        temporary,
        "r",
        encoding="utf-8",
    ) as f:
        check = json.load(f)

    validate_output(check)

    temporary.replace(OUTPUT_FILE)


def main():
    print("======================================")
    print("Snippet24 News Curator")
    print("======================================")

    existing = load_existing()

    print(
        f"Existing articles: {len(existing)}"
    )

    new_articles = fetch_new_articles()

    print(
        f"New articles: {len(new_articles)}"
    )

    merged = fifo_merge(
        existing,
        new_articles,
    )

    merged = ensure_minimum_categories(
        merged
    )

    output = build_output(merged)

    validate_output(output)

    save_output(output)

    print(
        f"Saved {len(output['articles'])} articles"
    )

    print("Category counts:")

    for category, count in sorted(
        output["category_counts"].items()
    ):
        print(
            f"  {category}: {count}"
        )

    print("SUCCESS")


if __name__ == "__main__":
    main()