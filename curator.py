import json
import hashlib
import html
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_DIR = Path(__file__).resolve().parent

SOURCES_FILE = BASE_DIR / "sources.json"
ARTICLES_FILE = BASE_DIR / "articles.json"

MAX_ARTICLES_PER_SOURCE = 5
MAX_TOTAL_ARTICLES = 50
MAX_STORED_ARTICLES = 200
TIMEOUT = 15


# ============================================================
# SNIPPET24 REGION / LANGUAGE SYSTEM
# ============================================================

STATE_LANGUAGES = {
    "Tamil Nadu": {
        "code": "ta",
        "name": "தமிழ்"
    },
    "Kerala": {
        "code": "ml",
        "name": "മലയാളം"
    },
    "Karnataka": {
        "code": "kn",
        "name": "ಕನ್ನಡ"
    },
    "Andhra Pradesh": {
        "code": "te",
        "name": "తెలుగు"
    },
    "Telangana": {
        "code": "te",
        "name": "తెలుగు"
    },
    "Maharashtra": {
        "code": "mr",
        "name": "मराठी"
    },
    "Gujarat": {
        "code": "gu",
        "name": "ગુજરાતી"
    },
    "West Bengal": {
        "code": "bn",
        "name": "বাংলা"
    },
    "Odisha": {
        "code": "or",
        "name": "ଓଡ଼ିଆ"
    },
    "Punjab": {
        "code": "pa",
        "name": "ਪੰਜਾਬੀ"
    },
    "Assam": {
        "code": "as",
        "name": "অসমীয়া"
    },
    "Rajasthan": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Uttar Pradesh": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Bihar": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Madhya Pradesh": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Chhattisgarh": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Jharkhand": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Uttarakhand": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Himachal Pradesh": {
        "code": "hi",
        "name": "हिन्दी"
    },
    "Goa": {
        "code": "kok",
        "name": "कोंकणी"
    },
    "Delhi": {
        "code": "hi",
        "name": "हिन्दी"
    }
}


CATEGORIES = [
    "Indian & International",
    "Tech & AI",
    "Business & Economy",
    "Lifestyle & Health",
    "Entertainment & Living",
    "Earth & Environment",
    "Sports & Culture"
]


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print("[SNIPPET24]", message, flush=True)


# ============================================================
# JSON
# ============================================================

def load_json(path, default):
    try:
        if not path.exists():
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        log(f"JSON load warning: {e}")
        return default


def save_json(path, data):
    temp = path.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp.replace(path)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<script.*?</script>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<style.*?</style>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# ARTICLE ID
# ============================================================

def make_id(title, url):
    raw = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:16]


# ============================================================
# RSS PARSING
# ============================================================

def get_tag(item, tag):
    match = re.search(
        rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>",
        item,
        flags=re.I | re.S
    )

    if not match:
        return ""

    return clean_text(match.group(1))


def get_link(item):

    match = re.search(
        r"<link(?:\s[^>]*)?>(.*?)</link>",
        item,
        flags=re.I | re.S
    )

    if match:
        value = clean_text(match.group(1))

        if value.startswith("http"):
            return value

    match = re.search(
        r"<link[^>]+href=[\"']([^\"']+)[\"']",
        item,
        flags=re.I
    )

    if match:
        return html.unescape(match.group(1))

    return ""


def get_items(xml):

    items = re.findall(
        r"<item(?:\s[^>]*)?>(.*?)</item>",
        xml,
        flags=re.I | re.S
    )

    if items:
        return items

    return re.findall(
        r"<entry(?:\s[^>]*)?>(.*?)</entry>",
        xml,
        flags=re.I | re.S
    )


# ============================================================
# RSS DOWNLOAD
# ============================================================

def fetch_feed(source):

    url = source.get("feed_url", "")

    if not url:
        return ""

    request = Request(
        url,
        headers={
            "User-Agent":
                "Snippet24NewsReader/1.0 "
                "(RSS reader; +https://snippet24.in)",

            "Accept":
                "application/rss+xml,"
                "application/atom+xml,"
                "application/xml,"
                "text/xml,"
                "*/*"
        }
    )

    try:

        log(f"Reading: {source.get('name', 'Unknown')}")
        log(f"RSS: {url}")

        with urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            data = response.read()

        return data.decode(
            "utf-8",
            errors="replace"
        )

    except HTTPError as e:

        log(
            f"HTTP {e.code}: "
            f"{source.get('name')}"
        )

    except URLError as e:

        log(
            f"Network error: "
            f"{source.get('name')}: {e.reason}"
        )

    except Exception as e:

        log(
            f"Feed error: "
            f"{source.get('name')}: "
            f"{type(e).__name__}: {e}"
        )

    return ""


# ============================================================
# SUMMARY
# ============================================================

def make_original_summary(
    description,
    title
):

    description = clean_text(description)
    title = clean_text(title)

    if description:

        summary = description

    else:

        summary = (
            f"This story reports on {title}. "
            "See the original publication "
            "for complete details and the "
            "latest information."
        )

    if len(summary) > 650:

        summary = (
            summary[:647]
            .rsplit(" ", 1)[0]
            + "..."
        )

    return summary


