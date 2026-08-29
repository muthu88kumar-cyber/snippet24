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
# SNIPPET24 NEWS CURATOR v13
# UNLIMITED CATEGORY COVERAGE
#
# - No per-category story limits
# - TARGET_STORIES = 0 means unlimited
# - Minimum target is only a success threshold
# - Official/public/institutional sources
# - Local AI images generated during curator run
# - Existing local images are reused
# ============================================================

CURATOR_VERSION = "13.0-unlimited-category-coverage"

OUTPUT_FILE = "articles.json"
IMAGES_DIR = "images"

POLLINATIONS_API_KEY = os.getenv(
    "POLLINATIONS_API_KEY",
    ""
).strip()


# ============================================================
# STORY LIMITS
# ============================================================

# 0 = unlimited
#
# IMPORTANT:
# This is NOT a maximum.
# The curator will collect every valid story available
# from the configured sources.
TARGET_STORIES = 0

# Minimum desired collection.
# This does NOT stop or cap collection.
MINIMUM_STORIES = 100

# There is intentionally NO MAX_PER_CATEGORY.
#
# Do NOT add:
#
# MAX_PER_CATEGORY = {
#     ...
# }
#
# Every category can contain as many valid stories as
# the configured sources provide.


# ============================================================
# NETWORK SETTINGS
# ============================================================

# Reduced from 15 seconds.
REQUEST_TIMEOUT = 8

# Small delay between source requests.
REQUEST_DELAY = 0.10

# Separate timeout for image generation.
IMAGE_TIMEOUT = 90

# Number of image-generation retries.
IMAGE_RETRIES = 3


