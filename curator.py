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
# FINAL UNLIMITED-NEWS VERSION
# ============================================================

OUTPUT_FILE = "articles.json"

# No artificial maximum.
# The curator keeps all usable unique stories collected
# from the configured sources.
MINIMUM_STORIES = 50

REQUEST_TIMEOUT = 8
REQUEST_DELAY = 0.15

HEADERS = {
    "User-Agent": (
        "Snippet24-News/3.0 "
        "(+https://snippet24.in)"
    )
}


# ============================================================
# CATEGORY ORDER
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

    # --------------------------------------------------------
    # WORLD
    #
    # International stories are the priority here.
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

        (
            "Reuters World",
            "https://feeds.reuters.com/reuters/worldNews"
        ),

    ],


    # --------------------------------------------------------
    # INDIA
    #
    # Indian news is the priority.
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

        (
            "Firstpost India",
            "https://www.firstpost.com/commonfeeds/v1/mfp/rss/india.xml"
        ),

    ],


    # --------------------------------------------------------
    # BUSINESS
    #
    # India-first business coverage.
    #
    # Includes:
    # MSME
    # State MSME
    # DIC
    # Skill development
    # FSSAI
    # Promotion / Export Councils
    # BIS
    # Indian economy
    # Startups
    # International business
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
            "Economic Times Industry",
            "https://economictimes.indiatimes.com/rssfeeds/13357270.cms"
        ),

        (
            "Economic Times Small Biz",
            "https://economictimes.indiatimes.com/small-biz/rssfeeds/5584166.cms"
        ),

        (
            "Mint Business",
            "https://www.livemint.com/rss/companies"
        ),

        (
            "PIB Press Releases",
            "https://pib.gov.in/RssMain.aspx"
        ),

    ],


    # --------------------------------------------------------
    # TECHNOLOGY & AI
    #
    # India-first where feeds permit, followed by important
    # international technology and AI developments.
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

        (
            "Google AI Blog",
            "https://blog.google/technology/ai/rss/"
        ),

    ],


    # --------------------------------------------------------
    # SPORTS
    #
    # Indian sports prioritized through India-focused feeds
    # where available, followed by international sports.
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
            "Sportsstar",
            "https://sportstar.thehindu.com/rss"
        ),

        (
            "Indian Express Sports",
            "https://indianexpress.com/section/sports/feed/"
        ),

    ],


    # --------------------------------------------------------
    # ENTERTAINMENT
    #
    # Expanded coverage:
    #
    # Bollywood
    # Tollywood
    # Kollywood
    # Mollywood
    # Sandalwood
    # Bengali cinema
    # Marathi cinema
    # Punjabi cinema
    # Indian television
    # International cinema
    # Hollywood
    # Streaming
    # YouTube
    # Creators
    # Influencers
    # Local stage shows
    # Theatre
    # Events
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
            "Deadline",
            "https://deadline.com/feed/"
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
            "Film Companion",
            "https://www.filmcompanion.in/feed"
        ),

        (
            "Koimoi",
            "https://www.koimoi.com/feed/"
        ),

    ],


    # --------------------------------------------------------
    # LIFESTYLE
    #
    # India-first where possible.
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

        (
            "Indian Express Lifestyle",
            "https://indianexpress.com/section/lifestyle/feed/"
        ),

        (
            "NDTV Lifestyle",
            "https://feeds.feedburner.com/ndtvlifestyle-latest"
        ),

    ],
}


# ============================================================
# KEYWORD PRIORITY
# ============================================================

