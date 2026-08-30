import os
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

REQUEST_TIMEOUT = 12
REQUEST_DELAY = 0.25

MINIMUM_STORIES = 50

HEADERS = {
    "User-Agent": (
        "Snippet24-News/4.0 "
        "(+https://snippet24.in)"
    )
}


# ============================================================
# OPTIONAL AI
# ============================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)


# ============================================================
# CATEGORIES
# ============================================================

CATEGORY_ORDER = [
    "Global",
    "India",
    "Security & Peace",
    "Law Around Us",
    "Science & Development",
    "Business & Economy",
    "Society & Culture",
    "Human & Environment",
    "Technology & AI",
    "Sports",
    "Entertainment",
    "Lifestyle",
]


# ============================================================
# OFFICIAL / GOVERNMENT SOURCES
# ============================================================

GOVERNMENT_SOURCES = [

    (
        "PIB",
        "https://pib.gov.in/RssMain.aspx",
        "India"
    ),

    (
        "PM India",
        "https://www.pmindia.gov.in/en/feed/",
        "India"
    ),

    (
        "RBI",
        "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "India"
    ),

]


# ============================================================
# PUBLIC / FREE NEWS SOURCES
# ============================================================

PUBLIC_NEWS_SOURCES = {

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

    "Business & Economy": [

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
            "Mint",
            "https://www.livemint.com/rss/companies"
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

        (
            "MIT Technology Review",
            "https://www.technologyreview.com/feed/"
        ),

        (
            "Google AI",
            "https://blog.google/technology/ai/rss/"
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

        (
            "Indian Express Sports",
            "https://indianexpress.com/section/sports/feed/"
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

        (
            "Indian Express Entertainment",
            "https://indianexpress.com/section/entertainment/feed/"
        ),

        (
            "Hindustan Times Entertainment",
            "https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml"
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

        (
            "Indian Express Lifestyle",
            "https://indianexpress.com/section/lifestyle/feed/"
        ),

    ],

}


# ============================================================
# PUBLIC TV / BROADCAST SOURCES
# ============================================================

TV_SOURCES = {

    "Global": [

        (
            "BBC News",
            "https://feeds.bbci.co.uk/news/rss.xml"
        ),

    ],

    "India": [

        (
            "NDTV",
            "https://feeds.feedburner.com/ndtvnews-top-stories"
        ),

    ],

}


# ============================================================
# YOUTUBE PUBLIC CHANNEL FEEDS
# ============================================================

YOUTUBE_CHANNELS = [

    # Add only official/public YouTube channel RSS URLs here.
    #
    # Example:
    #
    # (
    #     "Official Government YouTube",
    #     "https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID",
    #     "India"
    # ),
    #
]


# ============================================================
# CATEGORY KEYWORDS
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
        "central government",
    ],

    "Business & Economy": [
        "business",
        "economy",
        "finance",
        "market",
        "markets",
        "company",
        "companies",
        "startup",
        "msme",
        "gst",
        "rbi",
        "sebi",
        "fssai",
        "bis",
        "dgft",
        "exports",
        "imports",
        "employment",
        "jobs",
    ],

    "Technology & AI": [
        "technology",
        "technology & ai",
        "artificial intelligence",
        "ai",
        "machine learning",
        "generative ai",
        "software",
        "cybersecurity",
        "semiconductor",
        "chip",
        "robotics",
        "isro",
        "space",
        "digital",
    ],

    "Sports": [
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
        "sports",
    ],

    "Entertainment": [
        "bollywood",
        "tollywood",
        "kollywood",
        "mollywood",
        "sandalwood",
        "film",
        "movie",
        "cinema",
        "actor",
        "actress",
        "ott",
        "streaming",
        "netflix",
        "television",
        "youtube",
        "creator",
    ],

    "Lifestyle": [
        "food",
        "travel",
        "fashion",
        "wellness",
        "fitness",
        "lifestyle",
        "culture",
    ],

    "Security & Peace": [
        "security",
        "defence",
        "defense",
        "military",
        "army",
        "navy",
        "air force",
        "conflict",
        "war",
        "peace",
        "terror",
        "border",
        "cyber attack",
    ],

    "Law Around Us": [
        "court",
        "courts",
        "supreme court",
        "high court",
        "law",
        "legal",
        "lawsuit",
        "judgment",
        "judgement",
        "arrest",
        "bail",
        "fir",
        "constitution",
        "copyright",
        "trademark",
        "privacy",
        "data protection",
        "ai law",
        "media law",
    ],

    "Science & Development": [
        "science",
        "research",
        "development",
        "researchers",
        "climate science",
        "space mission",
        "infrastructure",
        "innovation",
    ],

}


# ============================================================
# INTERNATIONAL / GLOBAL DETECTION
# ============================================================

INDIA_TERMS = set(
    CATEGORY_KEYWORDS["India"]
)

INTERNATIONAL_TERMS = [

    "united states",
    "usa",
    "america",
    "uk",
    "united kingdom",
    "europe",
    "european union",
    "china",
    "japan",
    "russia",
    "ukraine",
    "israel",
    "gaza",
    "palestine",
    "iran",
    "iraq",
    "africa",
    "australia",
    "canada",
    "france",
    "germany",
    "italy",
    "spain",
    "brazil",
    "mexico",
    "south korea",
    "north korea",
    "united nations",
    "nato",
]


# ============================================================
# BASIC HELPERS
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


def normalize_url(value):

    if not value:
        return ""

    try:

        parsed =
            urlparse(
                str(value).strip()
            )

        if parsed.scheme not in (
            "http",
            "https"
        ):
            return ""

        return str(value).strip()

    except Exception:

        return ""


def normalize_title(value):

    value = clean_text(value)

    value = value.lower()

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

    value = clean_text(
        value
    )

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

        tag = (
            child.tag
            .split("}")[-1]
            .lower()
        )

        if tag in names:

            return clean_text(
                "".join(
                    child.itertext()
                )
            )

    return ""


def find_link(element):

    for child in list(element):

        tag = (
            child.tag
            .split("}")[-1]
            .lower()
        )

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

    for child in element.iter():

        tag = (
            child.tag
            .split("}")[-1]
            .lower()
        )

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

        tag = (
            child.tag
            .split("}")[-1]
            .lower()
        )

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
        r'https?://[^"\'>\s]+'
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
# CATEGORY DETECTION
# ============================================================

def contains_india(text):

    text = clean_text(
        text
    ).lower()

    return any(
        term.lower() in text
        for term in INDIA_TERMS
    )


def contains_international(text):

    text = clean_text(
        text
    ).lower()

    return any(
        term in text
        for term in INTERNATIONAL_TERMS
    )


def classify_category(
    requested_category,
    title,
    description
):

    text = (
        f"{title} "
        f"{description}"
    ).lower()

    # Global is STRICTLY international.
    if requested_category == "Global":

        if contains_india(text):

            return None

        if contains_international(
            text
        ):

            return "Global"

        # Global source itself can qualify.
        return "Global"

    # Government / India sources.
    if requested_category == "India":

        return "India"

    # Other categories.
    best_category = requested_category
    best_score = 0

    for category, keywords in (
        CATEGORY_KEYWORDS.items()
    ):

        score = sum(
            1
            for keyword in keywords
            if keyword.lower() in text
        )

        if score > best_score:

            best_score = score
            best_category = category

    return best_category


# ============================================================
# SOURCE VALIDATION
# ============================================================

def source_allowed(
    publisher,
    url
):

    publisher_text = (
        clean_text(
            publisher
        ).lower()
    )

    url_text = (
        clean_text(
            url
        ).lower()
    )

    blocked_private_terms = [

        "private channel",
        "private group",
        "private telegram",
        "private whatsapp",
        "whatsapp group",
        "telegram group",
        "closed channel",
        "members only",

    ]

    for term in blocked_private_terms:

        if (
            term in publisher_text
            or term in url_text
        ):

            return False

    return True


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

    ]

    for name in publishers:

        if not name:
            continue

        pattern = (
            r"\s*(?:\||-|–|—)\s*"
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
        " -|–—"
    )


