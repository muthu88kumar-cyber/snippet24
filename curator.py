import os
import re
import json
import html
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

CATEGORIES = [
    "World",
    "India",
    "Business",
    "Technology",
    "Lifestyle"
]

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

POLLINATIONS_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()

TEXT_MODEL = os.getenv(
    "POLLINATIONS_TEXT_MODEL",
    "openai"
)

IMAGE_MODEL = os.getenv(
    "POLLINATIONS_IMAGE_MODEL",
    "zimage"
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; Snippet24NewsBot/2.0; "
    "+https://snippet24.in)"
)

HEADERS = {
    "User-Agent": USER_AGENT
}


# ------------------------------------------------------------
# BASIC CLEANING
# ------------------------------------------------------------

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    soup = BeautifulSoup(value, "html.parser")
    value = soup.get_text(" ", strip=True)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_text(value):
    value = clean_text(value).lower()

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:24]


# ------------------------------------------------------------
# DATE
# ------------------------------------------------------------

def parse_date(entry):

    values = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created")
    ]

    for value in values:

        if not value:
            continue

        try:
            dt = parsedate_to_datetime(value)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).isoformat()

        except Exception:
            pass

    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------
# PUBLISHER
# ------------------------------------------------------------

def get_publisher(entry, fallback):

    publisher = entry.get("source")

    if isinstance(publisher, dict):
        publisher = publisher.get("title")

    if not publisher:
        publisher = entry.get("publisher")

    if not publisher:
        publisher = entry.get("author")

    publisher = clean_text(publisher)

    return publisher or clean_text(fallback) or "Original source"


# ------------------------------------------------------------
# URL
# ------------------------------------------------------------

def get_url(entry):

    if entry.get("link"):
        return entry["link"].strip()

    for link in entry.get("links", []):

        href = link.get("href")

        if href:
            return href.strip()

    return ""


# ------------------------------------------------------------
# RSS DESCRIPTION
# ------------------------------------------------------------

def get_description(entry):

    values = [
        entry.get("summary"),
        entry.get("description")
    ]

    content = entry.get("content")

    if content:
        for item in content:

            if isinstance(item, dict):
                values.append(item.get("value", ""))

    for value in values:

        value = clean_text(value)

        if value:
            return value

    return ""


# ------------------------------------------------------------
# CLEAN RSS HEADLINE
# ------------------------------------------------------------

