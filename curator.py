import json
import re
import html
import hashlib
import time
import os

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

import requests
import xml.etree.ElementTree as ET


# ============================================================
# SNIPPET24 NEWS CURATOR
# ============================================================
#
# MAIN RULE:
#
# GLOBAL = INTERNATIONAL NEWS ONLY
#
# India stories must NOT automatically become Global.
#
# ============================================================


OUTPUT_FILE = "articles.json"


MINIMUM_STORIES = 50


REQUEST_TIMEOUT = 10


REQUEST_DELAY = 0.20


HEADERS = {

    "User-Agent":
        "Snippet24-News/4.0 "
        "(+https://snippet24.in)"

}


# ============================================================
# CATEGORY ORDER
# ============================================================

CATEGORY_ORDER = [

    "Global",

    "India",

    "Security & Peace",

    "Law Around Us",

    "Science & Development",

    "Business",

    "Technology & AI",

    "Sports",

    "Society & Culture",

    "Environment",

    "Entertainment",

]


# ============================================================
# INDIA TERMS
# ============================================================

INDIA_TERMS = [

    "india",
    "indian",
    "new delhi",
    "delhi",
    "mumbai",
    "chennai",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "kolkata",
    "pune",
    "ahmedabad",
    "surat",
    "jaipur",
    "lucknow",
    "patna",
    "bhopal",
    "chandigarh",
    "guwahati",
    "kochi",
    "coimbatore",
    "madurai",
    "tamil nadu",
    "kerala",
    "karnataka",
    "telangana",
    "andhra pradesh",
    "maharashtra",
    "gujarat",
    "rajasthan",
    "punjab",
    "haryana",
    "uttar pradesh",
    "uttarakhand",
    "bihar",
    "jharkhand",
    "odisha",
    "assam",
    "west bengal",
    "central government",
    "government of india",
    "india government",
    "lok sabha",
    "rajya sabha",
    "supreme court of india",
    "rbi",
    "sebi",
    "isro",
    "uidai",
    "gst",
    "upi",
]


# ============================================================
# INTERNATIONAL TERMS
# ============================================================

INTERNATIONAL_TERMS = [

    "united states",
    "usa",
    "u.s.",
    "america",
    "american",
    "united kingdom",
    "uk",
    "britain",
    "british",
    "europe",
    "european union",
    "eu",
    "france",
    "germany",
    "italy",
    "spain",
    "ukraine",
    "russia",
    "russian",
    "china",
    "chinese",
    "japan",
    "japanese",
    "south korea",
    "north korea",
    "israel",
    "iran",
    "iraq",
    "syria",
    "lebanon",
    "palestine",
    "gaza",
    "afghanistan",
    "pakistan",
    "bangladesh",
    "nepal",
    "sri lanka",
    "australia",
    "canada",
    "mexico",
    "brazil",
    "argentina",
    "africa",
    "united nations",
    "nato",
    "world bank",
    "imf",
    "g7",
    "g20",
    "global",
    "international",
    "worldwide",
    "foreign government",
    "foreign ministry",
    "president",
    "prime minister",
]


# ============================================================
# RSS SOURCES
# ============================================================
#
# Public / openly accessible feeds only.
#
# No private Telegram/WhatsApp/private channels.
#
# ============================================================

