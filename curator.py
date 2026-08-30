import os
import re
import json
import html
import time
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urljoin

import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# ============================================================
# SNIPPET24 CURATOR — COMPLETE REPLACEMENT
# ============================================================
# Source policy:
#   1. Government sources
#   2. Public broadcasters / official TV
#   3. Verified official YouTube channels configured below
#
# Private/closed channels, WhatsApp groups, Telegram groups,
# scraped private feeds and unknown publishers are rejected.
#
# Output:
#   articles.json
#
# AI:
#   - Rephrases, does not copy
#   - Exactly 3 snippet lines
#   - Short summary
#   - Pre-generates English/Tamil/Telugu/Kannada/Malayalam/Hindi
# ============================================================

OUTPUT_FILE = "articles.json"
REQUEST_TIMEOUT = 20
AI_TIMEOUT = 60
REQUEST_DELAY = 0.35
MAX_ARTICLES_PER_SOURCE = 40
MAX_FINAL_ARTICLES = 400

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()
OPENAI_URL = "https://api.openai.com/v1/responses"

SITE_NAME = "Snippet24"
SITE_URL = os.getenv("SITE_URL", "https://snippet24.in").strip()

HEADERS = {
    "User-Agent": "Snippet24-News-Curator/2.0 (+https://snippet24.in)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, */*;q=0.8",
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

SOURCE_GOVERNMENT = "GOVERNMENT"
SOURCE_PUBLIC = "PUBLIC_BROADCASTER"
SOURCE_OFFICIAL_TV = "OFFICIAL_TV"
SOURCE_OFFICIAL_YOUTUBE = "OFFICIAL_YOUTUBE"

ALLOWED_SOURCE_TYPES = {
    SOURCE_GOVERNMENT,
    SOURCE_PUBLIC,
    SOURCE_OFFICIAL_TV,
    SOURCE_OFFICIAL_YOUTUBE,
}

SOURCE_PRIORITY = {
    SOURCE_GOVERNMENT: 100,
    SOURCE_PUBLIC: 90,
    SOURCE_OFFICIAL_TV: 85,
    SOURCE_OFFICIAL_YOUTUBE: 80,
}

# ============================================================
# VERIFIED SOURCES
# ============================================================
# PIB is the default Government RSS source.
# DD News and Akashvani are official public-service sources.
# Official YouTube channels are intentionally configured by
# channel ID so an ordinary/private YouTube channel can never
# accidentally enter the feed.
# ============================================================

RSS_SOURCES = [
    {
        "publisher": "Press Information Bureau",
        "source_type": SOURCE_GOVERNMENT,
        "category": "In India",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=22",
    },
]

# Official sites are parsed as public/official TV sources.
HTML_SOURCES = [
    {
        "publisher": "DD News",
        "source_type": SOURCE_OFFICIAL_TV,
        "category": "In India",
        "url": "https://ddnews.gov.in/en/",
        "base_url": "https://ddnews.gov.in",
    },
    {
        "publisher": "Akashvani",
        "source_type": SOURCE_PUBLIC,
        "category": "In India",
        "url": "https://newsonair.gov.in/",
        "base_url": "https://newsonair.gov.in",
    },
]

# Add official YouTube channel IDs in GitHub Actions:
# YOUTUBE_CHANNEL_IDS='[
#   {"publisher":"PIB India","channel_id":"...","category":"In India"},
#   {"publisher":"DD News","channel_id":"...","category":"In India"}
# ]'
#
# No IDs are hard-coded here because the YouTube handle can change
# and we do not want to treat an unverified channel as official.
try:
    YOUTUBE_CHANNELS = json.loads(os.getenv("YOUTUBE_CHANNEL_IDS", "[]"))
    if not isinstance(YOUTUBE_CHANNELS, list):
        YOUTUBE_CHANNELS = []
except Exception:
    YOUTUBE_CHANNELS = []

# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {
    "Security & Peace": [
        "security", "defence", "defense", "army", "navy", "air force",
        "police", "border", "terror", "terrorism", "cyber security",
        "cybersecurity", "peace", "military", "coast guard",
    ],
    "Law Around Us": [
        "law", "court", "supreme court", "high court", "judiciary",
        "legal", "justice", "judgment", "judgement", "bill", "act",
        "legislation", "constitution", "parliament", "petition",
        "tribunal", "fir", "federal court", "copyright", "ai act",
    ],
    "Science & Development": [
        "science", "research", "space", "isro", "satellite", "rocket",
        "innovation", "laboratory", "scientist", "development",
        "researchers", "biology", "medicine", "health research",
    ],
    "Business & Economy": [
        "business", "economy", "economic", "msme", "startup", "startups",
        "manufacturing", "industry", "gst", "tax", "rbi", "sebi",
        "bank", "banking", "trade", "export", "import", "investment",
        "employment", "jobs", "budget", "finance", "market", "shares",
        "stocks", "inflation", "gdp",
    ],
    "Society & Culture": [
        "society", "culture", "heritage", "education", "school",
        "university", "festival", "community", "women", "children",
        "social", "arts", "art", "religion", "museum",
    ],
    "Human & Environment": [
        "environment", "climate", "pollution", "forest", "wildlife",
        "water", "river", "agriculture", "farmer", "farmers", "health",
        "public health", "disaster", "flood", "cyclone", "drought",
        "weather", "heatwave", "rainfall",
    ],
    "Tech & AI": [
        "artificial intelligence", " ai ", "machine learning",
        "generative ai", "technology", "tech", "software", "semiconductor",
        "chip", "robotics", "robot", "cyber", "digital", "internet",
        "data", "cloud", "smartphone", "app",
    ],
    "Good Reads": [
        "explainer", "analysis", "background", "history", "feature",
        "special report", "explained",
    ],
}

