import json
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "articles.json")

# ============================================================
# CONFIGURATION
# ============================================================

MINIMUM_PER_CATEGORY = 50
MAX_PER_CATEGORY = 100

USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24-NewsBot/1.0; "
    "+https://snippet24.in)"
)

# ============================================================
# RSS SOURCES
# ============================================================

SOURCES = {

    "India": [
        "https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Indian+politics&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+latest+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+economy&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "World": [
        "https://news.google.com/rss/search?q=World+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=International+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Global+News&hl=en&gl=US&ceid=US:en",
    ],

    "States": [
        "https://news.google.com/rss/search?q=India+states+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Tamil+Nadu+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Kerala+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Karnataka+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Maharashtra+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Andhra+Pradesh+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Telangana+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Delhi+news&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "Tech & AI": [
        "https://news.google.com/rss/search?q=Technology+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Artificial+Intelligence&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=AI+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Startups+Technology&hl=en&gl=US&ceid=US:en",
    ],

    "Business": [
        "https://news.google.com/rss/search?q=Business+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Stock+Market&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Economy+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Indian+Business&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "Lifestyle": [
        "https://news.google.com/rss/search?q=Lifestyle+News&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Health+Lifestyle&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Travel+Lifestyle&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Food+Lifestyle&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Entertainment+Lifestyle&hl=en&gl=US&ceid=US:en",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def parse_date(value):
    if not value:
        return ""

    value = value.strip()

    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass

    return value


def fetch_xml(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )

    with urlopen(request, timeout=20) as response:
        return response.read()


def get_child_text(element, names):
    for name in names:
        child = element.find(name)

        if child is not None and child.text:
            return clean_text(child.text)

    return ""


# ============================================================
# RSS / ATOM PARSER
# ============================================================

def parse_feed(xml_data, category, source_url):
    articles = []

    try:
        root = ET.fromstring(xml_data)
    except Exception as error:
        print("XML error:", error)
        return articles

    # RSS
    items = root.findall(".//item")

    for item in items:

        title = get_child_text(item, ["title"])
        url = get_child_text(item, ["link"])
        description = get_child_text(
            item,
            ["description", "summary"]
        )

        published = get_child_text(
            item,
            ["pubDate", "published", "updated"]
        )

        source = get_child_text(
            item,
            ["source"]
        )

        if not title or not url:
            continue

        title = clean_text(title)
        description = clean_text(description)

        article = {
            "id": make_id(title, url),
            "title": title,
            "description": description,
            "url": url,
            "source": source or "News source",
            "category": category,
            "published_at": parse_date(published),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        articles.append(article)

    # ATOM
    if not items:

        for entry in root.findall(".//{*}entry"):

            title = get_child_text(
                entry,
                ["{*}title"]
            )

            summary = get_child_text(
                entry,
                ["{*}summary", "{*}content"]
            )

            published = get_child_text(
                entry,
                ["{*}published", "{*}updated"]
            )

            url = ""

            for link in entry.findall("{*}link"):
                href = link.attrib.get("href")

                if href:
                    url = href
                    break

            if not title or not url:
                continue

            article = {
                "id": make_id(title, url),
                "title": clean_text(title),
                "description": clean_text(summary),
                "url": url,
                "source": "News source",
                "category": category,
                "published_at": parse_date(published),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            articles.append(article)

    return articles


# ============================================================
# LOAD OLD CACHE
# ============================================================

def load_existing():

    if not os.path.exists(OUTPUT_FILE):
        return {}

    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception as error:
        print("Could not read existing articles.json:", error)

    return {}


# ============================================================
# FIFO MERGE
# ============================================================

def merge_fifo(old_articles, new_articles):

    combined = []

    seen = set()

    # New articles first
    for article in new_articles:

        article_id = article.get("id")

        if not article_id:
            continue

        if article_id in seen:
            continue

        seen.add(article_id)
        combined.append(article)

    # Then cached articles
    for article in old_articles:

        article_id = article.get("id")

        if not article_id:
            continue

        if article_id in seen:
            continue

        seen.add(article_id)
        combined.append(article)

    # Newest first
    combined.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    # FIFO limit
    return combined[:MAX_PER_CATEGORY]


# ============================================================
# FETCH CATEGORY
# ============================================================

def fetch_category(category, urls):

    print()
    print("=" * 60)
    print("CATEGORY:", category)
    print("=" * 60)

    collected = []

    for url in urls:

        try:

            print("Fetching:", url)

            xml_data = fetch_xml(url)

            articles = parse_feed(
                xml_data,
                category,
                url
            )

            print("  Articles:", len(articles))

            collected.extend(articles)

            time.sleep(0.3)

        except Exception as error:

            print(
                "  FAILED:",
                type(error).__name__,
                str(error)
            )

    # Deduplicate
    unique = {}
    for article in collected:
        unique[article["id"]] = article

    result = list(unique.values())

    result.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    print(
        "Unique articles:",
        len(result)
    )

    return result


# ============================================================
# TOP STORIES
# ============================================================

def create_top_stories(categories):

    all_articles = []

    for category, articles in categories.items():

        if category == "Top Stories":
            continue

        for article in articles:

            copy = dict(article)
            copy["category"] = "Top Stories"

            all_articles.append(copy)

    # Remove duplicates
    unique = {}

    for article in all_articles:
        unique[article["id"]] = article

    all_articles = list(unique.values())

    all_articles.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )

    return all_articles[:MAX_PER_CATEGORY]


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==============================================")
    print(" SNIPPET24 NEWS CURATOR")
    print(" 50+ ARTICLES / CATEGORY")
    print(" FIFO CACHE")
    print("==============================================")
    print()

    old_data = load_existing()

    final_data = {}

    # --------------------------------------------------------
    # Fetch every category
    # --------------------------------------------------------

    for category, urls in SOURCES.items():

        old_articles = old_data.get(
            category,
            []
        )

        fresh_articles = fetch_category(
            category,
            urls
        )

        merged = merge_fifo(
            old_articles,
            fresh_articles
        )

        # IMPORTANT:
        # If the network is temporarily unavailable,
        # retain cached articles.
        if len(merged) > 0:

            final_data[category] = merged

        else:

            final_data[category] = old_articles

        print(
            category,
            "=>",
            len(final_data[category]),
            "articles"
        )

    # --------------------------------------------------------
    # Top Stories
    # --------------------------------------------------------

    top_stories = create_top_stories(
        final_data
    )

    old_top = old_data.get(
        "Top Stories",
        []
    )

    final_data["Top Stories"] = merge_fifo(
        old_top,
        top_stories
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    output = {
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "minimum_per_category":
            MINIMUM_PER_CATEGORY,

        "maximum_per_category":
            MAX_PER_CATEGORY,

        "fifo": True,

        "categories": final_data
    }

    # --------------------------------------------------------
    # Write atomically
    # --------------------------------------------------------

    temp_file = OUTPUT_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        OUTPUT_FILE
    )

    print()
    print("==============================================")
    print(" DONE")
    print(" Output:", OUTPUT_FILE)
    print("==============================================")

    for category, articles in final_data.items():

        status = (
            "OK"
            if len(articles) >= MINIMUM_PER_CATEGORY
            else "CACHE / NEED MORE SOURCES"
        )

        print(
            f"{category}: "
            f"{len(articles)} "
            f"[{status}]"
        )


if __name__ == "__main__":
    main()