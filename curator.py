import json
import hashlib
import html
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ============================================================
# SNIPPET24 NEWS CURATOR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

MAX_ARTICLES_PER_SOURCE = 8
MAX_TOTAL_ARTICLES = 40
MAX_STORED_ARTICLES = 100

TIMEOUT = 12


# ------------------------------------------------------------
# FALLBACK SOURCES
# These work even if sources.json is empty or one source fails.
# ------------------------------------------------------------

DEFAULT_SOURCES = [
    {
        "name": "BBC News",
        "category": "World",
        "feed_url": "https://feeds.bbci.co.uk/news/rss.xml",
        "website": "https://www.bbc.com/news",
        "enabled": True
    },
    {
        "name": "BBC World",
        "category": "World",
        "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "website": "https://www.bbc.com/news/world",
        "enabled": True
    },
    {
        "name": "BBC Business",
        "category": "Business",
        "feed_url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "website": "https://www.bbc.com/news/business",
        "enabled": True
    },
    {
        "name": "BBC Technology",
        "category": "Technology",
        "feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "website": "https://www.bbc.com/news/technology",
        "enabled": True
    },
    {
        "name": "Google News India",
        "category": "India",
        "feed_url": (
            "https://news.google.com/rss?"
            "hl=en-IN&gl=IN&ceid=IN:en"
        ),
        "website": "https://news.google.com/",
        "enabled": True
    },
    {
        "name": "Google News Technology",
        "category": "Technology",
        "feed_url": (
            "https://news.google.com/rss/search?"
            "q=technology&hl=en-IN&gl=IN&ceid=IN:en"
        ),
        "website": "https://news.google.com/",
        "enabled": True
    },
    {
        "name": "Google News India",
        "category": "India",
        "feed_url": (
            "https://news.google.com/rss/search?"
            "q=India+news&hl=en-IN&gl=IN&ceid=IN:en"
        ),
        "website": "https://news.google.com/",
        "enabled": True
    }
]


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

def log(message):
    print("[SNIPPET24]", message, flush=True)


# ------------------------------------------------------------
# JSON
# ------------------------------------------------------------

def load_json(path, default):
    try:
        if not path.exists():
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        log(f"JSON load warning: {e}")
        return default


def save_json(path, data):
    temp = path.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp.replace(path)


# ------------------------------------------------------------
# TEXT CLEANING
# ------------------------------------------------------------

def clean_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<script.*?</script>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<style.*?</style>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<!\[CDATA\[(.*?)\]\]>",
        r"\1",
        value,
        flags=re.I | re.S
    )

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


# ------------------------------------------------------------
# ID
# ------------------------------------------------------------

def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:16]


# ------------------------------------------------------------
# RSS / ATOM PARSING
# ------------------------------------------------------------

def get_tag(item, tag):
    patterns = [
        rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>",
        rf"<[A-Za-z0-9_-]+:{tag}(?:\s[^>]*)?>(.*?)</[A-Za-z0-9_-]+:{tag}>"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            item,
            flags=re.I | re.S
        )

        if match:
            return clean_text(match.group(1))

    return ""


def get_link(item):
    # Normal RSS:
    # <link>https://example.com/story</link>

    match = re.search(
        r"<link(?:\s[^>]*)?>(.*?)</link>",
        item,
        flags=re.I | re.S
    )

    if match:
        value = clean_text(match.group(1))

        if value.startswith("http://") or value.startswith("https://"):
            return value

    # Atom:
    # <link href="https://example.com/story">

    matches = re.findall(
        r"<link\b[^>]*\bhref=[\"']([^\"']+)[\"'][^>]*>",
        item,
        flags=re.I
    )

    for value in matches:
        value = html.unescape(value)

        if value.startswith("http://") or value.startswith("https://"):
            return value

    return ""


def get_items(xml):
    # RSS
    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item>",
        xml,
        flags=re.I | re.S
    )

    if items:
        return items

    # Atom
    entries = re.findall(
        r"<entry(?:\s[^>]*)?>(.*?)</entry>",
        xml,
        flags=re.I | re.S
    )

    return entries


# ------------------------------------------------------------
# FETCH RSS
# ------------------------------------------------------------

def fetch_feed(source):
    url = source.get("feed_url", "")

    if not url:
        return ""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "Snippet24NewsReader/1.0"
            ),
            "Accept": (
                "application/rss+xml,"
                "application/atom+xml,"
                "application/xml,"
                "text/xml,"
                "*/*"
            )
        }
    )

    try:
        log(f"Reading: {source['name']}")
        log(f"URL: {url}")

        with urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            data = response.read()

        log(
            f"Downloaded {len(data)} bytes "
            f"from {source['name']}"
        )

        return data.decode(
            "utf-8",
            errors="replace"
        )

    except HTTPError as e:

        log(
            f"WARNING {source['name']}: "
            f"HTTP {e.code}"
        )

        return ""

    except URLError as e:

        log(
            f"WARNING {source['name']}: "
            f"network error: {e.reason}"
        )

        return ""

    except TimeoutError:

        log(
            f"WARNING {source['name']}: "
            "timeout"
        )

        return ""

    except Exception as e:

        log(
            f"WARNING {source['name']}: "
            f"{type(e).__name__}: {e}"
        )

        return ""


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

