import json
import hashlib
import html
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

MAX_ARTICLES_PER_SOURCE = 5
MAX_TOTAL_ARTICLES = 30
TIMEOUT = 15


def log(message):
    print("[SNIPPET24]", message, flush=True)


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


def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:16]


def get_tag(item, tag):
    match = re.search(
        rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>",
        item,
        flags=re.I | re.S
    )

    if not match:
        return ""

    return clean_text(match.group(1))


def get_link(item):
    # RSS <link>URL</link>
    match = re.search(
        r"<link(?:\s[^>]*)?>(.*?)</link>",
        item,
        flags=re.I | re.S
    )

    if match:
        value = clean_text(match.group(1))

        if value.startswith("http"):
            return value

    # Atom <link href="URL">
    match = re.search(
        r"<link[^>]+href=[\"']([^\"']+)[\"']",
        item,
        flags=re.I
    )

    if match:
        return html.unescape(match.group(1))

    return ""


def get_items(xml):
    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item>",
        xml,
        flags=re.I | re.S
    )

    if items:
        return items

    # Atom feeds
    entries = re.findall(
        r"<entry(?:\s[^>]*)?>(.*?)</entry>",
        xml,
        flags=re.I | re.S
    )

    return entries


def fetch_feed(source):
    url = source["feed_url"]

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Snippet24NewsReader/1.0 "
                "(RSS reader; +https://snippet24.in)"
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
        log(f"Reading RSS: {source['name']}")
        log(f"RSS URL: {url}")

        with urlopen(request, timeout=TIMEOUT) as response:
            data = response.read()

        return data.decode(
            "utf-8",
            errors="replace"
        )

    except HTTPError as e:
        log(
            f"RSS WARNING for {source['name']}: "
            f"HTTP {e.code}"
        )
        return ""

    except URLError as e:
        log(
            f"RSS WARNING for {source['name']}: "
            f"network error: {e.reason}"
        )
        return ""

    except TimeoutError:
        log(
            f"RSS WARNING for {source['name']}: "
            "connection timed out"
        )
        return ""

    except Exception as e:
        log(
            f"RSS WARNING for {source['name']}: "
            f"{type(e).__name__}: {e}"
        )
        return ""


def make_original_summary(description, title):
    description = clean_text(description)
    title = clean_text(title)

    if description:
        summary = description

    else:
        summary = (
            f"This story reports on {title}. "
            "See the original publication for the "
            "complete report and latest details."
        )

    # Keep the displayed summary reasonably short.
    if len(summary) > 650:
        summary = summary[:647].rsplit(" ", 1)[0] + "..."

    return summary


def parse_source(source):
    xml = fetch_feed(source)

    if not xml:
        log(f"No RSS data: {source['name']}")
        return []

    items = get_items(xml)

    log(
        f"RSS entries found for "
        f"{source['name']}: {len(items)}"
    )

    articles = []

    for item in items[:MAX_ARTICLES_PER_SOURCE]:

        title = get_tag(item, "title")
        link = get_link(item)

        description = (
            get_tag(item, "description")
            or get_tag(item, "summary")
            or get_tag(item, "content")
        )

        if not title or not link:
            continue

        title = clean_text(title)
        description = clean_text(description)

        article_id = make_id(title, link)

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
            "source": source["name"],
            "source_url": link,
            "source_website": source.get(
                "website",
                ""
            ),
            "snippet24_status": "PUBLISHED",
            "summary_type": "RSS-based summary",
            "published_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime()
            )
        }

        articles.append(article)

    return articles


def main():

    log("======================================")
    log("SNIPPET24 CURATOR START")
    log("======================================")

    sources = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(sources, list):
        log("ERROR: sources.json must contain a list")
        return 1

    log(
        f"Approved sources loaded: "
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

    existing_urls = {
        str(article.get("source_url", ""))
        for article in existing
        if isinstance(article, dict)
    }

    new_articles = []

    for source in sources:

        if not source.get("enabled", True):
            continue

        try:

            articles = parse_source(source)

            for article in articles:

                if article["source_url"] in existing_urls:
                    continue

                if any(
                    x["source_url"]
                    == article["source_url"]
                    for x in new_articles
                ):
                    continue

                new_articles.append(article)

                if len(new_articles) >= MAX_TOTAL_ARTICLES:
                    break

        except Exception as e:

            log(
                f"Source failed but curator "
                f"will continue: {source.get('name')}: {e}"
            )

        if len(new_articles) >= MAX_TOTAL_ARTICLES:
            break

    log(
        f"New articles: "
        f"{len(new_articles)}"
    )

    combined = new_articles + existing

    # Keep newest generated items first.
    combined = combined[:100]

    save_json(
        ARTICLES_FILE,
        combined
    )

    published_count = sum(
        1
        for article in combined
        if article.get(
            "snippet24_status"
        ) == "PUBLISHED"
    )

    log(
        f"Total stored articles: "
        f"{len(combined)}"
    )

    log(
        f"Published articles: "
        f"{published_count}"
    )

    log(
        "articles.json saved successfully."
    )

    log("======================================")
    log("SNIPPET24 CURATOR COMPLETE")
    log("======================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())