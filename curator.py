import json
import hashlib
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


ARTICLES_FILE = "articles.json"

MIN_ARTICLES_PER_CATEGORY = 50
MAX_ARTICLES_PER_CATEGORY = 100

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Snippet24/1.0 "
    "(https://snippet24.in)"
)


# ============================================================
# CATEGORIES
# ============================================================

CATEGORIES = {
    "India": [
        "India latest news",
        "India breaking news",
        "Indian politics",
        "India national news",
        "India economy",
        "India government",
        "India Supreme Court",
        "India parliament",
    ],

    "States": [
        "Tamil Nadu latest news",
        "Karnataka latest news",
        "Kerala latest news",
        "Andhra Pradesh latest news",
        "Telangana latest news",
        "Maharashtra latest news",
        "Gujarat latest news",
        "Delhi latest news",
        "Uttar Pradesh latest news",
        "West Bengal latest news",
        "Rajasthan latest news",
        "Madhya Pradesh latest news",
        "Odisha latest news",
    ],

    "Tech & AI": [
        "technology latest news",
        "artificial intelligence latest news",
        "AI latest news",
        "Google AI latest news",
        "Microsoft AI latest news",
        "Apple technology latest news",
        "OpenAI latest news",
        "cybersecurity latest news",
        "semiconductor latest news",
        "startup technology India",
    ],

    "Business": [
        "India business latest news",
        "business latest news",
        "Indian economy latest news",
        "stock market India latest",
        "finance India latest news",
        "banking India latest news",
        "startup India latest news",
        "companies India latest news",
        "markets latest news",
    ],

    "Lifestyle": [
        "lifestyle latest news",
        "travel latest news",
        "food latest news",
        "fashion latest news",
        "entertainment latest news",
        "movies latest news India",
        "culture latest news",
        "wellness lifestyle news",
    ],
}


# ============================================================
# TIME
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = str(value)

    value = re.sub(
        r"<script.*?</script>",
        " ",
        value,
        flags=re.I | re.S,
    )

    value = re.sub(
        r"<style.*?</style>",
        " ",
        value,
        flags=re.I | re.S,
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# DATE
# ============================================================

def parse_date(value):

    if not value:
        return now_iso()

    value = clean_text(value)

    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        ).isoformat()

    except Exception:
        return now_iso()


# ============================================================
# ID
# ============================================================

def article_id(title, url):

    value = (
        clean_text(title).lower()
        + "|"
        + url.strip().lower()
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:24]


# ============================================================
# GOOGLE NEWS RSS
# ============================================================

