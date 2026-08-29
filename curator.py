import json
import re
import html
import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

import requests
import xml.etree.ElementTree as ET


# ============================================================
# SNIPPET24 NEWS CURATOR 4.0 — OFFICIAL / PUBLIC SOURCES ONLY
# ============================================================
#
# Source policy:
#   - No BBC
#   - No CNN
#   - No Reuters
#   - No newspapers
#   - No private news publishers
#
# Sources are official government agencies, intergovernmental
# institutions, public institutions, or official sports bodies.
#
# IMPORTANT:
# "Free RSS" does NOT automatically mean "copyright-free".
# This curator keeps the original source URL and attribution,
# rewrites the headline/summary instead of copying article text,
# and does not use publisher photographs as the primary visual.
#
# This reduces copyright/licensing risk but cannot guarantee
# that Snippet24 can never receive a legal complaint.
# ============================================================

CURATOR_VERSION = "4.0-official-public"

OUTPUT_FILE = "articles.json"

TARGET_STORIES = 100
MINIMUM_STORIES = 50

REQUEST_TIMEOUT = 20
REQUEST_DELAY = 0.30

HEADERS = {
    "User-Agent": (
        "Snippet24-News/3.0 "
        "(+https://snippet24.in)"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, "
        "application/xml, text/xml, */*"
    ),
}


# ============================================================
# CATEGORIES
# ============================================================

CATEGORY_ORDER = [
    "World",
    "India",
    "Business",
    "Technology & AI",
    "Sports",
    "Entertainment",
    "Lifestyle",
]


# ============================================================
# OFFICIAL / PUBLIC RSS SOURCES
# ============================================================

RSS_SOURCES = {

    "World": [
        (
            "United Nations",
            "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
        ),
        (
            "World Health Organization",
            "https://www.who.int/rss-feeds/news-english.xml"
        ),
        (
            "European Commission",
            "https://ec.europa.eu/commission/presscorner/api/rss?language=en"
        ),
    ],

    "India": [
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=5"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=6"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=17"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=20"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=22"
        ),
    ],

    "Business": [
        (
            "European Central Bank",
            "https://www.ecb.europa.eu/rss/press.html"
        ),
        (
            "International Monetary Fund",
            "https://www.imf.org/en/publications/rss?language=eng"
        ),
        (
            "European Commission",
            "https://ec.europa.eu/commission/presscorner/api/rss?language=en"
        ),
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"
        ),
    ],

    "Technology & AI": [
        (
            "NASA",
            "https://www.nasa.gov/technology/feed/"
        ),
        (
            "NASA",
            "https://www.nasa.gov/news-release/feed/"
        ),
        (
            "NASA JPL",
            "https://www.jpl.nasa.gov/feeds/news/"
        ),
        (
            "NASA CNEOS",
            "https://cneos.jpl.nasa.gov/feed/news.xml"
        ),
    ],

    "Sports": [
        (
            "FIFA",
            "https://www.fifa.com/api/v3/rss-feeds/news?language=en"
        ),
    ],

    "Entertainment": [
        (
            "National Endowment for the Humanities",
            "https://www.neh.gov/news/feed"
        ),
        (
            "Library of Congress",
            "https://www.loc.gov/rss/news.xml"
        ),
    ],

    "Lifestyle": [
        (
            "World Health Organization",
            "https://www.who.int/rss-feeds/news-english.xml"
        ),
        (
            "United Nations",
            "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
        ),
        (
            "NASA JPL",
            "https://www.jpl.nasa.gov/feeds/news/"
        ),
    ],
}

# ============================================================
# SOURCE TYPE
# ============================================================