# ============================================================
# LOCATION
# ============================================================

def determine_region(source):

    region = source.get(
        "region",
        "WORLD"
    )

    return region.upper()


def determine_country(source):

    return source.get(
        "country",
        ""
    )


def determine_state(source):

    return source.get(
        "state",
        ""
    )


def determine_category(source):

    category = source.get(
        "category",
        "Indian & International"
    )

    if category not in CATEGORIES:

        category = "Indian & International"

    return category


# ============================================================
# LANGUAGE INFORMATION
# ============================================================

def get_language_info(state):

    if state in STATE_LANGUAGES:

        return STATE_LANGUAGES[state]

    return {
        "code": "en",
        "name": "English"
    }


# ============================================================
# PARSE SOURCE
# ============================================================

def parse_source(source):

    xml = fetch_feed(source)

    if not xml:

        log(
            f"No RSS data: "
            f"{source.get('name')}"
        )

        return []

    items = get_items(xml)

    log(
        f"Entries found: "
        f"{source.get('name')}: "
        f"{len(items)}"
    )

    articles = []

    for item in items[:MAX_ARTICLES_PER_SOURCE]:

        title = get_tag(
            item,
            "title"
        )

        link = get_link(item)

        description = (
            get_tag(item, "description")
            or get_tag(item, "summary")
            or get_tag(item, "content")
        )

        if not title or not link:
            continue

        title = clean_text(title)
        description = clean_text(description)

        region = determine_region(source)
        country = determine_country(source)
        state = determine_state(source)
        category = determine_category(source)

        language = get_language_info(state)

        article_id = make_id(
            title,
            link
        )

        article = {

            # ------------------------------------------------
            # BASIC
            # ------------------------------------------------

            "id": article_id,

            "title": title,

            "summary":
                make_original_summary(
                    description,
                    title
                ),

            # ------------------------------------------------
            # CLASSIFICATION
            # ------------------------------------------------

            "region": region,

            "country": country,

            "state": state,

            "category": category,

            # ------------------------------------------------
            # LANGUAGE
            # ------------------------------------------------

            "default_language":
                language["code"],

            "default_language_name":
                language["name"],

            "available_languages": [
                "en",
                language["code"]
            ],

            # ------------------------------------------------
            # SOURCE
            # ------------------------------------------------

            "source":
                source.get(
                    "name",
                    ""
                ),

            "source_url":
                link,

            "source_website":
                source.get(
                    "website",
                    ""
                ),

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            "snippet24_status":
                "PUBLISHED",

            "summary_type":
                "RSS-based summary",

            "published_at":
                time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime()
                )
        }

        # ----------------------------------------------------
        # LANGUAGE CONTAINER
        #
        # English is always available.
        # State language is prepared for translation.
        # ----------------------------------------------------

        article["translations"] = {

            "en": {
                "title": title,
                "summary":
                    make_original_summary(
                        description,
                        title
                    )
            }

        }

        if language["code"] != "en":

            article["translations"][
                language["code"]
            ] = {
                "title": "",
                "summary": ""
            }

        articles.append(article)

    return articles


# ============================================================
# MAIN
# ============================================================

def main():

    log("======================================")
    log("SNIPPET24 CURATOR START")
    log("======================================")

    sources = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(
        sources,
        list
    ):

        log(
            "ERROR: sources.json "
            "must contain a list"
        )

        return 1

    log(
        f"Sources loaded: "
        f"{len(sources)}"
    )

    existing = load_json(
        ARTICLES_FILE,
        []
    )

    if not isinstance(
        existing,
        list
    ):

        existing = []

    log(
        f"Existing articles: "
        f"{len(existing)}"
    )

    existing_urls = {

        str(
            article.get(
                "source_url",
                ""
            )
        )

        for article in existing

        if isinstance(
            article,
            dict
        )
    }

    new_articles = []

    for source in sources:

        if not source.get(
            "enabled",
            True
        ):
            continue

        try:

            articles = parse_source(
                source
            )

            for article in articles:

                url = article[
                    "source_url"
                ]

                if url in existing_urls:
                    continue

                if any(
                    x.get("source_url")
                    == url
                    for x in new_articles
                ):
                    continue

                new_articles.append(
                    article
                )

                if (
                    len(new_articles)
                    >= MAX_TOTAL_ARTICLES
                ):
                    break

        except Exception as e:

            log(
                "Source failed: "
                f"{source.get('name')}: "
                f"{e}"
            )

        if (
            len(new_articles)
            >= MAX_TOTAL_ARTICLES
        ):
            break

    log(
        f"New articles: "
        f"{len(new_articles)}"
    )

    combined = (
        new_articles
        + existing
    )

    combined = combined[
        :MAX_STORED_ARTICLES
    ]

    save_json(
        ARTICLES_FILE,
        combined
    )

    published_count = sum(

        1

        for article in combined

        if article.get(
            "snippet24_status"
        )
        == "PUBLISHED"
    )

    log(
        f"Total stored: "
        f"{len(combined)}"
    )

    log(
        f"Published: "
        f"{published_count}"
    )

    log(
        "articles.json saved."
    )

    log("======================================")
    log("SNIPPET24 CURATOR COMPLETE")
    log("======================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )