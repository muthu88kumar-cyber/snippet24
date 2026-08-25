import os
import json
import hashlib
import re
import time
from datetime import datetime, timezone

import feedparser
from google import genai


ARTICLES_FILE = "articles.json"
SOURCES_FILE = "sources.json"

MAX_ARTICLES_PER_SOURCE = 10
MAX_TOTAL_ARTICLES = 30
MAX_STORED_ARTICLES = 500

RSS_RETRIES = 3


def log(message):
    print(f"[SNIPPET24] {message}")


def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        log(f"Could not read {filename}: {error}")
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_id(title, url):
    value = f"{title}|{url}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:20]


def load_sources():

    sources = load_json(
        SOURCES_FILE,
        []
    )

    valid = []

    for source in sources:

        if not source.get(
            "reuse_policy_checked"
        ):
            continue

        if not source.get(
            "allow_publish"
        ):
            continue

        if not source.get(
            "feed_url"
        ):
            continue

        valid.append(source)

    return valid


def parse_feed(url):

    last_error = None

    for attempt in range(
        1,
        RSS_RETRIES + 1
    ):

        try:

            log(
                f"RSS attempt "
                f"{attempt}/{RSS_RETRIES}: {url}"
            )

            feed = feedparser.parse(
                url
            )

            entries = getattr(
                feed,
                "entries",
                []
            )

            if entries:

                log(
                    f"RSS entries found: "
                    f"{len(entries)}"
                )

                return feed

            if getattr(
                feed,
                "bozo",
                False
            ):

                log(
                    f"RSS warning: "
                    f"{feed.bozo_exception}"
                )

        except Exception as error:

            last_error = error

            log(
                f"RSS error: {error}"
            )

        if attempt < RSS_RETRIES:

            time.sleep(3)

    log(
        f"RSS failed after "
        f"{RSS_RETRIES} attempts"
    )

    if last_error:
        log(
            f"Last RSS error: "
            f"{last_error}"
        )

    return None


def fetch_feed(source):

    log(
        f"READING RSS: "
        f"{source['name']}"
    )

    feed = parse_feed(
        source["feed_url"]
    )

    if not feed:

        log(
            f"NO RSS ARTICLES FOUND: "
            f"{source['name']}"
        )

        return []

    articles = []

    for item in feed.entries[
        :MAX_ARTICLES_PER_SOURCE
    ]:

        title = clean_text(
            item.get(
                "title",
                ""
            )
        )

        link = (
            item.get(
                "link",
                ""
            )
            .strip()
        )

        description = clean_text(
            item.get(
                "summary",
                ""
            )
            or item.get(
                "description",
                ""
            )
        )

        if not title or not link:
            continue

        article_id = make_id(
            title,
            link
        )

        published = (
            item.get(
                "published",
                ""
            )
            or item.get(
                "updated",
                ""
            )
            or ""
        )

        articles.append({

            "id": article_id,

            "source": source[
                "name"
            ],

            "source_website": source.get(
                "website",
                ""
            ),

            "source_url": link,

            "feed_title": title,

            "feed_summary": (
                description[:5000]
            ),

            "published": published,

            "category": source.get(
                "category",
                "General"
            ),

            "allow_ai_rewrite": source.get(
                "allow_ai_rewrite",
                False
            )
        })

    log(
        f"Usable articles from "
        f"{source['name']}: "
        f"{len(articles)}"
    )

    return articles


def build_prompt(article):

    return f"""
You are the editorial AI for Snippet24.

Create an original news summary from ONLY
the supplied RSS information.

COPYRIGHT RULES:

- Do not copy sentences.
- Do not reproduce the source article.
- Do not invent facts.
- Do not add information from your own knowledge.
- Do not create direct quotations.
- Do not pretend Snippet24 is the original publisher.
- Keep the original source URL unchanged.
- Credit the original source.

SOURCE:
{article["source"]}

HEADLINE:
{article["feed_title"]}

RSS INFORMATION:
{article["feed_summary"]}

SOURCE URL:
{article["source_url"]}

Return ONLY valid JSON.

Structure:

{{
  "headline_1": "",
  "headline_2": "",
  "headline_3": "",
  "summary": "",
  "deep_dive": [],
  "risk_level": "AUTO",
  "risk_reasons": []
}}

HEADLINES:
Create three different original headlines.

SUMMARY:
Write an original concise summary.

DEEP_DIVE:
Create exactly 30 short information lines.

Only use information present in the supplied RSS data.

If there are not enough facts,
state that the available RSS information
does not contain additional verified detail.

RISK LEVEL:

AUTO:
Straightforward factual information.

REVIEW:
Use for allegations, crime accusations,
political controversy, deaths, serious injuries,
medical claims, financial claims,
defamation risks, uncertain facts,
or sensitive personal information.

BLOCK:
Use for clearly unsafe, malicious,
fabricated, private or prohibited content.

Never create direct quotations.
"""