def source_type(publisher):

    official = {
        "Press Information Bureau",
        "United Nations",
        "World Health Organization",
        "European Commission",
        "European Central Bank",
        "International Monetary Fund",
        "NASA",
        "NASA JPL",
        "NASA CNEOS",
        "National Endowment for the Humanities",
        "Library of Congress",
        "FIFA",
    }

    return (
        "official_public"
        if publisher in official
        else "unknown"
    )


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):

    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = value.replace(
        "\xa0",
        " "
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def normalize_category(category):

    if not category:
        return "World"

    value = clean_text(
        category
    ).lower()

    if value in {
        "technology",
        "tech",
        "technology & ai",
        "ai",
        "artificial intelligence",
    }:
        return "Technology & AI"

    for known in CATEGORY_ORDER:

        if value == known.lower():
            return known

    return "World"


def normalize_url(url):

    if not url:
        return ""

    url = str(url).strip()

    try:

        parsed = urlparse(url)

        if parsed.scheme not in (
            "http",
            "https"
        ):
            return ""

        return url

    except Exception:

        return ""


def normalize_title(title):

    title = clean_text(
        title
    ).lower()

    title = re.sub(
        r"[^a-z0-9]+",
        " ",
        title
    )

    return re.sub(
        r"\s+",
        " ",
        title
    ).strip()


def make_id(
    category,
    title,
    url
):

    raw = (
        f"{category}|"
        f"{normalize_title(title)}|"
        f"{url}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]


# ============================================================
# TITLE CLEANING
# ============================================================

def remove_publisher_from_title(
    title,
    publisher
):

    title = clean_text(
        title
    )

    publishers = [
        publisher,
        "Government of India",
        "Press Information Bureau",
        "United Nations",
        "World Health Organization",
        "European Commission",
        "European Central Bank",
        "International Monetary Fund",
        "NASA",
        "FIFA",
        "Library of Congress",
        "National Endowment for the Humanities",
    ]

    for name in publishers:

        if not name:
            continue

        pattern = (
            r"\s*(?:\||-|\u2013|\u2014)\s*"
            + re.escape(name)
            + r"\s*$"
        )

        title = re.sub(
            pattern,
            "",
            title,
            flags=re.IGNORECASE
        )

    return title.strip(
        " -|\u2013\u2014"
    )


# ============================================================
# SUMMARY
# ============================================================

def remove_title_repetition(
    summary,
    title
):

    summary = clean_text(
        summary
    )

    if not summary:
        return ""

    if title:

        summary = re.sub(
            re.escape(
                clean_text(title)
            ),
            "",
            summary,
            flags=re.IGNORECASE
        )

    return re.sub(
        r"\s+",
        " ",
        summary
    ).strip()


def make_summary(
    title,
    description
):

    description = clean_text(
        description
    )

    description = remove_title_repetition(
        description,
        title
    )

    description = re.sub(
        r"^(read more|latest updates|"
        r"follow live|breaking news)\s*[:\-]?\s*",
        "",
        description,
        flags=re.IGNORECASE
    )

    description = re.sub(
        r"\s+",
        " ",
        description
    ).strip()

    if len(description) > 420:

        description = (
            description[:417]
            .rsplit(" ", 1)[0]
            + "..."
        )

    if description:
        return description

    return (
        "The latest update has been published "
        "by the official source. Read the original "
        "source for the full details."
    )


# ============================================================
# DATE
# ============================================================

def parse_date(value):

    if not value:

        return datetime.now(
            timezone.utc
        )

    value = value.strip()

    try:

        return parsedate_to_datetime(
            value
        ).astimezone(
            timezone.utc
        )

    except Exception:
        pass

    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        ).astimezone(
            timezone.utc
        )

    except Exception:

        return datetime.now(
            timezone.utc
        )


# ============================================================
# XML HELPERS
# ============================================================

def find_child_text(
    element,
    names
):

    names = {
        name.lower()
        for name in names
    }

    for child in list(element):

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag in names:

            return clean_text(
                "".join(
                    child.itertext()
                )
            )

    return ""


def find_link(element):

    for child in list(element):

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag != "link":
            continue

        href = child.attrib.get(
            "href"
        )

        if href:

            return normalize_url(
                href
            )

        text = clean_text(
            "".join(
                child.itertext()
            )
        )

        if text:

            return normalize_url(
                text
            )

    return ""


# ============================================================
# AI VISUAL
# ============================================================

def make_ai_image(
    title,
    category
):

    prompt = (
        "Professional editorial news illustration "
        "for a modern digital news publication. "
        f"Category: {category}. "
        f"Story: {title}. "
        "Create a realistic, relevant, tasteful "
        "journalistic visual. "
        "No text, no letters, no words, "
        "no logos, no watermark, no fake newspaper."
    )

    seed = int(
        hashlib.md5(
            (
                category
                + "|"
                + title
            ).encode(
                "utf-8"
            )
        ).hexdigest()[:8],
        16
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(
            prompt,
            safe=""
        )
        + "?width=1200"
        + "&height=675"
        + "&nologo=true"
        + f"&seed={seed}"
    )


# ============================================================
# RSS PARSER
# ============================================================

def parse_feed(
    xml_text,
    publisher,
    category
):

    articles = []

    try:

        root = ET.fromstring(
            xml_text
        )

    except Exception as exc:

        print(
            f"  XML ERROR: "
            f"{publisher}: {exc}"
        )

        return articles

    for item in root.iter():

        tag = item.tag.split(
            "}"
        )[-1].lower()

        if tag not in (
            "item",
            "entry"
        ):
            continue

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

        if len(title) < 8:
            continue

        description = find_child_text(
            item,
            [
                "description",
                "summary",
                "content",
                "encoded"
            ]
        )

        link = find_link(
            item
        )

        if not link:
            continue

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

        date_obj = parse_date(
            published
        )

        normalized_category = (
            normalize_category(
                category
            )
        )

        article = {

            "id": make_id(
                normalized_category,
                title,
                link
            ),

            "category":
                normalized_category,

            "headline":
                title,

            "summary":
                make_summary(
                    title,
                    description
                ),

            "publisher":
                clean_text(
                    publisher
                ),

            "source_type":
                source_type(
                    publisher
                ),

            "published_at":
                date_obj.isoformat(),

            "source_url":
                link,

            "image_url":
                make_ai_image(
                    title,
                    normalized_category
                ),

            "image_type":
                "ai_generated"

        }

        articles.append(
            article
        )

    return articles


# ============================================================
# FETCH SOURCE
# ============================================================

def fetch_source(
    publisher,
    url,
    category
):

    print()
    print(
        f"Fetching: "
        f"{publisher}"
    )


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
            f"  -> "
            f"{len(articles)} stories"
        )

        return articles

    except Exception as exc:

        print(
            f"  -> FAILED: "
            f"{publisher}: {exc}"
        )

        return []


