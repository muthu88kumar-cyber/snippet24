import json
import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET


ARTICLES_FILE = "articles.json"

MINIMUM_PER_CATEGORY = 50
MAXIMUM_PER_CATEGORY = 100

CATEGORIES = [
    "World",
    "India",
    "States",
    "Tech & AI",
    "Business",
    "Lifestyle",
]


# Multiple RSS queries per category.
# Google News RSS is used because it provides many stories
# without requiring feedparser or a paid news API.
FEEDS = {

    "World": [
        "https://news.google.com/rss/search?q=world+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=international+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=global+politics&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=world+economy&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "India": [
        "https://news.google.com/rss/search?q=India+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Indian+politics&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+government&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+Supreme+Court&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+economy&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "States": [
        "https://news.google.com/rss/search?q=Tamil+Nadu+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Karnataka+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Kerala+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Maharashtra+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Delhi+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Andhra+Pradesh+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Telangana+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=West+Bengal+news&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "Tech & AI": [
        "https://news.google.com/rss/search?q=technology+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=AI+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Google+AI&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=OpenAI+AI&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Apple+technology&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Microsoft+technology&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "Business": [
        "https://news.google.com/rss/search?q=business+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=India+business&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=stock+market&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Indian+economy&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=startups+India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=markets+India&hl=en-IN&gl=IN&ceid=IN:en",
    ],

    "Lifestyle": [
        "https://news.google.com/rss/search?q=lifestyle+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=health+lifestyle&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=travel+news&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=food+lifestyle&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=entertainment+India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=movies+India&hl=en-IN&gl=IN&ceid=IN:en",
    ],
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_id(title, url):
    value = f"{title}|{url}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:24]


def parse_date(value):
    if not value:
        return now_iso()

    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        return now_iso()


def fetch_url(url):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "Snippet24-News/1.0"
            )
        },
    )

    try:
        with urlopen(request, timeout=25) as response:
            return response.read()

    except (HTTPError, URLError, TimeoutError) as error:
        print(f"RSS ERROR: {url}")
        print(f"           {error}")
        return None

    except Exception as error:
        print(f"RSS UNKNOWN ERROR: {error}")
        return None


def child_text(element, names):
    for child in element:
        tag = child.tag.lower().split("}")[-1]

        if tag in names:
            return clean_text(child.text or "")

    return ""


def parse_feed(data, category):
    if not data:
        return []

    try:
        root = ET.fromstring(data)
    except Exception as error:
        print(f"XML ERROR: {error}")
        return []

    articles = []

    for item in root.iter():

        tag = item.tag.lower().split("}")[-1]

        if tag not in ("item", "entry"):
            continue

        title = child_text(
            item,
            {"title"}
        )

        description = child_text(
            item,
            {
                "description",
                "summary",
                "content"
            }
        )

        published = child_text(
            item,
            {
                "pubdate",
                "published",
                "updated",
                "date",
                "dc:date"
            }
        )

        url = ""

        source = ""

        for child in item:

            child_tag = (
                child.tag
                .lower()
                .split("}")[-1]
            )

            if child_tag == "link":

                href = child.attrib.get("href")

                if href:
                    url = href.strip()

                elif child.text:
                    url = child.text.strip()

            if child_tag == "source":
                source = clean_text(
                    child.text or ""
                )

        if not title or not url:
            continue

        title = clean_text(title)

        description = clean_text(
            description
        )

        if not description:
            description = title

        if not source:
            source = "Google News"

        article = {
            "id": make_id(
                title,
                url
            ),

            "title": title,

            "description": description[:600],

            "url": url,

            "source": source,

            "category": category,

            "published_at": parse_date(
                published
            ),

            "fetched_at": now_iso(),
        }

        articles.append(article)

    return articles


def load_database():

    try:

        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if (
            isinstance(data, dict)
            and isinstance(
                data.get("categories"),
                dict
            )
        ):
            return data

    except Exception as error:

        print(
            "Existing articles.json "
            f"could not be loaded: {error}"
        )

    return {
        "updated_at": now_iso(),

        "minimum_per_category":
            MINIMUM_PER_CATEGORY,

        "maximum_per_category":
            MAXIMUM_PER_CATEGORY,

        "fifo": True,

        "categories": {
            category: []
            for category in CATEGORIES
        }
    }


def unique_articles(articles):

    seen = set()
    result = []

    for article in articles:

        article_id = article.get("id")

        if not article_id:
            continue

        if article_id in seen:
            continue

        seen.add(article_id)
        result.append(article)

    return result


def newest_first(articles):

    return sorted(
        articles,
        key=lambda item:
            item.get(
                "published_at",
                ""
            ),
        reverse=True
    )


def update_category(
    old_articles,
    new_articles
):

    combined = (
        new_articles
        + old_articles
    )

    combined = unique_articles(
        combined
    )

    combined = newest_first(
        combined
    )

    # FIFO:
    # newest stays,
    # oldest is removed after 100.
    return combined[
        :MAXIMUM_PER_CATEGORY
    ]


def collect_category(
    category
):

    collected = []

    feeds = FEEDS.get(
        category,
        []
    )

    print()
    print("=" * 60)
    print(category)
    print("=" * 60)

    for feed in feeds:

        print(
            f"Fetching: {feed}"
        )

        data = fetch_url(feed)

        if not data:
            continue

        items = parse_feed(
            data,
            category
        )

        print(
            f"Found {len(items)}"
        )

        collected.extend(items)

    return collected


def main():

    print()
    print("========================================")
    print("       SNIPPET24 NEWS CURATOR")
    print("========================================")

    database = load_database()

    database["minimum_per_category"] = (
        MINIMUM_PER_CATEGORY
    )

    database["maximum_per_category"] = (
        MAXIMUM_PER_CATEGORY
    )

    database["fifo"] = True

    categories = database.setdefault(
        "categories",
        {}
    )

    for category in CATEGORIES:

        categories.setdefault(
            category,
            []
        )

    for category in CATEGORIES:

        old_articles = categories[
            category
        ]

        new_articles = collect_category(
            category
        )

        updated = update_category(
            old_articles,
            new_articles
        )

        categories[category] = updated

        print(
            f"{category}: "
            f"{len(updated)} stored"
        )

    database["updated_at"] = now_iso()

    with open(
        ARTICLES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            database,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("========================================")
    print("FINAL CATEGORY COUNTS")
    print("========================================")

    total = 0

    for category in CATEGORIES:

        count = len(
            database[
                "categories"
            ][category]
        )

        total += count

        status = (
            "OK"
            if count >= MINIMUM_PER_CATEGORY
            else "LOW"
        )

        print(
            f"{category:<12} "
            f"{count:>3} [{status}]"
        )

    print("----------------------------------------")
    print(
        f"TOTAL ARTICLES: {total}"
    )

    print()
    print(
        f"Saved {ARTICLES_FILE}"
    )


if __name__ == "__main__":
    main()