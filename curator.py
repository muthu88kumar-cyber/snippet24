import os
import re
import json
import html
import time
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

import requests
import xml.etree.ElementTree as ET


# ============================================================
# SNIPPET24 NEWS CURATOR
# GOVERNMENT + PUBLIC + OFFICIAL YOUTUBE EDITION
#
# Flow:
#
# Official source
#       ↓
# RSS / YouTube
#       ↓
# Clean article
#       ↓
# AI editorial rewrite
#       ↓
# 3-line snippet + short summary
#       ↓
# articles.json
#
# ============================================================


OUTPUT_FILE = "articles.json"

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.25

# AI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# GPT-5.6 Luna is intended for cost-sensitive/high-volume workloads.
# Change this environment variable if you want another model.
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
)

OPENAI_URL = (
    "https://api.openai.com/v1/responses"
)


# ============================================================
# REQUEST HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Snippet24-News/4.0 "
        "(https://snippet24.in)"
    ),
    "Accept": (
        "application/rss+xml, "
        "application/xml, "
        "text/xml, "
        "text/html;q=0.9, "
        "*/*;q=0.8"
    ),
}


# ============================================================
# CATEGORY ORDER
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

SOURCE_GOVERNMENT = "GOVERNMENT"

SOURCE_PUBLIC_BROADCASTER = (
    "PUBLIC_BROADCASTER"
)

SOURCE_OFFICIAL_TV = "OFFICIAL_TV"

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
# Higher number = higher editorial priority
# ============================================================

SOURCE_PRIORITY = {

    SOURCE_GOVERNMENT: 100,

    SOURCE_STATE_GOVERNMENT: 95,

    SOURCE_LOCAL_GOVERNMENT: 90,

    SOURCE_PUBLIC_BROADCASTER: 85,

    SOURCE_OFFICIAL_TV: 80,

    SOURCE_OFFICIAL_YOUTUBE: 75,

}


# ============================================================
# OFFICIAL RSS SOURCES
#
# These are intentionally government/public-service focused.
#
# Do NOT add commercial publishers here unless you explicitly
# want them as a secondary source layer.
# ============================================================

RSS_SOURCES = [

    # --------------------------------------------------------
    # GOVERNMENT OF INDIA
    # --------------------------------------------------------

    {
        "publisher": "PIB",
        "source_type": SOURCE_GOVERNMENT,
        "category": "In India",
        "url": (
            "https://pib.gov.in/"
            "RssMain.aspx?ModId=6&Lang=1&Regid=22"
        ),
    },

    {
        "publisher": "PIB",
        "source_type": SOURCE_GOVERNMENT,
        "category": "Business & Economy",
        "url": (
            "https://pib.gov.in/"
            "RssMain.aspx?ModId=6&Lang=1&Regid=20"
        ),
    },

    {
        "publisher": "PIB",
        "source_type": SOURCE_GOVERNMENT,
        "category": "Tech & AI",
        "url": (
            "https://pib.gov.in/"
            "RssMain.aspx?ModId=6&Lang=1&Regid=6"
        ),
    },

    # --------------------------------------------------------
    # PUBLIC BROADCASTING
    # --------------------------------------------------------

    {
        "publisher": "News On AIR",
        "source_type": SOURCE_PUBLIC_BROADCASTER,
        "category": "In India",
        "url": (
            "https://www.newsonair.gov.in/feed/"
        ),
    },

    # --------------------------------------------------------
    # PRASAR BHARATI
    #
    # Keep these configurable because individual regional
    # feeds can change.
    # --------------------------------------------------------

    {
        "publisher": "Prasar Bharati",
        "source_type": SOURCE_PUBLIC_BROADCASTER,
        "category": "In India",
        "url": (
            "https://prasarbharati.gov.in/feed/"
        ),
    },

]


# ============================================================
# OFFICIAL YOUTUBE CHANNELS
#
# YouTube RSS requires a channel ID.
#
# These channel IDs are from official Prasar Bharati
# channel listings.
# ============================================================