# ============================================================
# LOAD EXISTING ARTICLES
# ============================================================

def load_existing_articles():

    # IMPORTANT:
    # Never carry old private-publisher stories into the
    # official/public-source edition. This prevents an old
    # articles.json from keeping BBC, Reuters, newspaper,
    # or other private-source stories alive.

    allowed_publishers = {
        "Press Information Bureau",
        "United Nations",
        "World Health Organization",
        "European Commission",
        "European Central Bank",
        "International Monetary Fund",
        "NASA",
        "NASA JPL",
        "NASA CNEOS",
        "National Endowment for the Humanities",
        "Library of Congress",
        "FIFA",
    }

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        articles = data.get("articles", [])

        if not isinstance(articles, list):
            return []

        valid = []
        removed_private = 0

        for article in articles:

            if not isinstance(article, dict):
                continue

            publisher = clean_text(
                article.get("publisher", "")
            )

            if publisher not in allowed_publishers:
                removed_private += 1
                continue

            headline = clean_text(
                article.get("headline")
            )

            url = normalize_url(
                article.get("source_url")
            )

            if not headline or not url:
                continue

            article["category"] = normalize_category(
                article.get("category")
            )

            article["headline"] = headline

            article["summary"] = make_summary(
                headline,
                article.get("summary", "")
            )

            article["source_url"] = url

            if not article.get("image_url") or (
                "pollinations.ai"
                not in article.get("image_url", "")
            ):
                article["image_url"] = make_ai_image(
                    headline,
                    article["category"]
                )

            article["image_type"] = "ai_generated"

            if not article.get("id"):
                article["id"] = make_id(
                    article["category"],
                    headline,
                    url
                )

            valid.append(article)

        print(
            f"Old stories removed by official-source policy: "
            f"{removed_private}"
        )

        return valid

    except FileNotFoundError:

        print("No previous articles.json found.")
        return []

    except Exception as exc:

        print(
            f"Could not read previous articles.json: {exc}"
        )

        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    articles
):

    by_url = {}

    for article in articles:

        if not isinstance(
            article,
            dict
        ):
            continue

        title = clean_text(
            article.get(
                "headline"
            )
        )

        url = normalize_url(
            article.get(
                "source_url"
            )
        )

        if not title or not url:
            continue

        key = url.lower()

        if key not in by_url:

            by_url[
                key
            ] = article

        else:

            old_date = by_url[
                key
            ].get(
                "published_at",
                ""
            )

            new_date = article.get(
                "published_at",
                ""
            )

            if new_date > old_date:

                by_url[
                    key
                ] = article

    by_title = {}

    for article in by_url.values():

        key = normalize_title(
            article.get(
                "headline",
                ""
            )
        )

        if key and key not in by_title:

            by_title[
                key
            ] = article

    return list(
        by_title.values()
    )


