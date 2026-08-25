import json
import os
import re
import time
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
ARTICLES_FILE = os.path.join(BASE_DIR, "articles.json")

# IMPORTANT:
# Each category will retain the newest 50 stories.
# When more arrive, the oldest are removed first (FIFO).
MAX_PER_CATEGORY = 50

# Fetch timeout for each RSS source.
REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Mozilla/5.0 (compatible; NewsCurator/1.0; "
    "+https://example.com/bot)"
)


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", " ", str(value))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def make_id(value):
    return hashlib.sha256(
        value.encode("utf-8", errors="ignore")
    ).hexdigest()[:24]


def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not read {path}: {e}")
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


# ---------------------------------------------------------
# DATE HANDLING
# ---------------------------------------------------------

def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    # RSS date
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # ISO date
    try:
        value2 = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value2)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return None


def date_to_iso(value):
    dt = parse_date(value)

    if dt:
        return dt.isoformat()

    return now_iso()


# ---------------------------------------------------------
# XML HELPERS
# ---------------------------------------------------------

def local_name(tag):
    """
    Converts:

        {namespace}title

    into:

        title
    """

    if not tag:
        return ""

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def child_text(element, names):
    names = set(names)

    for child in element.iter():
        if child is element:
            continue

        if local_name(child.tag) in names:
            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def child_link(element):
    """
    Supports RSS <link> and Atom <link href="..."/>.
    """

    # First look for normal RSS link.
    for child in element:
        if local_name(child.tag) == "link":
            text = "".join(child.itertext()).strip()

            if text:
                return text

            href = child.attrib.get("href")

            if href:
                return href

    # Fallback search.
    for child in element.iter():
        if child is element:
            continue

        if local_name(child.tag) == "link":
            href = child.attrib.get("href")

            if href:
                return href

    return ""


# ---------------------------------------------------------
# RSS FETCH
# ---------------------------------------------------------

def fetch_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/atom+xml, "
                "application/xml, "
                "text/xml, */*"
            )
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            return response.read()

    except Exception as e:
        print(f"  FAILED: {e}")
        return None


# ---------------------------------------------------------
# RSS / ATOM PARSER
# ---------------------------------------------------------

def parse_feed(xml_data):
    if not xml_data:
        return []

    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"  XML ERROR: {e}")
        return []

    items = []

    # RSS <item>
    for element in root.iter():

        if local_name(element.tag) not in ("item", "entry"):
            continue

        title = child_text(
            element,
            ["title"]
        )

        link = child_link(element)

        description = child_text(
            element,
            [
                "description",
                "summary",
                "content",
                "encoded"
            ]
        )

        guid = child_text(
            element,
            [
                "guid",
                "id"
            ]
        )

        published = child_text(
            element,
            [
                "pubDate",
                "published",
                "updated",
                "date"
            ]
        )

        title = clean_text(title)
        description = clean_text(description)

        if not title:
            continue

        if not link:
            link = guid

        if not link:
            continue

        items.append({
            "title": title,
            "url": link.strip(),
            "description": description,
            "published_at": date_to_iso(published),
            "guid": guid.strip()
        })

    return items


# ---------------------------------------------------------
# SOURCE NORMALIZATION
# ---------------------------------------------------------

def source_name(source):
    return (
        source.get("name")
        or source.get("title")
        or "Unknown Source"
    )


def source_category(source):
    return (
        source.get("category")
        or "General"
    ).strip()


def source_enabled(source):
    return source.get("enabled", True) is True


# ---------------------------------------------------------
# ARTICLE ID
# ---------------------------------------------------------

def article_key(article):
    """
    URL is the strongest duplicate key.
    GUID is used if available.
    Title is final fallback.
    """

    url = str(article.get("url", "")).strip()

    if url:
        return "url:" + url.lower()

    guid = str(article.get("guid", "")).strip()

    if guid:
        return "guid:" + guid.lower()

    title = clean_text(article.get("title", ""))

    return "title:" + title.lower()


# ---------------------------------------------------------
# LOAD EXISTING ARTICLES
# ---------------------------------------------------------

def load_existing_articles():
    data = load_json(
        ARTICLES_FILE,
        []
    )

    if isinstance(data, dict):

        # Support:
        # {"articles": [...]}
        if isinstance(data.get("articles"), list):
            return data["articles"]

        # Support:
        # {"items": [...]}
        if isinstance(data.get("items"), list):
            return data["items"]

        return []

    if isinstance(data, list):
        return data

    return []


# ---------------------------------------------------------
# CLEAN EXISTING DATA
# ---------------------------------------------------------

def normalize_article(article):
    return {
        "id": article.get(
            "id"
        ) or make_id(
            article_key(article)
        ),

        "title": clean_text(
            article.get("title", "")
        ),

        "url": str(
            article.get("url", "")
        ).strip(),

        "description": clean_text(
            article.get("description", "")
        ),

        "published_at": date_to_iso(
            article.get("published_at")
            or article.get("published")
        ),

        "source": article.get(
            "source",
            "Unknown Source"
        ),

        "category": article.get(
            "category",
            "General"
        ),

        "region": article.get(
            "region",
            ""
        ),

        "country": article.get(
            "country",
            ""
        ),

        "state": article.get(
            "state",
            ""
        ),

        "language": article.get(
            "language",
            "English"
        ),

        "guid": article.get(
            "guid",
            ""
        ),

        "added_at": article.get(
            "added_at"
        ) or now_iso()
    }