def clean_original_headline(title, publisher):

    title = clean_text(title)

    if not title:
        return ""

    publisher = clean_text(publisher)

    patterns = [
        r"\s*\|\s*" + re.escape(publisher) + r"\s*$",
        r"\s*-\s*" + re.escape(publisher) + r"\s*$"
    ]

    for pattern in patterns:

        title = re.sub(
            pattern,
            "",
            title,
            flags=re.IGNORECASE
        )

    # Remove common publisher suffixes.
    title = re.sub(
        r"\s*\|\s*(Hindustan Times|Business Standard|Firstpost|"
        r"Reuters|NDTV|The Hindu|Indian Express|News18|"
        r"Times of India|Moneycontrol)\s*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    return title.strip(" -|")


# ------------------------------------------------------------
# ORIGINAL ARTICLE EXTRACTION
# ------------------------------------------------------------

def fetch_original_article(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            include_links=False,
            favor_precision=True
        )

        if extracted:

            extracted = clean_text(extracted)

            # Prevent extremely large AI requests.
            return extracted[:18000]

    except Exception as exc:

        print(
            f"Article extraction failed: "
            f"{url} -> {exc}"
        )

    return ""


# ------------------------------------------------------------
# AI TEXT GENERATION
# ------------------------------------------------------------

def ai_text(prompt):

    if not POLLINATIONS_KEY:

        print(
            "WARNING: POLLINATIONS_API_KEY is missing. "
            "Using fallback text."
        )

        return ""

    endpoint = "https://gen.pollinations.ai/text"

    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the editorial AI for Snippet24. "
                    "You must be factual, concise and neutral. "
                    "Never invent facts. "
                    "Never add information that is not supported "
                    "by the supplied source material."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    try:

        response = requests.post(
            endpoint,
            headers={
                "Authorization": (
                    f"Bearer {POLLINATIONS_KEY}"
                ),
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            return ""

        message = choices[0].get("message", {})

        return clean_text(
            message.get("content", "")
        )

    except Exception as exc:

        print(
            f"AI text generation failed: {exc}"
        )

        return ""


# ------------------------------------------------------------
# AI HEADLINE + SUMMARY
# ------------------------------------------------------------

def generate_editorial_content(
    original_title,
    source_description,
    article_text,
    publisher
):

    source_material = article_text or source_description

    if not source_material:

        source_material = original_title

    prompt = f"""
Create the Snippet24 version of this news story.

ORIGINAL PUBLISHER:
{publisher}

ORIGINAL HEADLINE:
{original_title}

SOURCE MATERIAL:
{source_material}

Return EXACTLY this format:

HEADLINE:
<one clear original headline>

SUMMARY:
<2 or 3 short factual sentences>

Rules:

- Rephrase the headline instead of copying it.
- Do not use the publisher name in the headline.
- Do not copy the RSS description.
- The headline must tell readers what actually happened.
- The summary must explain the important facts.
- Use simple, natural English.
- Keep the summary approximately 35-70 words.
- Preserve names, places, dates and numbers when important.
- Never invent facts.
- Do not speculate.
- Do not add opinions.
- Do not sensationalize.
- Do not say "according to the article" repeatedly.
- Do not mention that AI was used.
"""

    result = ai_text(prompt)

    if not result:
        return (
            original_title,
            fallback_summary(
                original_title,
                source_description
            )
        )

    headline_match = re.search(
        r"HEADLINE:\s*(.*?)(?:\n|$)",
        result,
        flags=re.IGNORECASE
    )

    summary_match = re.search(
        r"SUMMARY:\s*(.*)",
        result,
        flags=re.IGNORECASE | re.DOTALL
    )

    headline = (
        headline_match.group(1).strip()
        if headline_match
        else original_title
    )

    summary = (
        summary_match.group(1).strip()
        if summary_match
        else ""
    )

    headline = clean_text(headline)
    summary = clean_text(summary)

    if not headline:
        headline = original_title

    if not summary:
        summary = fallback_summary(
            original_title,
            source_description
        )

    return headline, summary


# ------------------------------------------------------------
# FALLBACK SUMMARY
# ------------------------------------------------------------

def fallback_summary(title, description):

    description = clean_text(description)

    if not description:
        return (
            "This story has been reported by the original "
            "publication. Read the original article for the "
            "latest details and full context."
        )

    title_words = set(
        normalize_text(title).split()
    )

    description_words = set(
        normalize_text(description).split()
    )

    overlap = len(
        title_words.intersection(description_words)
    )

    ratio = (
        overlap / max(len(title_words), 1)
    )

    # RSS description is basically the headline.
    if ratio > 0.75:

        return (
            "The original report contains the latest "
            "developments on this story. Read the original "
            "article for the full details and context."
        )

    sentences = re.split(
        r"(?<=[.!?])\s+",
        description
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    summary = " ".join(sentences[:3])

    if len(summary) > 500:

        summary = (
            summary[:497]
            .rsplit(" ", 1)[0]
            + "..."
        )

    return summary


# ------------------------------------------------------------
# AI IMAGE
# ------------------------------------------------------------

def make_image_prompt(
    headline,
    summary,
    category
):

    return (
        "Create a high-quality editorial news illustration "
        "for a digital news website. "
        f"Category: {category}. "
        f"Story: {headline}. "
        f"Context: {summary}. "
        "Create a visually relevant scene that represents "
        "the subject of the story. "
        "Modern professional journalism aesthetic. "
        "Landscape 16:9 composition. "
        "No text. No headlines. No logos. "
        "Do not create a fake photograph of a real person. "
        "Do not make the image look like documentary evidence. "
        "It must clearly function as an editorial illustration."
    )


def generate_image_url(
    headline,
    summary,
    category,
    article_id
):

    prompt = make_image_prompt(
        headline,
        summary,
        category
    )

    encoded_prompt = quote(
        prompt,
        safe=""
    )

    seed = int(
        hashlib.sha256(
            article_id.encode("utf-8")
        ).hexdigest()[:8],
        16
    )

    url = (
        "https://gen.pollinations.ai/image/"
        f"{encoded_prompt}"
        f"?model={quote(IMAGE_MODEL)}"
        f"&width=1200"
        f"&height=675"
        f"&seed={seed}"
        f"&safe=true"
    )

    # Important:
    # We don't put the secret API key into articles.json.
    #
    # The website can use this URL only if the selected
    # image endpoint permits the request without the key.
    #
    # If your Pollinations account requires authentication
    # for image generation, use a server-side image proxy
    # rather than exposing the secret key in index.html.

    return url


# ------------------------------------------------------------
# CATEGORY
# ------------------------------------------------------------

def detect_category(
    title,
    summary,
    source_category=""
):

    text = normalize_text(
        f"{title} {summary} {source_category}"
    )

    technology = [
        "technology",
        "technology",
        "artificial intelligence",
        " ai ",
        "software",
        "cybersecurity",
        "cyber attack",
        "semiconductor",
        "chip",
        "iphone",
        "android",
        "google",
        "microsoft",
        "openai",
        "robot"
    ]

    business = [
        "business",
        "economy",
        "economic",
        "market",
        "markets",
        "stock",
        "stocks",
        "investment",
        "investor",
        "company",
        "companies",
        "bank",
        "banking",
        "finance",
        "financial",
        "trade",
        "revenue",
        "profit",
        "ipo",
        "tariff"
    ]

    lifestyle = [
        "lifestyle",
        "travel",
        "food",
        "fashion",
        "culture",
        "entertainment",
        "movie",
        "music",
        "celebrity",
        "wellness",
        "health"
    ]

    india = [
        "india",
        "indian",
        "new delhi",
        "mumbai",
        "chennai",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "kolkata",
        "modi",
        "sitharaman",
        "parliament of india",
        "supreme court of india"
    ]

    if any(word in text for word in technology):
        return "Technology"

    if any(word in text for word in business):
        return "Business"

    if any(word in text for word in lifestyle):
        return "Lifestyle"

    if any(word in text for word in india):
        return "India"

    return "World"


# ------------------------------------------------------------
# SOURCES
# ------------------------------------------------------------

def load_sources():

    if not SOURCES_FILE.exists():

        print("ERROR: sources.json not found")

        return []

    try:

        with open(
            SOURCES_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get("sources", [])

    except Exception as exc:

        print(
            f"ERROR loading sources.json: {exc}"
        )

    return []


# ------------------------------------------------------------
# ARTICLES
# ------------------------------------------------------------

def load_articles():

    if not ARTICLES_FILE.exists():

        return {
            "version": 3,
            "updated_at": "",
            "categories": {
                category: []
                for category in CATEGORIES
            }
        }

    try:

        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        data.setdefault(
            "categories",
            {}
        )

        for category in CATEGORIES:

            data["categories"].setdefault(
                category,
                []
            )

        return data

    except Exception as exc:

        print(
            f"ERROR loading articles.json: {exc}"
        )

        return {
            "version": 3,
            "updated_at": "",
            "categories": {
                category: []
                for category in CATEGORIES
            }
        }


# ------------------------------------------------------------
# RSS FETCH
# ------------------------------------------------------------

def fetch_feed(source):

    if isinstance(source, str):

        feed_url = source
        source_name = "Original source"
        source_category = ""

    else:

        feed_url = (
            source.get("url")
            or source.get("rss")
            or source.get("feed")
            or ""
        )

        source_name = (
            source.get("name")
            or source.get("publisher")
            or source.get("title")
            or "Original source"
        )

        source_category = (
            source.get("category")
            or ""
        )

    if not feed_url:
        return []

    print(
        f"Fetching {source_name}"
    )

    try:

        response = requests.get(
            feed_url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        results = []

        for entry in feed.entries:

            publisher = get_publisher(
                entry,
                source_name
            )

            rss_title = clean_original_headline(
                entry.get("title", ""),
                publisher
            )

            url = get_url(entry)

            if not rss_title or not url:
                continue

            rss_description = get_description(
                entry
            )

            print(
                f"Processing: {rss_title}"
            )

            # Fetch the actual source article.
            article_text = fetch_original_article(
                url
            )

            # AI rephrases headline + creates summary.
            headline, summary = (
                generate_editorial_content(
                    rss_title,
                    rss_description,
                    article_text,
                    publisher
                )
            )

            category = detect_category(
                headline,
                summary,
                source_category
            )

            article_id = make_id(
                headline,
                url
            )

            image_url = generate_image_url(
                headline,
                summary,
                category,
                article_id
            )

            article = {
                "id": article_id,

                "category": category,

                "headline": headline,

                "summary": summary,

                "publisher": publisher,

                "published_at": parse_date(
                    entry
                ),

                "url": url,

                "language": "en",

                "image": {
                    "url": image_url,
                    "type": "ai_generated",
                    "label": "AI-generated illustration"
                }
            }

            results.append(article)

            # Don't hammer sources / AI service.
            time.sleep(0.5)

        return results

    except Exception as exc:

        print(
            f"ERROR fetching {source_name}: {exc}"
        )

        return []


# ------------------------------------------------------------
# MERGE
# ------------------------------------------------------------

def add_articles(
    data,
    new_articles
):

    existing_ids = set()

    for category in CATEGORIES:

        for article in data[
            "categories"
        ].get(category, []):

            article_id = article.get("id")

            if article_id:
                existing_ids.add(article_id)

    added = 0

    for article in new_articles:

        article_id = article["id"]

        if article_id in existing_ids:
            continue

        category = article.get(
            "category",
            "World"
        )

        if category not in CATEGORIES:
            category = "World"

        article["category"] = category

        data["categories"][
            category
        ].append(article)

        existing_ids.add(article_id)

        added += 1

    return added


# ------------------------------------------------------------
# FIFO
# ------------------------------------------------------------

def sort_and_fifo(data):

    for category in CATEGORIES:

        articles = data[
            "categories"
        ].get(category, [])

        articles.sort(
            key=lambda item:
                item.get(
                    "published_at",
                    ""
                ),
            reverse=True
        )

        data["categories"][
            category
        ] = articles[
            :MAXIMUM_PER_CATEGORY
        ]


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

def save_articles(data):

    data["version"] = 3

    data["updated_at"] = (
        datetime.now(timezone.utc)
        .isoformat()
    )

    temporary = (
        ARTICLES_FILE.with_suffix(".tmp")
    )

    with open(
        temporary,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temporary.replace(
        ARTICLES_FILE
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("=" * 60)
    print("SNIPPET24 AI NEWS CURATOR")
    print("=" * 60)

    if not POLLINATIONS_KEY:

        print()
        print(
            "WARNING: POLLINATIONS_API_KEY is not set."
        )
        print(
            "AI headline/summary generation will "
            "use fallback mode."
        )
        print()

    sources = load_sources()

    if not sources:

        print(
            "ERROR: No RSS sources found."
        )

        return 1

    data = load_articles()

    all_articles = []

    for source in sources:

        articles = fetch_feed(
            source
        )

        all_articles.extend(
            articles
        )

    print()
    print(
        f"Fetched: {len(all_articles)}"
    )

    added = add_articles(
        data,
        all_articles
    )

    print(
        f"Added: {added}"
    )

    sort_and_fifo(data)

    save_articles(data)

    print()
    print("=" * 60)
    print("CATEGORY COUNTS")
    print("=" * 60)

    total = 0

    for category in CATEGORIES:

        count = len(
            data["categories"][
                category
            ]
        )

        total += count

        print(
            f"{category}: {count}"
        )

    print()
    print(
        f"TOTAL: {total}"
    )

    if total == 0:

        print(
            "ERROR: World has only 0 articles"
        )

        return 1

    print(
        f"Saved: {ARTICLES_FILE}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )