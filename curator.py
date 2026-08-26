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
# SNIPPET24 NEWS CURATOR
# ============================================================

OUTPUT_FILE = "articles.json"

TARGET_STORIES = 100
MINIMUM_STORIES = 50

MAX_PER_CATEGORY = 20

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.25

HEADERS = {
    "User-Agent": (
        "Snippet24-News/2.0 "
        "(+https://snippet24.in)"
    )
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
# RSS SOURCES
# ============================================================

RSS_SOURCES = {

    "World": [
        (
            "BBC News",
            "https://feeds.bbci.co.uk/news/world/rss.xml"
        ),
        (
            "NPR World",
            "https://feeds.npr.org/1004/rss.xml"
        ),
        (
            "Guardian World",
            "https://www.theguardian.com/world/rss"
        ),
    ],

    "India": [
        (
            "The Hindu",
            "https://www.thehindu.com/news/national/feeder/default.rss"
        ),
        (
            "Indian Express",
            "https://indianexpress.com/section/india/feed/"
        ),
        (
            "NDTV India",
            "https://feeds.feedburner.com/ndtvnews-india-news"
        ),
    ],

    "Business": [
        (
            "Moneycontrol",
            "https://www.moneycontrol.com/rss/business.xml"
        ),
        (
            "Business Standard",
            "https://www.business-standard.com/rss/home_page_top_stories.rss"
        ),
        (
            "Economic Times",
            "https://economictimes.indiatimes.com/rssfeedsdefault.cms"
        ),
    ],

    "Technology & AI": [
        (
            "TechCrunch",
            "https://techcrunch.com/feed/"
        ),
        (
            "The Verge",
            "https://www.theverge.com/rss/index.xml"
        ),
        (
            "Ars Technica",
            "https://feeds.arstechnica.com/arstechnica/index"
        ),
    ],

    "Lifestyle": [
        (
            "Hindustan Times Lifestyle",
            "https://www.hindustantimes.com/feeds/rss/lifestyle/rssfeed.xml"
        ),
        (
            "Guardian Lifestyle",
            "https://www.theguardian.com/lifeandstyle/rss"
        ),
    ],

    "Sports": [
        (
            "ESPN",
            "https://www.espn.com/espn/rss/news"
        ),
        (
            "BBC Sport",
            "https://feeds.bbci.co.uk/sport/rss.xml"
        ),
    ],

    "Entertainment": [
        (
            "Variety",
            "https://variety.com/feed/"
        ),
        (
            "Hollywood Reporter",
            "https://www.hollywoodreporter.com/feed/"
        ),
    ],
}


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

    value = value.replace(
        "&nbsp;",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_category(category):
    if not category:
        return "World"

    value = clean_text(category).lower()

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

    url = url.strip()

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
    title = clean_text(title)

    title = title.lower()

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


def make_id(category, title, url):
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

    title = clean_text(title)

    if not title:
        return ""

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
        "ESPN",
        "Hollywood Reporter",
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
# SUMMARY CLEANING
# ============================================================

def remove_title_repetition(
    summary,
    title
):

    summary = clean_text(summary)

    if not summary:
        return ""

    if title:

        summary = re.sub(
            re.escape(title),
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

    title = clean_text(title)

    description = clean_text(
        description
    )

    description = remove_title_repetition(
        description,
        title
    )

    # Remove common RSS noise.

    description = re.sub(
        r"^(read more|latest updates|"
        r"follow live|breaking news)\s*[:\-]?\s*",
        "",
        description,
        flags=re.IGNORECASE
    )

    # Remove repeated source endings.

    description = re.sub(
        r"\s*(?:\||-|\u2013|\u2014)\s*"
        r"[A-Za-z0-9 .&]+$",
        "",
        description
    ).strip()

    # Remove excessive whitespace.

    description = re.sub(
        r"\s+",
        " ",
        description
    ).strip()

    # Keep summaries compact.

    if len(description) > 420:

        description = (
            description[:417]
            .rsplit(" ", 1)[0]
            + "..."
        )

    if description:
        return description

    # Do not invent facts.

    return (
        "The latest developments are being "
        "reported by the original publisher. "
        "Read the original report for the "
        "full details."
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

    # RSS / Atom links.

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


def find_image_from_feed(
    element
):

    # media:content
    # media:thumbnail

    for child in element.iter():

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag in (
            "content",
            "thumbnail"
        ):

            url = child.attrib.get(
                "url"
            )

            if url:
                return normalize_url(
                    url
                )

    # enclosure

    for child in list(element):

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag != "enclosure":
            continue

        url = child.attrib.get(
            "url",
            ""
        )

        kind = child.attrib.get(
            "type",
            ""
        ).lower()

        if url and (
            "image" in kind
            or not kind
        ):

            return normalize_url(
                url
            )

    # Search raw HTML for image URL.

    raw = "".join(
        element.itertext()
    )

    match = re.search(
        r'https?://[^"\'>\s]+?'
        r'\.(?:jpg|jpeg|png|webp)'
        r'(?:\?[^"\'>\s]*)?',
        raw,
        flags=re.IGNORECASE
    )

    if match:

        return normalize_url(
            match.group(0)
        )

    return ""


# ============================================================
# AI IMAGE URL
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
            ).encode("utf-8")
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
            f"XML error from "
            f"{publisher}: {exc}"
        )

        return articles

    elements = []

    for element in root.iter():

        tag = element.tag.split(
            "}"
        )[-1].lower()

        if tag in (
            "item",
            "entry"
        ):

            elements.append(
                element
            )

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

        summary = make_summary(
            title,
            description
        )

        # IMPORTANT:
        # Snippet24 creates an original
        # editorial visual for every article.
        #
        # We do not use publisher images
        # as the primary visual.

        image = make_ai_image(
            title,
            normalized_category
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
                summary,

            "publisher":
                clean_text(
                    publisher
                ),

            "published_at":
                date_obj.isoformat(),

            "source_url":
                link,

            "image_url":
                image,

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
        f"Fetching: {publisher}"
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
# LOAD PREVIOUS FEED
# ============================================================

def load_existing_articles():

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        articles = data.get(
            "articles",
            []
        )

        if not isinstance(
            articles,
            list
        ):

            return []

        valid = []

        for article in articles:

            if not isinstance(
                article,
                dict
            ):
                continue

            headline = clean_text(
                article.get(
                    "headline"
                )
            )

            url = normalize_url(
                article.get(
                    "source_url"
                )
            )

            if not headline or not url:
                continue

            article[
                "category"
            ] = normalize_category(
                article.get(
                    "category"
                )
            )

            article[
                "headline"
            ] = headline

            article[
                "summary"
            ] = make_summary(
                headline,
                article.get(
                    "summary",
                    ""
                )
            )

            article[
                "source_url"
            ] = url

            # If old article has no AI
            # image, create one.

            image = article.get(
                "image_url"
            )

            if not image or (
                "pollinations.ai"
                not in image
            ):

                article[
                    "image_url"
                ] = make_ai_image(
                    headline,
                    article[
                        "category"
                    ]
                )

                article[
                    "image_type"
                ] = "ai_generated"

            else:

                article[
                    "image_type"
                ] = "ai_generated"

            if not article.get(
                "id"
            ):

                article[
                    "id"
                ] = make_id(
                    article[
                        "category"
                    ],
                    headline,
                    url
                )

            valid.append(
                article
            )

        return valid

    except FileNotFoundError:

        print(
            "No previous articles.json found."
        )

        return []

    except Exception as exc:

        print(
            f"Could not read previous "
            f"articles.json: {exc}"
        )

        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    articles
):

    unique = {}

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

        title_key = normalize_title(
            title
        )

        url_key = url.lower()

        # URL is the strongest duplicate key.

        key = url_key

        if key not in unique:

            unique[key] = article

        else:

            # Prefer newer item.

            old_date = unique[
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

                unique[
                    key
                ] = article

    # Second title-level deduplication.

    title_unique = {}

    for article in unique.values():

        title_key = normalize_title(
            article.get(
                "headline",
                ""
            )
        )

        if not title_key:
            continue

        if title_key not in title_unique:

            title_unique[
                title_key
            ] = article

    return list(
        title_unique.values()
    )


# ============================================================
# DATE SORTING
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
# FIFO
# ============================================================

def apply_fifo(
    articles
):

    articles = deduplicate(
        articles
    )

    articles.sort(
        key=article_timestamp,
        reverse=True
    )

    # Keep the newest TARGET_STORIES.

    return articles[
        :TARGET_STORIES
    ]


# ============================================================
# CATEGORY COUNTS
# ============================================================

def category_counts(
    articles
):

    counts = {
        category: 0
        for category in CATEGORY_ORDER
    }

    for article in articles:

        category = normalize_category(
            article.get(
                "category"
            )
        )

        if category in counts:

            counts[
                category
            ] += 1

    return counts


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print(
        "=" * 65
    )

    print(
        "SNIPPET24 NEWS CURATOR 2.0"
    )

    print(
        "=" * 65
    )

    previous_articles = (
        load_existing_articles()
    )

    print()
    print(
        f"Previous valid stories: "
        f"{len(previous_articles)}"
    )

    fresh_articles = []

    successful_sources = 0
    failed_sources = 0

    # --------------------------------------------------------
    # FETCH ALL CURRENT SOURCES
    # --------------------------------------------------------

    for category in CATEGORY_ORDER:

        sources = RSS_SOURCES.get(
            category,
            []
        )

        print()
        print(
            f"### {category}"
        )

        for publisher, url in sources:

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

    print(
        f"Successful sources: "
        f"{successful_sources}"
    )

    print(
        f"Failed/empty sources: "
        f"{failed_sources}"
    )

    # --------------------------------------------------------
    # COMBINE OLD + NEW
    # --------------------------------------------------------

    combined = (
        fresh_articles
        + previous_articles
    )

    print()
    print(
        f"Combined stories before "
        f"deduplication: "
        f"{len(combined)}"
    )

    combined = deduplicate(
        combined
    )

    print(
        f"After deduplication: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # FIFO
    # --------------------------------------------------------

    final_articles = apply_fifo(
        combined
    )

    print(
        f"After FIFO: "
        f"{len(final_articles)}"
    )

    # --------------------------------------------------------
    # CATEGORY COUNTS
    # --------------------------------------------------------

    counts = category_counts(
        final_articles
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output = {

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

        "categories":
            counts,

        "articles":
            final_articles

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

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print(
        "=" * 65
    )

    print(
        f"TOTAL STORIES: "
        f"{len(final_articles)}"
    )

    print(
        "=" * 65
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

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if len(final_articles) == 0:

        print()
        print(
            "ERROR: No usable articles "
            "are available."
        )

        print(
            "The previous articles.json "
            "has not been intentionally "
            "deleted by the curator."
        )

        return 1

    if len(final_articles) < MINIMUM_STORIES:

        print()
        print(
            "WARNING: Fewer than 50 "
            "usable stories are currently "
            "available."
        )

        print(
            "This is not a fabricated feed. "
            "The curator keeps only genuine "
            "stories supplied by the sources "
            "or previously retained stories."
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