HEADERS = {
    "User-Agent": (
        "Snippet24-News/13.0 "
        "(+https://snippet24.in)"
    ),
    "Accept": (
        "application/rss+xml, "
        "application/atom+xml, "
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
    "World",
    "India",
    "Business",
    "Technology & AI",
    "Sports",
    "Entertainment",
    "Lifestyle",
]


# ============================================================
# CATEGORY RULES
# ============================================================

CATEGORY_RULES = {

    "World": [
        "world",
        "international",
        "global",
        "united nations",
        "un",
        "who",
        "unicef",
        "unhcr",
        "unesco",
        "wmo",
        "fao",
        "international affairs",
        "diplomacy",
        "foreign affairs",
        "conflict",
        "war",
        "climate",
        "global health",
    ],

    "India": [
        "india",
        "indian",
        "government of india",
        "central government",
        "state government",
        "ministry",
        "parliament",
        "supreme court",
        "high court",
        "pib",
        "isro",
        "rbi",
        "income tax",
        "election",
        "railways",
        "defence",
        "education",
        "infrastructure",
    ],

    # --------------------------------------------------------
    # BUSINESS
    # --------------------------------------------------------
    #
    # User-requested additions:
    # - MSME
    # - State MSME
    # - DIC
    # - Skill development
    # - FSSAI
    # - Promotion / Export Councils
    # - BIS
    #
    "Business": [
        "business",
        "economy",
        "economic",
        "finance",
        "bank",
        "banking",
        "rbi",
        "interest rate",
        "inflation",
        "trade",
        "export",
        "import",
        "investment",
        "startup",
        "company",
        "corporate",

        # MSME
        "msme",
        "micro small and medium enterprises",
        "micro enterprise",
        "small enterprise",
        "medium enterprise",
        "msmed",

        # State MSME
        "state msme",
        "msme department",
        "industries department",
        "industrial development",

        # DIC
        "district industries centre",
        "district industries center",
        "dic",

        # Skill development
        "skill development",
        "skill development mission",
        "vocational training",
        "employment skills",
        "upskilling",
        "reskilling",
        "apprenticeship",
        "industrial training",

        # FSSAI
        "fssai",
        "food safety",
        "food safety and standards",
        "food business operator",
        "food standards",

        # Promotion / Export Councils
        "export promotion council",
        "promotion council",
        "export council",
        "engineering export promotion council",
        "textiles export promotion",
        "pharmaceuticals export promotion",
        "electronics export promotion",
        "services export promotion",
        "trade promotion",

        # BIS
        "bis",
        "bureau of indian standards",
        "standardization",
        "quality standards",
        "product standards",
        "isi mark",
        "hallmark",

        # Major business institutions
        "world bank",
        "imf",
        "international monetary fund",
        "world trade organization",
        "wto",
        "oecd",
        "european central bank",
        "sec",
        "securities",
    ],

    # --------------------------------------------------------
    # TECHNOLOGY & AI
    # --------------------------------------------------------

    "Technology & AI": [
        "technology",
        "tech",
        "artificial intelligence",
        "ai",
        "machine learning",
        "generative ai",
        "robotics",
        "software",
        "hardware",
        "semiconductor",
        "chip",
        "space",
        "nasa",
        "isro",
        "esa",
        "cern",
        "quantum",
        "cyber",
        "cybersecurity",
        "internet",
        "cloud",
        "data",
        "science",
        "research",
        "innovation",
        "astronomy",
    ],

    "Sports": [
        "sport",
        "sports",
        "football",
        "soccer",
        "fifa",
        "cricket",
        "icc",
        "olympics",
        "olympic",
        "athletics",
        "tennis",
        "badminton",
        "hockey",
        "basketball",
        "rugby",
        "formula 1",
        "motorsport",
        "boxing",
        "wrestling",
    ],

    # --------------------------------------------------------
    # ENTERTAINMENT
    # --------------------------------------------------------
    #
    # User-requested additions:
    #
    # ALL major "woods":
    # - Bollywood
    # - Hollywood
    # - Kollywood
    # - Tollywood
    # - Mollywood
    # - Sandalwood
    # - Pollywood
    # - other Indian regional film industries
    #
    # PLUS:
    # - YouTube
    # - creator platforms
    # - creator news
    # - local stage shows
    # - theatre
    # - live performances
    #
    "Entertainment": [
        "entertainment",
        "film",
        "films",
        "movie",
        "movies",
        "cinema",
        "actor",
        "actress",
        "director",
        "producer",
        "trailer",
        "film festival",

        # Bollywood
        "bollywood",
        "hindi cinema",

        # Hollywood
        "hollywood",
        "american cinema",

        # Tamil
        "kollywood",
        "tamil cinema",
        "tamil film",

        # Telugu
        "tollywood",
        "telugu cinema",
        "telugu film",

        # Malayalam
        "mollywood",
        "malayalam cinema",
        "malayalam film",

        # Kannada
        "sandalwood",
        "kannada cinema",
        "kannada film",

        # Punjabi
        "pollywood",
        "punjabi cinema",
        "punjabi film",

        # Bengali
        "bengali cinema",
        "bangla cinema",

        # Marathi
        "marathi cinema",
        "marathi film",

        # Gujarati
        "gujarati cinema",
        "gujarati film",

        # Other Indian regional cinema
        "regional cinema",
        "regional film",
        "indian cinema",

        # Global cinema
        "korean cinema",
        "japanese cinema",
        "french cinema",
        "british cinema",
        "international cinema",

        # Streaming
        "streaming",
        "ott",
        "web series",
        "series",
        "television",
        "tv",

        # YouTube / creators
        "youtube",
        "youtube creator",
        "youtube creators",
        "creator",
        "creators",
        "content creator",
        "content creators",
        "creator economy",
        "influencer",
        "influencers",
        "podcast",
        "podcasters",
        "streamer",
        "streamers",
        "twitch",

        # Stage / live entertainment
        "stage show",
        "stage shows",
        "live show",
        "live shows",
        "theatre",
        "theater",
        "play",
        "plays",
        "drama",
        "musical",
        "musicals",
        "live performance",
        "live performances",
        "performing arts",
        "cultural performance",
        "cultural performances",
        "concert",
        "concerts",
    ],

    "Lifestyle": [
        "lifestyle",
        "health",
        "healthcare",
        "wellness",
        "food",
        "nutrition",
        "fitness",
        "travel",
        "tourism",
        "environment",
        "climate",
        "family",
        "education",
        "science",
        "culture",
        "arts",
        "nature",
        "mental wellbeing",
        "public health",
    ],
}


# ============================================================
# RSS SOURCES
# ============================================================
#
# These are official / public / institutional sources.
#
# IMPORTANT:
# The category does NOT limit the number of articles.
# If a source produces 100 valid stories, all 100 can enter
# the collection.
#
# Broader entertainment/business sources can be added here
# only after their source terms / reuse permissions have
# been checked separately.
# ============================================================

RSS_SOURCES = {

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    "World": [
        (
            "United Nations",
            "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
        ),
        (
            "World Health Organization",
            "https://www.who.int/feeds/entity/news/en/rss.xml"
        ),
        (
            "UNICEF",
            "https://www.unicef.org/press-releases/rss.xml"
        ),
        (
            "UNHCR",
            "https://www.unhcr.org/rss/news.xml"
        ),
        (
            "UNESCO",
            "https://www.unesco.org/en/rss.xml"
        ),
        (
            "World Meteorological Organization",
            "https://public.wmo.int/en/rss.xml"
        ),
        (
            "FAO",
            "https://www.fao.org/feeds/fao-news/en"
        ),
    ],

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    "India": [
        (
            "Press Information Bureau",
            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"
        ),
        (
            "Press Information Bureau - Features",
            "https://pib.gov.in/RssMain.aspx?ModId=18&Lang=1&Regid=1"
        ),
        (
            "ISRO",
            "https://www.isro.gov.in/media_isro/rss.xml"
        ),
        (
            "Income Tax Department",
            "https://wmstatic-prd.incometaxindia.gov.in/en/press-release-rss-feed/-/asset_publisher/ovrx/rss"
        ),
        (
            "Reserve Bank of India",
            "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=RSS"
        ),
        (
            "Ministry of External Affairs",
            "https://www.mea.gov.in/rss.htm"
        ),
    ],

    # --------------------------------------------------------
    # BUSINESS
    # --------------------------------------------------------

    "Business": [
        (
            "Reserve Bank of India",
            "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=RSS"
        ),
        (
            "European Central Bank",
            "https://www.ecb.europa.eu/rss/press.html"
        ),
        (
            "International Monetary Fund",
            "https://www.imf.org/en/News/RSS"
        ),
        (
            "World Bank",
            "https://www.worldbank.org/en/news/all?format=rss"
        ),
        (
            "World Trade Organization",
            "https://www.wto.org/english/news_e/news_e.xml"
        ),
        (
            "OECD",
            "https://www.oecd.org/newsroom/rss.xml"
        ),
        (
            "U.S. Securities and Exchange Commission",
            "https://www.sec.gov/news/pressreleases.rss"
        ),
    ],

    # --------------------------------------------------------
    # TECHNOLOGY & AI
    # --------------------------------------------------------

    "Technology & AI": [
        (
            "NASA",
            "https://www.nasa.gov/feed/"
        ),
        (
            "NASA JPL",
            "https://www.jpl.nasa.gov/feeds/news/"
        ),
        (
            "NASA CNEOS",
            "https://cneos.jpl.nasa.gov/feed/news.xml"
        ),
        (
            "European Space Agency",
            "https://www.esa.int/rssfeed/Our_Activities"
        ),
        (
            "CERN",
            "https://home.cern/rss"
        ),
        (
            "National Science Foundation",
            "https://www.nsf.gov/rss/rss.php"
        ),
        (
            "NIST",
            "https://www.nist.gov/news-events/news/rss.xml"
        ),
        (
            "NOAA",
            "https://www.noaa.gov/rss.xml"
        ),
    ],

    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

    "Sports": [
        (
            "FIFA",
            "https://inside.fifa.com/rss"
        ),
        (
            "International Olympic Committee",
            "https://olympics.com/ioc/rss"
        ),
        (
            "Olympics",
            "https://olympics.com/en/news/rss"
        ),
        (
            "International Cricket Council",
            "https://www.icc-cricket.com/rss"
        ),
        (
            "World Athletics",
            "https://worldathletics.org/rss"
        ),
    ],

    # --------------------------------------------------------
    # ENTERTAINMENT
    # --------------------------------------------------------
    #
    # Official cultural / film institutions.
    #
    # The keyword rules above are intentionally broad so that
    # when approved feeds are added for Bollywood/Hollywood/
    # Kollywood/etc., they automatically remain in Entertainment.
    # --------------------------------------------------------

    "Entertainment": [
        (
            "Academy of Motion Picture Arts and Sciences",
            "https://www.oscars.org/rss/news.xml"
        ),
        (
            "National Endowment for the Arts",
            "https://www.arts.gov/rss/news.xml"
        ),
        (
            "Library of Congress",
            "https://www.loc.gov/rss/"
        ),
        (
            "Smithsonian",
            "https://www.si.edu/rss"
        ),
        (
            "National Gallery of Art",
            "https://www.nga.gov/rss.xml"
        ),
        (
            "Kennedy Center",
            "https://www.kennedy-center.org/rss/"
        ),
    ],

    # --------------------------------------------------------
    # LIFESTYLE
    # --------------------------------------------------------

    "Lifestyle": [
        (
            "World Health Organization",
            "https://www.who.int/feeds/entity/news/en/rss.xml"
        ),
        (
            "UNICEF",
            "https://www.unicef.org/press-releases/rss.xml"
        ),
        (
            "FAO",
            "https://www.fao.org/feeds/fao-news/en"
        ),
        (
            "Centers for Disease Control and Prevention",
            "https://tools.cdc.gov/api/v2/resources/media/403372.rss"
        ),
        (
            "National Institutes of Health",
            "https://www.nih.gov/news-events/news-releases/feed"
        ),
        (
            "NASA Earth",
            "https://www.nasa.gov/earth/feed/"
        ),
        (
            "Smithsonian",
            "https://www.si.edu/rss"
        ),
        (
            "Library of Congress",
            "https://www.loc.gov/rss/"
        ),
    ],
}


# ============================================================
# APPROVED OFFICIAL DOMAINS
# ============================================================

APPROVED_SOURCE_DOMAINS = {
    "pib.gov.in",
    "isro.gov.in",
    "incometaxindia.gov.in",
    "rbi.org.in",
    "mea.gov.in",

    "un.org",
    "news.un.org",
    "who.int",
    "unicef.org",
    "unhcr.org",
    "unesco.org",
    "wmo.int",
    "fao.org",

    "imf.org",
    "worldbank.org",
    "wto.org",
    "oecd.org",
    "ecb.europa.eu",
    "sec.gov",

    "nasa.gov",
    "jpl.nasa.gov",
    "esa.int",
    "cern.ch",
    "nsf.gov",
    "nist.gov",
    "noaa.gov",

    "fifa.com",
    "olympics.com",
    "icc-cricket.com",
    "worldathletics.org",

    "oscars.org",
    "arts.gov",
    "loc.gov",
    "si.edu",
    "nga.gov",
    "kennedy-center.org",

    "cdc.gov",
    "nih.gov",
}


# ============================================================
# SOURCE CHECK
# ============================================================

def is_approved_source_url(url):
    if not url:
        return False

    try:
        host = (
            urlparse(url)
            .netloc
            .lower()
            .split(":")[0]
        )

        return any(
            host == domain
            or host.endswith("." + domain)
            for domain in APPROVED_SOURCE_DOMAINS
        )

    except Exception:
        return False


# ============================================================
# TEXT HELPERS
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


def normalize_url(url):
    if not url:
        return ""

    url = clean_text(url).strip()

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


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================

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


# ============================================================
# CATEGORY CLASSIFICATION
# ============================================================

def classify_category(
    supplied_category,
    title,
    description="",
    publisher=""
):
    """
    Primary category comes from RSS_SOURCES.

    Keyword rules are also used as a secondary check,
    especially for Business and Entertainment.
    """

    supplied = normalize_category(
        supplied_category
    )

    text = " ".join([
        clean_text(title),
        clean_text(description),
        clean_text(publisher),
    ]).lower()

    # Strong category-specific overrides.

    entertainment_hits = sum(
        1
        for keyword in CATEGORY_RULES["Entertainment"]
        if keyword in text
    )

    business_hits = sum(
        1
        for keyword in CATEGORY_RULES["Business"]
        if keyword in text
    )

    technology_hits = sum(
        1
        for keyword in CATEGORY_RULES["Technology & AI"]
        if keyword in text
    )

    sports_hits = sum(
        1
        for keyword in CATEGORY_RULES["Sports"]
        if keyword in text
    )

    india_hits = sum(
        1
        for keyword in CATEGORY_RULES["India"]
        if keyword in text
    )

    world_hits = sum(
        1
        for keyword in CATEGORY_RULES["World"]
        if keyword in text
    )

    lifestyle_hits = sum(
        1
        for keyword in CATEGORY_RULES["Lifestyle"]
        if keyword in text
    )

    scores = {
        "Entertainment": entertainment_hits,
        "Business": business_hits,
        "Technology & AI": technology_hits,
        "Sports": sports_hits,
        "India": india_hits,
        "World": world_hits,
        "Lifestyle": lifestyle_hits,
    }

    best_category = max(
        scores,
        key=scores.get
    )

    best_score = scores[best_category]

    # Only override the source category when
    # there is meaningful evidence.
    if best_score >= 2:
        return best_category

    return supplied


# ============================================================
# PUBLISHER REMOVAL
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
        "Government of India",
        "Press Information Bureau",
        "United Nations",
        "World Health Organization",
        "European Commission",
        "European Central Bank",
        "International Monetary Fund",
        "World Bank",
        "World Trade Organization",
        "NASA",
        "NASA JPL",
        "NASA CNEOS",
        "FIFA",
        "International Olympic Committee",
        "International Cricket Council",
        "National Endowment for the Arts",
        "Library of Congress",
        "Smithsonian",
        "Kennedy Center",
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

    summary = clean_text(summary)

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

    title = clean_text(title)

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
        "by the original source. Read the original "
        "report for the full details."
    )


