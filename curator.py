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
# SNIPPET24 NEWS CURATOR 5.0
# OFFICIAL / PUBLIC SOURCES ONLY
# ============================================================

CURATOR_VERSION = "5.0-official-public"

OUTPUT_FILE = "articles.json"

TARGET_STORIES = 100
MINIMUM_STORIES = 50

REQUEST_TIMEOUT = 20
REQUEST_DELAY = 0.30

HEADERS = {
    "User-Agent": (
        "Snippet24-News/5.0 "
        "(+https://snippet24.in)"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, "
        "application/xml, text/xml, text/html, */*"
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
# OFFICIAL / PUBLIC SOURCES
# ============================================================
#
# IMPORTANT:
# A public RSS feed is not automatically copyright-free.
# Snippet24 keeps the original source URL and attribution,
# creates its own headline/summary treatment, and uses an
# AI-generated visual rather than copying publisher photos.
#
# This reduces risk but cannot guarantee zero legal risk.
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
        (
            "International Olympic Committee",
            "https://olympics.com/ioc/news/rss"
        ),
    ],

    "Entertainment": [
        (
            "National Endowment for the Arts",
            "https://www.arts.gov/news/feed"
        ),
        (
            "National Endowment for the Humanities",
            "https://www.neh.gov/news/feed"
        ),
        (
            "Smithsonian",
            "https://www.si.edu/rss"
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
            "NASA",
            "https://www.nasa.gov/news-release/feed/"
        ),
    ],
}


# ============================================================
# APPROVED PUBLISHERS
# ============================================================

APPROVED_PUBLISHERS = {
    "Press Information Bureau",
    "United Nations",
    "World Health Organization",
    "European Commission",
    "European Central Bank",
    "International Monetary Fund",
    "NASA",
    "NASA JPL",
    "NASA CNEOS",
    "FIFA",
    "International Olympic Committee",
    "National Endowment for the Arts",
    "National Endowment for the Humanities",
    "Smithsonian",
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

    value = value.replace("\xa0", " ")

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


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

    url = str(url).strip()

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        if not parsed.netloc:
            return ""

        return url

    except Exception:
        return ""


def normalize_title(title):
    title = clean_text(title).lower()

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


def article_timestamp(article):
    value = article.get(
        "published_at",
        ""
    )

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except Exception:
        return datetime.min.replace(
            tzinfo=timezone.utc
        )


# ============================================================
# CATEGORY COUNTS
# ============================================================

def category_counts(articles):
    counts = {
        category: 0
        for category in CATEGORY_ORDER
    }

    for article in articles:

        category = normalize_category(
            article.get("category")
        )

        if category in counts:
            counts[category] += 1

    return counts


# ============================================================
# SOURCE TYPE
# ============================================================

def source_type(publisher):
    if publisher in APPROVED_PUBLISHERS:
        return "official_public"

    return "unknown"


# ============================================================
# TITLE CLEANING
# ============================================================

def remove_publisher_from_title(title, publisher):
    title = clean_text(title)

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
        "NASA JPL",
        "NASA CNEOS",
        "FIFA",
        "International Olympic Committee",
        "National Endowment for the Arts",
        "National Endowment for the Humanities",
        "Smithsonian",
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

def remove_title_repetition(summary, title):
    summary = clean_text(summary)

    if not summary:
        return ""

    if title:
        summary = re.sub(
            re.escape(clean_text(title)),
            "",
            summary,
            flags=re.IGNORECASE
        )

    return re.sub(
        r"\s+",
        " ",
        summary
    ).strip()


def make_summary(title, description):
    description = clean_text(description)

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
        return datetime.now(timezone.utc)

    value = clean_text(value)

    try:
        return parsedate_to_datetime(
            value
        ).astimezone(timezone.utc)

    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)

    except Exception:
        return datetime.now(timezone.utc)


# ============================================================
# XML HELPERS
# ============================================================

def tag_name(element):
    return element.tag.split("}")[-1].lower()


def find_child_text(element, names):
    names = {
        name.lower()
        for name in names
    }

    for child in list(element):

        if tag_name(child) in names:

            return clean_text(
                "".join(
                    child.itertext()
                )
            )

    return ""


def find_link(element):
    links = []

    for child in list(element):

        if tag_name(child) != "link":
            continue

        href = child.attrib.get("href")

        if href:
            links.append(href)

        text = clean_text(
            "".join(
                child.itertext()
            )
        )

        if text:
            links.append(text)

    for link in links:
        normalized = normalize_url(link)

        if normalized:
            return normalized

    return ""


# ============================================================
# AI IMAGE
# ============================================================

def make_ai_image(title, category):
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
        + quote(prompt, safe="")
        + "?width=1200"
        + "&height=675"
        + "&nologo=true"
        + f"&seed={seed}"
    )


# ============================================================
# RSS PARSER
# ============================================================

def parse_feed(xml_text, publisher, category):
    articles = []

    if source_type(publisher) != "official_public":
        return articles

    try:
        root = ET.fromstring(xml_text)

    except Exception as exc:
        print(
            f"  XML ERROR: {publisher}: {exc}"
        )
        return articles

    for item in root.iter():

        if tag_name(item) not in ("item", "entry"):
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
                "encoded",
            ]
        )

        link = find_link(item)

        if not link:
            continue

        published = find_child_text(
            item,
            [
                "pubdate",
                "published",
                "updated",
                "date",
                "created",
            ]
        )

        date_obj = parse_date(published)

        normalized_category = normalize_category(
            category
        )

        article = {
            "id": make_id(
                normalized_category,
                title,
                link
            ),
            "category": normalized_category,
            "headline": title,
            "summary": make_summary(
                title,
                description
            ),
            "publisher": publisher,
            "source_type": "official_public",
            "published_at": date_obj.isoformat(),
            "source_url": link,
            "image_url": make_ai_image(
                title,
                normalized_category
            ),
            "image_type": "ai_generated",
        }

        articles.append(article)

    return articles


