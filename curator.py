import json
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET

ARTICLES_FILE = "articles.json"
SOURCES_FILE = "sources.json"

# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

MAX_TOTAL = 300
MIN_TOTAL = 50

CATEGORIES = [
    "India",
    "World",
    "States",
    "Tech & AI",
    "Business",
    "Lifestyle",
]

# We want every category represented.
MIN_PER_CATEGORY = 8

USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/1.0; "
    "+https://snippet24.in)"
)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def make_id(title, link):
    raw = f"{title}|{link}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def fetch_url(url, timeout=20):
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as exc:
        print(f"FETCH ERROR: {url}")
        print(exc)
        return b""


def tag_name(element):
    return element.tag.split("}")[-1].lower()


def get_child_text(element, names):
    names = {n.lower() for n in names}

    for child in list(element):
        if tag_name(child) in names:
            return clean_text(child.text)

    return ""


def parse_rss(data, source):
    if not data:
        return []

    try:
        root = ET.fromstring(data)
    except Exception as exc:
        print("XML ERROR:", exc)
        return []

    items = []

    # RSS <item>
    for element in root.iter():
        if tag_name(element) != "item":
            continue

        title = get_child_text(element, {"title"})
        link = get_child_text(element, {"link"})
        description = get_child_text(
            element,
            {"description", "summary", "content"},
        )
        published = get_child_text(
            element,
            {
                "pubdate",
                "published",
                "updated",
                "date",
            },
        )

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "published": published,
                "source": source,
            }
        )

    return items


# ---------------------------------------------------------
# CATEGORY DETECTION
# ---------------------------------------------------------

def detect_category(title, description, source_category=""):
    text = (
        f"{title} {description} {source_category}"
    ).lower()

    tech_words = [
        "technology",
        "tech",
        "ai",
        "artificial intelligence",
        "software",
        "google",
        "apple",
        "microsoft",
        "openai",
        "chip",
        "semiconductor",
        "cyber",
        "iphone",
        "android",
        "startup",
        "robot",
    ]

    business_words = [
        "business",
        "economy",
        "market",
        "stock",
        "stocks",
        "finance",
        "bank",
        "banking",
        "rupee",
        "investment",
        "company",
        "corporate",
        "trade",
        "ipo",
        "profit",
    ]

    lifestyle_words = [
        "lifestyle",
        "health",
        "food",
        "travel",
        "fashion",
        "culture",
        "fitness",
        "entertainment",
        "movie",
        "music",
        "sports",
    ]

    state_words = [
        "tamil nadu",
        "kerala",
        "karnataka",
        "andhra pradesh",
        "telangana",
        "maharashtra",
        "delhi",
        "mumbai",
        "chennai",
        "bengaluru",
        "hyderabad",
        "kolkata",
        "punjab",
        "rajasthan",
        "gujarat",
        "uttar pradesh",
        "madhya pradesh",
        "west bengal",
        "odisha",
        "bihar",
    ]

    if any(word in text for word in tech_words):
        return "Tech & AI"

    if any(word in text for word in business_words):
        return "Business"

    if any(word in text for word in lifestyle_words):
        return "Lifestyle"

    if any(word in text for word in state_words):
        return "States"

    india_words = [
        "india",
        "indian",
        "delhi",
        "mumbai",
        "chennai",
        "bengaluru",
        "hyderabad",
        "kolkata",
    ]

    if any(word in text for word in india_words):
        return "India"

    return "World"


# ---------------------------------------------------------
# SOURCE LOADING
# ---------------------------------------------------------

def load_sources():
    try:
        with open(
            SOURCES_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)
    except Exception as exc:
        print("Could not read sources.json:", exc)
        return []

    if isinstance(data, dict):
        for key in ["sources", "feeds", "items"]:
            if isinstance(data.get(key), list):
                return data[key]

    if isinstance(data, list):
        return data

    return []


# ---------------------------------------------------------
# EXISTING ARTICLES
# ---------------------------------------------------------

def load_existing():
    try:
        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)
    except Exception:
        return []

    # Accept all common formats.

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        # Preferred
        if isinstance(data.get("articles"), list):
            return data["articles"]

        # Sometimes stored under items
        if isinstance(data.get("items"), list):
            return data["items"]

        # Sometimes category based
        result = []

        for category in CATEGORIES:
            values = data.get(category)

            if isinstance(values, list):
                result.extend(values)

        if result:
            return result

    return []


# ---------------------------------------------------------
# NORMALIZE
# ---------------------------------------------------------