def fallback_article(article):

    summary = article[
        "feed_summary"
    ]

    if not summary:

        summary = (
            "The available RSS information "
            "does not contain enough detail "
            "for a complete summary."
        )

    lines = []

    for number in range(30):

        if number == 0:

            lines.append(
                "The source reports: "
                + summary[:250]
            )

        else:

            lines.append(
                "No additional verified "
                "detail is available in "
                "the supplied RSS information."
            )

    return {

        "headline_1":
            article["feed_title"],

        "headline_2":
            f"Latest update: "
            f"{article['feed_title']}",

        "headline_3":
            f"What we know about "
            f"{article['feed_title']}",

        "summary":
            summary[:1000],

        "deep_dive":
            lines,

        "risk_level":
            "REVIEW",

        "risk_reasons": [
            "AI generation was unavailable."
        ]
    }


def generate_ai(article):

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        log(
            "GEMINI_API_KEY not found."
        )

        return fallback_article(
            article
        )

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=build_prompt(
                article
            )
        )

        text = (
            response.text
            or ""
        ).strip()

        if text.startswith(
            "```"
        ):

            text = re.sub(
                r"^```json\s*",
                "",
                text,
                flags=re.IGNORECASE
            )

            text = re.sub(
                r"\s*```$",
                "",
                text
            )

        result = json.loads(
            text
        )

        headline_1 = str(
            result.get(
                "headline_1",
                ""
            )
        ).strip()

        headline_2 = str(
            result.get(
                "headline_2",
                ""
            )
        ).strip()

        headline_3 = str(
            result.get(
                "headline_3",
                ""
            )
        ).strip()

        summary = str(
            result.get(
                "summary",
                ""
            )
        ).strip()

        deep_dive = result.get(
            "deep_dive",
            []
        )

        if not isinstance(
            deep_dive,
            list
        ):

            raise ValueError(
                "deep_dive is not a list"
            )

        if len(
            deep_dive
        ) != 30:

            raise ValueError(
                "deep_dive must contain "
                "exactly 30 lines"
            )

        if not headline_1:
            raise ValueError(
                "Missing headline"
            )

        risk_level = str(
            result.get(
                "risk_level",
                "REVIEW"
            )
        ).upper()

        if risk_level not in [
            "AUTO",
            "REVIEW",
            "BLOCK"
        ]:

            risk_level = "REVIEW"

        risk_reasons = result.get(
            "risk_reasons",
            []
        )

        if not isinstance(
            risk_reasons,
            list
        ):

            risk_reasons = [
                str(risk_reasons)
            ]

        log(
            f"AI result: "
            f"{risk_level}"
        )

        return {

            "headline_1":
                headline_1,

            "headline_2":
                headline_2,

            "headline_3":
                headline_3,

            "summary":
                summary,

            "deep_dive": [
                str(x).strip()
                for x in deep_dive
            ],

            "risk_level":
                risk_level,

            "risk_reasons":
                risk_reasons
        }

    except Exception as error:

        log(
            f"AI generation failed: "
            f"{error}"
        )

        return fallback_article(
            article
        )


def process():

    log(
        "========== "
        "SNIPPET24 CURATOR START "
        "=========="
    )

    sources = load_sources()

    log(
        f"Approved sources loaded: "
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

    existing_ids = {

        item.get("id")

        for item in existing

        if item.get("id")
    }

    new_articles = []

    for source in sources:

        if len(
            new_articles
        ) >= MAX_TOTAL_ARTICLES:

            break

        try:

            feed_articles = fetch_feed(
                source
            )

            if not feed_articles:

                log(
                    f"No articles from "
                    f"{source['name']}"
                )

                continue

            for article in feed_articles:

                if len(
                    new_articles
                ) >= MAX_TOTAL_ARTICLES:

                    break

                if article["id"] in existing_ids:

                    log(
                        f"Duplicate skipped: "
                        f"{article['feed_title']}"
                    )

                    continue

                if not article[
                    "allow_ai_rewrite"
                ]:

                    log(
                        f"AI rewrite disabled: "
                        f"{article['feed_title']}"
                    )

                    continue

                log(
                    f"GENERATING: "
                    f"{article['feed_title']}"
                )

                ai = generate_ai(
                    article
                )

                status = (
                    "PUBLISHED"
                    if ai["risk_level"]
                    == "AUTO"
                    else ai["risk_level"]
                )

                record = {

                    "id":
                        article["id"],

                    "title":
                        ai["headline_1"],

                    "alternative_headlines": [
                        ai["headline_2"],
                        ai["headline_3"]
                    ],

                    "summary":
                        ai["summary"],

                    "deep_dive":
                        ai["deep_dive"],

                    "category":
                        article["category"],

                    "source":
                        article["source"],

                    "source_url":
                        article["source_url"],

                    "source_website":
                        article[
                            "source_website"
                        ],

                    "original_rss_title":
                        article[
                            "feed_title"
                        ],

                    "published_at":
                        article[
                            "published"
                        ],

                    "snippet24_status":
                        status,

                    "risk_level":
                        ai["risk_level"],

                    "risk_reasons":
                        ai["risk_reasons"],

                    "created_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                }

                new_articles.append(
                    record
                )

                log(
                    f"ARTICLE CREATED: "
                    f"{record['title']}"
                )

                log(
                    f"STATUS: "
                    f"{status}"
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

    log(
        "--------------------------------"
    )

    log(
        f"New articles: "
        f"{len(new_articles)}"
    )

    log(
        f"Total stored: "
        f"{len(combined)}"
    )

    log(
        "articles.json saved successfully."
    )

    log(
        "========== "
        "SNIPPET24 CURATOR END "
        "=========="
    )


if __name__ == "__main__":
    process()