# ============================================================
# DATE
# ============================================================

def parse_date(value):

    if not value:
        return datetime.now(
            timezone.utc
        )

    value = clean_text(value)

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

def tag_name(element):

    return (
        element.tag
        .split("}")[-1]
        .lower()
    )


def find_child_text(
    element,
    names
):

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

        href = child.attrib.get(
            "href"
        )

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

        normalized = normalize_url(
            link
        )

        if normalized:
            return normalized

    guid = find_child_text(
        element,
        [
            "guid",
            "id"
        ]
    )

    return normalize_url(
        guid
    )


# ============================================================
# FEED IMAGE
# ============================================================

def find_image_from_feed(element):

    for child in element.iter():

        tag = tag_name(child)

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

        if tag_name(child) != "enclosure":
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
        r'https?://[^"\'>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\'>\s]*)?',
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

def make_ai_prompt(
    title,
    category
):

    return (
        "Professional editorial news illustration "
        "for a modern digital news publication. "
        f"Category: {category}. "
        f"Story: {title}. "
        "Create a realistic, relevant, tasteful "
        "journalistic visual suitable for a news "
        "website. "
        "No text, no letters, no words, "
        "no logos, no watermark, "
        "no fake newspaper, "
        "no headline typography."
    )


def make_ai_image_url(
    title,
    category
):

    prompt = make_ai_prompt(
        title,
        category
    )

    return (
        "https://gen.pollinations.ai/image/"
        + quote(
            prompt,
            safe=""
        )
        + "?model=flux"
        + "&width=1200"
        + "&height=675"
        + "&nologo=true"
    )


