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

REQUEST_TIMEOUT = 8

REQUEST_DELAY = 0.10

HEADERS = {
    "User-Agent": (
        "Snippet24-News/3.0 "
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
#
# IMPORTANT:
#
# RSS feeds provide headlines/descriptions/links.
# Snippet24 does NOT copy full publisher articles.
#
# World:
# international priority.
#
# All other categories:
# Indian sources are prioritised where practical.
#
# ============================================================

RSS_SOURCES = {

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    "World": [

        (
            "BBC World",
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


    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    "India": [

        (
            "PIB",
            "https://www.pib.gov.in/RssMain.aspx"
        ),

        (
            "The Hindu India",
            "https://www.thehindu.com/news/national/feeder/default.rss"
        ),

        (
            "Indian Express India",
            "https://indianexpress.com/section/india/feed/"
        ),

    ],


    # --------------------------------------------------------
    # BUSINESS
    # --------------------------------------------------------

    "Business": [

        (
            "PIB Business",
            "https://www.pib.gov.in/RssMain.aspx"
        ),

        (
            "RBI",
            "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=RSS"
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


    # --------------------------------------------------------
    # TECHNOLOGY & AI
    # --------------------------------------------------------

    "Technology & AI": [

        (
            "PIB Science & Technology",
            "https://www.pib.gov.in/RssMain.aspx"
        ),

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


    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # ENTERTAINMENT
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # LIFESTYLE
    # --------------------------------------------------------

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

}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):

    if not value:

        return ""

    value = html.unescape(
        str(value)
    )

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


# ============================================================
# URL
# ============================================================

def normalize_url(value):

    if not value:

        return ""

    try:

        parsed = urlparse(
            value.strip()
        )

        if parsed.scheme not in (
            "http",
            "https"
        ):

            return ""

        if not parsed.netloc:

            return ""

        return parsed.geturl()

    except Exception:

        return ""


# ============================================================
# TITLE NORMALIZATION
# ============================================================

def normalize_title(value):

    value = clean_text(
        value
    ).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


# ============================================================
# ID
# ============================================================

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
# XML CHILD TEXT
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


# ============================================================
# LINK
# ============================================================

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
# IMAGE
# ============================================================

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

            url = normalize_url(
                child.attrib.get(
                    "url",
                    ""
                )
            )


            if url:

                return url


    # enclosure

    for child in list(element):

        tag = child.tag.split(
            "}"
        )[-1].lower()


        if tag != "enclosure":

            continue


        url = normalize_url(
            child.attrib.get(
                "url",
                ""
            )
        )


        kind = child.attrib.get(
            "type",
            ""
        ).lower()


        if url and (
            "image" in kind
            or not kind
        ):

            return url


    return ""


# ============================================================
# AI IMAGE
# ============================================================
#
# No Pollinations API key is required for this fallback URL.
#
# If you later use a paid/protected image API, replace this
# function with that provider's API implementation.
#
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
        "no logos, no watermark, "
        "no fake newspaper."

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
# SUMMARY
# ============================================================

def make_summary(
    title,
    description
):

    title = clean_text(
        title
    )

    description = clean_text(
        description
    )


    if title:

        description = re.sub(

            re.escape(title),

            "",

            description,

            flags=re.IGNORECASE

        )


    description = re.sub(

        r"^(read more|latest updates|"
        r"follow live|breaking news)"
        r"\s*[:\-]?\s*",

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

        "The latest developments are being "
        "reported by the original publisher. "
        "Read the original report for the "
        "full details."

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


    for element in root.iter():

        tag = element.tag.split(
            "}"
        )[-1].lower()


        if tag not in (
            "item",
            "entry"
        ):

            continue


        title = find_child_text(
            element,
            ["title"]
        )


        if not title:

            continue


        link = find_link(
            element
        )


        if not link:

            continue


        description = find_child_text(

            element,

            [
                "description",
                "summary",
                "content",
                "encoded"
            ]

        )


        published = find_child_text(

            element,

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


        summary = make_summary(
            title,
            description
        )


        image = make_ai_image(
            title,
            category
        )


        article = {

            "id":
                make_id(
                    category,
                    title,
                    link
                ),

            "category":
                category,

            "headline":
                clean_text(
                    title
                ),

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
# FETCH
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
# OLD ARTICLES
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


        return articles


    except FileNotFoundError:

        return []


    except Exception as exc:

        print(
            "Could not read previous "
            f"articles.json: {exc}"
        )

        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    articles
):

    unique_by_url = {}


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


        category = article.get(
            "category",
            "World"
        )


        if category not in CATEGORY_ORDER:

            category = "World"


        article["category"] = category

        article["headline"] = headline

        article["source_url"] = url

        article["summary"] = make_summary(

            headline,

            article.get(
                "summary",
                ""
            )

        )


        if not article.get(
            "image_url"
        ):

            article["image_url"] = (
                make_ai_image(
                    headline,
                    category
                )
            )


        article[
            "image_type"
        ] = "ai_generated"


        if not article.get(
            "id"
        ):

            article["id"] = make_id(

                category,

                headline,

                url

            )


        url_key = url.lower()


        old = unique_by_url.get(
            url_key
        )


        if old is None:

            unique_by_url[
                url_key
            ] = article

        else:

            old_date = old.get(
                "published_at",
                ""
            )

            new_date = article.get(
                "published_at",
                ""
            )


            if new_date > old_date:

                unique_by_url[
                    url_key
                ] = article


    # --------------------------------------------------------
    # TITLE DEDUPLICATION
    # --------------------------------------------------------

    unique_by_title = {}


    for article in unique_by_url.values():

        key = normalize_title(

            article.get(
                "headline",
                ""
            )

        )


        if not key:

            continue


        old = unique_by_title.get(
            key
        )


        if old is None:

            unique_by_title[
                key
            ] = article

        else:

            old_date = old.get(
                "published_at",
                ""
            )

            new_date = article.get(
                "published_at",
                ""
            )


            if new_date > old_date:

                unique_by_title[
                    key
                ] = article


    return list(
        unique_by_title.values()
    )


# ============================================================
# BUILD
# ============================================================

def build_feed():

    print(
        "=" * 65
    )

    print(
        "SNIPPET24 NEWS CURATOR"
    )

    print(
        "=" * 65
    )


    previous =
        load_existing_articles()


    print(
        f"Previous stories: "
        f"{len(previous)}"
    )


    fresh = []


    successful = 0

    failed = 0


    # --------------------------------------------------------
    # FETCH
    # --------------------------------------------------------

    for category in CATEGORY_ORDER:

        print()
        print(
            f"### {category}"
        )


        for publisher, url in (
            RSS_SOURCES
            .get(
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

                successful += 1

                fresh.extend(
                    found
                )

            else:

                failed += 1


            time.sleep(
                REQUEST_DELAY
            )


    print()

    print(
        f"Fresh stories: "
        f"{len(fresh)}"
    )


    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    combined = (
        fresh
        + previous
    )


    print(
        f"Combined before "
        f"dedupe: {len(combined)}"
    )


    final_articles = deduplicate(
        combined
    )


    # --------------------------------------------------------
    # NEWEST FIRST
    # --------------------------------------------------------

    final_articles.sort(

        key=lambda article:
            parse_date(
                article.get(
                    "published_at",
                    ""
                )
            ),

        reverse=True

    )


    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    counts = {

        category:
            sum(
                1
                for article
                in final_articles
                if article.get(
                    "category"
                ) == category
            )

        for category
        in CATEGORY_ORDER

    }


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
            f"{counts[category]}"
        )


    print()

    print(
        f"Successful sources: "
        f"{successful}"
    )

    print(
        f"Failed/empty sources: "
        f"{failed}"
    )


    if not final_articles:

        print(
            "ERROR: No usable stories."
        )

        return 1


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