# These terms identify an international event. India-related foreign
# affairs stay under In India unless the story is clearly about a
# non-Indian event.
GLOBAL_TERMS = [
    "united states", "usa", "china", "russia", "ukraine", "israel",
    "iran", "gaza", "palestine", "europe", "european union", "nato",
    "united nations", "un", "japan", "south korea", "north korea",
    "australia", "canada", "mexico", "brazil", "france", "germany",
    "italy", "spain", "africa", "middle east", "latin america",
    "uk", "britain", "london", "washington", "beijing", "moscow",
    "kyiv", "tehran", "jerusalem", "international",
]

INDIA_TERMS = [
    "india", "indian", "new delhi", "delhi", "mumbai", "chennai",
    "bengaluru", "bangalore", "hyderabad", "kolkata", "kerala",
    "tamil nadu", "andhra pradesh", "telangana", "karnataka",
    "maharashtra", "gujarat", "rajasthan", "punjab", "uttar pradesh",
    "madhya pradesh", "west bengal", "odisha", "bihar", "assam",
    "government of india", "union government", "parliament of india",
    "supreme court of india", "pm modi", "president of india",
]

# ============================================================
# LEGAL / EDITORIAL FOOTNOTES
# ============================================================

AI_DISCLOSURE = (
    "Snippet24 uses an AI-assisted editorial process to condense and "
    "rephrase source material. The original source remains the authority "
    "for the complete report."
)

COPYRIGHT_NOTICE = (
    "Third-party text, photographs, video, audio, logos and trademarks "
    "remain the property of their respective owners. Snippet24 does not "
    "claim ownership of third-party material and links readers to the "
    "original source."
)

MEDIA_LAW_NOTICE = (
    "News summaries are presented for information and reporting purposes. "
    "Attribution is retained. Publication of third-party material should "
    "be reviewed for applicable Indian media, copyright, privacy and "
    "defamation requirements."
)

AI_LAW_NOTICE = (
    "AI-assisted rewriting is editorial support, not a guarantee of factual "
    "accuracy or legal compliance. Human review remains necessary for "
    "sensitive allegations, legal matters and regulated topics."
)

EDITORIAL_NOTICE = (
    "Claims and allegations are attributed to the identified source or "
    "authority. Snippet24 does not present allegations as independently "
    "verified facts."
)

LEGAL_NOTICE = (
    "Snippet24 provides general news and informational content and does not "
    "provide legal, financial, medical, tax or investment advice."
)

# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def normalize_url(url):
    if not url:
        return ""
    url = str(url).strip()
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ""
        return url
    except Exception:
        return ""

