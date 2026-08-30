import os
import re
import json
import html
import time
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
import xml.etree.ElementTree as ET


# ============================================================
# SNIPPET24 CURATOR
# ============================================================
#
# SOURCE
#   Government
#   Public broadcasters
#   Official TV
#   Verified official YouTube
#
#        ↓
#
# AI EDITORIAL PROCESSING
#
#        ↓
#
# Headline
# 3-line snippet
# Short summary
#
#        ↓
#
# articles.json
#
# ============================================================


OUTPUT_FILE = "articles.json"

REQUEST_TIMEOUT = 20
AI_TIMEOUT = 45
REQUEST_DELAY = 0.5


# ============================================================
# AI CONFIGURATION
# ============================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    ""
).strip()

# Set this in GitHub Actions as OPENAI_MODEL.
# Do not hard-code a model name that your API account does not
# support.
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    ""
).strip()

OPENAI_URL = (
    "https://api.openai.com/v1/responses"
)


# ============================================================
# WEBSITE
# ============================================================

SITE_NAME = "Snippet24"

SITE_URL = (
    os.getenv(
        "SITE_URL",
        "https://snippet24.in"
    ).strip()
)


# ============================================================
# REQUEST HEADERS
# ============================================================

HEADERS = {

    "User-Agent":
        "Snippet24 News Curator/1.0",

    "Accept":
        "application/rss+xml, "
        "application/xml, "
        "text/xml, "
        "application/atom+xml, "
        "*/*;q=0.8",

}


# ============================================================
# CATEGORIES
# ============================================================

CATEGORY_ORDER = [

    "In India",

    "Security & Peace",

    "Law Around Us",

    "Science & Development",

    "Business & Economy",

    "Society & Culture",

    "Human & Environment",

    "Tech & AI",

    "Good Reads",

    "Global",

]


# ============================================================
# SOURCE TYPES
# ============================================================

SOURCE_GOVERNMENT = (
    "GOVERNMENT"
)

SOURCE_PUBLIC = (
    "PUBLIC_BROADCASTER"
)

SOURCE_OFFICIAL_TV = (
    "OFFICIAL_TV"
)

SOURCE_OFFICIAL_YOUTUBE = (
    "OFFICIAL_YOUTUBE"
)

SOURCE_STATE_GOVERNMENT = (
    "STATE_GOVERNMENT"
)

SOURCE_LOCAL_GOVERNMENT = (
    "LOCAL_GOVERNMENT"
)


# ============================================================
# SOURCE PRIORITY
# ============================================================

SOURCE_PRIORITY = {

    SOURCE_GOVERNMENT:
        100,

    SOURCE_STATE_GOVERNMENT:
        98,

    SOURCE_LOCAL_GOVERNMENT:
        95,

    SOURCE_PUBLIC:
        90,

    SOURCE_OFFICIAL_TV:
        85,

    SOURCE_OFFICIAL_YOUTUBE:
        80,

}


# ============================================================
# OFFICIAL RSS SOURCES
#
# IMPORTANT:
# Keep only feeds you have verified.
#
# You can add additional government feeds here.
# ============================================================

RSS_SOURCES = [

    {
        "publisher":
            "Press Information Bureau",

        "source_type":
            SOURCE_GOVERNMENT,

        "category":
            "In India",

        "url":
            "https://pib.gov.in/"
            "RssMain.aspx?ModId=6&Lang=1&Regid=22",
    },

]


# ============================================================
# OFFICIAL YOUTUBE SOURCES
#
# Add verified channel IDs only.
#
# Do NOT put ordinary user channels here.
#
# Example:
#
# {
#     "publisher": "ISRO",
#     "source_type": SOURCE_OFFICIAL_YOUTUBE,
#     "category": "Science & Development",
#     "channel_id": "VERIFIED_CHANNEL_ID"
# }
#
# ============================================================