# ============================================================
# SIMPLE SUMMARY
# ============================================================

def make_basic_summary(
    title,
    description
):

    title = clean_text(
        title
    )

    description = clean_text(
        description
    )

    if not description:

        return (
            "The original publisher has "
            "reported the latest development. "
            "Read the original report for "
            "complete details."
        )

    description = re.sub(
        re.escape(title),
        "",
        description,
        flags=re.IGNORECASE
    )

    description = re.sub(
        r"\s+",
        " ",
        description
    ).strip()

    if len(description) > 500:

        description = (
            description[:497]
            .rsplit(" ",1)[0]
            + "..."
        )

    return description


# ============================================================
# AI REQUEST
# ============================================================

def gemini_generate(prompt):

    if not GEMINI_API_KEY:

        return None

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload = {

        "contents":[
            {
                "parts":[
                    {
                        "text":prompt
                    }
                ]
            }
        ],

        "generationConfig":{
            "temperature":0.2,
            "maxOutputTokens":1200
        }

    }

    try:

        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        candidates =
            data.get(
                "candidates",
                []
            )

        if not candidates:
            return None

        parts =
            candidates[0]\
                .get("content", {})\
                .get("parts", [])

        text = "".join(
            part.get("text","")
            for part in parts
        )

        return clean_text(
            text
        )

    except Exception as exc:

        print(
            "AI request failed:",
            exc
        )

        return None