def normalize_title(title):
    value = clean_text(title).lower()
    value = re.sub(r"[^a-z0-9\u0900-\u0dff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def make_id(title, url):
    raw = normalize_title(title) + "|" + url
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

def parse_date(value):
    if not value:
        return datetime.now(timezone.utc)
    value = clean_text(value)
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def find_child_text(element, names):
    wanted = {n.lower() for n in names}
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()
        if tag in wanted:
            return clean_text("".join(child.itertext()))
    return ""

def find_link(element):
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()
        if tag != "link":
            continue
        href = child.attrib.get("href", "")
        if href:
            return normalize_url(href)
        value = clean_text("".join(child.itertext()))
        if value:
            return normalize_url(value)
    return ""

def find_image(element):
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()
        if tag in ("content", "thumbnail", "enclosure"):
            url = child.attrib.get("url", "")
            if url:
                return normalize_url(url)
    return ""

def source_label(source_type):
    return {
        SOURCE_GOVERNMENT: "Government Source",
        SOURCE_PUBLIC: "Public Broadcaster",
        SOURCE_OFFICIAL_TV: "Official TV",
        SOURCE_OFFICIAL_YOUTUBE: "Official YouTube",
    }.get(source_type, "Verified Source")

# ============================================================
# CATEGORY
# ============================================================

def detect_category(title, description, preferred="In India"):
    text = (" " + clean_text(title) + " " + clean_text(description) + " ").lower()

    # GLOBAL IS STRICT: only clearly international events with no India
    # anchor are put in Global.
    has_india = any(term in text for term in INDIA_TERMS)
    has_global = any(term in text for term in GLOBAL_TERMS)

    if has_global and not has_india:
        return "Global"

    if preferred in CATEGORY_ORDER and preferred != "Global":
        preferred_terms = CATEGORY_KEYWORDS.get(preferred, [])
        if any(k.lower() in text for k in preferred_terms):
            return preferred

    best_category = "In India" if has_india else (preferred if preferred in CATEGORY_ORDER else "In India")
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in text)
        if score > best_score:
            best_score = score
            best_category = category

    if has_india and best_category == "Global":
        best_category = "In India"

    return best_category

# ============================================================
# AI HELPERS
# ============================================================

def extract_response_text(data):
    if not isinstance(data, dict):
        return ""
    if data.get("output_text"):
        return str(data["output_text"])

    chunks = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for part in item.get("content", []):
            if isinstance(part, dict) and part.get("text"):
                chunks.append(str(part["text"]))
    return "\n".join(chunks).strip()

def extract_json(text):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None

def fallback_lines(title, description):
    sentences = [
        clean_text(x) for x in
        re.split(r"(?<=[.!?])\s+", clean_text(description))
        if clean_text(x)
    ]
    defaults = [
        "The latest development has been reported by the identified source.",
        "The source has provided information about the reported development.",
        "Readers can consult the original source for complete details.",
    ]
    lines = []
    for i in range(3):
        lines.append((sentences[i][:180] if i < len(sentences) else defaults[i]))
    return lines

def fallback_editorial(title, description, category):
    lines = fallback_lines(title, description)
    summary = clean_text(description)[:500] if clean_text(description) else (
        "The original source has published the latest update. "
        "Readers can consult the original report for complete details."
    )
    return {
        "headline": clean_text(title),
        "snippet_lines": lines,
        "snippet": "\n".join(lines),
        "summary": summary,
        "category": category,
        "importance": "MEDIUM",
        "ai_rewritten": False,
        "translations": {},
    }