CATEGORY_KEYWORDS = {

    "India": [
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
        "kerala",
        "tamil nadu",
        "andhra pradesh",
        "telangana",
        "karnataka",
        "maharashtra",
        "gujarat",
        "rajasthan",
        "punjab",
        "uttar pradesh",
        "madhya pradesh",
        "west bengal",
        "odisha",
        "bihar",
        "assam",
        "india government",
        "centre",
        "central government",
    ],


    "Business": [
        "india",
        "indian",
        "msme",
        "micro small medium enterprise",
        "small business",
        "startup",
        "startups",
        "dic",
        "district industries centre",
        "district industries center",
        "skill development",
        "skills",
        "fssai",
        "food safety",
        "bureau of indian standards",
        "bis",
        "export promotion council",
        "promotion council",
        "export council",
        "dgft",
        "make in india",
        "mudra",
        "sidbi",
        "nsic",
        "udyam",
        "manufacturing",
        "gst",
        "upi",
        "rbi",
        "sebi",
        "india economy",
        "indian economy",
    ],


    "Technology & AI": [
        "india",
        "indian",
        "artificial intelligence",
        "ai",
        "machine learning",
        "generative ai",
        "technology",
        "tech",
        "startup",
        "robot",
        "robotics",
        "semiconductor",
        "chip",
        "software",
        "cybersecurity",
        "space",
        "isro",
        "digital india",
    ],


    "Sports": [
        "india",
        "indian",
        "team india",
        "cricket",
        "ipl",
        "bcci",
        "icc",
        "football",
        "hockey",
        "badminton",
        "kabaddi",
        "tennis",
        "olympics",
        "paralympics",
    ],


    "Entertainment": [
        "india",
        "indian",
        "bollywood",
        "tollywood",
        "kollywood",
        "mollywood",
        "sandalwood",
        "bengali cinema",
        "marathi cinema",
        "punjabi cinema",
        "tamil cinema",
        "telugu cinema",
        "malayalam cinema",
        "hindi cinema",
        "actor",
        "actress",
        "film",
        "movie",
        "cinema",
        "youtube",
        "youtuber",
        "creator",
        "influencer",
        "streaming",
        "ott",
        "netflix",
        "prime video",
        "stage show",
        "theatre",
        "theater",
        "play",
        "concert",
        "stand-up",
    ],


    "Lifestyle": [
        "india",
        "indian",
        "tamil",
        "kerala",
        "mumbai",
        "delhi",
        "chennai",
        "health",
        "fitness",
        "food",
        "travel",
        "fashion",
        "culture",
        "wellness",
        "lifestyle",
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


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================

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


# ============================================================
# URL NORMALIZATION
# ============================================================

def normalize_url(url):

    if not url:
        return ""

    url = url.strip()

    try:

        parsed = urlparse(
            url
        )

        if parsed.scheme not in (
            "http",
            "https"
        ):

            return ""

        return url

    except Exception:

        return ""


# ============================================================
# TITLE NORMALIZATION
# ============================================================

def normalize_title(title):

    title = clean_text(
        title
    )

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
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:20]


# ============================================================
# PUBLISHER REMOVAL
# ============================================================

def remove_publisher_from_title(
    title,
    publisher
):

    title = clean_text(
        title
    )

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
        "Deadline",
        "Film Companion",
        "Koimoi",

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

    summary = clean_text(
        summary
    )

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

    # Remove obvious source endings.

    description = re.sub(
        r"\s*(?:\||-|\u2013|\u2014)\s*"
        r"[A-Za-z0-9 .&]+$",
        "",
        description
    ).strip()

    description = re.sub(
        r"\s+",
        " ",
        description
    ).strip()

    # Compact but useful summary.

    if len(description) > 420:

        description = (
            description[:417]
            .rsplit(
                " ",
                1
            )[0]
            + "..."
        )

    if description:

        return description

    # Never fabricate facts.

    return (
        "The latest developments are being "
        "reported by the original publisher. "
        "Read the original report for the "
        "full details."
    )


# ============================================================
# DATE PARSER
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
# XML LINK
# ============================================================

def find_link(
    element
):

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
# LOCAL AI-STYLE IMAGE
# ============================================================

def make_ai_image(
    title,
    category
):

    # Pollinations does not require a user API key
    # for this public image URL approach.
    #
    # The URL is generated deterministically so that
    # the same story gets the same image URL.

    prompt = (
        "Professional editorial news illustration "
        "for a modern digital news publication. "
        f"Category: {category}. "
        f"Story: {title}. "
        "Realistic journalistic visual, "
        "tasteful editorial composition, "
        "high quality, cinematic lighting. "
        "No text, no letters, no words, "
        "no logos, no watermark."
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
# INDIA PRIORITY SCORE
# ============================================================

def india_priority_score(
    article
):

    text = " ".join([
        clean_text(
            article.get(
                "headline",
                ""
            )
        ),
        clean_text(
            article.get(
                "summary",
                ""
            )
        )
    ]).lower()

    score = 0

    for keyword in CATEGORY_KEYWORDS.get(
        article.get(
            "category",
            ""
        ),
        []
    ):

        if keyword.lower() in text:

            # India-related keywords receive a stronger
            # boost than generic category keywords.

            if keyword.lower() in {
                "india",
                "indian",
                "team india",
                "india government",
                "indian economy",
                "indian economy",
            }:

                score += 10

            else:

                score += 2

    return score


# ============================================================
# SOURCE PRIORITY
# ============================================================

def source_priority(
    article
):

    publisher = clean_text(
        article.get(
            "publisher",
            ""
        )
    ).lower()

    category = article.get(
        "category",
        ""
    )

    score = 0

    indian_publishers = {

        "the hindu",
        "indian express",
        "ndtv india",
        "hindustan times india",
        "times of india",
        "firstpost india",
        "moneycontrol business",
        "business standard",
        "economic times",
        "economic times industry",
        "economic times small biz",
        "mint business",
        "indian express sports",
        "sportsstar",
        "indian express entertainment",
        "hindustan times entertainment",
        "ndtv entertainment",
        "film companion",
        "koimoi",
        "indian express lifestyle",
        "ndtv lifestyle",
    }

    if publisher in indian_publishers:

        score += 20

    # World intentionally remains international-first.

    if category == "World":

        score = 0

    return score


# ============================================================
# FINAL ARTICLE SCORE
# ============================================================

def article_priority_score(
    article
):

    score = 0

    category = article.get(
        "category",
        ""
    )

    # India priority for every category except World.

    if category != "World":

        score += (
            india_priority_score(
                article
            )
        )

        score += (
            source_priority(
                article
            )
        )

    return score


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
                "ai_generated",

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
# LOAD EXISTING ARTICLES
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

            image = article.get(
                "image_url"
            )

            if not image:

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

    unique_url = {}

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

        if key not in unique_url:

            unique_url[
                key
            ] = article

        else:

            old_date = unique_url[
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

                unique_url[
                    key
                ] = article

    # --------------------------------------------------------
    # SECOND LEVEL: TITLE
    # --------------------------------------------------------

    unique_title = {}

    for article in unique_url.values():

        title_key = normalize_title(
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

            old = unique_title[
                title_key
            ]

            old_score = article_priority_score(
                old
            )

            new_score = article_priority_score(
                article
            )

            if new_score > old_score:

                unique_title[
                    title_key
                ] = article

            elif new_score == old_score:

                old_date = old.get(
                    "published_at",
                    ""
                )

                new_date = article.get(
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
# ARTICLE TIMESTAMP
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
# SORT ARTICLES
# ============================================================

def sort_articles(
    articles
):

    def sort_key(article):

        return (
            article_priority_score(
                article
            ),
            article_timestamp(
                article
            ).timestamp()
        )

    return sorted(
        articles,
        key=sort_key,
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
        "=" * 70
    )

    print(
        "SNIPPET24 NEWS CURATOR"
    )

    print(
        "UNLIMITED NEWS VERSION"
    )

    print(
        "=" * 70
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
    # FETCH ALL SOURCES
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
    # COMBINE
    # --------------------------------------------------------

    combined = (
        fresh_articles
        + previous_articles
    )

    print()

    print(
        f"Combined before deduplication: "
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
    # SORT
    # --------------------------------------------------------
    #
    # Important:
    #
    # We do NOT slice the list.
    #
    # Therefore there is NO 50/100/any maximum.
    #
    # Priority affects ordering only.
    #
    # Newer stories and Indian-priority stories appear
    # earlier in categories where India is preferred.
    #
    # --------------------------------------------------------

    final_articles = sort_articles(
        combined
    )

    print(
        f"Final usable stories: "
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
            None,

        "categories":
            counts,

        "articles":
            final_articles,

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
            "The existing articles.json "
            "was not intentionally deleted."
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
            "No artificial stories were created."
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