YOUTUBE_CHANNELS = []


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "In India": [

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
        "government of india",
        "central government",
        "union government",

    ],

    "Security & Peace": [

        "security",
        "defence",
        "defense",
        "army",
        "navy",
        "air force",
        "police",
        "border",
        "terror",
        "terrorism",
        "cyber security",
        "cybersecurity",
        "peace",
        "military",
        "coast guard",

    ],

    "Law Around Us": [

        "law",
        "court",
        "supreme court",
        "high court",
        "judiciary",
        "legal",
        "justice",
        "judgment",
        "judgement",
        "bill",
        "act",
        "legislation",
        "constitution",
        "parliament",
        "petition",
        "tribunal",

    ],

    "Science & Development": [

        "science",
        "research",
        "space",
        "isro",
        "satellite",
        "rocket",
        "innovation",
        "laboratory",
        "scientist",
        "development",
        "researchers",

    ],

    "Business & Economy": [

        "business",
        "economy",
        "economic",
        "msme",
        "startup",
        "startups",
        "manufacturing",
        "industry",
        "gst",
        "tax",
        "rbi",
        "sebi",
        "bank",
        "banking",
        "trade",
        "export",
        "import",
        "investment",
        "employment",
        "jobs",
        "budget",
        "finance",

    ],

    "Society & Culture": [

        "society",
        "culture",
        "heritage",
        "education",
        "school",
        "university",
        "festival",
        "community",
        "women",
        "children",
        "social",
        "arts",
        "art",

    ],

    "Human & Environment": [

        "environment",
        "climate",
        "pollution",
        "forest",
        "wildlife",
        "water",
        "river",
        "agriculture",
        "farmer",
        "farmers",
        "health",
        "public health",
        "disaster",
        "flood",
        "cyclone",
        "drought",

    ],

    "Tech & AI": [

        "artificial intelligence",
        "ai",
        "machine learning",
        "generative ai",
        "technology",
        "tech",
        "software",
        "semiconductor",
        "chip",
        "robotics",
        "robot",
        "cyber",
        "digital",
        "internet",
        "data",

    ],

    "Good Reads": [

        "explainer",
        "analysis",
        "background",
        "history",
        "feature",
        "special report",
        "explained",

    ],

    "Global": [

        "world",
        "international",
        "united states",
        "usa",
        "china",
        "russia",
        "uk",
        "europe",
        "middle east",
        "united nations",
        "global",

    ],

}


# ============================================================
# LEGAL / EDITORIAL TEXT
# ============================================================

AI_DISCLOSURE = (
    "This article has been condensed and "
    "rephrased using an AI-assisted editorial "
    "process based on the identified source. "
    "Readers should consult the original source "
    "for the complete report."
)


COPYRIGHT_NOTICE = (
    "Third-party content, trademarks, photographs, "
    "videos, audio and other copyrighted material "
    "remain the property of their respective owners. "
    "Snippet24 does not claim ownership of third-party "
    "material."
)


EDITORIAL_NOTICE = (
    "Snippet24 aims to provide concise, factual and "
    "responsible news summaries. Claims, allegations "
    "and unverified information should not be presented "
    "as established facts."
)


LEGAL_NOTICE = (
    "Information published by Snippet24 is provided "
    "for general news and informational purposes and "
    "does not constitute legal, financial, medical, "
    "tax, investment or other professional advice."
)


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

    url = str(
        url
    ).strip()

    try:

        parsed = urlparse(
            url
        )

        if parsed.scheme not in (
            "http",
            "https",
        ):

            return ""

        return url

    except Exception:

        return ""


# ============================================================
# NORMALIZE TITLE
# ============================================================

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


# ============================================================
# ARTICLE ID
# ============================================================

