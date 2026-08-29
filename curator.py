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

OUTPUT_FILE = "articles.json"
TARGET_STORIES = 100
MINIMUM_STORIES = 50
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.25

HEADERS = {
    "User-Agent": "Snippet24-News/2.0 (+https://snippet24.in)"
}

CATEGORY_ORDER = [
    "World", "India", "Business", "Technology & AI",
    "Sports", "Entertainment", "Lifestyle"
]

RSS_SOURCES = {
    "World": [
        ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("Guardian World", "https://www.theguardian.com/world/rss"),
    ],
    "India": [
        ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
        ("Indian Express", "https://indianexpress.com/section/india/feed/"),
        ("NDTV India", "https://feeds.feedburner.com/ndtvnews-india-news"),
    ],
    "Business": [
        ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml"),
        ("Business Standard", "https://www.business-standard.com/rss/home_page_top_stories.rss"),
        ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
    ],
    "Technology & AI": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "Lifestyle": [
        ("Hindustan Times Lifestyle", "https://www.hindustantimes.com/feeds/rss/lifestyle/rssfeed.xml"),
        ("Guardian Lifestyle", "https://www.theguardian.com/lifeandstyle/rss"),
    ],
    "Sports": [
        ("ESPN", "https://www.espn.com/espn/rss/news"),
        ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
    ],
    "Entertainment": [
        ("Variety", "https://variety.com/feed/"),
        ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/"),
    ],
}

def clean_text(value):
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()

def normalize_category(category):
    value = clean_text(category).lower()
    if value in {"technology", "tech", "technology & ai", "ai", "artificial intelligence"}:
        return "Technology & AI"
    for known in CATEGORY_ORDER:
        if value == known.lower():
            return known
    return "World"

def normalize_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        return url.strip() if parsed.scheme in ("http", "https") else ""
    except Exception:
        return ""

def normalize_title(title):
    title = clean_text(title).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title)).strip()

def make_id(category, title, url):
    raw = f"{category}|{normalize_title(title)}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

def remove_publisher_from_title(title, publisher):
    title = clean_text(title)
    publishers = [
        publisher, "Hindustan Times", "Business Standard", "Firstpost",
        "Moneycontrol", "News18", "NDTV", "The Hindu", "Indian Express",
        "BBC", "BBC News", "Reuters", "CNN", "CNBC", "TechCrunch",
        "The Verge", "Variety", "ESPN", "Hollywood Reporter"
    ]
    for name in publishers:
        if name:
            title = re.sub(
                r"\s*(?:\||-|\u2013|\u2014)\s*" + re.escape(name) + r"\s*$",
                "", title, flags=re.IGNORECASE
            )
    return title.strip(" -|\u2013\u2014")

def make_summary(title, description):
    summary = clean_text(description)
    if title:
        summary = re.sub(re.escape(clean_text(title)), "", summary, flags=re.IGNORECASE)
    summary = re.sub(
        r"^(read more|latest updates|follow live|breaking news)\s*[:\-]?\s*",
        "", summary, flags=re.IGNORECASE
    )
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "..."
    return summary or (
        "The latest developments are being reported by the original publisher. "
        "Read the original report for the full details."
    )

def parse_date(value):
    if not value:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(value.strip()).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def child_text(element, names):
    names = {n.lower() for n in names}
    for child in list(element):
        if child.tag.split("}")[-1].lower() in names:
            return clean_text("".join(child.itertext()))
    return ""

def find_link(element):
    for child in list(element):
        if child.tag.split("}")[-1].lower() != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return normalize_url(href)
        text = clean_text("".join(child.itertext()))
        if text:
            return normalize_url(text)
    return ""

def make_ai_image(title, category):
    prompt = (
        "Professional editorial news illustration for a modern digital news publication. "
        f"Category: {category}. Story: {title}. "
        "Create a realistic, relevant, tasteful journalistic visual. "
        "No text, no letters, no words, no logos, no watermark."
    )
    seed = int(hashlib.md5((category + "|" + title).encode()).hexdigest()[:8], 16)
    return (
        "https://image.pollinations.ai/prompt/" + quote(prompt, safe="") +
        f"?width=1200&height=675&nologo=true&seed={seed}"
    )

def parse_feed(xml_text, publisher, category):
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"XML error from {publisher}: {exc}")
        return articles

    for item in root.iter():
        if item.tag.split("}")[-1].lower() not in ("item", "entry"):
            continue

        title = child_text(item, ["title"])
        if not title:
            continue

        title = remove_publisher_from_title(title, publisher)
        if len(title) < 8:
            continue

        description = child_text(item, ["description", "summary", "content", "encoded"])
        link = find_link(item)
        if not link:
            continue

        published = child_text(item, ["pubdate", "published", "updated", "date", "created"])
        cat = normalize_category(category)

        articles.append({
            "id": make_id(cat, title, link),
            "category": cat,
            "headline": title,
            "summary": make_summary(title, description),
            "publisher": clean_text(publisher),
            "published_at": parse_date(published).isoformat(),
            "source_url": link,
            "image_url": make_ai_image(title, cat),
            "image_type": "ai_generated"
        })
    return articles

def fetch_source(publisher, url, category):
    print(f"Fetching: {publisher}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        articles = parse_feed(response.text, publisher, category)
        print(f"  -> {len(articles)} stories")
        return articles
    except Exception as exc:
        print(f"  -> FAILED: {publisher}: {exc}")
        return []

def load_existing_articles():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        articles = data.get("articles", [])
        return [a for a in articles if isinstance(a, dict) and
                clean_text(a.get("headline")) and normalize_url(a.get("source_url"))]
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"Could not read previous articles.json: {exc}")
        return []

def deduplicate(articles):
    by_url = {}
    for article in articles:
        title = clean_text(article.get("headline"))
        url = normalize_url(article.get("source_url"))
        if not title or not url:
            continue
        key = url.lower()
        if key not in by_url or article.get("published_at", "") > by_url[key].get("published_at", ""):
            by_url[key] = article

    by_title = {}
    for article in by_url.values():
        key = normalize_title(article.get("headline", ""))
        if key and key not in by_title:
            by_title[key] = article
    return list(by_title.values())

def timestamp(article):
    try:
        return datetime.fromisoformat(article.get("published_at", "").replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)

def build_feed():
    print("=" * 65)
    print("SNIPPET24 NEWS CURATOR")
    print("=" * 65)

    previous = load_existing_articles()
    fresh = []
    success = failed = 0

    for category in CATEGORY_ORDER:
        print(f"\n### {category}")
        for publisher, url in RSS_SOURCES.get(category, []):
            found = fetch_source(publisher, url, category)
            if found:
                success += 1
                fresh.extend(found)
            else:
                failed += 1
            time.sleep(REQUEST_DELAY)

    combined = deduplicate(fresh + previous)
    combined.sort(key=timestamp, reverse=True)
    final = combined[:TARGET_STORIES]

    counts = {c: 0 for c in CATEGORY_ORDER}
    for article in final:
        cat = normalize_category(article.get("category"))
        if cat in counts:
            counts[cat] += 1

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(final),
        "minimum_target": MINIMUM_STORIES,
        "maximum_target": TARGET_STORIES,
        "categories": counts,
        "articles": final
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nTOTAL STORIES: {len(final)}")
    print(f"Successful sources: {success}")
    print(f"Failed/empty sources: {failed}")

    if len(final) < MINIMUM_STORIES:
        print("WARNING: Fewer than 50 usable stories are available.")
    else:
        print("SUCCESS: Minimum 50-story target reached.")

    return 0 if final else 1

if __name__ == "__main__":
    raise SystemExit(build_feed())
