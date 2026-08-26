import json
import hashlib
import html
import re
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


# ============================================================
# SNIPPET24 NEWS CURATOR
# ============================================================
# Features:
# - No feedparser dependency
# - Reads sources.json
# - Fetches RSS feeds
# - Removes duplicates
# - Creates one MASTER "articles" array
# - Creates category arrays
# - FIFO storage
# - 50 minimum target per category
# - 100 maximum per category
# - Keeps newest articles
# - Works even when some RSS feeds fail
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

CATEGORIES = [
    "India",
    "World",
    "States",
    "Tech & AI",
    "Business",
    "Lifestyle",
]

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100


# ------------------------------------------------------------
# HTTP
# ------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/1.0; "
    "+https://snippet24.in)"
)

SSL_CONTEXT = ssl.create_default_context()


def fetch_url(url, timeout=20):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, application/xml, "
                "text/xml, application/atom+xml, */*"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=SSL_CONTEXT,
        ) as response:
            return response.read()

    except Exception as exc:
        print(f"WARNING: failed to fetch {url}")
        print(f"         {exc}")
        return None


# ------------------------------------------------------------
# TEXT CLEANING
# ------------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<script.*?</script>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    value = re.sub(
        r"<style.*?</style>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def shorten(text, maximum=500):
    text = clean_text(text)

    if len(text) <= maximum:
        return text

    return text[:maximum].rsplit(" ", 1)[0] + "..."


# ------------------------------------------------------------
# DATE
# ------------------------------------------------------------

def parse_date(value):
    if not value:
        return datetime.now(timezone.utc)

    value = str(value).strip()

    # RFC date
    try:
        date = parsedate_to_datetime(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc)

    except Exception:
        pass

    # ISO date
    try:
        iso = value.replace("Z", "+00:00")
        date = datetime.fromisoformat(iso)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc)

    except Exception:
        return datetime.now(timezone.utc)


def iso_date(value):
    return parse_date(value).isoformat()


# ------------------------------------------------------------
# XML HELPERS
# ------------------------------------------------------------

def strip_namespace(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def child_text(element, names):
    names = {name.lower() for name in names}

    for child in list(element):
        tag = strip_namespace(child.tag).lower()

        if tag in names:
            if child.text:
                return child.text.strip()

            # Some Atom elements contain nested content
            return "".join(child.itertext()).strip()

    return ""


def find_link(element):
    # RSS <link>
    for child in list(element):
        tag = strip_namespace(child.tag).lower()

        if tag == "link":
            href = child.attrib.get("href")

            if href:
                return href.strip()

            if child.text:
                return child.text.strip()

    # Atom alternative
    for child in list(element):
        tag = strip_namespace(child.tag).lower()

        if tag == "link":
            href = child.attrib.get("href")

            if href:
                return href.strip()

    return ""


# ------------------------------------------------------------
# RSS / ATOM PARSER
# ------------------------------------------------------------

def parse_feed(xml_data):
    articles = []

    if not xml_data:
        return articles

    try:
        root = ET.fromstring(xml_data)
    except Exception as exc:
        print(f"WARNING: invalid XML feed: {exc}")
        return articles

    root_name = strip_namespace(root.tag).lower()

    # --------------------------------------------------------
    # RSS
    # --------------------------------------------------------

    if root_name in ("rss", "rdf", "rdf:rdf"):

        for item in root.iter():

            tag = strip_namespace(item.tag).lower()

            if tag != "item":
                continue

            title = child_text(
                item,
                ["title"],
            )

            description = child_text(
                item,
                [
                    "description",
                    "summary",
                    "content",
                ],
            )

            link = find_link(item)

            published = child_text(
                item,
                [
                    "pubdate",
                    "published",
                    "updated",
                    "date",
                ],
            )

            guid = child_text(
                item,
                [
                    "guid",
                    "id",
                ],
            )

            source = child_text(
                item,
                ["source"],
            )

            articles.append(
                {
                    "title": clean_text(title),
                    "description": shorten(description),
                    "url": link.strip(),
                    "published_at": iso_date(published),
                    "guid": clean_text(guid),
                    "source": clean_text(source),
                }
            )

    # --------------------------------------------------------
    # ATOM
    # --------------------------------------------------------

    elif root_name == "feed":

        for entry in root.iter():

            tag = strip_namespace(entry.tag).lower()

            if tag != "entry":
                continue

            title = child_text(
                entry,
                ["title"],
            )

            description = child_text(
                entry,
                [
                    "summary",
                    "content",
                    "description",
                ],
            )

            link = find_link(entry)

            published = child_text(
                entry,
                [
                    "published",
                    "updated",
                ],
            )

            guid = child_text(
                entry,
                ["id"],
            )

            source = child_text(
                entry,
                ["source"],
            )

            articles.append(
                {
                    "title": clean_text(title),
                    "description": shorten(description),
                    "url": link.strip(),
                    "published_at": iso_date(published),
                    "guid": clean_text(guid),
                    "source": clean_text(source),
                }
            )

    return articles


# ------------------------------------------------------------
# SOURCE NAME
# ------------------------------------------------------------

def source_name(article, source_config):
    source = article.get("source", "").strip()

    if source:
        return source

    return (
        source_config.get("name")
        or source_config.get("website")
        or "Unknown source"
    )


# ------------------------------------------------------------
# CATEGORY NORMALIZATION
# ------------------------------------------------------------

def normalize_category(value):
    if not value:
        return "World"

    value = str(value).strip()

    aliases = {
        "India": "India",
        "Indian": "India",
        "National": "India",

        "World": "World",
        "International": "World",

        "States": "States",
        "State": "States",

        "Tech": "Tech & AI",
        "Technology": "Tech & AI",
        "AI": "Tech & AI",
        "Tech & AI": "Tech & AI",

        "Business": "Business",
        "Finance": "Business",
        "Economy": "Business",

        "Lifestyle": "Lifestyle",
        "Life": "Lifestyle",
        "Entertainment": "Lifestyle",
        "Health": "Lifestyle",
        "Sports": "Lifestyle",
    }

    return aliases.get(value, "World")


# ------------------------------------------------------------
# ID
# ------------------------------------------------------------

def article_id(article):
    raw = (
        article.get("guid")
        or article.get("url")
        or (
            article.get("title", "")
            + "|"
            + article.get("source", "")
        )
    )

    return hashlib.sha256(
        raw.encode("utf-8", errors="ignore")
    ).hexdigest()[:24]


# ------------------------------------------------------------
# DUPLICATE DETECTION
# ------------------------------------------------------------

def normalize_title(title):
    title = clean_text(title).lower()

    title = re.sub(
        r"[^a-z0-9\u0900-\u097f\u0b80-\u0bff]+",
        " ",
        title,
    )

    title = re.sub(r"\s+", " ", title)

    return title.strip()


def is_duplicate(article, seen_ids, seen_titles, seen_urls):

    aid = article.get("id", "")

    title = normalize_title(
        article.get("title", "")
    )

    url = article.get("url", "").strip()

    if aid and aid in seen_ids:
        return True

    if title and title in seen_titles:
        return True

    if url and url in seen_urls:
        return True

    if aid:
        seen_ids.add(aid)

    if title:
       