# ============================================================
# AI THREE-LINE REWRITE
# ============================================================

def ai_rewrite(
    title,
    description,
    category
):

    fallback_summary =
        make_basic_summary(
            title,
            description
        )

    fallback_snippet = (
        f"{title}\n"
        f"{fallback_summary[:180]}\n"
        f"Read the original source for complete details."
    )

    if not GEMINI_API_KEY:

        return (
            fallback_summary,
            fallback_snippet
        )

    prompt = f"""
You are the editorial AI for Snippet24.

Rewrite the following news information.

CATEGORY:
{category}

HEADLINE:
{title}

SOURCE DESCRIPTION:
{description}

Rules:

1. Do NOT copy sentences verbatim.
2. Do NOT invent facts.
3. Do NOT add facts not present in the source.
4. Keep the wording neutral and factual.
5. Create exactly THREE short snippet lines.
6. Each line should be concise.
7. Then create ONE short summary of 2-3 sentences.
8. If allegations are mentioned, attribute them.
9. Do not provide legal advice.
10. Do not reproduce copyrighted source text.

Return exactly:

LINE1: ...
LINE2: ...
LINE3: ...
SUMMARY: ...
"""

    result =
        gemini_generate(
            prompt
        )

    if not result:

        return (
            fallback_summary,
            fallback_snippet
        )

    lines = []

    summary = ""

    for raw_line in result.splitlines():

        line =
            raw_line.strip()

        if line.startswith(
            "LINE1:"
        ):

            lines.append(
                line[6:].strip()
            )

        elif line.startswith(
            "LINE2:"
        ):

            lines.append(
                line[6:].strip()
            )

        elif line.startswith(
            "LINE3:"
        ):

            lines.append(
                line[6:].strip()
            )

        elif line.startswith(
            "SUMMARY:"
        ):

            summary =
                line[8:].strip()

    if len(lines) != 3:

        lines = [
            title,
            fallback_summary[:180],
            "Read the original source for complete details."
        ]

    if not summary:

        summary =
            fallback_summary

    return (
        summary,
        "\n".join(lines[:3])
    )


# ============================================================
# AI TRANSLATION
# ============================================================

LANGUAGES = {

    "ta":"Tamil",
    "te":"Telugu",
    "kn":"Kannada",
    "ml":"Malayalam",
    "hi":"Hindi",

}


