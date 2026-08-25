import os
import json
import hashlib
import re
from datetime import datetime, timezone

import feedparser
from google import genai
from google.genai import types


ARTICLES_FILE = "articles.json"
SOURCES_FILE = "sources.json"

MAX_ARTICLES_PER_SOURCE = 10
MAX_TOTAL_ARTICLES = 30
MAX_STORED_ARTICLES = 500

MODEL_NAME = "gemini-2.5-flash"


def log(message):
    print(f"[SNIPPET24] {message}", flush=True)


def load_json(filename, default):
    if not os.path.exists(filename):
        log(f"File not found: {filename}")
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

    text = str(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def make_id(title, url):
    value = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(
        value
    ).hexdigest()[:20]


def load_sources():

    sources = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(sources, list):
        log("ERROR: sources.json is not a list.")
        return []

    valid = []

    for source in sources:

        name = source.get(
            "name",
            "Unnamed source"
        )

        if not source.get(
            "reuse_policy_checked",
            False
        ):
            log(
                f"SKIP {name}: "
                "reuse_policy_checked is false"
            )
            continue

        if not source.get(
            "allow_publish",
            False
        ):
            log(
                f"SKIP {name}: "
                "allow_publish is false"
            )
            continue

        if not source.get("feed_url"):
            log(
                f"SKIP {name}: "
                "feed_url missing"
            )
            continue

        if not source.get(
            "allow_ai_rewrite",
            False
        ):
            log(
                f"SKIP {name}: "
                "allow_ai_rewrite is false"
            )
            continue

        valid.append(source)

    log(
        f"Approved sources loaded: "
        f"{len(valid)}"
    )

    return valid


def fetch_feed(source):

    name = source["name"]
    url = source["feed_url"]

    log(f"READING RSS: {name}")
    log(f"RSS URL: {url}")

    try:

        feed = feedparser.parse(url)

    except Exception as error:

        log(
            f"RSS ERROR for {name}: "
            f"{error}"
        )

        return []

    if getattr(
        feed,
        "bozo",
        False
    ):

        exception = getattr(
            feed,
            "bozo_exception",
            None
        )

        log(
            f"RSS WARNING for {name}: "
            f"{exception}"
        )

    entries = getattr(
        feed,
        "entries",
        []
    )

    log(
        f"RSS entries found for "
        f"{name}: {len(entries)}"
    )

    if not entries:
        log(
            f"NO RSS ARTICLES FOUND: "
            f"{name}"
        )

        return []

    articles = []

    for item in entries[
        :MAX_ARTICLES_PER_SOURCE
    ]:

        title = clean_text(
            item.get(
                "title",
                ""
            )
        )

        link = clean_text(
            item.get(
                "link",
                ""
            )
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

        # Some RSS feeds expose content differently.
        if not description:

            content = item.get(
                "content",
                []
            )

            if content:

                try:
                    description = clean_text(
                        content[0].get(
                            "value",
                            ""
                        )
                    )
                except Exception:
                    pass

        if not title:

            log(
                f"SKIP RSS item: "
                "missing title"
            )

            continue

        if not link:

            log(
                f"SKIP RSS item "
                f"'{title}': missing URL"
            )

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

            "source": name,

            "source_website":
                source.get(
                    "website",
                    ""
                ),

            "source_url": link,

            "feed_title": title,

            "feed_summary":
                description[:5000],

            "published":
                published,

            "category":
                source.get(
                    "category",
                    "General"
                ),

            "allow_ai_rewrite":
                bool(
                    source.get(
                        "allow_ai_rewrite",
                        False
                    )
                )

        })

    log(
        f"Usable RSS articles from "
        f"{name}: {len(articles)}"
    )

    return articles