def make_original_summary(description, title):

    description = clean_text(description)
    title = clean_text(title)

    if description:

        summary = description

    else:

        summary = (
            f"{title}. "
            "Read the original publication "
            "for the complete report and latest details."
        )

    if len(summary) > 650:

        summary = (
            summary[:647]
            .rsplit(" ", 1)[0]
            + "..."
        )

    return summary


# ------------------------------------------------------------
# PARSE ONE SOURCE
# ------------------------------------------------------------

def parse_source(source):

    xml = fetch_feed(source)

    if not xml:

        log(
            f"No RSS data from "
            f"{source['name']}"
        )

        return []

    items = get_items(xml)

    log(
        f"Entries found from "
        f"{source['name']}: {len(items)}"
    )

    articles = []

    for item in items[:MAX_ARTICLES_PER_SOURCE]:

        title = (
            get_tag(item, "title")
            or get_tag(item, "name")
        )

        link = get_link(item)

        description = (
            get_tag(item, "description")
            or get_tag(item, "summary")
            or get_tag(item, "encoded")
            or get_tag(item, "content")
        )

        if not title:
            continue

        if not link:
            continue

        title = clean_text(title)
        link = html.unescape(link).strip()
        description = clean_text(description)

        article_id = make_id(
            title,
            link
        )

        article = {
            "id": article_id,

            "title": title,

            "summary": make_original_summary(
                description,
                title
            ),

            "category": source.get(
                "category",
                "News"
            ),

            "source": source.get(
                "name",
                "Unknown"
            ),

            "source_url": link,

            "source_website": source.get(
                "website",
                ""
            ),

            "snippet24_status": "PUBLISHED",

            "summary_type": (
                "RSS-based original summary"
            ),

            "published_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime()
            )
        }

        articles.append(article)

    return articles


# ------------------------------------------------------------
# SOURCE LOADING
# ------------------------------------------------------------

def load_sources():

    custom = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(custom, list):
        custom = []

    # If sources.json contains sources,
    # use those first.
    if custom:

        log(
            f"Custom sources loaded: "
            f"{len(custom)}"
        )

        sources = custom + DEFAULT_SOURCES

    else:

        log(
            "sources.json empty or missing."
        )

        log(
            "Using built-in fallback sources."
        )

        sources = DEFAULT_SOURCES

    # Remove duplicate feed URLs
    result = []
    seen = set()

    for source in sources:

        if not isinstance(source, dict):
            continue

        if not source.get("enabled", True):
            continue

        feed_url = source.get(
            "feed_url",
            ""
        )

        if not feed_url:
            continue

        if feed_url in seen:
            continue

        seen.add(feed_url)
        result.append(source)

    return result


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    log("")
    log("======================================")
    log("SNIPPET24 CURATOR START")
    log("======================================")
    log("")

    sources = load_sources()

    log(
        f"Total usable sources: "
        f"{len(sources)}"
    )

    existing = load_json(
        ARTICLES_FILE,
        []
    )

    if not isinstance(existing, list):
        existing = []

    log(
        f"Existing articles: "
        f"{len(existing)}"
    )

    existing_urls = set()

    for article in existing:

        if not isinstance(article, dict):
            continue

        url = str(
            article.get(
                "source_url",
                ""
            )
        ).strip()

        if url:
            existing_urls.add(url)

    new_articles = []
    new_urls = set()

    for source in sources:

        if len(new_articles) >= MAX_TOTAL_ARTICLES:
            break

        try:

            articles = parse_source(
                source
            )

            for article in articles:

                url = article.get(
                    "source_url",
                    ""
                )

                if not url:
                    continue

                if url in existing_urls:
                    continue

                if url in new_urls:
                    continue

                new_urls.add(url)

                new_articles.append(
                    article
                )

                log(
                    "NEW: "
                    + article["title"]
                )

                if len(
                    new_articles
                ) >= MAX_TOTAL_ARTICLES:

                    break

        except Exception as e:

            log(
                "Source error: "
                f"{source.get('name')}: {e}"
            )

            continue

    log("")
    log(
        f"New articles collected: "
        f"{len(new_articles)}"
    )

    # New articles first.
    combined = (
        new_articles
        + existing
    )

    # Remove duplicate URLs.
    final_articles = []
    final_urls = set()

    for article in combined:

        if not isinstance(article, dict):
            continue

        url = str(
            article.get(
                "source_url",
                ""
            )
        ).strip()

        if not url:
            continue

        if url in final_urls:
            continue

        final_urls.add(url)

        final_articles.append(
            article
        )

        if len(final_articles) >= MAX_STORED_ARTICLES:
            break

    save_json(
        ARTICLES_FILE,
        final_articles
    )

    published_count = sum(
        1
        for article in final_articles
        if article.get(
            "snippet24_status"
        ) == "PUBLISHED"
    )

    log("")
    log(
        f"Total stored: "
        f"{len(final_articles)}"
    )

    log(
        f"Published: "
        f"{published_count}"
    )

    log(
        "articles.json saved successfully."
    )

    log("")
    log("======================================")
    log("SNIPPET24 CURATOR COMPLETE")
    log("======================================")
    log("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())