import json
import re
import html
import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests
import xml.etree.ElementTree as ET


OUTPUT_FILE = "articles.json"

TARGET_STORIES = 100
MAX_PER_CATEGORY = 20
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": "Snippet24-News/1.0 (+https://snippet24.in)"
}


# ---------------------------------------------------------
# RSS SOURCES
# ---------------------------------------------------------

RSS_SOURCES = {
    "World": [
        ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("Guardian World", "https://www.theguardian.com/world/rss"),
    ],

    "India": [
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("Indian Express", "https://indianexpress.com/section/india/feed/"),
        ("NDTV India", "https://feeds.feedburner.com/ndtvnews-india-news"),
    ],

    "Business": [
        ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml"),
        ("Business Standard", "https://www.business-standard.com/rss/home_page_top_stories.rss"),
        ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
    ],

    "Technology": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],

    "Lifestyle": [
        ("Hindustan Times Lifestyle", "https://www.hindustantimes.com/feeds/rss/lifestyle/rssfeed.xml"),
        ("Guardian Lifestyle", "https://www.theguardian.com/lifeandstyle/rss"),
    ],

    "Sports": [
        ("ESPN", "https://www.espn.com/espn/rss/news"),
        ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
    ],

    "Entertainment": [
        ("Variety", "https://variety.com/feed/"),
        ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/"),
    ]
}


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(r"<[^>]+>", " ", value)

    value = value.replace("\xa0", " ")
    value = value.replace("&nbsp;", " ")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def remove_publisher_from_title(title, publisher):
    """
    Removes common RSS title endings such as:

    Story | Hindustan Times
    Story - Hindustan Times
    Story | Business Standard
    """

    if not title:
        return ""

    title = clean_text(title)

    publishers = [
        publisher,
        "Hindustan Times",
        "Business Standard",
        "Firstpost",
        "Moneycontrol",
        "News18",
        "NDTV",
        "The Hindu",
        "Indian Express",
        "BBC",
        "BBC News",
        "Reuters",
        "CNN",
        "CNBC",
        "TechCrunch",
        "The Verge",
        "Variety",
        "ESPN"
    ]

    for name in publishers:
        if not name:
            continue

        pattern = r"\s*(?:\||-|\u2013|\u2014)\s*" + re.escape(name) + r"\s*$"
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)

    return title.strip(" -|\u2013\u2014")


def remove_title_repetition(summary, title):
    if not summary:
        return ""

    summary = clean_text(summary)

    if title:
        summary = re.sub(
            re.escape(title),
            "",
            summary,
            flags=re.IGNORECASE
        )

    summary = re.sub(r"\s+", " ", summary).strip()

    return summary


def make_summary(title, description):
    title = clean_text(title)
    description = clean_text(description)

    description = remove_title_repetition(description, title)

    if description:
        # Remove obvious publisher suffixes.
        description = re.sub(
            r"\s*(?:\||-|\u2013|\u2014)\s*[A-Za-z0-9 .&]+$",
            "",
            description
        ).strip()

        if len(description) > 360:
            description = description[:357].rsplit(" ", 1)[0] + "..."

        return description

    # Fallback if RSS has no description.
    return (
        f"{title}. "
        "The latest developments are being reported as more information "
        "becomes available."
    )


def parse_date(value):
    if not value:
        return datetime.now(timezone.utc)

    value = value.strip()

    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass

    # ISO format fallback
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def find_child_text(element, names):
    names = {x.lower() for x in names}

    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag in names:
            return clean_text("".join(child.itertext()))

    return ""


def find_link(element):
    # RSS <link>
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag == "link":
            href = child.attrib.get("href")

            if href:
                return href.strip()

            text = clean_text("".join(child.itertext()))

            if text:
                return text

    # Atom links
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag == "link":
            href = child.attrib.get("href")

            if href:
                return href.strip()

    return ""


def find_image(element, title):
    # media:content / media:thumbnail
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()

        if tag in ("content", "thumbnail"):
            url = child.attrib.get("url")

            if url:
                return url

    # enclosure
    for child in element:
        tag = child.tag.split("}")[-1].lower()

        if tag == "enclosure":
            url = child.attrib.get("url", "")
            kind = child.attrib.get("type", "")

            if url and ("image" in kind or not kind):
                return url

    # Look for image URLs in HTML description
    raw = "".join(element.itertext())

    match = re.search(
        r'https?://[^"\'>\s]+?\.(?:jpg|jpeg|png|webp)',
        raw,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(0)

    return make_ai_image(title)


def make_ai_image(title):
    """
    Generates a deterministic AI-image URL.

    Pollinations can generate an image from the headline.
    If the image service is temporarily unavailable,
    the article itself still works.
    """

    prompt = (
        "Editorial news illustration, realistic professional journalism style, "
        "visually representing this news story: "
        + title
        + ", no text, no words, no logos, no watermark"
    )

    seed = int(
        hashlib.md5(title.encode("utf-8")).hexdigest()[:8],
        16
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt)
        + f"?width=1200&height=675&nologo=true&seed={seed}"
    )