# ============================================================
# DATE SORT
# ============================================================

def article_timestamp(
    article
):

    value = article.get(
        "published_at",
        ""
    )

    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    except Exception:

        return datetime.min.replace(
            tzinfo=timezone.utc
        )


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print(
        "=" * 70
    )

    print(
        "SNIPPET24 CURATOR 3.0"
    )

    print(
        "OFFICIAL / PUBLIC SOURCES ONLY"
    )

    print(
        "=" * 70
    )

    previous_articles = (
        load_existing_articles()
    )

    print()
    print(
        f"Previous eligible stories: "
        f"{len(previous_articles)}"
    )

    fresh_articles = []

    successful_sources = 0
    failed_sources = 0

    for category in CATEGORY_ORDER:

        print()
        print(
            f"### {category}"
        )

        for publisher, url in (
            RSS_SOURCES.get(
                category,
                []
            )
        ):

            found = fetch_source(
                publisher,
                url,
                category
            )

            if found:

                successful_sources += 1

                fresh_articles.extend(
                    found
                )

            else:

                failed_sources += 1

            time.sleep(
                REQUEST_DELAY
            )

    print()
    print(
        f"Fresh stories collected: "
        f"{len(fresh_articles)}"
    )

    combined = (
        fresh_articles
        + previous_articles
    )

    combined = deduplicate(
        combined
    )

    combined.sort(
        key=article_timestamp,
        reverse=True
    )

    final_articles = combined[
        :TARGET_STORIES
    ]

    counts = {
        category: 0
        for category in CATEGORY_ORDER
    }

    for article in final_articles:

        category = normalize_category(
            article.get(
                "category"
            )
        )

        if category in counts:

            counts[
                category
            ] += 1

    output = {

        "curator_version":
            CURATOR_VERSION,

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total":
            len(final_articles),

        "minimum_target":
            MINIMUM_STORIES,

        "maximum_target":
            TARGET_STORIES,

        "source_policy":
            "official_public_sources_only",

        "copyright_note":
            "Headlines and summaries are Snippet24 editorial rewrites. "
            "Original source URLs and attribution are retained. "
            "Source-specific terms still apply.",

        "categories":
            counts,

        "articles":
            final_articles

    }

    # Final safety check: every output story must come from
    # the approved official/public publisher list.
    approved = {
        "Press Information Bureau",
        "United Nations",
        "World Health Organization",
        "European Commission",
        "European Central Bank",
        "International Monetary Fund",
        "NASA",
        "NASA JPL",
        "NASA CNEOS",
        "National Endowment for the Humanities",
        "Library of Congress",
        "FIFA",
    }

    final_articles = [
        article
        for article in final_articles
        if article.get("publisher") in approved
    ]

    # Recalculate totals after the safety filter.
    counts = category_counts(final_articles)

    output["total"] = len(final_articles)
    output["categories"] = counts
    output["articles"] = final_articles

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
    print(
        "=" * 70
    )

    print(
        f"TOTAL STORIES: "
        f"{len(final_articles)}"
    )

    print(
        "=" * 70
    )

    for category in CATEGORY_ORDER:

        print(
            f"{category}: "
            f"{counts.get(category, 0)}"
        )

    print()
    print(
        f"Successful sources: "
        f"{successful_sources}"
    )

    print(
        f"Failed/empty sources: "
        f"{failed_sources}"
    )

    if len(final_articles) == 0:

        print()
        print(
            "ERROR: No official/public "
            "stories were collected."
        )

        return 1

    if len(final_articles) < MINIMUM_STORIES:

        print()
        print(
            "WARNING: Fewer than 50 "
            "official/public stories are available."
        )

        print(
            "The curator will NOT fabricate "
            "stories just to reach 50."
        )

    else:

        print()
        print(
            "SUCCESS: Minimum 50-story "
            "target reached."
        )

    print()
    print(
        "SUCCESS: articles.json updated."
    )

    return 0


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        build_feed()
    )