def ai_translate(
    headline,
    summary,
    snippet,
    language
):

    language_name =
        LANGUAGES[
            language
        ]

    if not GEMINI_API_KEY:

        return (
            headline,
            summary,
            snippet
        )

    prompt = f"""
Translate the following Snippet24 news
content into {language_name}.

Preserve meaning.
Do not add facts.
Do not remove facts.
Do not translate the publisher name.
Do not create a new headline that changes the meaning.

HEADLINE:
{headline}

SUMMARY:
{summary}

THREE-LINE SNIPPET:
{snippet}

Return exactly:

HEADLINE: ...
SUMMARY: ...
LINE1: ...
LINE2: ...
LINE3: ...
"""

    result =
        gemini_generate(
            prompt
        )

    if not result:

        return (
            headline,
            summary,
            snippet
        )

    translated_headline =
        headline

    translated_summary =
        summary

    translated_lines = []

    for raw_line in result.splitlines():

        line =
            raw_line.strip()

        if line.startswith(
            "HEADLINE:"
        ):

            translated_headline =
                line[9:].strip()

        elif line.startswith(
            "SUMMARY:"
        ):

            translated_summary =
                line[8:].strip()

        elif line.startswith(
            "LINE1:"
        ):

            translated_lines.append(
                line[6:].strip()
            )

        elif line.startswith(
            "LINE2:"
        ):

            translated_lines.append(
                line[6:].strip()
            )

        elif line.startswith(
            "LINE3:"
        ):

            translated_lines.append(
                line[6:].strip()
            )

    if len(
        translated_lines
    ) != 3:

        translated_lines = [
            snippet
        ]

    return (
        translated_headline,
        translated_summary,
        "\n".join(
            translated_lines[:3]
        )
    )


# ============================================================
# AI IMAGE
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
        "Realistic journalistic visual. "
        "Tasteful editorial composition. "
        "No text. No letters. No words. "
        "No logos. No watermark."
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
# PARSE RSS
# ============================================================

def parse_feed(
    xml_text,
    publisher,
    requested_category
):

    results = []

    try:

        root =
            ET.fromstring(
                xml_text
            )

    except Exception as exc:

        print(
            f"XML error from {publisher}:",
            exc
        )

        return results

    elements = []

    for element in root.iter():

        tag =
            element.tag\
                .split("}")[-1]\
                .lower()

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

        if not source_allowed(
            publisher,
            link
        ):
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

        category =
            classify_category(
                requested_category,
                title,
                description
            )

        if not category:
            continue

        summary, snippet =
            ai_rewrite(
                title,
                description,
                category
            )

        image =
            find_image_from_feed(
                item
            )

        if not image:

            image =
                make_ai_image(
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
                title,

            "summary":
                summary,

            "snippet":
                snippet,

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
                "source_or_ai_generated",

            "source_type":
                "public",

            "source_policy":
                "public-government-tv-youtube",

            "copyright_note":
                "Original source credited; "
                "Snippet24 provides a short "
                "AI-rephrased summary.",

        }

        # ====================================================
        # TRANSLATIONS
        # ====================================================

        for language in LANGUAGES:

            (
                translated_headline,
                translated_summary,
                translated_snippet
            ) = ai_translate(
                title,
                summary,
                snippet,
                language
            )

            article[
                f"headline_{language}"
            ] = translated_headline

            article[
                f"summary_{language}"
            ] = translated_summary

            article[
                f"snippet_{language}"
            ] = translated_snippet

        results.append(
            article
        )

        # Avoid hammering AI APIs.
        if GEMINI_API_KEY:

            time.sleep(
                0.15
            )

    return results


# ============================================================
# FETCH
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

        found =
            parse_feed(
                response.text,
                publisher,
                category
            )

        print(
            f"  -> {len(found)} stories"
        )

        return found

    except Exception as exc:

        print(
            f"  -> FAILED: "
            f"{publisher}: {exc}"
        )

        return []


# ============================================================
# EXISTING ARTICLES
# ============================================================

def load_existing_articles():

    if not os.path.exists(
        OUTPUT_FILE
    ):

        return []

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

        return [
            article
            for article in articles
            if isinstance(
                article,
                dict
            )
        ]

    except Exception as exc:

        print(
            "Could not load existing articles:",
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

        url =
            normalize_url(
                article.get(
                    "source_url",
                    ""
                )
            )

        title =
            clean_text(
                article.get(
                    "headline",
                    ""
                )
            )

        if not url or not title:
            continue

        key =
            url.lower()

        if key not in unique_url:

            unique_url[key] =
                article

        else:

            old =
                unique_url[key]

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

                unique_url[key] =
                    article

    # Second-level title deduplication.

    unique_title = {}

    for article in (
        unique_url.values()
    ):

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
            ).timestamp(),
        reverse=True
    )


# ============================================================
# CATEGORY COUNTS
# ============================================================