def build_prompt(article):

    return f"""
You are the editorial AI for Snippet24.

You are processing RSS metadata supplied by an approved source.

COPYRIGHT AND ATTRIBUTION RULES:

- Do not reproduce the source article.
- Do not copy sentences from the source.
- Do not create a near-verbatim rewrite.
- Do not create direct quotations.
- Do not claim Snippet24 is the original publisher.
- Write genuinely original wording.
- Keep the source name.
- Keep the original source URL unchanged.
- Use only information contained in the supplied RSS title and summary.
- Do not use outside knowledge.
- Do not invent facts.
- Do not invent names.
- Do not invent dates.
- Do not invent numbers.
- Do not invent quotes.

SOURCE:
{article["source"]}

RSS TITLE:
{article["feed_title"]}

RSS SUMMARY:
{article["feed_summary"]}

ORIGINAL SOURCE URL:
{article["source_url"]}

Create:

1. Three substantially different headlines.
2. One concise summary.
3. Exactly 30 short deep-dive lines.

The deep dive must contain only information supported by the supplied RSS information.

If the RSS information is insufficient for 30 distinct factual points, clearly state that the available source information is limited. Never invent additional facts.

RISK CLASSIFICATION:

AUTO:
Use only for straightforward factual information where there is no obvious allegation, defamation concern, sensitive personal information, or other high-risk issue.

REVIEW:
Use for:
- allegations
- accusations
- crime claims involving identifiable people
- political controversy
- deaths
- serious injuries
- medical claims
- financial claims
- potentially defamatory content
- uncertain facts
- sensitive personal information

BLOCK:
Use for:
- private personal information
- malicious or fabricated content
- instructions facilitating wrongdoing
- clearly unsafe material
- content that should not be published

Return only the requested structured JSON.
"""


def fallback_article(
    article,
    reason
):

    summary = (
        article["feed_summary"]
        or
        "The available RSS information "
        "does not contain enough detail "
        "for a complete summary."
    )

    lines = []

    lines.append(
        "The available RSS information "
        "was received from the credited source."
    )

    lines.append(
        f"The source headline is: "
        f"{article['feed_title']}."
    )

    lines.append(
        "The remaining details require "
        "additional verified source information."
    )

    while len(lines) < 30:

        lines.append(
            "Additional verified detail "
            "is not available in the supplied "
            "RSS information."
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
            lines[:30],

        "risk_level":
            "REVIEW",

        "risk_reasons":
            [reason]

    }


def generate_ai(article):

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        log(
            "ERROR: GEMINI_API_KEY "
            "is not available."
        )

        return fallback_article(
            article,
            "Gemini API key unavailable."
        )

    try:

        log(
            f"Calling Gemini for: "
            f"{article['feed_title']}"
        )

        client = genai.Client(
            api_key=api_key
        )

        schema = {
            "type": "object",

            "properties": {

                "headline_1": {
                    "type": "string"
                },

                "headline_2": {
                    "type": "string"
                },

                "headline_3": {
                    "type": "string"
                },

                "summary": {
                    "type": "string"
                },

                "deep_dive": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    },

                    "minItems": 30,
                    "maxItems": 30
                },

                "risk_level": {
                    "type": "string",

                    "enum": [
                        "AUTO",
                        "REVIEW",
                        "BLOCK"
                    ]
                },

                "risk_reasons": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }

            },

            "required": [
                "headline_1",
                "headline_2",
                "headline_3",
                "summary",
                "deep_dive",
                "risk_level",
                "risk_reasons"
            ],

            "additionalProperties": False
        }

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=build_prompt(
                article
            ),

            config=types.GenerateContentConfig(

                response_mime_type=
                    "application/json",

                response_schema=
                    schema,

                temperature=0.2

            )
        )

        text = (
            response.text
            if response.text
            else ""
        ).strip()

        if not text:

            raise ValueError(
                "Gemini returned empty response."
            )

        result = json.loads(text)

        headlines = [

            clean_text(
                result.get(
                    "headline_1",
                    ""
                )
            ),

            clean_text(
                result.get(
                    "headline_2",
                    ""
                )
            ),

            clean_text(
                result.get(
                    "headline_3",
                    ""
                )
            )

        ]

        if not all(headlines):

            raise ValueError(
                "Gemini returned missing headline."
            )

        deep_dive = result.get(
            "deep_dive",
            []
        )

        if not isinstance(
            deep_dive,
            list
        ):

            raise ValueError(
                "Deep dive is not a list."
            )

        deep_dive = [

            clean_text(line)

            for line in deep_dive

            if clean_text(line)

        ]

        if len(deep_dive) != 30:

            raise ValueError(
                "Gemini returned "
                f"{len(deep_dive)} deep-dive "
                "lines instead of 30."
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
            f"Gemini success: "
            f"{article['feed_title']}"
        )

        log(
            f"Risk classification: "
            f"{risk_level}"
        )

        return {

            "headline_1":
                headlines[0],

            "headline_2":
                headlines[1],

            "headline_3":
                headlines[2],

            "summary":
                clean_text(
                    result.get(
                        "summary",
                        ""
                    )
                ),

            "deep_dive":
                deep_dive,

            "risk_level":
                risk_level,

            "risk_reasons":
                [
                    clean_text(
                        str(reason)
                    )

                    for reason
                    in risk_reasons
                ]

        }

    except Exception as error:

        log(
            "GEMINI ERROR: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return fallback_article(
            article,
            f"AI generation failed: {error}"
        )


