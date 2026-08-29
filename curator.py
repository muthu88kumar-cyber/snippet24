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
# SNIPPET24 NEWS CURATOR v6
# Official/public-source focused, balanced categories
# ============================================================

OUTPUT_FILE = "articles.json"

TARGET_STORIES = 100
MINIMUM_STORIES = 50

# Maximum stories retained from each category.
MAX_PER_CATEGORY = {
    "World": 18,
    "India": 18,
    "Business": 14,
    "Technology & AI": 14,
    "Sports": 14,
    "Entertainment": 11,
    "Lifestyle": 11,
}

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.25

HEADERS = {
    "User-Agent": "Snippet24-News/6.0 (+https://snippet24.in)"
}

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
# OFFICIAL / PUBLIC RSS SOURCES
# ============================================================
# Sources are intentionally biased toward government,
# intergovernmental, institutional and public official feeds.
# Where a category needs broader current coverage, established
# public RSS feeds are included as fallback sources.
# ============================================================

RSS_SOURCES = {
    # Government / intergovernmental / official institutional sources only.
    # Commercial news publishers are intentionally excluded.
    "World": [
        ("United Nations", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
        ("World Health Organization", "https://www.who.int/feeds/entity/news/en/rss.xml"),
        ("UNICEF", "https://www.unicef.org/press-releases/rss.xml"),
        ("UNHCR", "https://www.unhcr.org/rss/news.xml"),
        ("UNESCO", "https://www.unesco.org/en/rss.xml"),
        ("World Meteorological Organization", "https://public.wmo.int/en/rss.xml"),
        ("FAO", "https://www.fao.org/feeds/fao-news/en"),
    ],

    "India": [
        ("Press Information Bureau", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"),
        ("Press Information Bureau - Features", "https://pib.gov.in/RssMain.aspx?ModId=18&Lang=1&Regid=1"),
        ("ISRO", "https://www.isro.gov.in/media_isro/rss.xml"),
        ("Income Tax Department", "https://wmstatic-prd.incometaxindia.gov.in/en/press-release-rss-feed/-/asset_publisher/ovrx/rss"),
        ("Reserve Bank of India", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=RSS"),
        ("Ministry of External Affairs", "https://www.mea.gov.in/rss.htm"),
    ],

    "Business": [
        ("Reserve Bank of India", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=RSS"),
        ("European Central Bank", "https://www.ecb.europa.eu/rss/press.html"),
        ("International Monetary Fund", "https://www.imf.org/en/News/RSS"),
        ("World Bank", "https://www.worldbank.org/en/news/all?format=rss"),
        ("World Trade Organization", "https://www.wto.org/english/news_e/news_e.xml"),
        ("OECD", "https://www.oecd.org/newsroom/rss.xml"),
        ("U.S. Securities and Exchange Commission", "https://www.sec.gov/news/pressreleases.rss"),
    ],

    "Technology & AI": [
        ("NASA", "https://www.nasa.gov/feed/"),
        ("NASA JPL", "https://www.jpl.nasa.gov/feeds/news/"),
        ("NASA CNEOS", "https://cneos.jpl.nasa.gov/feed/news.xml"),
        ("European Space Agency", "https://www.esa.int/rssfeed/Our_Activities"),
        ("CERN", "https://home.cern/rss"),
        ("National Science Foundation", "https://www.nsf.gov/rss/rss.php"),
        ("NIST", "https://www.nist.gov/news-events/news/rss.xml"),
        ("NOAA", "https://www.noaa.gov/rss.xml"),
    ],

    "Sports": [
        # Official sports governing bodies / Olympic institutions.
        ("FIFA", "https://inside.fifa.com/rss"),
        ("International Olympic Committee", "https://olympics.com/ioc/rss"),
        ("Olympics", "https://olympics.com/en/news/rss"),
        ("International Cricket Council", "https://www.icc-cricket.com/rss"),
        ("World Athletics", "https://worldathletics.org/rss"),
    ],

    "Entertainment": [
        # Official cultural institutions rather than commercial entertainment media.
        ("Academy of Motion Picture Arts and Sciences", "https://www.oscars.org/rss/news.xml"),
        ("National Endowment for the Arts", "https://www.arts.gov/rss/news.xml"),
        ("Library of Congress", "https://www.loc.gov/rss/"),
        ("Smithsonian", "https://www.si.edu/rss"),
        ("National Gallery of Art", "https://www.nga.gov/rss.xml"),
        ("Kennedy Center", "https://www.kennedy-center.org/rss/"),
    ],

    "Lifestyle": [
        ("World Health Organization", "https://www.who.int/feeds/entity/news/en/rss.xml"),
        ("UNICEF", "https://www.unicef.org/press-releases/rss.xml"),
        ("FAO", "https://www.fao.org/feeds/fao-news/en"),
        ("Centers for Disease Control and Prevention", "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
        ("National Institutes of Health", "https://www.nih.gov/news-events/news-releases/feed"),
        ("NASA Earth", "https://www.nasa.gov/earth/feed/"),
        ("Smithsonian", "https://www.si.edu/rss"),
        ("Library of Congress", "https://www.loc.gov/rss/"),
    ],
}

# Only retain stories whose original source URL belongs to an approved
# government, intergovernmental, or official institutional domain.
# This also cleans old articles.json entries from previously used
# commercial/private publishers.
APPROVED_SOURCE_DOMAINS = {
    "pib.gov.in", "isro.gov.in", "incometaxindia.gov.in", "rbi.org.in", "mea.gov.in",
    "un.org", "news.un.org", "who.int", "unicef.org", "unhcr.org", "unesco.org",
    "wmo.int", "fao.org", "imf.org", "worldbank.org", "wto.org", "oecd.org",
    "ecb.europa.eu", "sec.gov", "nasa.gov", "jpl.nasa.gov", "esa.int", "cern.ch",
    "nsf.gov", "nist.gov", "noaa.gov", "fifa.com", "olympics.com", "icc-cricket.com",
    "worldathletics.org", "oscars.org", "arts.gov", "loc.gov", "si.edu", "nga.gov",
    "kennedy-center.org", "cdc.gov", "nih.gov",
}


def is_approved_source_url(url):
    """Return True only for approved official/public institutional domains."""
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return any(host == domain or host.endswith("." + domain)
                   for domain in APPROVED_SOURCE_DOMAINS)
    except Exception:
        return False


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    value = value.replace("&nbsp;", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


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


def normalize_url(url):
    if not url:
        return ""

    url = clean_text(url).strip()

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ""
        return url
    except Exception:
        return ""


def normalize_title(title):
    title = clean_text(title).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def make_id(category, title, url):
    raw = f"{category}|{normalize_title(title)}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def remove_publisher_from_title(title, publisher):
    title = clean_text(title)
    if not title:
        return ""

    publishers = [
        publisher, "Hindustan Times", "Business Standard",
        "Firstpost", "Moneycontrol", "News18", "NDTV",
        "The Hindu", "Indian Express", "BBC", "BBC News",
        "Reuters", "CNN", "CNBC", "TechCrunch", "The Verge",
        "Variety", "ESPN", "Hollywood Reporter"
    ]

    for name in publishers:
        if not name:
            continue
        pattern = r"\s*(?:\||-|\u2013|\u2014)\s*" + re.escape(name) + r"\s*$"
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)

    return title.strip(" -|\u2013\u2014")


def remove_title_repetition(summary, title):
    summary = clean_text(summary)
    if not summary:
        return ""

    if title:
        summary = re.sub(re.escape(title), "", summary, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", summary).strip()


def make_summary(title, description):
    title = clean_text(title)
    description = clean_text(description)

    description = remove_title_repetition(description, title)

    description = re.sub(
        r"^(read more|latest updates|follow live|breaking news)\s*[:\-]?\s*",
        "",
        description,
        flags=re.IGNORECASE,
    )

    if len(description) > 420:
        description = description[:417].rsplit(" ", 1)[0] + "..."

    if description:
        return description

    return (
        "The latest developments are being reported by the "
        "original publisher. Read the original report for "
        "the full details."
    )


def parse_date(value):
    if not value:
        return datetime.now(timezone.utc)

    value = clean_text(value).strip()

    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def find_child_text(element, names):
    names = {name.lower() for name in names}

    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag in names:
            return clean_text("".join(child.itertext()))

    return ""


def find_link(element):
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag != "link":
            continue

        href = child.attrib.get("href")
        if href:
            return normalize_url(href)

        text = clean_text("".join(child.itertext()))
        if text:
            return normalize_url(text)

    # Some feeds use guid as the URL.
    guid = find_child_text(element, ["guid", "id"])
    return normalize_url(guid)


def find_image_from_feed(element):
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()

        if tag in ("content", "thumbnail"):
            url = child.attrib.get("url")
            if url:
                return normalize_url(url)

    for child in list(element):
        tag = child.tag.split("}")[-1].lower()

        if tag != "enclosure":
            continue

        url = child.attrib.get("url", "")
        kind = child.attrib.get("type", "").lower()

        if url and ("image" in kind or not kind):
            return normalize_url(url)

    raw = "".join(element.itertext())

    match = re.search(
        r'https?://[^"\'>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\'>\s]*)?',
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        return normalize_url(match.group(0))

    return ""


def make_ai_image(title, category):
    prompt = (
        "Professional editorial news illustration for a modern "
        "digital news publication. "
        f"Category: {category}. Story: {title}. "
        "Create a realistic, relevant, tasteful journalistic visual. "
        "No text, no letters, no words, no logos, no watermark, "
        "no fake newspaper."
    )

    seed = int(
        hashlib.md5(
            (category + "|" + title).encode("utf-8")
        ).hexdigest()[:8],
        16,
    )

    return (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe="")
        + "?width=1200&height=675"
        + "&nologo=true"
        + f"&seed={seed}"
    )

# ============================================================
# RSS PARSER
# ============================================================

def parse_feed(xml_text, publisher, category):
    articles = []

    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"  XML ERROR: {publisher}: {exc}")
        return articles

    elements = []

    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()

        if tag in ("item", "entry"):
            elements.append(element)

    for item in elements:
        title = find_child_text(item, ["title"])

        if not title:
            continue

        title = remove_publisher_from_title(title, publisher)

        if len(title) < 8:
            continue

        description = find_child_text(
            item,
            ["description", "summary", "content", "encoded"]
        )

        link = find_link(item)

        if not link:
            continue

        published = find_child_text(
            item,
            ["pubdate", "published", "updated", "date", "created"]
        )

        date_obj = parse_date(published)
        normalized_category = normalize_category(category)

        summary = make_summary(title, description)

        article = {
            "id": make_id(
                normalized_category,
                title,
                link
            ),
            "category": normalized_category,
            "headline": title,
            "summary": summary,
            "publisher": clean_text(publisher),
            "source_type": "official_institutional",
            "published_at": date_obj.isoformat(),
            "source_url": link,
            "image_url": make_ai_image(
                title,
                normalized_category
            ),
            "image_type": "ai_generated",
        }

        articles.append(article)

    return articles

# ============================================================
# FETCH
# ============================================================

def fetch_source(publisher, url, category):
    print(f"Fetching: {publisher}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        articles = parse_feed(
            response.text,
            publisher,
            category,
        )

        print(f"  -> {len(articles)} stories")
        return articles

    except Exception as exc:
        print(f"  -> FAILED: {publisher}: {exc}")
        return []

# ============================================================
# EXISTING ARTICLES
# ============================================================

def load_existing_articles():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        articles = data.get("articles", [])

        if not isinstance(articles, list):
            return []

        valid = []

        for article in articles:
            if not isinstance(article, dict):
                continue

            headline = clean_text(article.get("headline"))
            url = normalize_url(article.get("source_url"))

            if not headline or not url:
                continue

            # Remove legacy articles from commercial/private publishers.
            if not is_approved_source_url(url):
                continue

            article["category"] = normalize_category(
                article.get("category")
            )
            article["headline"] = headline
            article["summary"] = make_summary(
                headline,
                article.get("summary", "")
            )
            article["source_url"] = url

            # v6 keeps all visuals as Snippet24-generated visuals.
            if not article.get("image_url"):
                article["image_url"] = make_ai_image(
                    headline,
                    article["category"]
                )

            article["image_type"] = "ai_generated"

            if not article.get("id"):
                article["id"] = make_id(
                    article["category"],
                    headline,
                    url
                )

            valid.append(article)

        return valid

    except FileNotFoundError:
        print("No previous articles.json found.")
        return []

    except Exception as exc:
        print(f"Could not read previous articles.json: {exc}")
        return []

# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(articles):
    unique = {}

    for article in articles:
        if not isinstance(article, dict):
            continue

        title = clean_text(article.get("headline"))
        url = normalize_url(article.get("source_url"))

        if not title or not url:
            continue

        key = url.lower()

        if key not in unique:
            unique[key] = article
        else:
            old_date = unique[key].get("published_at", "")
            new_date = article.get("published_at", "")

            if new_date > old_date:
                unique[key] = article

    title_unique = {}

    for article in unique.values():
        title_key = normalize_title(article.get("headline", ""))

        if not title_key:
            continue

        if title_key not in title_unique:
            title_unique[title_key] = article

    return list(title_unique.values())

# ============================================================
# SORT / DATE
# ============================================================

def article_timestamp(article):
    value = article.get("published_at", "")

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)

# ============================================================
# BALANCED CATEGORY SELECTION
# ============================================================

def select_balanced(articles):
    """
    Select newest genuine stories while preventing one category
    from taking all 100 slots.

    Pass 1: give each category a fair base allocation.
    Pass 2: fill remaining slots using newest available stories.
    """

    by_category = {
        category: []
        for category in CATEGORY_ORDER
    }

    for article in articles:
        category = normalize_category(
            article.get("category")
        )

        if category in by_category:
            by_category[category].append(article)

    for category in CATEGORY_ORDER:
        by_category[category].sort(
            key=article_timestamp,
            reverse=True
        )

    selected = []
    used_ids = set()

    # Fair base allocation.
    # Start with 5 per category when available.
    for category in CATEGORY_ORDER:
        bucket = by_category[category]
        limit = min(5, MAX_PER_CATEGORY[category], len(bucket))

        for article in bucket[:limit]:
            article_id = article.get("id") or article.get("source_url")

            if article_id in used_ids:
                continue

            selected.append(article)
            used_ids.add(article_id)

    # Fill remaining capacity category-by-category using newest
    # available stories, respecting category maximums.
    while len(selected) < TARGET_STORIES:
        added = False

        for category in CATEGORY_ORDER:
            category_count = sum(
                1
                for article in selected
                if normalize_category(article.get("category")) == category
            )

            if category_count >= MAX_PER_CATEGORY[category]:
                continue

            bucket = by_category[category]

            for article in bucket:
                article_id = article.get("id") or article.get("source_url")

                if article_id in used_ids:
                    continue

                selected.append(article)
                used_ids.add(article_id)
                added = True
                break

            if len(selected) >= TARGET_STORIES:
                break

        if not added:
            break

    selected.sort(
        key=article_timestamp,
        reverse=True
    )

    return selected[:TARGET_STORIES]

# ============================================================
# COUNTS
# ============================================================

def category_counts(articles):
    counts = {
        category: 0
        for category in CATEGORY_ORDER
    }

    for article in articles:
        category = normalize_category(
            article.get("category")
        )

        if category in counts:
            counts[category] += 1

    return counts

# ============================================================
# BUILD
# ============================================================

def build_feed():
    print("=" * 65)
    print("SNIPPET24 NEWS CURATOR v6")
    print("BALANCED OFFICIAL/PUBLIC SOURCE MODE")
    print("=" * 65)

    previous_articles = load_existing_articles()

    print(f"Previous valid stories: {len(previous_articles)}")

    fresh_articles = []
    successful_sources = 0
    failed_sources = 0

    for category in CATEGORY_ORDER:
        print()
        print(f"### {category}")

        sources = RSS_SOURCES.get(category, [])

        for publisher, url in sources:
            found = fetch_source(
                publisher,
                url,
                category,
            )

            if found:
                successful_sources += 1
                fresh_articles.extend(found)
            else:
                failed_sources += 1

            time.sleep(REQUEST_DELAY)

    print()
    print(f"Fresh stories collected: {len(fresh_articles)}")
    print(f"Successful sources: {successful_sources}")
    print(f"Failed/empty sources: {failed_sources}")

    combined = fresh_articles + previous_articles

    print(f"Combined before deduplication: {len(combined)}")

    combined = deduplicate(combined)

    print(f"After deduplication: {len(combined)}")

    final_articles = select_balanced(combined)

    print(f"After balanced selection: {len(final_articles)}")

    counts = category_counts(final_articles)

    output = {
        "curator_version": "7.0-official-only",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(final_articles),
        "minimum_target": MINIMUM_STORIES,
        "maximum_target": TARGET_STORIES,
        "source_policy": "official_government_intergovernmental_and_institutional_sources_only",
        "copyright_note": (
            "Snippet24 publishes its own headlines and summaries and "
            "credits the original publisher with a source link. "
            "This is not a guarantee of legal immunity."
        ),
        "categories": counts,
        "articles": final_articles,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 65)
    print(f"TOTAL STORIES: {len(final_articles)}")
    print("=" * 65)

    for category in CATEGORY_ORDER:
        print(f"{category}: {counts.get(category, 0)}")

    print()
    print(f"Successful sources: {successful_sources}")
    print(f"Failed/empty sources: {failed_sources}")

    if len(final_articles) == 0:
        print()
        print("ERROR: No usable articles are available.")
        print("Existing articles were not intentionally deleted.")
        return 1

    if len(final_articles) < MINIMUM_STORIES:
        print()
        print("WARNING: Fewer than 50 genuine stories are available.")
        print("The curator will not fabricate stories to reach 50.")
    else:
        print()
        print("SUCCESS: Minimum 50-story target reached.")

    print()
    print("SUCCESS: articles.json updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_feed())