def make_id(
    title,
    url
):

    raw = (
        normalize_title(
            title
        )
        + "|"
        + url
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
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

    wanted = {
        name.lower()
        for name in names
    }

    for child in list(
        element
    ):

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag in wanted:

            return clean_text(
                "".join(
                    child.itertext()
                )
            )

    return ""


def find_link(
    element
):

    for child in list(
        element
    ):

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag != "link":

            continue

        href = child.attrib.get(
            "href",
            ""
        )

        if href:

            return normalize_url(
                href
            )

        value = clean_text(
            "".join(
                child.itertext()
            )
        )

        if value:

            return normalize_url(
                value
            )

    return ""


def find_image(
    element
):

    # We intentionally DO NOT automatically
    # copy or download the source image.
    #
    # We only preserve a source image URL
    # as metadata for later editorial/licensing
    # review.

    for child in element.iter():

        tag = child.tag.split(
            "}"
        )[-1].lower()

        if tag in (
            "content",
            "thumbnail",
        ):

            url = child.attrib.get(
                "url",
                ""
            )

            if url:

                return normalize_url(
                    url
                )

    return ""


# ============================================================
# CATEGORY
# ============================================================

def detect_category(
    title,
    description,
    preferred
):

    text = (
        clean_text(title)
        + " "
        + clean_text(description)
    ).lower()


    if preferred in CATEGORY_ORDER:

        keywords = CATEGORY_KEYWORDS.get(
            preferred,
            []
        )

        for keyword in keywords:

            if keyword.lower() in text:

                return preferred


    best_category = (
        preferred
        if preferred in CATEGORY_ORDER
        else "In India"
    )

    best_score = 0


    for category in CATEGORY_ORDER:

        score = 0

        for keyword in CATEGORY_KEYWORDS.get(
            category,
            []
        ):

            if keyword.lower() in text:

                score += 1


        if score > best_score:

            best_score = score

            best_category = category


    return best_category


# ============================================================
# AI RESPONSE TEXT
# ============================================================

def extract_response_text(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return ""


    if data.get(
        "output_text"
    ):

        return str(
            data[
                "output_text"
            ]
        )


    output = data.get(
        "output",
        []
    )


    if not isinstance(
        output,
        list
    ):

        return ""


    chunks = []


    for item in output:

        if not isinstance(
            item,
            dict
        ):

            continue


        content = item.get(
            "content",
            []
        )


        if not isinstance(
            content,
            list
        ):

            continue


        for part in content:

            if not isinstance(
                part,
                dict
            ):

                continue


            text = part.get(
                "text"
            )


            if text:

                chunks.append(
                    str(text)
                )


    return "\n".join(
        chunks
    ).strip()


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(
    text
):

    text = text.strip()


    try:

        return json.loads(
            text
        )

    except Exception:

        pass


    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )


    if not match:

        return None


    try:

        return json.loads(
            match.group(0)
        )

    except Exception:

        return None


# ============================================================
# AI EDITOR
# ============================================================

def ai_rewrite_article(
    title,
    description,
    publisher,
    source_type,
    category
):

    # --------------------------------------------------------
    # If AI isn't configured, use safe fallback.
    # --------------------------------------------------------

    if not OPENAI_API_KEY:

        return fallback_editorial(
            title,
            description,
            category
        )


    if not OPENAI_MODEL:

        print(
            "  WARNING: OPENAI_MODEL not configured."
        )

        return fallback_editorial(
            title,
            description,
            category
        )


    source_text = clean_text(
        description
    )


    if len(source_text) > 6000:

        source_text = (
            source_text[:6000]
            + "..."
        )


    system_prompt = """
You are the editorial AI for Snippet24,
an Indian public-interest news platform.

Your job is to transform supplied source
material into concise, neutral and factual
news presentation.

SOURCE MATERIAL IS THE ONLY FACTUAL BASIS.

DO NOT INVENT:
- names
- numbers
- dates
- locations
- quotations
- causes
- motives
- statistics
- allegations
- conclusions
- legal conclusions

DO NOT:
- exaggerate
- sensationalise
- create clickbait
- add political opinion
- add unsupported analysis
- copy long passages
- fabricate quotations

You may paraphrase and condense.

HEADLINE:
8 to 14 words.

SNIPPET:
EXACTLY 3 short lines.
Each line should contain useful factual information.

SUMMARY:
2 or 3 sentences.
Approximately 35 to 60 words.

CATEGORY:
Choose exactly one:

In India
Security & Peace
Law Around Us
Science & Development
Business & Economy
Society & Culture
Human & Environment
Tech & AI
Good Reads
Global

IMPORTANCE:
HIGH, MEDIUM or LOW.

If a claim is attributed to a person,
organisation or authority, preserve the
attribution rather than presenting it as
independently verified fact.

Return ONLY JSON.
"""


    user_prompt = f"""
SOURCE TYPE:
{source_type}

SOURCE PUBLISHER:
{publisher}

SUGGESTED CATEGORY:
{category}

ORIGINAL HEADLINE:
{clean_text(title)}

ORIGINAL DESCRIPTION:
{source_text}
"""


    payload = {

        "model":
            OPENAI_MODEL,

        "input": [

            {
                "role":
                    "system",

                "content":
                    system_prompt,
            },

            {
                "role":
                    "user",

                "content":
                    user_prompt,
            },

        ],

        "max_output_tokens":
            700,

    }


    headers = {

        "Authorization":
            f"Bearer {OPENAI_API_KEY}",

        "Content-Type":
            "application/json",

    }


    try:

        response = requests.post(

            OPENAI_URL,

            headers=headers,

            json=payload,

            timeout=AI_TIMEOUT,

        )


        response.raise_for_status()


        data = response.json()


        text = extract_response_text(
            data
        )


        result = extract_json(
            text
        )


        if not result:

            raise ValueError(
                "Invalid AI JSON"
            )


        headline = clean_text(
            result.get(
                "headline",
                title
            )
        )


        lines = result.get(
            "snippet_lines",
            []
        )


        if not isinstance(
            lines,
            list
        ):

            lines = []


        lines = [

            clean_text(
                line
            )

            for line in lines

            if clean_text(
                line
            )

        ]


        # Exactly three lines.
        while len(lines) < 3:

            lines.append(
                fallback_snippet_line(
                    title,
                    description,
                    len(lines)
                )
            )


        lines = lines[:3]


        summary = clean_text(
            result.get(
                "summary",
                ""
            )
        )


        result_category = clean_text(
            result.get(
                "category",
                category
            )
        )


        if result_category not in CATEGORY_ORDER:

            result_category = category


        importance = clean_text(
            result.get(
                "importance",
                "MEDIUM"
            )
        ).upper()


        if importance not in (
            "HIGH",
            "MEDIUM",
            "LOW",
        ):

            importance = "MEDIUM"


        return {

            "headline":
                headline,

            "snippet_lines":
                lines,

            "snippet":
                "\n".join(
                    lines
                ),

            "summary":
                summary,

            "category":
                result_category,

            "importance":
                importance,

            "ai_rewritten":
                True,

        }


    except Exception as exc:

        print(
            "  AI ERROR:",
            exc
        )

        return fallback_editorial(
            title,
            description,
            category
        )


# ============================================================
# FALLBACK
# ============================================================

def fallback_snippet_line(
    title,
    description,
    index
):

    sentences = re.split(
        r"(?<=[.!?])\s+",
        clean_text(
            description
        )
    )


    sentences = [

        clean_text(
            sentence
        )

        for sentence in sentences

        if clean_text(
            sentence
        )

    ]


    if index < len(
        sentences
    ):

        return sentences[
            index
        ][:180]


    if index == 0:

        return (
            "The latest development "
            "has been reported by "
            "the identified source."
        )


    if index == 1:

        return (
            "The source has provided "
            "information about the "
            "reported development."
        )


    return (
        "Readers can consult the "
        "original source for complete details."
    )


def fallback_editorial(
    title,
    description,
    category
):

    title = clean_text(
        title
    )

    description = clean_text(
        description
    )


    lines = [

        fallback_snippet_line(
            title,
            description,
            0
        ),

        fallback_snippet_line(
            title,
            description,
            1
        ),

        fallback_snippet_line(
            title,
            description,
            2
        ),

    ]


    summary = (
        description[:500]
        if description
        else
        "The original source has "
        "published the latest update. "
        "Readers can consult the "
        "original report for complete details."
    )


    return {

        "headline":
            title,

        "snippet_lines":
            lines,

        "snippet":
            "\n".join(
                lines
            ),

        "summary":
            summary,

        "category":
            category,

        "importance":
            "MEDIUM",

        "ai_rewritten":
            False,

    }


# ============================================================
# PARSE RSS
# ============================================================

def parse_feed(
    xml_text,
    source
):

    articles = []


    try:

        root = ET.fromstring(
            xml_text
        )

    except Exception as exc:

        print(
            "  XML ERROR:",
            exc
        )

        return articles


    items = []


    for element in root.iter():

        tag = element.tag.split(
            "}"
        )[-1].lower()


        if tag in (
            "item",
            "entry",
        ):

            items.append(
                element
            )


    for item in items:

        title = find_child_text(
            item,
            ["title"]
        )


        if not title:

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
                "created",
            ]
        )


        published_at = parse_date(
            published
        )


        image_url = find_image(
            item
        )


        publisher = clean_text(
            source[
                "publisher"
            ]
        )


        source_type = source[
            "source_type"
        ]


        preferred_category = source[
            "category"
        ]


        category = detect_category(

            title,

            description,

            preferred_category

        )


        print(
            "  AI editing:",
            title[:100]
        )


        editorial = ai_rewrite_article(

            title,

            description,

            publisher,

            source_type,

            category

        )


        final_category = editorial.get(
            "category",
            category
        )


        article = {

            "id":
                make_id(
                    editorial[
                        "headline"
                    ],
                    link
                ),

            "category":
                final_category,

            "headline":
                editorial[
                    "headline"
                ],

            "snippet":
                editorial[
                    "snippet"
                ],

            "snippet_lines":
                editorial[
                    "snippet_lines"
                ],

            "summary":
                editorial[
                    "summary"
                ],

            "publisher":
                publisher,

            "source_type":
                source_type,

            "source_label":
                source_label(
                    source_type
                ),

            "importance":
                editorial[
                    "importance"
                ],

            "published_at":
                published_at.isoformat(),

            "source_url":
                link,

            "original_source_url":
                link,

            # Do NOT automatically republish
            # third-party images.
            "image_url":
                image_url,

            "image_usage":
                "SOURCE_REFERENCE_ONLY",

            # AI transparency
            "ai_rewritten":
                editorial[
                    "ai_rewritten"
                ],

            "ai_disclosure":
                True,

            "ai_disclosure_text":
                AI_DISCLOSURE,

            # Copyright/source attribution
            "attribution_required":
                True,

            "copyright_status":
                "THIRD_PARTY_SOURCE",

            "copyright_notice":
                COPYRIGHT_NOTICE,

            # Editorial
            "editorial_notice":
                EDITORIAL_NOTICE,

            "legal_notice":
                LEGAL_NOTICE,

            # User correction system
            "correction_available":
                True,

            "grievance_available":
                True,

        }


        articles.append(
            article
        )


    return articles