RSS_SOURCES = {


    # --------------------------------------------------------
    # GLOBAL
    # --------------------------------------------------------

    "Global": [

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

        (
            "Hindustan Times India",
            "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"
        ),

        (
            "Times of India",
            "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"
        ),

    ],


    # --------------------------------------------------------
    # SECURITY & PEACE
    # --------------------------------------------------------

    "Security & Peace": [

        (
            "BBC Security",
            "https://feeds.bbci.co.uk/news/world/rss.xml"
        ),

        (
            "Guardian World",
            "https://www.theguardian.com/world/rss"
        ),

    ],


    # --------------------------------------------------------
    # LAW
    # --------------------------------------------------------

    "Law Around Us": [

        (
            "Indian Express India",
            "https://indianexpress.com/section/india/feed/"
        ),

        (
            "The Hindu India",
            "https://www.thehindu.com/news/national/feeder/default.rss"
        ),

    ],


    # --------------------------------------------------------
    # SCIENCE
    # --------------------------------------------------------

    "Science & Development": [

        (
            "ScienceDaily",
            "https://www.sciencedaily.com/rss/top/science.xml"
        ),

        (
            "NASA",
            "https://www.nasa.gov/rss/dyn/breaking_news.rss"
        ),

    ],


    # --------------------------------------------------------
    # BUSINESS
    # --------------------------------------------------------

    "Business": [

        (
            "Moneycontrol Business",
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

        (
            "Economic Times Small Business",
            "https://economictimes.indiatimes.com/small-biz/rssfeeds/5584166.cms"
        ),

        (
            "Mint Companies",
            "https://www.livemint.com/rss/companies"
        ),

        (
            "PIB",
            "https://pib.gov.in/RssMain.aspx"
        ),

    ],


    # --------------------------------------------------------
    # TECHNOLOGY & AI
    # --------------------------------------------------------

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

        (
            "MIT Technology Review",
            "https://www.technologyreview.com/feed/"
        ),

        (
            "VentureBeat AI",
            "https://venturebeat.com/category/ai/feed/"
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

        (
            "Cricbuzz",
            "https://www.cricbuzz.com/rss-feed"
        ),

        (
            "Indian Express Sports",
            "https://indianexpress.com/section/sports/feed/"
        ),

    ],


    # --------------------------------------------------------
    # SOCIETY & CULTURE
    # --------------------------------------------------------

    "Society & Culture": [

        (
            "The Guardian Culture",
            "https://www.theguardian.com/culture/rss"
        ),

        (
            "Indian Express Lifestyle",
            "https://indianexpress.com/section/lifestyle/feed/"
        ),

    ],


    # --------------------------------------------------------
    # ENVIRONMENT
    # --------------------------------------------------------

    "Environment": [

        (
            "Guardian Environment",
            "https://www.theguardian.com/environment/rss"
        ),

        (
            "ScienceDaily Environment",
            "https://www.sciencedaily.com/rss/earth_climate/environmental_science.xml"
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

        (
            "Indian Express Entertainment",
            "https://indianexpress.com/section/entertainment/feed/"
        ),

        (
            "Hindustan Times Entertainment",
            "https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml"
        ),

        (
            "NDTV Entertainment",
            "https://feeds.feedburner.com/ndtvmovies-latest"
        ),

        (
            "Koimoi",
            "https://www.koimoi.com/feed/"
        ),

    ],

}


# ============================================================
# PUBLIC / OFFICIAL SOURCE TYPES
# ============================================================

PUBLIC_SOURCE_TYPES = {

    "BBC World":
        "Public News",

    "NPR World":
        "Public News",

    "Guardian World":
        "Public News",

    "The Hindu":
        "Public News",

    "Indian Express":
        "Public News",

    "NDTV India":
        "Public News",

    "Hindustan Times India":
        "Public News",

    "Times of India":
        "Public News",

    "PIB":
        "Government",

}


# ============================================================
# CLEAN TEXT
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

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# NORMALIZE URL
# ============================================================

def normalize_url(url):

    if not url:
        return ""

    try:

        url = url.strip()

        parsed =
            urlparse(url)

        if parsed.scheme not in (
            "http",
            "https"
        ):
            return ""

        return url

    except Exception:

        return ""


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    title =
        clean_text(title).lower()

    title =
        re.sub(
            r"[^a-z0-9]+",
            " ",
            title
        )

    return re.sub(
        r"\s+",
        " ",
        title
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
# CATEGORY NORMALIZATION
# ============================================================

def normalize_category(
    category
):

    if not category:
        return ""

    value =
        clean_text(
            category
        ).lower()

    aliases = {

        "world":
            "Global",

        "international":
            "Global",

        "world news":
            "Global",

        "international news":
            "Global",

        "india":
            "India",

        "technology":
            "Technology & AI",

        "technology & ai":
            "Technology & AI",

        "tech":
            "Technology & AI",

        "ai":
            "Technology & AI",

        "business":
            "Business",

        "sports":
            "Sports",

        "entertainment":
            "Entertainment",

        "lifestyle":
            "Society & Culture",

        "environment":
            "Environment",

    }

    if value in aliases:

        return aliases[value]

    for known in CATEGORY_ORDER:

        if value == known.lower():

            return known

    return ""


# ============================================================
# GLOBAL VALIDATION
# ============================================================

def is_india_story(
    title,
    summary
):

    text = (
        clean_text(title)
        + " "
        + clean_text(summary)
    ).lower()

    for term in INDIA_TERMS:

        if term in text:

            return True

    return False


def is_global_story(
    title,
    summary
):

    text = (
        clean_text(title)
        + " "
        + clean_text(summary)
    ).lower()

    if is_india_story(
        title,
        summary
    ):

        return False

    for term in INTERNATIONAL_TERMS:

        if term in text:

            return True

    return True


# ============================================================
# TITLE CLEANING
# ============================================================

def remove_publisher_from_title(
    title,
    publisher
):

    title =
        clean_text(title)

    publishers = [

        publisher,

        "BBC",

        "BBC News",

        "Reuters",

        "NPR",

        "Guardian",

        "The Hindu",

        "Indian Express",

        "NDTV",

        "Hindustan Times",

        "Times of India",

        "TechCrunch",

        "The Verge",

        "Variety",

        "Koimoi",

    ]

    for name in publishers:

        if not name:
            continue

        pattern = (
            r"\s*(?:\||-|\u2013|\u2014)\s*"
            +
            re.escape(name)
            +
            r"\s*$"
        )

        title =
            re.sub(
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

def clean_summary(
    summary
):

    summary =
        clean_text(summary)

    summary =
        re.sub(
            r"^(read more|"
            r"latest updates|"
            r"follow live|"
            r"breaking news)\s*[:\-]?\s*",
            "",
            summary,
            flags=re.IGNORECASE
        )

    return summary.strip()


# ============================================================
# THREE-LINE SNIPPET
# ============================================================

def make_three_line_snippet(
    title,
    description
):

    description =
        clean_summary(
            description
        )

    if not description:

        return (
            "The original publisher has "
            "reported the latest development. "
            "Read the original report for complete details."
        )

    sentences =
        re.split(
            r"(?<=[.!?])\s+",
            description
        )

    sentences =
        [
            s.strip()
            for s in sentences
            if s.strip()
        ]

    selected =
        sentences[:3]

    if not selected:

        return description[:360]

    return " ".join(
        selected
    )


# ============================================================
# AI REPHRASING
# ============================================================
#
# Optional.
#
# Set GitHub Actions secret:
#
# OPENAI_API_KEY
#
# If unavailable, the original feed description is used.
#
# ============================================================

def ai_rephrase(
    title,
    description,
    category
):

    api_key =
        os.getenv(
            "OPENAI_API_KEY",
            ""
        )

    if not api_key:

        return (
            make_three_line_snippet(
                title,
                description
            ),
            clean_summary(
                description
            )
        )

    prompt = f"""
Rewrite the following news item for Snippet24.

Category: {category}

Headline:
{title}

Original description:
{description}

Rules:

1. Do not invent facts.
2. Do not add opinions.
3. Do not add quotations.
4. Do not copy the original article.
5. Produce exactly three short factual sentences
   for the snippet.
6. Then produce one short summary paragraph.
7. Preserve names, dates and numbers accurately.
8. Keep the writing neutral and journalistic.

Return JSON only:

{{
  "snippet": "...",
  "summary": "..."
}}
"""

    try:

        response =
            requests.post(

                "https://api.openai.com/v1/chat/completions",

                headers={
                    "Authorization":
                        f"Bearer {api_key}",

                    "Content-Type":
                        "application/json"
                },

                json={

                    "model":
                        "gpt-4o-mini",

                    "messages": [

                        {
                            "role":
                                "system",

                            "content":
                                "You are a careful news editor."
                        },

                        {
                            "role":
                                "user",

                            "content":
                                prompt
                        }

                    ],

                    "temperature":
                        0.2

                },

                timeout=20

            )

        response.raise_for_status()

        data =
            response.json()

        content =
            data["choices"][0]["message"]["content"]

        content =
            content.strip()

        content =
            re.sub(
                r"^```json",
                "",
                content
            )

        content =
            re.sub(
                r"```$",
                "",
                content
            )

        parsed =
            json.loads(
                content.strip()
            )

        snippet =
            clean_text(
                parsed.get(
                    "snippet",
                    ""
                )
            )

        summary =
            clean_text(
                parsed.get(
                    "summary",
                    ""
                )
            )

        if snippet and summary:

            return (
                snippet,
                summary
            )

    except Exception as exc:

        print(
            "AI rewrite failed:",
            exc
        )

    return (
        make_three_line_snippet(
            title,
            description
        ),
        clean_summary(
            description
        )
    )


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(
    value
):

    if not value:

        return datetime.now(
            timezone.utc
        )

    value =
        value.strip()

    try:

        return (
            parsedate_to_datetime(
                value
            )
            .astimezone(
                timezone.utc
            )
        )

    except Exception:
        pass

    try:

        return (
            datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )
            .astimezone(
                timezone.utc
            )
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

    for child in list(
        element
    ):

        tag =
            child.tag.split(
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
# XML LINK
# ============================================================

def find_link(
    element
):

    for child in list(
        element
    ):

        tag =
            child.tag.split(
                "}"
            )[-1].lower()

        if tag != "link":

            continue

        href =
            child.attrib.get(
                "href"
            )

        if href:

            return normalize_url(
                href
            )

        text =
            clean_text(
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

    for child in element.iter():

        tag =
            child.tag.split(
                "}"
            )[-1].lower()

        if tag in (
            "content",
            "thumbnail"
        ):

            url =
                child.attrib.get(
                    "url"
                )

            if url:

                return normalize_url(
                    url
                )

    for child in list(
        element
    ):

        tag =
            child.tag.split(
                "}"
            )[-1].lower()

        if tag != "enclosure":
            continue

        url =
            child.attrib.get(
                "url",
                ""
            )

        kind =
            child.attrib.get(
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

    raw =
        "".join(
            element.itertext()
        )

    match =
        re.search(
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
# AI IMAGE
# ============================================================

def make_ai_image(
    title,
    category
):

    prompt = (

        "Professional editorial news "
        "illustration for Snippet24. "

        f"Category: {category}. "

        f"Story: {title}. "

        "Realistic journalistic visual. "

        "Modern newspaper photography style. "

        "No text. "
        "No letters. "
        "No logo. "
        "No watermark."

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
        +
        quote(
            prompt,
            safe=""
        )
        +
        "?width=1200"
        +
        "&height=675"
        +
        "&nologo=true"
        +
        f"&seed={seed}"
    )


# ============================================================
# PARSE FEED
# ============================================================

def parse_feed(
    xml_text,
    publisher,
    category
):

    articles = []

    try:

        root =
            ET.fromstring(
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

        tag =
            element.tag.split(
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

        title =
            find_child_text(
                item,
                ["title"]
            )

        if not title:
            continue


        title =
            remove_publisher_from_title(
                title,
                publisher
            )


        if len(title) < 8:
            continue


        description =
            find_child_text(
                item,
                [
                    "description",
                    "summary",
                    "content",
                    "encoded"
                ]
            )


        link =
            find_link(
                item
            )


        if not link:
            continue


        published =
            find_child_text(
                item,
                [
                    "pubdate",
                    "published",
                    "updated",
                    "date",
                    "created"
                ]
            )


        date_obj =
            parse_date(
                published
            )


        normalized_category =
            normalize_category(
                category
            )


        # ----------------------------------------------------
        # STRICT GLOBAL FILTER
        # ----------------------------------------------------

        if normalized_category == "Global":

            if not is_global_story(
                title,
                description
            ):

                continue


        # ----------------------------------------------------
        # AI / EDITORIAL REWRITE
        # ----------------------------------------------------

        snippet, summary =
            ai_rephrase(
                title,
                description,
                normalized_category
            )


        image =
            find_image_from_feed(
                item
            )


        if not image:

            image =
                make_ai_image(
                    title,
                    normalized_category
                )


        source_type =
            PUBLIC_SOURCE_TYPES.get(
                publisher,
                "Public News"
            )


        article = {

            "id":
                make_id(
                    normalized_category,
                    title,
                    link
                ),

            "category":
                normalized_category,

            "headline":
                title,

            "snippet":
                snippet,

            "summary":
                summary,

            "publisher":
                clean_text(
                    publisher
                ),

            "source_type":
                source_type,

            "language":
                "English",

            "published_at":
                date_obj.isoformat(),

            "source_url":
                link,

            "image_url":
                image,

            "image_type":
                (
                    "feed"
                    if find_image_from_feed(item)
                    else "ai_generated"
                ),

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

    print(
        f"Fetching: {publisher}"
    )

    try:

        response =
            requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

        response.raise_for_status()

        articles =
            parse_feed(
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
            f"  -> FAILED: "
            f"{publisher}: {exc}"
        )

        return []


# ============================================================
# LOAD EXISTING ARTICLES
# ============================================================

def load_existing_articles():

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data =
                json.load(file)


        articles =
            data.get(
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


            headline =
                clean_text(
                    article.get(
                        "headline"
                    )
                )


            url =
                normalize_url(
                    article.get(
                        "source_url"
                    )
                )


            if not headline or not url:

                continue


            category =
                normalize_category(
                    article.get(
                        "category"
                    )
                )


            # Do NOT convert unknown categories
            # into Global.

            if not category:

                continue


            if category == "Global":

                if not is_global_story(
                    headline,
                    article.get(
                        "summary",
                        ""
                    )
                ):

                    continue


            article[
                "category"
            ] = category


            article[
                "headline"
            ] = headline


            article[
                "source_url"
            ] = url


            article[
                "snippet"
            ] = make_three_line_snippet(
                headline,
                article.get(
                    "summary",
                    ""
                )
            )


            if not article.get(
                "image_url"
            ):

                article[
                    "image_url"
                ] = make_ai_image(
                    headline,
                    category
                )


            if not article.get(
                "language"
            ):

                article[
                    "language"
                ] = "English"


            valid.append(
                article
            )


        return valid


    except FileNotFoundError:

        print(
            "No existing articles.json found."
        )

        return []


    except Exception as exc:

        print(
            "Could not read articles.json:",
            exc
        )

        return []


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    articles
):

    unique_url = {}


    for article in articles:

        if not isinstance(
            article,
            dict
        ):

            continue


        title =
            clean_text(
                article.get(
                    "headline"
                )
            )


        url =
            normalize_url(
                article.get(
                    "source_url"
                )
            )


        if not title or not url:

            continue


        key =
            url.lower()


        if key not in unique_url:

            unique_url[
                key
            ] = article

        else:

            old =
                unique_url[
                    key
                ]

            old_date =
                old.get(
                    "published_at",
                    ""
                )

            new_date =
                article.get(
                    "published_at",
                    ""
                )

            if new_date > old_date:

                unique_url[
                    key
                ] = article


    # --------------------------------------------------------
    # TITLE DEDUPLICATION
    # --------------------------------------------------------

    unique_title = {}


    for article in unique_url.values():

        title_key =
            normalize_title(
                article.get(
                    "headline",
                    ""
                )
            )


        if not title_key:

            continue


        if title_key not in unique_title:

            unique_title[
                title_key
            ] = article

        else:

            old =
                unique_title[
                    title_key
                ]

            old_date =
                old.get(
                    "published_at",
                    ""
                )

            new_date =
                article.get(
                    "published_at",
                    ""
                )

            if new_date > old_date:

                unique_title[
                    title_key
                ] = article


    return list(
        unique_title.values()
    )


# ============================================================
# TIMESTAMP
# ============================================================

def article_timestamp(
    article
):

    value =
        article.get(
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
# SORT
# ============================================================

def sort_articles(
    articles
):

    return sorted(
        articles,
        key=lambda article:
            article_timestamp(
                article
            ),
        reverse=True
    )


# ============================================================
# CATEGORY COUNTS
# ============================================================

def category_counts(
    articles
):

    counts = {

        category: 0

        for category
        in CATEGORY_ORDER

    }


    for article in articles:

        category =
            article.get(
                "category",
                ""
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
        "=" * 70
    )

    print(
        "SNIPPET24 NEWS CURATOR"
    )

    print(
        "GLOBAL = INTERNATIONAL ONLY"
    )

    print(
        "=" * 70
    )


    previous_articles =
        load_existing_articles()


    print()

    print(
        "Previous valid stories:",
        len(previous_articles)
    )


    fresh_articles = []


    successful_sources = 0

    failed_sources = 0


    # --------------------------------------------------------
    # FETCH
    # --------------------------------------------------------

    for category in CATEGORY_ORDER:

        sources =
            RSS_SOURCES.get(
                category,
                []
            )


        print()

        print(
            f"### {category}"
        )


        for publisher, url in sources:

            found =
                fetch_source(
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
        "Fresh stories collected:",
        len(fresh_articles)
    )

    print(
        "Successful sources:",
        successful_sources
    )

    print(
        "Failed/empty sources:",
        failed_sources
    )


    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    combined =
        fresh_articles + previous_articles


    print()

    print(
        "Combined before deduplication:",
        len(combined)
    )


    combined =
        deduplicate(
            combined
        )


    print(
        "After deduplication:",
        len(combined)
    )


    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    final_articles =
        sort_articles(
            combined
        )


    print(
        "Final usable stories:",
        len(final_articles)
    )


    # --------------------------------------------------------
    # CATEGORY COUNTS
    # --------------------------------------------------------

    counts =
        category_counts(
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
            None,

        "categories":
            counts,

        "articles":
            final_articles

    }


    # --------------------------------------------------------
    # WRITE JSON
    # --------------------------------------------------------

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
        "=" * 70
    )

    print(
        "CATEGORY REPORT"
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
        "Successful sources:",
        successful_sources
    )

    print(
        "Failed/empty sources:",
        failed_sources
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not final_articles:

        print()

        print(
            "ERROR: No usable articles."
        )

        return 1


    if len(final_articles) < MINIMUM_STORIES:

        print()

        print(
            "WARNING: Fewer than 50 "
            "usable stories."
        )

        print(
            "No artificial stories created."
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