YOUTUBE_CHANNELS = [

    {
        "publisher": "DD News",
        "source_type": SOURCE_OFFICIAL_YOUTUBE,
        "category": "In India",
        "channel_id": (
            "UCKwucPzHZ7zCUI7fI-Wo1g"
        ),
    },

    {
        "publisher": "News On AIR Official",
        "source_type": SOURCE_OFFICIAL_YOUTUBE,
        "category": "In India",
        "channel_id": (
            "UCY0v0QZr2B70Rkx_ZqIA84w"
        ),
    },

    {
        "publisher": "Doordarshan National",
        "source_type": SOURCE_OFFICIAL_YOUTUBE,
        "category": "Society & Culture",
        "channel_id": (
            "UCSjPe5kinQtwcyHcFJyyMfw"
        ),
    },

    {
        "publisher": "DD Kisan",
        "source_type": SOURCE_OFFICIAL_YOUTUBE,
        "category": "Human & Environment",
        "channel_id": (
            "UCnDfmcUyhgJp6xC1LmBLfUg"
        ),
    },

]


# ============================================================
# OPTIONAL YOUTUBE CHANNELS
#
# Add more official government/TV channels here.
#
# Example:
#
# {
#     "publisher": "ISRO",
#     "source_type": SOURCE_OFFICIAL_YOUTUBE,
#     "category": "Science & Development",
#     "channel_id": "YOUR_CHANNEL_ID",
# },
#
# Only use verified official channels.
# ============================================================


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
        "counter terrorism",
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
    ],

    "Science & Development": [
        "science",
        "research",
        "space",
        "isro",
        "satellite",
        "rocket",
        "technology research",
        "development",
        "innovation",
        "laboratory",
        "scientist",
        "climate research",
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
        "startup",
        "space technology",
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

    url = str(url).strip()

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
# ID
# ============================================================

def make_id(
    title,
    url
):

    raw = (
        normalize_title(title)
        + "|"
        + url
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]


# ============================================================
# DATE PARSER
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
            "href",
            ""
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
# FIND IMAGE
# ============================================================

def find_image(
    element
):

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

    return ""


# ============================================================
# CATEGORY DETECTION
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

    # Preferred category gets priority.
    if preferred in CATEGORY_ORDER:

        preferred_words = (
            CATEGORY_KEYWORDS.get(
                preferred,
                []
            )
        )

        for keyword in preferred_words:

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
# OPENAI AI EDITOR
# ============================================================

def ai_rewrite_article(
    title,
    description,
    publisher,
    source_type,
    category
):

    # --------------------------------------------------------
    # No API key:
    # return a safe non-AI fallback.
    # --------------------------------------------------------

    if not OPENAI_API_KEY:

        return fallback_editorial(
            title,
            description,
            category
        )


    source_text = clean_text(
        description
    )

    if len(source_text) > 5000:

        source_text = (
            source_text[:5000]
            + "..."
        )


    system_prompt = """
You are the editorial AI for Snippet24,
an Indian public-interest digital news platform.

Your job is to transform supplied source
material into concise, neutral and factual
news presentation.

IMPORTANT:

You MUST use only information contained
in the supplied source material.

Never invent:
- names
- numbers
- dates
- locations
- quotations
- causes
- motives
- consequences
- statistics
- claims

Do not add opinion.

Do not exaggerate.

Do not use clickbait.

Do not copy long passages from the source.

Paraphrase naturally.

OUTPUT EXACTLY THIS JSON STRUCTURE:

{
  "headline": "...",
  "snippet_lines": [
    "...",
    "...",
    "..."
  ],
  "summary": "...",
  "category": "...",
  "importance": "HIGH|MEDIUM|LOW"
}

HEADLINE:
8 to 14 words.
Clear and factual.

SNIPPET:
Exactly 3 short lines.
Each line should communicate one useful fact.
Approximately 8 to 14 words per line.

SUMMARY:
2 or 3 sentences.
Approximately 35 to 60 words.
Explain what happened and why it matters,
but only when the source supports that explanation.

CATEGORY:
Choose one of:

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

If information is insufficient,
do not guess.
Use only supported facts.
"""


    user_prompt = f"""
SOURCE TYPE:
{source_type}

PUBLISHER:
{publisher}

CURRENT CATEGORY:
{category}

SOURCE HEADLINE:
{clean_text(title)}

SOURCE DESCRIPTION:
{source_text}

Rewrite this information for Snippet24.
"""


    payload = {

        "model":
            OPENAI_MODEL,

        "input": [

            {
                "role": "system",
                "content": system_prompt,
            },

            {
                "role": "user",
                "content": user_prompt,
            },

        ],

        "max_output_tokens": 500,

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

            timeout=30,

        )

        response.raise_for_status()

        data = response.json()


        text = extract_response_text(
            data
        )


        if not text:

            raise ValueError(
                "AI returned empty output"
            )


        result = extract_json(
            text
        )


        if not result:

            raise ValueError(
                "AI output was not valid JSON"
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
            clean_text(line)
            for line in lines
            if clean_text(line)
        ]


        # EXACTLY 3 lines.
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


        result_category = (
            result.get(
                "category",
                category
            )
        )


        if result_category not in CATEGORY_ORDER:

            result_category = category


        importance = str(
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

            "snippet":
                "\n".join(lines),

            "snippet_lines":
                lines,

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
            "  AI rewrite failed:",
            exc
        )

        return fallback_editorial(

            title,

            description,

            category

        )


# ============================================================
# EXTRACT RESPONSE TEXT
# ============================================================

def extract_response_text(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return ""


    # Responses API output_text
    if data.get(
        "output_text"
    ):

        return str(
            data["output_text"]
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
# EXTRACT JSON FROM AI OUTPUT
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
        flags=re.DOTALL
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
# FALLBACK EDITORIAL
# ============================================================

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


    sentences = re.split(
        r"(?<=[.!?])\s+",
        description
    )


    sentences = [
        clean_text(s)
        for s in sentences
        if clean_text(s)
    ]


    lines = []


    if title:

        lines.append(
            title
        )


    for sentence in sentences:

        if len(lines) >= 3:

            break

        lines.append(
            sentence
        )


    while len(lines) < 3:

        lines.append(
            fallback_snippet_line(
                title,
                description,
                len(lines)
            )
        )


    summary = (
        description[:500]
        if description
        else
        "The original source has "
        "published the latest update. "
        "Read the original report "
        "for complete details."
    )


    return {

        "headline":
            title,

        "snippet":
            "\n".join(
                lines[:3]
            ),

        "snippet_lines":
            lines[:3],

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
# FALLBACK SNIPPET LINE
# ============================================================

def fallback_snippet_line(
    title,
    description,
    index
):

    if description:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            description
        )

        clean_sentences = [
            clean_text(s)
            for s in sentences
            if clean_text(s)
        ]

        if clean_sentences:

            return clean_sentences[
                min(
                    index,
                    len(clean_sentences) - 1
                )
            ][:160]


    if index == 0:

        return (
            "The latest development "
            "has been reported by "
            "the original source."
        )

    if index == 1:

        return (
            "The source has provided "
            "additional information "
            "about the development."
        )

    return (
        "Read the original report "
        "for the complete details."
    )


# ============================================================
# PARSE RSS / ATOM FEED
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
            f"  XML error: {exc}"
        )

        return articles


    elements = []


    for element in root.iter():

        tag = element.tag.split(
            "}"
        )[-1].lower()


        if tag in (
            "item",
            "entry",
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


        date_obj = parse_date(
            published
        )


        image = find_image(
            item
        )


        publisher = clean_text(
            source["publisher"]
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
            title[:80]
        )


        editorial = ai_rewrite_article(

            title,

            description,

            publisher,

            source_type,

            category,

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

            "importance":
                editorial[
                    "importance"
                ],

            "ai_rewritten":
                editorial[
                    "ai_rewritten"
                ],

            "published_at":
                date_obj.isoformat(),

            "source_url":
                link,

            "image_url":
                image,

            "image_type":
                "source",

        }


        articles.append(
            article
        )


    return articles


# ============================================================
# FETCH RSS SOURCE
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
            "  ->",
            len(articles),
            "stories"
        )


        return articles


    except Exception as exc:

        print(
            "  -> FAILED:",
            publisher,
            exc
        )

        return []


# ============================================================
# YOUTUBE RSS URL
# ============================================================

def youtube_feed_url(
    channel_id
):

    return (
        "https://www.youtube.com/"
        "feeds/videos.xml?channel_id="
        + channel_id
    )


# ============================================================
# FETCH YOUTUBE
# ============================================================

def fetch_youtube_source(
    source
):

    publisher = source[
        "publisher"
    ]

    channel_id = source[
        "channel_id"
    ]


    source_config = {

        "publisher":
            publisher,

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


    print()
    print(
        "Fetching YouTube:",
        publisher
    )


    return fetch_rss_source(
        source_config
    )


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


        return [

            article

            for article in articles

            if isinstance(
                article,
                dict
            )

        ]


    except Exception:

        return []


# ============================================================
# ARTICLE PRIORITY
# ============================================================

def article_priority(
    article
):

    source_type = article.get(
        "source_type",
        ""
    )


    score = SOURCE_PRIORITY.get(
        source_type,
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


    category = article.get(
        "category",
        ""
    )


    if category == "In India":

        score += 15


    if category == "Security & Peace":

        score += 10


    if category == "Law Around Us":

        score += 10


    return score


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


        title = clean_text(
            article.get(
                "headline",
                ""
            )
        )


        if not url or not title:

            continue


        key = url.lower()


        if key not in by_url:

            by_url[
                key
            ] = article

            continue


        existing = by_url[
            key
        ]


        if article_timestamp(
            article
        ) > article_timestamp(
            existing
        ):

            by_url[
                key
            ] = article


    # --------------------------------------------------------
    # TITLE DEDUPLICATION
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


        if title_key not in by_title:

            by_title[
                title_key
            ] = article

            continue


        existing = by_title[
            title_key
        ]


        if article_priority(
            article
        ) > article_priority(
            existing
        ):

            by_title[
                title_key
            ] = article

        elif (
            article_priority(
                article
            )
            ==
            article_priority(
                existing
            )
        ):

            if article_timestamp(
                article
            ) > article_timestamp(
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

        reverse=True,

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
        ] = counts.get(
            source_type,
            0
        ) + 1


    return counts


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print()
    print("=" * 72)
    print(
        "SNIPPET24 NEWS CURATOR"
    )
    print(
        "GOVERNMENT + PUBLIC + OFFICIAL YOUTUBE"
    )
    print(
        "AI EDITORIAL VERSION"
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
            "Stories will use the safe fallback editor."
        )
        print()


    previous_articles = (
        load_existing_articles()
    )


    print(
        "Previous stories:",
        len(previous_articles)
    )


    fresh_articles = []


    successful_sources = 0
    failed_sources = 0


    # ========================================================
    # RSS SOURCES
    # ========================================================

    for source in RSS_SOURCES:

        found = fetch_rss_source(
            source
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
    # YOUTUBE SOURCES
    # ========================================================

    for source in YOUTUBE_CHANNELS:

        found = fetch_youtube_source(
            source
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
        "Fresh stories:",
        len(fresh_articles)
    )


    # ========================================================
    # COMBINE
    # ========================================================

    combined = (
        fresh_articles
        + previous_articles
    )


    print(
        "Combined:",
        len(combined)
    )


    # ========================================================
    # DEDUPLICATE
    # ========================================================

    combined = deduplicate(
        combined
    )


    print(
        "After deduplication:",
        len(combined)
    )


    # ========================================================
    # SORT
    # ========================================================

    final_articles = sort_articles(
        combined
    )


    # ========================================================
    # NO ARTIFICIAL LIMIT
    # ========================================================

    print(
        "Final stories:",
        len(final_articles)
    )


    # ========================================================
    # CATEGORY COUNTS
    # ========================================================

    counts = category_counts(
        final_articles
    )


    # ========================================================
    # SOURCE COUNTS
    # ========================================================

    source_type_counts = (
        source_counts(
            final_articles
        )
    )


    # ========================================================
    # OUTPUT
    # ========================================================

    output = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total":
            len(final_articles),

        "editor":
            "Snippet24 AI Editorial",

        "source_policy":
            "Government, public-service broadcasters, official TV and verified official YouTube channels",

        "ai_model":
            OPENAI_MODEL
            if OPENAI_API_KEY
            else None,

        "categories":
            counts,

        "source_types":
            source_type_counts,

        "successful_sources":
            successful_sources,

        "failed_sources":
            failed_sources,

        "articles":
            final_articles,

    }


    # ========================================================
    # WRITE FILE
    # ========================================================

    temporary_file = (
        OUTPUT_FILE
        + ".tmp"
    )


    with open(

        temporary_file,

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
        temporary_file,
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
        "Total stories:",
        len(final_articles)
    )


    print()
    print(
        "CATEGORY COUNTS"
    )


    for category in CATEGORY_ORDER:

        print(
            f"{category}: "
            f"{counts.get(category, 0)}"
        )


    print()
    print(
        "SOURCE TYPE COUNTS"
    )


    for source_type, count in (
        source_type_counts.items()
    ):

        print(
            f"{source_type}: {count}"
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


    print()
    print(
        "articles.json updated successfully."
    )


    return 0


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        build_feed()
    )