# ============================================================
# SOURCE LABEL
# ============================================================

def source_label(
    source_type
):

    labels = {

        SOURCE_GOVERNMENT:
            "Government Source",

        SOURCE_PUBLIC:
            "Public Broadcaster",

        SOURCE_OFFICIAL_TV:
            "Official TV",

        SOURCE_OFFICIAL_YOUTUBE:
            "Official YouTube",

        SOURCE_STATE_GOVERNMENT:
            "State Government",

        SOURCE_LOCAL_GOVERNMENT:
            "Local Government",

    }


    return labels.get(
        source_type,
        "Verified Source"
    )


# ============================================================
# FETCH RSS
# ============================================================

def fetch_rss_source(
    source
):

    publisher = source[
        "publisher"
    ]

    url = source[
        "url"
    ]


    print()
    print(
        "Fetching:",
        publisher
    )


    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=REQUEST_TIMEOUT,

        )


        response.raise_for_status()


        articles = parse_feed(

            response.text,

            source

        )


        print(
            "  Stories:",
            len(articles)
        )


        return articles


    except Exception as exc:

        print(
            "  FAILED:",
            exc
        )

        return []


# ============================================================
# YOUTUBE FEED
# ============================================================

def youtube_feed_url(
    channel_id
):

    return (
        "https://www.youtube.com/"
        "feeds/videos.xml?channel_id="
        + channel_id
    )