def google_news_url(query):

    encoded = urllib.parse.quote(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


# ============================================================
# FETCH RSS
# ============================================================

def fetch_rss(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml,"
                "application/xml,"
                "text/xml"
            ),
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:

            data = response.read()

        root = ET.fromstring(data)

    except Exception as error:

        print(
            f"[RSS FAILED] {error}"
        )

        return []

    results = []

    for item in root.findall(".//item"):

        title = clean_text(
            item.findtext(
                "title",
                default="",
            )
        )

        link = clean_text(
            item.findtext(
                "link",
                default="",
            )
        )

        description = clean_text(
            item.findtext(
                "description",
                default="",
            )
        )

        published = clean_text(
            item.findtext(
                "pubDate",
                default="",
            )
        )

        source = ""

        source_element = item.find(
            "source"
        )

        if source_element is not None:
            source = clean_text(
                source_element.text
                or ""
            )

        if not title or not link:
            continue

        results.append(
            {
                "title": title,
                "url": link,
                "description": description,
                "published_at": parse_date(
                    published
                ),
                "source": source,
            }
        )

    return results


# ============================================================
# NORMALIZE
# ============================================================

def normalize(item, category):

    title = clean_text(
        item.get("title", "")
    )

    url = clean_text(
        item.get("url", "")
    )

    if not title or not url:
        return None

    description = clean_text(
        item.get("description", "")
    )

    # Keep descriptions short.
    if len(description) > 500:
        description = (
            description[:497]
            + "..."
        )

    return {
        "id": article_id(
            title,
            url,
        ),
        "title": title,
        "description": description,
        "url": url,
        "source": (
            clean_text(
                item.get("source", "")
            )
            or "News source"
        ),
        "category": category,
        "published_at": item.get(
            "published_at",
            now_iso(),
        ),
    }


# ============================================================
# LOAD EXISTING DATA
# ============================================================

def load_existing():

    if not os.path.exists(
        ARTICLES_FILE
    ):
        return {
            "articles": []
        }

    try:

        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return {
                "articles": data
            }

        if isinstance(data, dict):

            return {
                "articles": data.get(
                    "articles",
                    [],
                )
            }

    except Exception as error:

        print(
            "[JSON WARNING]",
            error,
        )

    return {
        "articles": []
    }


# ============================================================
# CURATE ONE CATEGORY
# ============================================================

def curate_category(
    category,
    queries,
):

    print("")
    print(
        "=" * 60
    )
    print(
        f"CATEGORY: {category}"
    )
    print(
        "=" * 60
    )

    collected = []

    for query in queries:

        print(
            f"Searching: {query}"
        )

        url = google_news_url(
            query
        )

        items = fetch_rss(url)

        print(
            f"  received: {len(items)}"
        )

        for item in items:

            article = normalize(
                item,
                category,
            )

            if article:
                collected.append(
                    article
                )

        time.sleep(0.25)

    # Remove duplicates.
    unique = {}

    for article in collected:

        unique[
            article["id"]
        ] = article

    articles = list(
        unique.values()
    )

    # Newest first.
    articles.sort(
        key=lambda x: x.get(
            "published_at",
            "",
        ),
        reverse=True,
    )

    print(
        f"Unique: {len(articles)}"
    )

    return articles


# ============================================================
# MERGE + FIFO
# ============================================================

def merge_articles(
    existing,
    incoming,
):

    all_articles = (
        existing
        + incoming
    )

    # --------------------------------------------------------
    # GLOBAL DUPLICATE REMOVAL
    # --------------------------------------------------------

    unique = {}

    for article in all_articles:

        aid = article.get(
            "id"
        )

        if not aid:

            aid = article_id(
                article.get(
                    "title",
                    "",
                ),
                article.get(
                    "url",
                    "",
                ),
            )

            article["id"] = aid

        unique[aid] = article

    all_articles = list(
        unique.values()
    )

    # --------------------------------------------------------
    # GROUP BY CATEGORY
    # --------------------------------------------------------

    grouped = {}

    for article in all_articles:

        category = article.get(
            "category",
            "India",
        )

        grouped.setdefault(
            category,
            [],
        ).append(article)

    final = []

    # --------------------------------------------------------
    # FIFO
    # --------------------------------------------------------

    for category in CATEGORIES:

        articles = grouped.get(
            category,
            [],
        )

        # Oldest first.
        articles.sort(
            key=lambda x: x.get(
                "published_at",
                "",
            )
        )

        # Keep newest MAX.
        if len(articles) > MAX_ARTICLES_PER_CATEGORY:

            articles = articles[
                -MAX_ARTICLES_PER_CATEGORY:
            ]

        # Add to final collection.
        final.extend(
            articles
        )

        print(
            f"{category}: "
            f"{len(articles)} stored"
        )

    # Newest first for website.
    final.sort(
        key=lambda x: x.get(
            "published_at",
            "",
        ),
        reverse=True,
    )

    return final


# ============================================================
# SAVE ATOMICALLY
# ============================================================

def save_articles(articles):

    data = {
        "updated_at": now_iso(),
        "article_count": len(
            articles
        ),
        "categories": {
            category: sum(
                1
                for article in articles
                if article.get(
                    "category"
                ) == category
            )
            for category in CATEGORIES
        },
        "articles": articles,
    }

    temp_file = (
        ARTICLES_FILE
        + ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temp_file,
        ARTICLES_FILE,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print(
        "=========================================="
    )
    print(
        "        SNIPPET24 NEWS CURATOR"
    )
    print(
        "=========================================="
    )

    old_data = load_existing()

    existing = old_data.get(
        "articles",
        [],
    )

    print(
        f"Existing articles: "
        f"{len(existing)}"
    )

    incoming = []

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    for category, queries in CATEGORIES.items():

        articles = curate_category(
            category,
            queries,
        )

        incoming.extend(
            articles
        )

    print("")
    print(
        f"New articles collected: "
        f"{len(incoming)}"
    )

    # --------------------------------------------------------
    # MERGE + FIFO
    # --------------------------------------------------------

    final_articles = merge_articles(
        existing,
        incoming,
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_articles(
        final_articles
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print("")
    print(
        "=========================================="
    )
    print(
        "              FINAL STATUS"
    )
    print(
        "=========================================="
    )

    failed_categories = []

    for category in CATEGORIES:

        count = sum(
            1
            for article in final_articles
            if article.get(
                "category"
            ) == category
        )

        if count < MIN_ARTICLES_PER_CATEGORY:

            failed_categories.append(
                category
            )

        print(
            f"{category}: "
            f"{count} articles"
        )

    print("")
    print(
        f"TOTAL: "
        f"{len(final_articles)}"
    )

    if failed_categories:

        print("")
        print(
            "WARNING:"
        )

        print(
            "These categories have "
            "less than 50 articles:"
        )

        for category in failed_categories:
            print(
                f" - {category}"
            )

        # IMPORTANT:
        # Do NOT erase the existing data.
        # Existing articles remain available.

    else:

        print("")
        print(
            "SUCCESS: Every category "
            "has at least 50 articles."
        )

    print("")
    print(
        "articles.json updated."
    )


if __name__ == "__main__":
    main()