def local_image_path(
    article_id
):

    return os.path.join(
        IMAGES_DIR,
        f"{article_id}.jpg"
    )


def local_image_url(
    article_id
):

    return (
        f"images/{article_id}.jpg"
    )


def is_valid_image_bytes(
    data,
    content_type=""
):

    if not data:
        return False

    if len(data) < 10_000:
        return False

    content_type = (
        content_type
        or ""
    ).lower()

    signatures = (
        data[:3] == b"\xff\xd8\xff",

        data[:8] == (
            b"\x89PNG\r\n\x1a\n"
        ),

        data[:4] == b"RIFF"
        and data[8:12] == b"WEBP",

        data[:6] in (
            b"GIF87a",
            b"GIF89a"
        ),
    )

    return (
        "image/" in content_type
        or any(signatures)
    )


def generate_and_save_ai_image(
    article_id,
    title,
    category
):

    os.makedirs(
        IMAGES_DIR,
        exist_ok=True
    )

    path = local_image_path(
        article_id
    )

    # --------------------------------------------------------
    # Reuse existing image
    # --------------------------------------------------------

    if (
        os.path.exists(path)
        and os.path.getsize(path) > 10_000
    ):

        print(
            f"  -> AI IMAGE REUSED: {path}"
        )

        return local_image_url(
            article_id
        )

    # --------------------------------------------------------
    # Check API key
    # --------------------------------------------------------

    if not POLLINATIONS_API_KEY:

        print(
            "  -> AI IMAGE SKIPPED: "
            "POLLINATIONS_API_KEY is not configured."
        )

        return ""

    image_url = make_ai_image_url(
        title,
        category
    )

    last_error = ""

    for attempt in range(
        1,
        IMAGE_RETRIES + 1
    ):

        try:

            print(
                "  -> AI IMAGE: "
                f"generating attempt "
                f"{attempt}/{IMAGE_RETRIES}"
            )

            response = requests.get(
                image_url,
                headers={
                    "Authorization": (
                        "Bearer "
                        + POLLINATIONS_API_KEY
                    ),
                    "Accept": (
                        "image/jpeg,"
                        "image/png,"
                        "image/webp,"
                        "image/*"
                    ),
                },
                timeout=IMAGE_TIMEOUT
            )

            response.raise_for_status()

            data = response.content

            content_type = (
                response.headers.get(
                    "content-type",
                    ""
                )
            )

            if not is_valid_image_bytes(
                data,
                content_type
            ):

                last_error = (
                    "Invalid image response: "
                    f"type={content_type}, "
                    f"bytes={len(data)}"
                )

                print(
                    "  -> AI IMAGE RETRY: "
                    + last_error
                )

                time.sleep(
                    attempt
                )

                continue

            with open(
                path,
                "wb"
            ) as image_file:

                image_file.write(
                    data
                )

            print(
                f"  -> AI IMAGE SAVED: {path}"
            )

            return local_image_url(
                article_id
            )

        except Exception as exc:

            last_error = str(exc)

            print(
                "  -> AI IMAGE RETRY: "
                + last_error
            )

            time.sleep(
                attempt
            )

    print(
        "  -> AI IMAGE FAILED AFTER "
        f"{IMAGE_RETRIES} ATTEMPTS: "
        f"{last_error}"
    )

    return ""