def normalize(article):
    if not isinstance(article, dict):
        return None

    title = clean_text(
        article.get("title")
        or article.get("headline")
        or ""
    )

    link = (
        article.get("link")
        or article.get("url")
        or article.get("source_url")
        or ""
    )

    if not title or not link:
        return None

    description = clean_text(
        article.get("description")
        or article.get("summary")
        or ""
    )

    category = article.get("category")

    if category not in CATEGORIES:
        category = detect_category(
            title,
            description,
            article.get("source_category", ""),
        )

    published = (
        article.get("published")
        or article.get("published_at")
        or article.get("date")
        or now_iso()
    )

    source = (
        article.get("source")
        or article.get("publisher")
        or "News"
    )

    return {
        "id": article.get("id") or make_id(title, link),
        "title": title,
        "description": description,
        "link": link,
        "source": source,
        "category": category,
        "published": published,
        "created_at": article.get("created_at") or now_iso(),
    }


# ---------------------------------------------------------
# FETCH NEWS
# ---------------------------------------------------------

def fetch_all_sources():
    sources = load_sources()

    print(f"Sources configured: {len(sources)}")

    collected = []

    for source in sources:

        if source.get("enabled") is False:
            continue

        feed_url = (
            source.get("feed_url")
            or source.get("url")
            or source.get("rss")
        )

        if not feed_url:
            continue

        name = source.get("name", "News source")

        print("Fetching:", name)

        data = fetch_url(feed_url)

        articles = parse_rss(data, name)

        source_category = source.get("category", "")

        for article in articles:
            article["category"] = detect_category(
                article["title"],
                article["description"],
                source_category,
            )

        print("  Articles:", len(articles))

        collected.extend(articles)

        # Small delay between feeds
        time.sleep(0.2)

    return collected


# ---------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------

def deduplicate(articles):
    result = []
    seen_ids = set()
    seen_links = set()
    seen_titles = set()

    for article in articles:

        normalized = normalize(article)

        if not normalized:
            continue

        article_id = normalized["id"]
        link = normalized["link"]
        title_key = normalized["title"].lower()

        if article_id in seen_ids:
            continue

        if link in seen_links:
            continue

        if title_key in seen_titles:
            continue

        seen_ids.add(article_id)
        seen_links.add(link)
        seen_titles.add(title_key)

        result.append(normalized)

    return result


# ---------------------------------------------------------
# FIFO
# ---------------------------------------------------------

def fifo_limit(articles):
    """
    Newest articles stay.
    Oldest articles leave first.
    """

    if len(articles) <= MAX_TOTAL:
        return articles

    return articles[:MAX_TOTAL]


# ---------------------------------------------------------
# CATEGORY BALANCING
# ---------------------------------------------------------

def balance_categories(articles):
    """
    Keeps the newest articles but makes sure every category
    has representation whenever enough source articles exist.
    """

    buckets = {
        category: []
        for category in CATEGORIES
    }

    for article in articles:
        category = article.get("category", "World")

        if category not in buckets:
            category = "World"

        buckets[category].append(article)

    selected = []
    selected_ids = set()

    # First guarantee minimum category coverage.
    for category in CATEGORIES:

        for article in buckets[category][:MIN_PER_CATEGORY]:

            if article["id"] not in selected_ids:
                selected.append(article)
                selected_ids.add(article["id"])

    # Then fill with newest remaining.
    for article in articles:

        if article["id"] in selected_ids:
            continue

        selected.append(article)
        selected_ids.add(article["id"])

        if len(selected) >= MAX_TOTAL:
            break

    return selected[:MAX_TOTAL]


# ---------------------------------------------------------
# WRITE JSON
# ---------------------------------------------------------

def save_articles(articles):

    # IMPORTANT:
    # The main JSON structure is a LIST.
    # This fixes your "Total articles: 0" problem.

    with open(
        ARTICLES_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            articles,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 60)

    existing = load_existing()

    print("Existing articles:", len(existing))

    fresh_raw = fetch_all_sources()

    print("Fresh RSS articles:", len(fresh_raw))

    fresh = deduplicate(fresh_raw)
    old = deduplicate(existing)

    # Fresh first, old second.
    # This naturally implements FIFO after limiting.
    combined = fresh + old

    combined = deduplicate(combined)

    # Newest first where possible.
    combined.sort(
        key=lambda x: x.get("published", ""),
        reverse=True,
    )

    combined = balance_categories(combined)

    combined = fifo_limit(combined)

    save_articles(combined)

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print("Total articles:", len(combined))

    for category in CATEGORIES:
        count = sum(
            1
            for article in combined
            if article.get("category") == category
        )

        print(f"{category}: {count}")

    if len(combined) < MIN_TOTAL:
        print()
        print(
            f"WARNING: only {len(combined)} articles available."
        )
        print(
            "Add more RSS sources to sources.json."
        )

    print()
    print("articles.json successfully written.")
    print("=" * 60)


if __name__ == "__main__":
    main()