def category_counts(
    articles
):

    counts = {
        category:0
        for category in CATEGORY_ORDER
    }

    for article in articles:

        category =
            article.get(
                "category"
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

    print("=" * 70)
    print("SNIPPET24 NEWS CURATOR")
    print("PUBLIC / GOVERNMENT / TV / YOUTUBE SOURCE VERSION")
    print("=" * 70)

    if GEMINI_API_KEY:

        print(
            "AI rewriting: ENABLED"
        )

        print(
            "AI translation: ENABLED"
        )

    else:

        print(
            "AI rewriting: FALLBACK MODE"
        )

        print(
            "AI translation: FALLBACK MODE"
        )

        print(
            "Set GEMINI_API_KEY to enable AI rewriting."
        )

    previous_articles =
        load_existing_articles()

    print(
        f"Previous stories: "
        f"{len(previous_articles)}"
    )

    fresh_articles = []

    successful_sources = 0
    failed_sources = 0

    # ========================================================
    # PUBLIC NEWS
    # ========================================================

    for category, sources in (
        PUBLIC_NEWS_SOURCES.items()
    ):

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

    # ========================================================
    # GOVERNMENT
    # ========================================================

    print()
    print(
        "### Government / Official"
    )

    for publisher, url, category in (
        GOVERNMENT_SOURCES
    ):

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

    # ========================================================
    # TV / BROADCAST
    # ========================================================

    print()
    print(
        "### TV / Broadcast"
    )

    for category, sources in (
        TV_SOURCES.items()
    ):

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

    # ========================================================
    # YOUTUBE
    # ========================================================

    print()
    print(
        "### YouTube Official/Public"
    )

    for publisher, url, category in (
        YOUTUBE_CHANNELS
    ):

        found =
            fetch_source(
                publisher,
                url,
                category
            )

        if found:

            successful_sources += 1

            for article in found:

                article[
                    "source_type"
                ] = "youtube"

            fresh_articles.extend(
                found
            )

        else:

            failed_sources += 1

        time.sleep(
            REQUEST_DELAY
        )

    # ========================================================
    # COMBINE
    # ========================================================

    combined =
        fresh_articles + previous_articles

    print(
        f"Combined: {len(combined)}"
    )

    combined =
        deduplicate(
            combined
        )

    print(
        f"After deduplication: "
        f"{len(combined)}"
    )

    # ========================================================
    # SORT
    # ========================================================

    final_articles =
        sort_articles(
            combined
        )

    # ========================================================
    # GLOBAL SAFETY FILTER
    # ========================================================

    cleaned_articles = []

    for article in final_articles:

        category =
            article.get(
                "category"
            )

        title =
            article.get(
                "headline",
                ""
            )

        summary =
            article.get(
                "summary",
                ""
            )

        text =
            f"{title} {summary}"

        # Global must not become India news.

        if category == "Global":

            if contains_india(
                text
            ):

                continue

        cleaned_articles.append(
            article
        )

    final_articles =
        cleaned_articles

    counts =
        category_counts(
            final_articles
        )

    output = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total":
            len(final_articles),

        "minimum_target":
            MINIMUM_STORIES,

        "source_policy":
            [
                "government",
                "public-free-news",
                "tv-broadcast",
                "official-youtube"
            ],

        "private_channels_allowed":
            False,

        "ai_rephrasing":
            bool(GEMINI_API_KEY),

        "translations":
            list(
                LANGUAGES.keys()
            ),

        "categories":
            counts,

        "legal_notice":
            "Snippet24 publishes short "
            "AI-rephrased summaries, "
            "credits original sources, "
            "and links to original reports.",

        "articles":
            final_articles,

    }

    # ========================================================
    # WRITE
    # ========================================================

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

    # ========================================================
    # REPORT
    # ========================================================

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
            f"{counts.get(category,0)}"
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
            "ERROR: No usable stories."
        )

        return 1

    if len(final_articles) < MINIMUM_STORIES:

        print()
        print(
            "WARNING: Fewer than "
            f"{MINIMUM_STORIES} "
            "usable stories."
        )

        print(
            "No artificial stories "
            "were created."
        )

    else:

        print()
        print(
            "SUCCESS: Minimum story "
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
