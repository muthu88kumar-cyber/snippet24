import json
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET
from html import unescape


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
ARTICLES_FILE = os.path.join(BASE_DIR, "articles.json")

MAX_ARTICLES_PER_SOURCE = 10
REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/1.0; "
    "+https://snippet24.in/)"
)


def log(message):
    print(f"[SNIPPET24] {message}", flush=True)


def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        log(f"Could not read {filename}: {e}")
        return default


def save_json(filename, data):
    temp_file = filename + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp_file, filename)


def clean_text(text):
    if not text:
        return ""

    text = unescape(str(text))

    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_id(source_name, title, url):
    raw = f"{source_name}|{title}|{url}".encode(
        "utf-8",
        errors="ignore"
    )

    return hashlib.sha256(raw).hexdigest()[:20]


def fetch_url(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/xml, "
                "text/xml, "
                "text/html;q=0.9, "
                "*/*;q=0.8"
            ),
            "Cache-Control": "no-cache",
        }
    )

    last_error = None

    for attempt in range(3):

        try:

            log(
                f"Downloading source "
                f"(attempt {attempt + 1}/3)"
            )

            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT
            ) as response:

                data = response.read()

                log(
                    f"Downloaded {len(data)} bytes"
                )

                return data

        except HTTPError as e:

            last_error = e

            log(
                f"HTTP error {e.code}: {e.reason}"
            )

        except URLError as e:

            last_error = e

            log(
                f"URL error: {e.reason}"
            )

        except TimeoutError as e:

            last_error = e

            log(
                "Connection timed out"
            )

        except Exception as e:

            last_error = e

            log(
                f"Download error: {e}"
            )

        if attempt < 2:
            time.sleep(3)

    raise last_error


def parse_rss(xml_data):
    try:

        root = ET.fromstring(xml_data)

    except ET.ParseError as e:

        log(f"RSS XML parsing failed: {e}")

        return []

    items = []

    # Standard RSS
    for item in root.findall(".//item"):

        title = clean_text(
            item.findtext("title", "")
        )

        link = clean_text(
            item.findtext("link", "")
        )

        description = clean_text(
            item.findtext("description", "")
        )

        pub_date = clean_text(
            item.findtext("pubDate", "")
        )

        if title and link:

            items.append({
                "title": title,
                "url": link,
                "description": description,
                "published": pub_date
            })

    # Atom fallback
    if not items:

        namespaces = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        for entry in root.findall(
            ".//atom:entry",
            namespaces
        ):

            title_node = entry.find(
                "atom:title",
                namespaces
            )

            summary_node = entry.find(
                "atom:summary",
                namespaces
            )

            link_node = entry.find(
                "atom:link",
                namespaces
            )

            title = clean_text(
                title_node.text
                if title_node is not None
                else ""
            )

            summary = clean_text(
                summary_node.text
                if summary_node is not None
                else ""
            )

            link = ""

            if link_node is not None:
                link = link_node.attrib.get(
                    "href",
                    ""
                )

            if title and link:

                items.append({
                    "title": title,
                    "url": link,
                    "description": summary,
                    "published": ""
                })

    return items


def make_summary(title, description):
    """
    Creates a short original summary from RSS metadata.
    No article text is copied to the site.
    """

    title = clean_text(title)
    description = clean_text(description)

    if description:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            description
        )

        sentences = [
            s.strip()
            for s in sentences
            if s.strip()
        ]

        summary = " ".join(
            sentences[:2]
        )

        if len(summary) > 500:
            summary = summary[:497].rsplit(
                " ",
                1
            )[0] + "..."

        return summary

    return (
        "This Snippet24 story summarizes the "
        "latest information published by the source."
    )


def process_source(source, existing_articles):

    name = source.get(
        "name",
        "Unknown source"
    )

    category = source.get(
        "category",
        "News"
    )

    feed_url = source.get(
        "feed_url",
        ""
    )

    allow_publish = source.get(
        "allow_publish",
        False
    )

    if not allow_publish:

        log(
            f"Publishing disabled for {name}"
        )

        return []

    if not feed_url:

        log(
            f"No feed URL for {name}"
        )

        return []

    log(
        f"READING RSS: {name}"
    )

    log(
        f"RSS URL: {feed_url}"
    )

    try:

        xml_data = fetch_url(feed_url)

    except Exception as e:

        log(
            f"RSS WARNING for {name}: {e}"
        )

        return []

    entries = parse_rss(xml_data)

    log(
        f"RSS entries found for {name}: "
        f"{len(entries)}"
    )

    if not entries:

        log(
            f"NO RSS ARTICLES FOUND: {name}"
        )

        return []

    existing_ids = {
        article.get("id")
        for article in existing_articles
        if article.get("id")
    }

    new_articles = []

    for entry in entries[:MAX_ARTICLES_PER_SOURCE]:

        title = clean_text(
            entry.get("title", "")
        )

        url = clean_text(
            entry.get("url", "")
        )

        description = clean_text(
            entry.get("description", "")
        )

        published = clean_text(
            entry.get("published", "")
        )

        if not title or not url:
            continue

        article_id = make_id(
            name,
            title,
            url
        )

        if article_id in existing_ids:
            continue

        summary = make_summary(
            title,
            description
        )

        article = {
            "id": article_id,
            "title": title,
            "summary": summary,
            "category": category,
            "source": name,
            "source_url": url,
            "published_at": published,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "snippet24_status": "PUBLISHED",
            "summary_method": "automated",
            "rights_note": (
                "Original publication remains "
                "with the source publisher."
            )
        }

        new_articles.append(article)

    return new_articles


def main():

    log("=" * 50)
    log("SNIPPET24 CURATOR START")
    log("=" * 50)

    sources = load_json(
        SOURCES_FILE,
        []
    )

    articles = load_json(
        ARTICLES_FILE,
        []
    )

    if not isinstance(sources, list):
        log("sources.json must contain an array")
        return

    if not isinstance(articles, list):
        articles = []

    log(
        f"Approved sources loaded: {len(sources)}"
    )

    log(
        f"Existing articles: {len(articles)}"
    )

    all_new_articles = []

    for source in sources:

        try:

            new_articles = process_source(
                source,
                articles
            )

            if new_articles:

                log(
                    f"New articles from "
                    f"{source.get('name')}: "
                    f"{len(new_articles)}"
                )

                all_new_articles.extend(
                    new_articles
                )

            else:

                log(
                    f"No new articles from "
                    f"{source.get('name')}"
                )

        except Exception as e:

            log(
                f"Source processing error: {e}"
            )

    if all_new_articles:

        articles = (
            all_new_articles +
            articles
        )

        # Keep newest 100 articles
        articles = articles[:100]

    log(
        f"New articles: "
        f"{len(all_new_articles)}"
    )

    log(
        f"Total stored: "
        f"{len(articles)}"
    )

    save_json(
        ARTICLES_FILE,
        articles
    )

    log(
        "articles.json saved successfully."
    )

    log("=" * 50)
    log("SNIPPET24 CURATOR END")
    log("=" * 50)


if __name__ == "__main__":
    main()