# ============================================================
# ARTICLE ID
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
            f"  XML ERROR: {publisher}: {exc}"
        )

        return articles

    elements = []

    for element in root.iter():

        tag = tag_name(
            element
        )

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

        # ----------------------------------------------------
        # SOURCE SAFETY
        # ----------------------------------------------------

        if not is_approved_source_url(
            link
        ):

            print(
                "  -> SOURCE REJECTED: "
                f"{link}"
            )

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
            classify_category(
                category,
                title,
                description,
                publisher
            )
        )

        summary = make_summary(
            title,
            description
        )

        article_id = make_id(
            normalized_category,
            title,
            link
        )

        # ----------------------------------------------------
        # LOCAL AI IMAGE
        # ----------------------------------------------------

        image_url = (
            generate_and_save_ai_image(
                article_id,
                title,
                normalized_category
            )
        )

        article = {
            "id": article_id,

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

            "source_type":
                "official_institutional",

            "published_at":
                date_obj.isoformat(),

            "source_url":
                link,

            "image_url":
                image_url,

            "image_type":
                (
                    "ai_generated_local"
                    if image_url
                    else
                    "ai_generation_failed"
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
            f"  -> FAILED: "
            f"{publisher}: {exc}"
        )

        return []


# ============================================================
# EXISTING ARTICLES
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

            # Remove old unapproved
            # commercial/private entries.
            if not is_approved_source_url(
                url
            ):

                continue

            category = normalize_category(
                article.get(
                    "category"
                )
            )

            article["category"] = category

            article["headline"] = (
                headline
            )

            article["summary"] = (
                make_summary(
                    headline,
                    article.get(
                        "summary",
                        ""
                    )
                )
            )

            article["source_url"] = url

            publisher = clean_text(
                article.get(
                    "publisher",
                    ""
                )
            )

            article_id = (
                article.get("id")
                or
                make_id(
                    category,
                    headline,
                    url
                )
            )

            article["id"] = article_id

            # ------------------------------------------------
            # Existing local image
            # ------------------------------------------------

            existing_local = (
                local_image_path(
                    article_id
                )
            )

            if (
                os.path.exists(
                    existing_local
                )
                and
                os.path.getsize(
                    existing_local
                ) > 10_000
            ):

                article["image_url"] = (
                    local_image_url(
                        article_id
                    )
                )

                article["image_type"] = (
                    "ai_generated_local"
                )

            else:

                image_url = (
                    generate_and_save_ai_image(
                        article_id,
                        headline,
                        category
                    )
                )

                article["image_url"] = (
                    image_url
                )

                article["image_type"] = (
                    "ai_generated_local"
                    if image_url
                    else
                    "ai_generation_failed"
                )

            if not article.get(
                "published_at"
            ):

                article["published_at"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

            if not article.get(
                "publisher"
            ):

                article["publisher"] = (
                    publisher
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
            "Could not read "
            f"previous articles.json: {exc}"
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

        if not is_approved_source_url(
            url
        ):

            continue

        key = url.lower()

        if key not in by_url:

            by_url[key] = article

        else:

            old_date = (
                by_url[key].get(
                    "published_at",
                    ""
                )
            )

            new_date = (
                article.get(
                    "published_at",
                    ""
                )
            )

            if new_date > old_date:

                by_url[key] = article

    # --------------------------------------------------------
    # Title-level deduplication
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

        else:

            old_date = (
                by_title[
                    title_key
                ].get(
                    "published_at",
                    ""
                )
            )

            new_date = (
                article.get(
                    "published_at",
                    ""
                )
            )

            if new_date > old_date:

                by_title[
                    title_key
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
# UNLIMITED SELECTION
# ============================================================

def select_all_articles(
    articles
):

    """
    IMPORTANT:

    There is NO category limit.

    There is NO global 100-story limit.

    TARGET_STORIES = 0 means unlimited.

    The only things removed are:
      - invalid articles
      - duplicate URLs
      - duplicate titles
      - unapproved sources
    """

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

        source_url = normalize_url(
            article.get(
                "source_url"
            )
        )

        if not headline:
            continue

        if not source_url:
            continue

        if not is_approved_source_url(
            source_url
        ):

            continue

        valid.append(
            article
        )

    # --------------------------------------------------------
    # Newest first
    # --------------------------------------------------------

    valid.sort(
        key=article_timestamp,
        reverse=True
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # No:
    #
    # valid[:100]
    #
    # No:
    #
    # valid[-100:]
    #
    # No category slicing.
    #
    # Return EVERYTHING.
    # --------------------------------------------------------

    if TARGET_STORIES <= 0:

        return valid

    # Optional future safety setting.
    # Currently TARGET_STORIES = 0.
    return valid[:TARGET_STORIES]


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
# IMAGE COUNT
# ============================================================

def image_count(
    articles
):

    return sum(
        1
        for article in articles
        if article.get(
            "image_url"
        )
    )


# ============================================================
# BUILD FEED
# ============================================================

def build_feed():

    print()
    print("=" * 72)
    print(
        "SNIPPET24 NEWS CURATOR v13"
    )
    print(
        "UNLIMITED CATEGORY COVERAGE"
    )
    print(
        "OFFICIAL/PUBLIC SOURCES + LOCAL AI IMAGES"
    )
    print("=" * 72)
    print()

    # --------------------------------------------------------
    # Existing stories
    # --------------------------------------------------------

    previous_articles = (
        load_existing_articles()
    )

    print(
        "Previous valid stories: "
        f"{len(previous_articles)}"
    )

    # --------------------------------------------------------
    # Fresh stories
    # --------------------------------------------------------

    fresh_articles = []

    successful_sources = 0
    failed_sources = 0

    # --------------------------------------------------------
    # Fetch every category
    # --------------------------------------------------------

    for category in CATEGORY_ORDER:

        print()
        print(
            "#" * 10
            + f" {category} "
            + "#" * 10
        )

        sources = RSS_SOURCES.get(
            category,
            []
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

    # --------------------------------------------------------
    # Collection report
    # --------------------------------------------------------

    print()
    print(
        "Fresh stories collected: "
        f"{len(fresh_articles)}"
    )

    print(
        "Successful sources: "
        f"{successful_sources}"
    )

    print(
        "Failed/empty sources: "
        f"{failed_sources}"
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    combined = (
        fresh_articles
        + previous_articles
    )

    print()
    print(
        "Combined before deduplication: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    combined = deduplicate(
        combined
    )

    print(
        "After deduplication: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # UNLIMITED SELECTION
    # --------------------------------------------------------

    final_articles = (
        select_all_articles(
            combined
        )
    )

    print(
        "After unlimited selection: "
        f"{len(final_articles)}"
    )

    # --------------------------------------------------------
    # Counts
    # --------------------------------------------------------

    counts = category_counts(
        final_articles
    )

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    images = image_count(
        final_articles
    )

    print()
    print(
        "AI images available locally: "
        f"{images}/{len(final_articles)}"
    )

    # --------------------------------------------------------
    # Output
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

        # This is a minimum threshold,
        # NOT a cap.
        "minimum_target":
            MINIMUM_STORIES,

        # 0 explicitly means unlimited.
        "maximum_target":
            0,

        "unlimited_collection":
            True,

        "category_limits":
            False,

        "source_policy":
            (
                "official_government_"
                "intergovernmental_and_"
                "institutional_sources_only"
            ),

        "image_policy":
            (
                "ai_images_generated_"
                "during_curator_run_"
                "and_saved_locally"
            ),

        "copyright_note":
            (
                "Snippet24 publishes its own "
                "editorial headlines and summaries "
                "and credits the original publisher "
                "with a source link. Source-specific "
                "terms still apply. This is not a "
                "guarantee of legal immunity."
            ),

        "category_rules": {
            "Business": [
                "MSME",
                "State MSME",
                "District Industries Centres",
                "Skill Development",
                "FSSAI",
                "Promotion Councils",
                "Export Promotion Councils",
                "BIS",
            ],

            "Entertainment": [
                "Bollywood",
                "Hollywood",
                "Kollywood",
                "Tollywood",
                "Mollywood",
                "Sandalwood",
                "Pollywood",
                "Other major regional film industries",
                "International film industries",
                "YouTube",
                "Creator platforms",
                "Content creators",
                "Influencers",
                "Podcasters",
                "Local stage shows",
                "Theatre",
                "Live performances",
            ],
        },

        "categories":
            counts,

        "articles":
            final_articles,
    }

    # --------------------------------------------------------
    # Write articles.json
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
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "SNIPPET24 CURATOR COMPLETE"
    )
    print("=" * 72)

    print(
        f"TOTAL STORIES: "
        f"{len(final_articles)}"
    )

    print()

    for category in CATEGORY_ORDER:

        print(
            f"{category}: "
            f"{counts.get(category, 0)}"
        )

    print()

    print(
        "AI IMAGES: "
        f"{images}/{len(final_articles)}"
    )

    print()

    print(
        "Successful sources: "
        f"{successful_sources}"
    )

    print(
        "Failed/empty sources: "
        f"{failed_sources}"
    )

    # --------------------------------------------------------
    # Empty feed protection
    # --------------------------------------------------------

    if len(final_articles) == 0:

        print()
        print(
            "ERROR: No usable articles "
            "were collected."
        )

        print(
            "Existing articles were not "
            "intentionally deleted."
        )

        return 1

    # --------------------------------------------------------
    # Minimum target is NOT a limit
    # --------------------------------------------------------

    if len(final_articles) < MINIMUM_STORIES:

        print()
        print(
            "WARNING: Fewer than "
            f"{MINIMUM_STORIES} genuine "
            "stories are currently available."
        )

        print(
            "The curator will NOT fabricate "
            "stories to reach the minimum."
        )

    else:

        print()
        print(
            f"SUCCESS: Minimum "
            f"{MINIMUM_STORIES}-story "
            "threshold reached."
        )

    # --------------------------------------------------------
    # Important unlimited message
    # --------------------------------------------------------

    print()
    print(
        "UNLIMITED MODE: ON"
    )

    print(
        "No per-category story limit."
    )

    print(
        "No 100-story global limit."
    )

    print(
        "All valid deduplicated stories "
        "are retained."
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