# ============================================================
# FETCH SOURCE
# ============================================================

def fetch_source(publisher, url, category):
    print()
    print(f"Fetching: {publisher}")
    print(f"  URL: {url}")

    if publisher not in APPROVED_PUBLISHERS:
        print(
            f"  -> BLOCKED: {publisher} "
            f"is not on the official/public allow-list."
        )
        return []

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

            data = json.load(file)

        articles = data.get(
            "articles",
            []
        )

        if not isinstance(articles, list):
            return []

        valid = []
        removed = 0

        for article in articles:

            if not isinstance(article, dict):
                continue

            publisher = clean_text(
                article.get(
                    "publisher",
                    ""
                )
            )

            # Critical safety rule:
            # old private-source articles never return.
            if publisher not in APPROVED_PUBLISHERS:
                removed += 1
                continue

            headline = clean_text(
                article.get(
                    "headline",
                    ""
                )
            )

            url = normalize_url(
                article.get(
                    "source_url",
                    ""
                )
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

            article["publisher"] = publisher
            article["source_type"] = "official_public"
            article["source_url"] = url

            if not article.get("published_at"):
                article["published_at"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

            if not article.get("image_url"):
                article["image_url"] = make_ai_image(
                    headline,
                    article["category"]
                )

            article["image_type"] = "ai_generated"

            article["id"] = article.get(
                "id"
            ) or make_id(
                article["category"],
                headline,
                url
            )

            valid.append(article)

        print(
            f"Old private/non-approved stories removed: "
            f"{removed}"
        )

        return valid

    except FileNotFoundError:
        print(
            "No previous articles.json found."
        )
        return []

    except Exception as exc:
        print(
            f"Could not read previous articles.json: {exc}"
        )
        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(articles):
    by_url = {}

    for article in articles:

        if not isinstance(article, dict):
            continue

        try:

            publisher = clean_text(
                article.get(
                    "publisher",
                    ""
                )
            )

            if publisher not in APPROVED_PUBLISHERS:
                continue

            title = clean_text(
                article.get(
                    "headline",
                    ""
                )
            )

            url = normalize_url(
                article.get(
                    "source_url",
                    ""
                )
            )

            if not title or not url:
                continue

            key = url.lower().strip()

            if key not in by_url:

                by_url[key] = article

            else:

                if (
                    article_timestamp(article)
                    >
                    article_timestamp(by_url[key])
                ):
                    by_url[key] = article

        except Exception as exc:

            print(
                f"  Skipping invalid article: {exc}"
            )

    by_title = {}

    for article in by_url.values():

        try:

            key = normalize_title(
                article.get(
                    "headline",
                    ""
                )
            )

            if not key:
                continue

            if key not in by_title:
                by_title[key] = article

            elif (
                article_timestamp(article)
                >
                article_timestamp(by_title[key])
            ):
                by_title[key] = article

        except Exception as exc:

            print(
                f"  Skipping title-check error: {exc}"
            )

    return list(
        by_title.values()
    )


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print("=" * 70)
    print(
        "SNIPPET24 NEWS CURATOR 5.0"
    )
    print(
        "OFFICIAL / PUBLIC SOURCES ONLY"
    )
    print("=" * 70)

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

    # --------------------------------------------------------
    # FETCH
    # --------------------------------------------------------

    for category in CATEGORY_ORDER:

        print()
        print(f"### {category}")

        for publisher, url in RSS_SOURCES.get(
            category,
            []
        ):

            found = fetch_source(
                publisher,
                url,
                category
            )

            if found:
                successful_sources += 1
                fresh_articles.extend(found)
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

    # --------------------------------------------------------
    # COMBINE + CLEAN
    # --------------------------------------------------------

    combined = (
        fresh_articles
        + previous_articles
    )

    combined = deduplicate(
        combined
    )

    print(
        f"After deduplication: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # NEWEST FIRST
    # --------------------------------------------------------

    combined.sort(
        key=article_timestamp,
        reverse=True
    )

    final_articles = combined[
        :TARGET_STORIES
    ]

    # --------------------------------------------------------
    # FINAL SAFETY FILTER
    # --------------------------------------------------------

    final_articles = [
        article
        for article in final_articles
        if article.get("publisher")
        in APPROVED_PUBLISHERS
    ]

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
            (
                "Headlines and summaries are Snippet24 "
                "editorial rewrites. Original source URLs "
                "and attribution are retained. Source-"
                "specific terms still apply."
            ),

        "categories":
            counts,

        "articles":
            final_articles,
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
    print("=" * 70)

    print(
        f"TOTAL STORIES: "
        f"{len(final_articles)}"
    )

    print("=" * 70)

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

    print()

    if len(final_articles) == 0:

        print(
            "ERROR: No official/public stories "
            "are available."
        )

        return 1

    if len(final_articles) < MINIMUM_STORIES:

        print(
            "WARNING: Fewer than 50 official/public "
            "stories are available."
        )

        print(
            "The curator will NOT fabricate stories."
        )

    else:

        print(
            "SUCCESS: Minimum 50-story target reached."
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