def ai_edit_article(title, description, publisher, source_type, category):
    base = fallback_editorial(title, description, category)

    if not OPENAI_API_KEY or not OPENAI_MODEL:
        return base

    source_text = clean_text(description)
    if len(source_text) > 6000:
        source_text = source_text[:6000] + "..."

    system_prompt = """
You are the senior editorial AI for Snippet24, an Indian public-interest
news platform.

Use ONLY the supplied source material as the factual basis.

Do not invent names, numbers, dates, locations, quotations, causes, motives,
statistics, allegations, legal conclusions or facts.

Create:
1. A concise neutral English headline of 8-14 words.
2. EXACTLY 3 short English snippet lines.
3. A short English summary of 35-60 words.
4. One category from the supplied list.
5. Importance: HIGH, MEDIUM or LOW.
6. Translations of the headline, the same three snippet lines and summary
   into Tamil, Telugu, Kannada, Malayalam and Hindi.

Translations must be translations/rephrasings of YOUR English editorial
output, not independent summaries. Preserve names, numbers, dates and
locations. Do not add facts.

Return ONLY JSON with this shape:
{
  "headline": "...",
  "snippet_lines": ["...", "...", "..."],
  "summary": "...",
  "category": "...",
  "importance": "MEDIUM",
  "translations": {
    "ta": {"headline":"...","snippet_lines":["...","...","..."],"summary":"..."},
    "te": {"headline":"...","snippet_lines":["...","...","..."],"summary":"..."},
    "kn": {"headline":"...","snippet_lines":["...","...","..."],"summary":"..."},
    "ml": {"headline":"...","snippet_lines":["...","...","..."],"summary":"..."},
    "hi": {"headline":"...","snippet_lines":["...","...","..."],"summary":"..."}
  }
}
"""

    user_prompt = f"""
SOURCE PUBLISHER: {publisher}
SOURCE TYPE: {source_type}
SUGGESTED CATEGORY: {category}

ORIGINAL HEADLINE:
{clean_text(title)}

ORIGINAL DESCRIPTION:
{source_text}
"""

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": 1600,
    }

    try:
        response = requests.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=AI_TIMEOUT,
        )
        response.raise_for_status()
        result = extract_json(extract_response_text(response.json()))
        if not result:
            raise ValueError("Invalid AI JSON")

        headline = clean_text(result.get("headline") or title)
        lines = result.get("snippet_lines")
        if not isinstance(lines, list):
            lines = []
        lines = [clean_text(x) for x in lines if clean_text(x)]
        while len(lines) < 3:
            lines.append(fallback_lines(title, description)[len(lines)])
        lines = lines[:3]

        summary = clean_text(result.get("summary") or clean_text(description)[:500])
        result_category = clean_text(result.get("category") or category)
        if result_category not in CATEGORY_ORDER:
            result_category = category

        importance = clean_text(result.get("importance") or "MEDIUM").upper()
        if importance not in {"HIGH", "MEDIUM", "LOW"}:
            importance = "MEDIUM"

        translations = result.get("translations")
        if not isinstance(translations, dict):
            translations = {}

        # Validate language objects so the frontend never mixes languages.
        clean_translations = {}
        for lang in ("ta", "te", "kn", "ml", "hi"):
            obj = translations.get(lang)
            if not isinstance(obj, dict):
                continue
            tlang = clean_text(obj.get("headline"))
            tlines = obj.get("snippet_lines")
            tsum = clean_text(obj.get("summary"))
            if not isinstance(tlines, list):
                tlines = []
            tlines = [clean_text(x) for x in tlines if clean_text(x)][:3]
            if tlang and len(tlines) == 3 and tsum:
                clean_translations[lang] = {
                    "headline": tlang,
                    "snippet_lines": tlines,
                    "summary": tsum,
                }

        return {
            "headline": headline,
            "snippet_lines": lines,
            "snippet": "\n".join(lines),
            "summary": summary,
            "category": result_category,
            "importance": importance,
            "ai_rewritten": True,
            "translations": clean_translations,
        }

    except Exception as exc:
        print("  AI ERROR:", exc)
        return base

# ============================================================
# RSS / ATOM
# ============================================================

def parse_feed(xml_text, source):
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print("  XML ERROR:", exc)
        return articles

    items = []
    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()
        if tag in ("item", "entry"):
            items.append(element)

    for item in items[:MAX_ARTICLES_PER_SOURCE]:
        title = find_child_text(item, ["title"])
        description = find_child_text(item, ["description", "summary", "content", "encoded"])
        link = find_link(item)
        if not title or not link:
            continue

        published = find_child_text(item, ["pubdate", "published", "updated", "date", "created"])
        published_at = parse_date(published)
        image_url = find_image(item)

        publisher = clean_text(source["publisher"])
        source_type = source["source_type"]
        preferred_category = source.get("category", "In India")
        category = detect_category(title, description, preferred_category)

        editorial = ai_edit_article(
            title, description, publisher, source_type, category
        )

        article = {
            "id": make_id(editorial["headline"], link),
            "category": editorial["category"],
            "headline": editorial["headline"],
            "snippet": editorial["snippet"],
            "snippet_lines": editorial["snippet_lines"],
            "summary": editorial["summary"],
            "publisher": publisher,
            "source_type": source_type,
            "source_label": source_label(source_type),
            "importance": editorial["importance"],
            "published_at": published_at.isoformat(),
            "source_url": link,
            "original_source_url": link,
            "image_url": image_url,
            "image_usage": "SOURCE_REFERENCE_ONLY",
            "ai_rewritten": editorial["ai_rewritten"],
            "ai_disclosure": True,
            "ai_disclosure_text": AI_DISCLOSURE,
            "attribution_required": True,
            "copyright_status": "THIRD_PARTY_SOURCE",
            "copyright_notice": COPYRIGHT_NOTICE,
            "editorial_notice": EDITORIAL_NOTICE,
            "legal_notice": LEGAL_NOTICE,
            "media_law_notice": MEDIA_LAW_NOTICE,
            "ai_law_notice": AI_LAW_NOTICE,
            "correction_available": True,
            "grievance_available": True,
            "translations": editorial.get("translations", {}),
        }
        articles.append(article)

    return articles

