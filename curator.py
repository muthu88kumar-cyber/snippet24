#!/usr/bin/env python3

"""
Snippet24 News Curator
----------------------

Goals:
- No third-party Python packages required.
- Fetch real RSS news.
- Minimum 50 articles per category when feeds provide enough articles.
- Maximum 100 articles per category.
- FIFO: newest articles enter at the back; oldest are removed first.
- Preserve previously stored articles if a feed temporarily fails.
- Deduplicate articles.
- Generate articles.json.
- Never replace a good existing database with an empty one.
"""

import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_FILE = BASE_DIR / "articles.json"

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

REQUEST_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/1.0; "
    "+https://snippet24.in)"
)

# Categories shown on your website.
CATEGORIES = [
    "World",
    "India",
    "States",
    "Tech & AI",
    "Business",
    "Lifestyle",
]

# ============================================================
# RSS SEARCHES
# ============================================================
#
# Google News RSS search feeds are used instead of feedparser.
# Multiple searches are used so one failed source does not
# destroy the entire category.
#

SEARCHES = {

    "World": [
        "world news",
        "international news",
        "global politics",
        "global economy",
        "United Nations",
        "Europe news",
        "Asia news",
        "Middle East news",
        "US international news",
    ],

    "India": [
        "India news",
        "Indian politics",
        "India government",
        "India economy",
        "India Supreme Court",
        "India Parliament",
        "Indian Express India",
        "Hindustan Times India",
        "NDTV India",
    ],

    "States": [
        "Tamil Nadu news",
        "Karnataka news",
        "Kerala news",
        "Andhra Pradesh news",
        "Telangana news",
        "Maharashtra news",
        "Delhi news",
        "Uttar Pradesh news",
        "West Bengal news",
        "Gujarat news",
        "Rajasthan news",
        "Madhya Pradesh news",
        "Bihar news",
        "Punjab India news",
        "Odisha news",
    ],

    "Tech & AI": [
        "technology news",
        "artificial intelligence AI news",
        "OpenAI news",
        "Google AI news",
        "Microsoft AI news",
        "Apple technology news",
        "Meta AI news",
        "Nvidia news",
        "cybersecurity news",
        "semiconductor news",
        "startup technology India",
    ],

    "Business": [
        "business news",
        "India business news",
        "stock market India",
        "Indian economy",
        "global economy",
        "finance news",
        "banking India",
        "startup funding India",
        "markets news",
        "companies India",
    ],

    "Lifestyle": [
        "lifestyle news",
        "health lifestyle news",
        "travel news",
        "food news",
        "entertainment news",
        "culture news",
        "fashion news",
        "fitness lifestyle",
        "science lifestyle",
        "education news",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    # Remove HTML.
    value = re.sub(r"<[^>]+>", " ", value)

    # Normalize whitespace.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:24]


def parse_date(value):
    if not value:
        return ""

    value = clean_text(value)

    # RFC822 / RSS dates.
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        pass

    # ISO dates.
    try:
        value2 = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value2)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        return ""


def get_text(element, names):
    for name in names:
        child = element.find(name)

        if child is not None:
            text = child.text

            if text:
                return clean_text(text)

    return ""


def get_link(element):
    # RSS <link>
    child = element.find("link")

    if child is not None and child.text:
        return child.text.strip()

    # Atom <link href="...">
    for child in element:
        if child.tag.endswith("link"):
            href = child.attrib.get("href")

            if href:
                return href.strip()

    return ""


def source_from_item(item):
    source = item.find("source")

    if source is not None and source.text:
        return clean_text(source.text)

    return "RSS"


# ============================================================
# GOOGLE NEWS RSS
# ============================================================

def google_news_url(query):
    encoded = quote(query)

    return (
        "https://news.google.com/rss/search"
        f"?q={encoded}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


def download(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def parse_rss(xml_data, category):
    articles = []

    try:
        root = ET.fromstring(xml_data)
    except Exception as exc:
        print(f"XML parse failed: {exc}")
        return articles

    # RSS <item>
    items = root.findall(".//item")

    # Atom fallback.
    if not items:
        items = [
            element
            for element in root.iter()
            if element.tag.endswith("entry")
        ]

    for item in items:

        title = get_text(
            item,
            ["title", "{http://www.w3.org/2005/Atom}title"],
        )

        description = get_text(
            item,
            [
                "description",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
            ],
        )

        link = get_link(item)

        published = get_text(
            item,
            [
                "pubDate",
                "published",
                "updated",
                "{http://www.w3.org/2005/Atom}published",
                "{http://www.w3.org/2005/Atom}updated",
            ],
        )

        source = source_from_item(item)

        title = clean_text(title)
        description = clean_text(description)

        if not title or not link:
            continue

        published_at = parse_date(published)

        if not published_at:
            published_at = now_iso()

        article = {
            "id": make_id(title, link),
            "title": title,
            "description": description[:1000],
            "url": link,
            "source": source,
            "category": category,
            "published_at": published_at,
            "fetched_at": now_iso(),
        }

        articles.append(article)

    return articles


# ============================================================
# LOAD OLD DATABASE
# ============================================================

def empty_database():
    return {
        "updated_at": now_iso(),
        "minimum_per_category": MINIMUM_PER_CATEGORY,
        "maximum_per_category": MAXIMUM_PER_CATEGORY,
        "fifo": True,
        "categories": {
            category: []
            for category in CATEGORIES
        },
    }


def load_database():
    if not ARTICLES_FILE.exists():
        print("articles.json does not exist. Creating new database.")
        return empty_database()

    try:
        with ARTICLES_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Root JSON is not an object.")

        data.setdefault("categories", {})

        for category in CATEGORIES:
            if not isinstance(
                data["categories"].get(category),
                list
            ):
                data["categories"][category] = []

        return data

    except Exception as exc:
        print(f"Could not read articles.json: {exc}")

        # IMPORTANT:
        # Do not destroy a valid file because of a temporary error.
        return empty_database()


# ============================================================
# DEDUPLICATION
# ============================================================

def normalize_url(url):
    url = url.strip()

    # Remove tracking parameters commonly added to RSS URLs.
    url = re.sub(r"[?&](utm_[^=&]+|ocid|ved|usg)=[^&]*", "", url)

    return url.rstrip("?")


def deduplicate(articles):
    result = []
    seen_ids = set()
    seen_urls = set()

    for article in articles:

        article_id = article.get("id", "")
        url = normalize_url(article.get("url", ""))

        if not article_id:
            continue

        if article_id in seen_ids:
            continue

        if url and url in seen_urls:
            continue

        seen_ids.add(article_id)

        if url:
            seen_urls.add(url)

        article["url"] = url

        result.append(article)

    return result


# ============================================================
# FIFO DATABASE UPDATE
# ============================================================

def update_category(category, fresh_articles, old_articles):
    print()
    print("=" * 60)
    print(category)
    print("=" * 60)

    fresh_articles = deduplicate(fresh_articles)
    old_articles = deduplicate(old_articles)

    print(f"Fresh articles: {len(fresh_articles)}")
    print(f"Existing articles: {len(old_articles)}")

    # Fresh articles first.
    combined = fresh_articles + old_articles

    combined = deduplicate(combined)

    # Sort newest first.
    def sort_key(article):
        return article.get("published_at", "")

    combined.sort(
        key=sort_key,
        reverse=True
    )

    # FIFO:
    # Keep the newest MAXIMUM_PER_CATEGORY articles.
    combined = combined[:MAXIMUM_PER_CATEGORY]

    print(f"Final articles: {len(combined)}")

    if len(combined) < MINIMUM_PER_CATEGORY:
        print(
            f"WARNING: {category} has only "
            f"{len(combined)} articles."
        )
        print(
            "The program will NOT create fake articles."
        )

    return combined


# ============================================================
# FETCH CATEGORY
# ============================================================

def fetch_category(category):
    all_articles = []

    searches = SEARCHES.get(category, [])

    print()
    print(f"Fetching category: {category}")

    for query in searches:

        url = google_news_url(query)

        print(f"  RSS: {query}")

        try:
            data = download(url)

            articles = parse_rss(
                data,
                category
            )

            print(
                f"     -> {len(articles)} articles"
            )

            all_articles.extend(articles)

        except Exception as exc:
            print(
                f"     -> FAILED: {exc}"
            )

        # Avoid hammering the RSS service.
        time.sleep(0.25)

    return deduplicate(all_articles)


# ============================================================
# SAVE DATABASE
# ============================================================

def save_database(database):
    temp_file = ARTICLES_FILE.with_suffix(
        ".json.tmp"
    )

    database["updated_at"] = now_iso()

    database["minimum_per_category"] = (
        MINIMUM_PER_CATEGORY
    )

    database["maximum_per_category"] = (
        MAXIMUM_PER_CATEGORY
    )

    database["fifo"] = True

    with temp_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            database,
            file,
            ensure_ascii=False,
            indent=2
        )

        file.write("\n")

    # Atomic replacement.
    temp_file.replace(ARTICLES_FILE)

    print()
    print(f"Saved: {ARTICLES_FILE}")


# ============================================================
# VALIDATION
# ============================================================

def validate(database):
    print()
    print("=" * 60)
    print("FINAL VALIDATION")
    print("=" * 60)

    total = 0
    failed = []

    for category in CATEGORIES:

        articles = database["categories"].get(
            category,
            []
        )

        count = len(articles)

        total += count

        print(
            f"{category:15} : {count:3} articles"
        )

        if count < MINIMUM_PER_CATEGORY:
            failed.append(
                f"{category}: {count}"
            )

    print("-" * 60)
    print(f"TOTAL ARTICLES: {total}")

    if failed:
        print()
        print("WARNING:")
        for item in failed:
            print(f"  {item}")

        print()
        print(
            "Some categories have fewer than 50 "
            "REAL articles."
        )

        print(
            "No fake articles were generated."
        )

    else:
        print()
        print(
            "SUCCESS: Every category contains "
            f"at least {MINIMUM_PER_CATEGORY} articles."
        )

    # The critical test:
    if total == 0:
        raise RuntimeError(
            "articles.json contains no articles."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==============================================")
    print("        SNIPPET24 NEWS CURATOR")
    print("==============================================")
    print()
    print("No feedparser required.")
    print(
        f"Minimum/category: {MINIMUM_PER_CATEGORY}"
    )
    print(
        f"Maximum/category: {MAXIMUM_PER_CATEGORY}"
    )
    print("FIFO: ENABLED")
    print()

    database = load_database()

    for category in CATEGORIES:

        old_articles = database["categories"].get(
            category,
            []
        )

        fresh_articles = fetch_category(
            category
        )

        database["categories"][category] = (
            update_category(
                category,
                fresh_articles,
                old_articles
            )
        )

    save_database(database)

    validate(database)

    print()
    print("==============================================")
    print("CURATION COMPLETE")
    print("==============================================")


if __name__ == "__main__":
    main()