# ---------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------

def deduplicate_articles(articles):
    result = []
    seen = set()

    for article in articles:

        article = normalize_article(article)

        if not article["title"]:
            continue

        key = article_key(article)

        if key in seen:
            continue

        seen.add(key)
        result.append(article)

    return result


# ---------------------------------------------------------
# FIFO PER CATEGORY
# ---------------------------------------------------------

def apply_fifo(articles):
    """
    Keep only MAX_PER_CATEGORY newest stories
    in each category.

    Oldest stories leave first.

    This is effectively:

        queue.append(new_story)

        while len(queue) > 50:
            queue.pop(0)
    """

    categories = {}

    for article in articles:

        category = (
            article.get("category")
            or "General"
        ).strip()

        categories.setdefault(
            category,
            []
        ).append(article)

    final_articles = []

    for category, category_articles in categories.items():

        # Oldest -> newest
        category_articles.sort(
            key=lambda x: parse_date(
                x.get("published_at")
            ) or datetime.min.replace(
                tzinfo=timezone.utc
            )
        )

        # FIFO:
        # Remove oldest until only 50 remain.
        if len(category_articles) > MAX_PER_CATEGORY:

            category_articles = category_articles[
                -MAX_PER_CATEGORY:
            ]

        final_articles.extend(
            category_articles
        )

    # Newest first for the application UI.
    final_articles.sort(
        key=lambda x: parse_date(
            x.get("published_at")
        ) or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        reverse=True
    )

    return final_articles


# ---------------------------------------------------------
# MAIN CURATOR
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("NEWS CURATOR")
    print("=" * 60)

    sources = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(sources, list):
        print("ERROR: sources.json must contain a JSON array.")
        return

    existing = load_existing_articles()

    print(
        f"Existing articles: {len(existing)}"
    )

    existing = deduplicate_articles(
        existing
    )

    new_articles = []

    enabled_sources = [
        s for s in sources
        if isinstance(s, dict)
        and source_enabled(s)
    ]

    print(
        f"Enabled sources: {len(enabled_sources)}"
    )

    # -----------------------------------------------------
    # FETCH EVERY SOURCE
    # -----------------------------------------------------

    for index, source in enumerate(
        enabled_sources,
        start=1
    ):

        name = source_name(source)
        category = source_category(source)

        feed_url = (
            source.get("feed_url")
            or source.get("url")
            or ""
        ).strip()

        if not feed_url:
            print(
                f"[{index}] {name}: NO FEED URL"
            )
            continue

        print()
        print(
            f"[{index}/{len(enabled_sources)}] "
            f"{name}"
        )
        print(
            f"Category: {category}"
        )

        xml_data = fetch_url(
            feed_url
        )

        if not xml_data:
            continue

        feed_items = parse_feed(
            xml_data
        )

        print(
            f"  Found {len(feed_items)} stories"
        )

        for item in feed_items:

            article = {
                "id": make_id(
                    article_key(item)
                ),

                "title": item["title"],

                "url": item["url"],

                "description": item.get(
                    "description",
                    ""
                ),

                "published_at": item[
                    "published_at"
                ],

                "source": name,

                "category": category,

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

                "guid": item.get(
                    "guid",
                    ""
                ),

                "added_at": now_iso()
            }

            new_articles.append(
                article
            )

        # Small delay so we don't hammer feeds.
        time.sleep(0.25)

    print()
    print("-" * 60)

    print(
        f"New fetched stories: "
        f"{len(new_articles)}"
    )

    # -----------------------------------------------------
    # MERGE
    # -----------------------------------------------------

    combined = (
        existing
        + new_articles
    )

    combined = deduplicate_articles(
        combined
    )

    print(
        f"After deduplication: "
        f"{len(combined)}"
    )

    # -----------------------------------------------------
    # FIFO
    # -----------------------------------------------------

    final_articles = apply_fifo(
        combined
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    save_json(
        ARTICLES_FILE,
        final_articles
    )

    print(
        f"Saved articles: "
        f"{len(final_articles)}"
    )

    # -----------------------------------------------------
    # CATEGORY REPORT
    # -----------------------------------------------------

    category_counts = {}

    for article in final_articles:

        category = article.get(
            "category",
            "General"
        )

        category_counts[
            category
        ] = category_counts.get(
            category,
            0
        ) + 1

    print()
    print("CATEGORY STATUS")
    print("-" * 60)

    for category in sorted(
        category_counts
    ):

        count = category_counts[
            category
        ]

        status = (
            "READY"
            if count >= MAX_PER_CATEGORY
            else "BUILDING"
        )

        print(
            f"{category}: "
            f"{count}/{MAX_PER_CATEGORY} "
            f"[{status}]"
        )

    print()
    print("=" * 60)
    print("CURATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()