def fetch_url(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text

def fetch_rss_source(source):
    try:
        print("Fetching:", source["publisher"])
        return parse_feed(fetch_url(source["url"]), source)
    except Exception as exc:
        print("  FAILED:", exc)
        return []

# ============================================================
# OFFICIAL HTML SOURCES
# ============================================================

def parse_official_html(text, source):
    soup = BeautifulSoup(text, "html.parser")
    articles = []
    seen = set()

    # Official pages can change layout. We deliberately collect only
    # links from the official host and turn the visible title into source
    # material. We do NOT copy full page text.
    base = source["base_url"]

    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        href = normalize_url(urljoin(base, a["href"]))

        if not title or len(title) < 25 or len(title) > 260:
            continue
        if not href or not href.startswith(base):
            continue

        key = href.lower()
        if key in seen:
            continue
        seen.add(key)

        # Skip menus, policy pages, navigation and generic links.
        blocked = (
            "about", "contact", "privacy", "copyright", "disclaimer",
            "login", "archive", "search", "category", "feed", "sitemap"
        )
        if any(x in href.lower() for x in blocked):
            continue

        category = detect_category(title, "", source.get("category", "In India"))
        editorial = ai_edit_article(
            title, title, source["publisher"],
            source["source_type"], category
        )

        articles.append({
            "id": make_id(editorial["headline"], href),
            "category": editorial["category"],
            "headline": editorial["headline"],
            "snippet": editorial["snippet"],
            "snippet_lines": editorial["snippet_lines"],
            "summary": editorial["summary"],
            "publisher": source["publisher"],
            "source_type": source["source_type"],
            "source_label": source_label(source["source_type"]),
            "importance": editorial["importance"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "source_url": href,
            "original_source_url": href,
            "image_url": "",
            "image_usage": "NONE",
            "ai_rewritten": editorial["ai_rewritten"],
            "ai_disclosure": True,
            "ai_disclosure_text": AI_DISCLOSURE,
            "attribution_required": True,
            "copyright_status": "THIRD_PARTY_SOURCE",
            "copyright_notice": COPYRIGHT_NOTICE,
            "editorial_notice": EDITORIAL_NOTICE,
            "legal_notice": LEGAL_NOTICE,
            "media_law_notice": MEDIA_LAW_NOTICE,
            "ai_law_notice": AI_LAW_NOTICE,
            "correction_available": True,
            "grievance_available": True,
            "translations": editorial.get("translations", {}),
        })

        if len(articles) >= MAX_ARTICLES_PER_SOURCE:
            break

    return articles

def fetch_html_source(source):
    try:
        print("Fetching official page:", source["publisher"])
        return parse_official_html(fetch_url(source["url"]), source)
    except Exception as exc:
        print("  HTML FAILED:", exc)
        return []

# ============================================================
# YOUTUBE
# ============================================================

def youtube_feed_url(channel_id):
    return "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id

def fetch_youtube_source(source):
    channel_id = clean_text(source.get("channel_id"))
    if not channel_id:
        return []

    config = {
        "publisher": clean_text(source.get("publisher", "Official YouTube")),
        "source_type": SOURCE_OFFICIAL_YOUTUBE,
        "category": source.get("category", "In India"),
        "url": youtube_feed_url(channel_id),
    }
    return fetch_rss_source(config)

# ============================================================
# EXISTING DATA — KEEP ONLY APPROVED SOURCE TYPES
# ============================================================

def load_existing_articles():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        articles = data.get("articles", []) if isinstance(data, dict) else []
        if not isinstance(articles, list):
            return []

        clean = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            if article.get("source_type") not in ALLOWED_SOURCE_TYPES:
                continue
            if not normalize_url(article.get("source_url", "")):
                continue
            clean.append(article)
        return clean
    except Exception:
        return []

# ============================================================
# SORT / DEDUP
# ============================================================

def article_priority(article):
    score = SOURCE_PRIORITY.get(article.get("source_type"), 0)
    score += {"HIGH": 30, "MEDIUM": 15, "LOW": 0}.get(
        article.get("importance", "MEDIUM"), 15
    )
    if article.get("category") == "In India":
        score += 10
    return score

def article_timestamp(article):
    try:
        return datetime.fromisoformat(
            article.get("published_at", "").replace("Z", "+00:00")
        )
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)

def deduplicate(articles):
    by_url = {}
    for article in articles:
        if article.get("source_type") not in ALLOWED_SOURCE_TYPES:
            continue
        url = normalize_url(article.get("source_url", ""))
        if not url:
            continue
        key = url.lower()
        existing = by_url.get(key)
        if not existing or article_priority(article) > article_priority(existing):
            by_url[key] = article

    by_title = {}
    for article in by_url.values():
        key = normalize_title(article.get("headline", ""))
        if not key:
            continue
        existing = by_title.get(key)
        if not existing or article_priority(article) > article_priority(existing):
            by_title[key] = article

    return list(by_title.values())

def sort_articles(articles):
    return sorted(
        articles,
        key=lambda a: (
            article_priority(a),
            article_timestamp(a).timestamp()
        ),
        reverse=True,
    )

def category_counts(articles):
    counts = {category: 0 for category in CATEGORY_ORDER}
    for article in articles:
        category = article.get("category", "In India")
        if category not in counts:
            category = "In India"
        counts[category] += 1
    return counts

def source_counts(articles):
    counts = {}
    for article in articles:
        source_type = article.get("source_type", "UNKNOWN")
        counts[source_type] = counts.get(source_type, 0) + 1
    return counts

# ============================================================
# BUILD
# ============================================================

def build_feed():
    print("=" * 72)
    print("SNIPPET24 — APPROVED SOURCE CURATOR")
    print("Government + Public Broadcaster + Official TV + Verified YouTube")
    print("=" * 72)

    if not OPENAI_API_KEY or not OPENAI_MODEL:
        print("WARNING: OPENAI_API_KEY and/or OPENAI_MODEL is not configured.")
        print("English fallback mode will be used; translations will be unavailable.")

    previous = load_existing_articles()
    fresh = []
    successful = 0
    failed = 0

    for source in RSS_SOURCES:
        stories = fetch_rss_source(source)
        if stories:
            fresh.extend(stories)
            successful += 1
        else:
            failed += 1
        time.sleep(REQUEST_DELAY)

    for source in HTML_SOURCES:
        stories = fetch_html_source(source)
        if stories:
            fresh.extend(stories)
            successful += 1
        else:
            failed += 1
        time.sleep(REQUEST_DELAY)

    for source in YOUTUBE_CHANNELS:
        stories = fetch_youtube_source(source)
        if stories:
            fresh.extend(stories)
            successful += 1
        else:
            failed += 1
        time.sleep(REQUEST_DELAY)

    combined = deduplicate(fresh + previous)
    final_articles = sort_articles(combined)[:MAX_FINAL_ARTICLES]

    output = {
        "site": SITE_NAME,
        "site_url": SITE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(final_articles),
        "editorial_engine": "Snippet24 AI Editorial",
        "source_policy": (
            "Only government, public broadcaster, official TV and verified "
            "official YouTube sources are accepted. Private/unknown sources "
            "are rejected."
        ),
        "global_policy": (
            "Global contains clearly international events. India-related "
            "foreign affairs remain under In India."
        ),
        "ai_policy": (
            "AI-assisted rewriting produces a headline, exactly three "
            "snippet lines, a short summary and controlled translations."
        ),
        "copyright_policy": COPYRIGHT_NOTICE,
        "legal_notice": LEGAL_NOTICE,
        "editorial_notice": EDITORIAL_NOTICE,
        "media_law_notice": MEDIA_LAW_NOTICE,
        "ai_law_notice": AI_LAW_NOTICE,
        "ai_disclosure": AI_DISCLOSURE,
        "grievance": True,
        "corrections": True,
        "categories": category_counts(final_articles),
        "source_types": source_counts(final_articles),
        "successful_sources": successful,
        "failed_sources": failed,
        "articles": final_articles,
    }

    temp = OUTPUT_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    os.replace(temp, OUTPUT_FILE)

    print("Fresh articles:", len(fresh))
    print("Final articles:", len(final_articles))
    print("Approved source types:", source_counts(final_articles))
    print("articles.json written.")
    return 0

if __name__ == "__main__":
    raise SystemExit(build_feed())