def fetch_youtube_source(
    source
):

    channel_id = source[
        "channel_id"
    ]


    if not channel_id:

        return []


    config = {

        "publisher":
            source[
                "publisher"
            ],

        "source_type":
            source[
                "source_type"
            ],

        "category":
            source[
                "category"
            ],

        "url":
            youtube_feed_url(
                channel_id
            ),

    }


    return fetch_rss_source(
        config
    )


# ============================================================
# LOAD EXISTING
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


    except Exception:

        return []


# ============================================================
# PRIORITY
# ============================================================

def article_priority(
    article
):

    score = SOURCE_PRIORITY.get(

        article.get(
            "source_type",
            ""
        ),

        0

    )


    importance = article.get(
        "importance",
        "MEDIUM"
    )


    if importance == "HIGH":

        score += 30

    elif importance == "MEDIUM":

        score += 15


    if article.get(
        "category"
    ) == "In India":

        score += 10


    return score


# ============================================================
# TIMESTAMP
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
# DEDUPLICATE
# ============================================================

def deduplicate(
    articles
):

    by_url = {}


    for article in articles:

        url = normalize_url(
            article.get(
                "source_url",
                ""
            )
        )


        if not url:

            continue


        key = url.lower()


        existing = by_url.get(
            key
        )


        if not existing:

            by_url[
                key
            ] = article

            continue


        if article_priority(
            article
        ) > article_priority(
            existing
        ):

            by_url[
                key
            ] = article


    # --------------------------------------------------------
    # Similar headline deduplication
    # --------------------------------------------------------

    by_title = {}


    for article in by_url.values():

        title_key = normalize_title(

            article.get(
                "headline",
                ""
            )

        )


        if not title_key:

            continue


        existing = by_title.get(
            title_key
        )


        if not existing:

            by_title[
                title_key
            ] = article

            continue


        if article_priority(
            article
        ) > article_priority(
            existing
        ):

            by_title[
                title_key
            ] = article


    return list(
        by_title.values()
    )