def create_record(
    article,
    ai
):

    risk_level = ai[
        "risk_level"
    ]

    if risk_level == "AUTO":

        status = "PUBLISHED"

    elif risk_level == "REVIEW":

        status = "REVIEW"

    else:

        status = "BLOCK"


    return {

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
            article["source_website"],

        "original_rss_title":
            article["feed_title"],

        "published_at":
            article["published"],

        "snippet24_status":
            status,

        "risk_level":
            risk_level,

        "risk_reasons":
            ai["risk_reasons"],

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat()

    }


def process():

    log(
        "========== SNIPPET24 CURATOR START =========="
    )

    sources = load_sources()

    if not sources:

        log(
            "ERROR: No approved sources."
        )

        # Do not destroy existing articles.
        return

    existing = load_json(
        ARTICLES_FILE,
        []
    )

    if not isinstance(
        existing,
        list
    ):

        log(
            "WARNING: articles.json "
            "was not a list. Starting empty."
        )

        existing = []

    existing_ids = {

        item.get("id")

        for item in existing

        if item.get("id")

    }

    log(
        f"Existing articles: "
        f"{len(existing)}"
    )

    new_articles = []

    for source in sources:

        if (
            len(new_articles)
            >= MAX_TOTAL_ARTICLES
        ):
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

                if (
                    len(new_articles)
                    >= MAX_TOTAL_ARTICLES
                ):
                    break

                if article["id"] in existing_ids:

                    log(
                        f"DUPLICATE: "
                        f"{article['feed_title']}"
                    )

                    continue

                log(
                    f"PROCESSING: "
                    f"{article['feed_title']}"
                )

                ai = generate_ai(
                    article
                )

                record = create_record(
                    article,
                    ai
                )

                new_articles.append(
                    record
                )

                existing_ids.add(
                    article["id"]
                )

                log(
                    f"STATUS: "
                    f"{record['snippet24_status']}"
                )

        except Exception as error:

            log(
                f"SOURCE ERROR "
                f"{source['name']}: "
                f"{type(error).__name__}: "
                f"{error}"
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
        "=========================================="
    )

    log(
        f"New articles created: "
        f"{len(new_articles)}"
    )

    log(
        f"Total stored articles: "
        f"{len(combined)}"
    )

    log(
        "articles.json saved successfully."
    )

    log(
        "========== SNIPPET24 CURATOR END =========="
    )


if __name__ == "__main__":
    process()
    