def make_id(category, title, url):
    raw = f"{category}|{title}|{url}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]


# ---------------------------------------------------------
# RSS PARSER
# ---------------------------------------------------------

def parse_feed(xml_text, publisher, category):
    articles = []

    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"XML error from {publisher}: {exc}")
        return articles

    # RSS items
    elements = []

    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()

        if tag in ("item", "entry"):
            elements.append(element)

    for item in elements:

        title = find_child_text(
            item,
            ["title"]
        )

        if not title:
            continue

        title = remove_publisher_from_title(
            title,
            publisher
        )

        description = find_child_text(
            item,
            [
                "description",
                "summary",
                "content",
                "encoded"
            ]
        )

        link = find_link(item)

        published = find_child_text(
            item,
            [
                "pubdate",
                "published",
                "updated",
                "date",
                "created"
            ]
        )

        date_obj = parse_date(published)

        summary = make_summary(
            title,
            description
        )

        image = find_image(
            item,
            title
        )

        article = {
            "id": make_id(category, title, link),

            "category": category,

            "headline": title,

            "summary": summary,

            "publisher": publisher,

            "published_at": date_obj.isoformat(),

            "source_url": link,

            "image_url": image,

            "image_type": (
                "source"
                if image and "pollinations.ai" not in image
                else "ai_generated"
            )
        }

        if not article["source_url"]:
            continue

        articles.append(article)

    return articles


# ---------------------------------------------------------
# FETCH RSS
# ---------------------------------------------------------

def fetch_source(publisher, url, category):

    print(f"Fetching: {publisher}")
    print(f"URL: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        articles = parse_feed(
            response.text,
            publisher,
            category
        )

        print(
            f"  -> {len(articles)} stories"
        )

        return articles

    except Exception as exc:

        print(
            f"  -> FAILED: {publisher}: {exc}"
        )

        return []


# ---------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------

def deduplicate(articles):

    unique = {}

    for article in articles:

        title_key = re.sub(
            r"[^a-z0-9]+",
            " ",
            article["headline"].lower()
        ).strip()

        if not title_key:
            continue

        unique[title_key] = article

    return list(unique.values())


# ---------------------------------------------------------
# BUILD FEED
# ---------------------------------------------------------

def build_feed():

    print("=" * 60)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 60)

    all_articles = []

    category_counts = {}

    for category, sources in RSS_SOURCES.items():

        print()
        print(f"### {category}")

        category_articles = []

        for publisher, url in sources:

            found = fetch_source(
                publisher,
                url,
                category
            )

            category_articles.extend(found)

            time.sleep(0.2)

        category_articles = deduplicate(
            category_articles
        )

        category_articles.sort(
            key=lambda x: x["published_at"],
            reverse=True
        )

        category_articles = category_articles[
            :MAX_PER_CATEGORY
        ]

        category_counts[category] = len(
            category_articles
        )

        all_articles.extend(
            category_articles
        )

    # Global deduplication
    all_articles = deduplicate(
        all_articles
    )

    # Newest first
    all_articles.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    # FIFO-style retention:
    # newest TARGET_STORIES remain.
    all_articles = all_articles[
        :TARGET_STORIES
    ]

    # Final chronological order
    all_articles.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    output = {
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total": len(all_articles),

        "categories": category_counts,

        "articles": all_articles
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print(
        f"TOTAL STORIES: {len(all_articles)}"
    )
    print("=" * 60)

    for category, count in category_counts.items():

        print(
            f"{category}: {count}"
        )

    if len(all_articles) == 0:

        print()
        print(
            "ERROR: No articles were collected."
        )

        return 1

    if len(all_articles) < 50:

        print()
        print(
            "WARNING: Fewer than 50 stories were collected."
        )

        print(
            "The available RSS sources may have returned fewer "
            "valid stories."
        )

    else:

        print()
        print(
            "SUCCESS: News feed generated."
        )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        build_feed()
    )