# ============================================================
# SORT
# ============================================================

def sort_articles(
    articles
):

    return sorted(

        articles,

        key=lambda article: (

            article_priority(
                article
            ),

            article_timestamp(
                article
            ).timestamp()

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

        for category in CATEGORY_ORDER

    }


    for article in articles:

        category = article.get(
            "category",
            "In India"
        )


        if category not in counts:

            category = "In India"


        counts[
            category
        ] += 1


    return counts


# ============================================================
# SOURCE COUNTS
# ============================================================

def source_counts(
    articles
):

    counts = {}


    for article in articles:

        source_type = article.get(
            "source_type",
            "UNKNOWN"
        )


        counts[
            source_type
        ] = (
            counts.get(
                source_type,
                0
            )
            + 1
        )


    return counts


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print()
    print("=" * 72)

    print(
        "SNIPPET24 AI NEWS CURATOR"
    )

    print(
        "Government + Public + Official Sources"
    )

    print("=" * 72)


    if not OPENAI_API_KEY:

        print()
        print(
            "WARNING:"
        )

        print(
            "OPENAI_API_KEY is not configured."
        )

        print(
            "Fallback editorial mode is active."
        )


    if not OPENAI_MODEL:

        print()
        print(
            "WARNING:"
        )

        print(
            "OPENAI_MODEL is not configured."
        )

        print(
            "Set OPENAI_MODEL to a model "
            "available in your API account."
        )


    previous = (
        load_existing_articles()
    )


    print(
        "Existing articles:",
        len(previous)
    )


    fresh = []


    successful = 0
    failed = 0


    # ========================================================
    # RSS
    # ========================================================

    for source in RSS_SOURCES:

        articles = fetch_rss_source(
            source
        )


        if articles:

            fresh.extend(
                articles
            )

            successful += 1

        else:

            failed += 1


        time.sleep(
            REQUEST_DELAY
        )


    # ========================================================
    # YOUTUBE
    # ========================================================

    for source in YOUTUBE_CHANNELS:

        articles = fetch_youtube_source(
            source
        )


        if articles:

            fresh.extend(
                articles
            )

            successful += 1

        else:

            failed += 1


        time.sleep(
            REQUEST_DELAY
        )


    print()
    print(
        "Fresh articles:",
        len(fresh)
    )


    # ========================================================
    # COMBINE
    # ========================================================

    combined = (
        fresh
        + previous
    )


    # ========================================================
    # DEDUPLICATE
    # ========================================================

    combined = deduplicate(
        combined
    )


    # ========================================================
    # SORT
    # ========================================================

    final_articles = sort_articles(
        combined
    )


    # ========================================================
    # COUNTS
    # ========================================================

    categories = category_counts(
        final_articles
    )


    sources = source_counts(
        final_articles
    )


    # ========================================================
    # OUTPUT
    # ========================================================

    output = {

        "site":
            SITE_NAME,

        "site_url":
            SITE_URL,

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total":
            len(final_articles),

        "editorial_engine":
            "Snippet24 AI Editorial",

        "source_policy":
            (
                "Government, public-service, "
                "official TV and verified "
                "official YouTube sources."
            ),

        "ai_policy":
            (
                "AI-assisted rewriting is used "
                "for concise summaries. "
                "Original sources are retained."
            ),

        "copyright_policy":
            (
                "Third-party source material "
                "is attributed and linked. "
                "Full article reproduction is "
                "not performed by the curator."
            ),

        "legal_notice":
            LEGAL_NOTICE,

        "editorial_notice":
            EDITORIAL_NOTICE,

        "copyright_notice":
            COPYRIGHT_NOTICE,

        "ai_disclosure":
            AI_DISCLOSURE,

        "grievance":
            True,

        "corrections":
            True,

        "categories":
            categories,

        "source_types":
            sources,

        "successful_sources":
            successful,

        "failed_sources":
            failed,

        "articles":
            final_articles,

    }


    # ========================================================
    # SAFE WRITE
    # ========================================================

    temp_file = (
        OUTPUT_FILE
        + ".tmp"
    )


    with open(

        temp_file,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            output,

            file,

            ensure_ascii=False,

            indent=2,

        )


    os.replace(
        temp_file,
        OUTPUT_FILE
    )


    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 72)

    print(
        "SNIPPET24 UPDATE COMPLETE"
    )

    print("=" * 72)

    print(
        "Total:",
        len(final_articles)
    )

    print()

    print(
        "Categories:"
    )


    for category in CATEGORY_ORDER:

        print(
            f"  {category}: "
            f"{categories.get(category, 0)}"
        )


    print()

    print(
        "Source types:"
    )


    for source_type, count in (
        sources.items()
    ):

        print(
            f"  {source_type}: {count}"
        )


    print()

    print(
        "Successful sources:",
        successful
    )

    print(
        "Failed sources:",
        failed
    )

    print()

    print(
        "articles.json written."
    )


    return 0


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        build_feed()
    )
