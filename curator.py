import os
import json
import hashlib
import re
import time
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai


ARTICLES_FILE = "articles.json"
SOURCES_FILE = "sources.json"

MAX_ARTICLES_PER_SOURCE = 10
MAX_TOTAL_ARTICLES = 30
MAX_STORED_ARTICLES = 500

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 "
    "Snippet24-NewsBot/1.0"
)


def log(message):
    print(f"[SNIPPET24] {message}", flush=True)


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
    temp_file = filename + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp_file, filename)


def clean_text(text):
    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"<script.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

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
        return []

    valid = []

    for source in sources:

        if not isinstance(source, dict):
            continue

        if not source.get("reuse_policy_checked"):
            continue

        if not source.get("allow_publish"):
            continue

        if not source.get("allow_ai_rewrite"):
            continue

        if not source.get("feed_url"):
            continue

        valid.append(source)

    return valid


def request_url(url):

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml, "
            "application/xml, "
            "text/xml, "
            "text/html, "
            "*/*"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    last_error = None

    for attempt in range(1, 4):

        try:

            log(
                f"HTTP attempt {attempt}/3: {url}"
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            response.raise_for_status()

            log(
                f"HTTP {response.status_code}: "
                f"{len(response.content)} bytes"
            )

            return response

        except Exception as error:

            last_error = error

            log(
                f"HTTP attempt {attempt} failed: "
                f"{error}"
            )

            if attempt < 3:
                time.sleep(attempt * 2)

    raise last_error


def parse_rss_response(response):

    parsed = feedparser.parse(
        response.content
    )

    if parsed.bozo:
        log(
            f"RSS parser warning: "
            f"{parsed.bozo_exception}"
        )

    entries = parsed.entries or []

    log(
        f"RSS entries found: {len(entries)}"
    )

    return entries


def fetch_rss(source):

    url = source["feed_url"]

    log(
        f"READING RSS: {source['name']}"
    )

    log(
        f"RSS URL: {url}"
    )

    try:

        response = request_url(url)

        entries = parse_rss_response(
            response
        )

        if entries:
            return entries

    except Exception as error:

        log(
            f"RSS failed for "
            f"{source['name']}: {error}"
        )

    return []


def fetch_pib_fallback(source):

    fallback_url = source.get(
        "fallback_url"
    )

    if not fallback_url:
        return []

    log(
        "RSS unavailable. Trying PIB "
        "web-page fallback."
    )

    log(
        f"Fallback URL: {fallback_url}"
    )

    try:

        response = request_url(
            fallback_url
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        entries = []

        seen_urls = set()

        /*
        Find PIB press release links.
        */

        for link in soup.find_all("a"):

            href = link.get(
                "href",
                ""
            )

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True
                )
            )

            if not href or not title:
                continue

            if "PressRelease" not in href:
                continue

            if not (
                "PressReleasePage" in href
                or "PressReleseDetail" in href
            ):
                continue

            if href.startswith("/"):
                href = (
                    "https://www.pib.gov.in"
                    + href
                )

            elif href.startswith(
                "http://"
            ):
                href = (
                    "https://"
                    + href[7:]
                )

            elif not href.startswith(
                "https://"
            ):
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)

            entries.append({
                "title": title,
                "link": href,
                "summary": "",
                "description": "",
                "published": ""
            })

            if len(entries) >= (
                MAX_ARTICLES_PER_SOURCE
            ):
                break

        log(
            "PIB fallback entries found: "
            f"{len(entries)}"
        )

        return entries

    except Exception as error:

        log(
            f"PIB fallback failed: {error}"
        )

        return []


def build_articles(source, entries):

    articles = []

    for item in entries[
        :MAX_ARTICLES_PER_SOURCE
    ]:

        title = clean_text(
            item.get("title", "")
        )

        link = (
            item.get("link", "")
            or item.get("url", "")
        )

        link = str(link).strip()

        description = clean_text(
            item.get("summary", "")
            or item.get("description", "")
            or item.get("content", "")
        )

        published = (
            item.get("published", "")
            or item.get("updated", "")
            or ""
        )

        if not title or not link:
            continue

        article_id = make_id(
            title,
            link
        )

        articles.append({
            "id": article_id,

            "source": source["name"],

            "source_website": source.get(
                "website",
                ""
            ),

            "source_url": link,

            "feed_title": title,

            "feed_summary": description[
                :5000
            ],

            "published": str(
                published
            ),

            "category": source.get(
                "category",
                "General"
            ),

            "allow_ai_rewrite": bool(
                source.get(
                    "allow_ai_rewrite",
                    False
                )
            )
        })

    return articles


def build_prompt(article):

    return f"""
You are the editorial AI for Snippet24.

You are NOT the original publisher.

Create an original news explanation using ONLY
the information supplied below.

COPYRIGHT RULES:

- Do not copy sentences from the source.
- Do not reproduce the source article.
- Do not create fake quotations.
- Do not add information from your own knowledge.
- Do not invent names, numbers, dates or events.
- Do not pretend Snippet24 is the original publisher.
- Keep the original source URL unchanged.
- Use genuinely original wording.

SOURCE:

Publisher:
{article["source"]}

Original headline:
{article["feed_title"]}

RSS information:
{article["feed_summary"]}

Original URL:
{article["source_url"]}

Return ONLY valid JSON.

Required JSON:

{{
  "headline_1": "",
  "headline_2": "",
  "headline_3": "",
  "summary": "",
  "deep_dive": [],
  "risk_level": "REVIEW",
  "risk_reasons": []
}}

HEADLINES:

Create 3 substantially different
original headlines.

SUMMARY:

Write a concise original summary based
ONLY on the supplied information.

DEEP DIVE:

Write exactly 30 short information lines.

Do NOT invent facts.

If the supplied information is insufficient,
say that the supplied information is limited.
Do not invent details merely to reach 30 lines.

RISK:

AUTO:
Straightforward factual information.

REVIEW:
Allegations, accusations, crime, politics,
named individuals accused of wrongdoing,
deaths, serious injuries, medical claims,
financial claims, uncertain information,
sensitive personal information.

BLOCK:
Clearly unsafe, malicious, fabricated,
private personal information, or instructions
for wrongdoing.

Never create direct quotations.
"""


def fallback_article(article):

    summary = article.get(
        "feed_summary",
        ""
    )

    if not summary:

        summary = (
            "The available source information "
            "is limited. Please open the original "
            "publication for the complete report."
        )

    lines = []

    lines.append(
        "The available source information "
        "was insufficient for a complete "
        "30-point explanation."
    )

    for _ in range(29):

        lines.append(
            "Additional verified detail is "
            "not available in the supplied "
            "source information."
        )

    return {
        "headline_1": article[
            "feed_title"
        ],

        "headline_2": (
            "Latest update: "
            + article["feed_title"]
        ),

        "headline_3": (
            "What the source reports: "
            + article["feed_title"]
        ),

        "summary": summary[:1000],

        "deep_dive": lines,

        "risk_level": "REVIEW",

        "risk_reasons": [
            "AI generation was unavailable "
            "or source information was limited."
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
            if response.text
            else ""
        ).strip()

        if not text:
            raise ValueError(
                "Gemini returned empty response."
            )

        if text.startswith("```"):

            text = re.sub(
                r"^```(?:json)?\s*",
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

        headlines = [
            str(
                result.get(
                    "headline_1",
                    ""
                )
            ).strip(),

            str(
                result.get(
                    "headline_2",
                    ""
                )
            ).strip(),

            str(
                result.get(
                    "headline_3",
                    ""
                )
            ).strip()
        ]

        deep_dive = result.get(
            "deep_dive",
            []
        )

        if not isinstance(
            deep_dive,
            list
        ):
            raise ValueError(
                "deep_dive is not a list."
            )

        if len(deep_dive) != 30:

            raise ValueError(
                "Deep dive must contain "
                "exactly 30 lines."
            )

        if not all(headlines):

            raise ValueError(
                "Missing headline."
            )

        summary = str(
            result.get(
                "summary",
                ""
            )
        ).strip()

        if not summary:

            raise ValueError(
                "Missing summary."
            )

        risk_level = str(
            result.get(
                "risk_level",
                "REVIEW"
            )
        ).upper().strip()

        if risk_level not in {
            "AUTO",
            "REVIEW",
            "BLOCK"
        }:

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

        return {
            "headline_1": headlines[0],

            "headline_2": headlines[1],

            "headline_3": headlines[2],

            "summary": summary,

            "deep_dive": [
                str(x).strip()
                for x in deep_dive
            ],

            "risk_level": risk_level,

            "risk_reasons": [
                str(x).strip()
                for x in risk_reasons
            ]
        }

    except Exception as error:

        log(
            f"AI generation failed: {error}"
        )

        return fallback_article(
            article
        )


def fetch_feed(source):

    entries = fetch_rss(
        source
    )

    if not entries:

        entries = fetch_pib_fallback(
            source
        )

    return build_articles(
        source,
        entries
    )


def process():

    log(
        "========== SNIPPET24 CURATOR START =========="
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
        if isinstance(item, dict)
        and item.get("id")
    }

    new_articles = []

    for source in sources:

        try:

            articles = fetch_feed(
                source
            )

            if not articles:

                log(
                    f"No articles from "
                    f"{source['name']}"
                )

                continue

            log(
                f"Usable articles from "
                f"{source['name']}: "
                f"{len(articles)}"
            )

            for article in articles:

                if article["id"] in existing_ids:
                    continue

                if not article[
                    "allow_ai_rewrite"
                ]:
                    continue

                log(
                    "Generating: "
                    + article["feed_title"]
                )

                ai = generate_ai(
                    article
                )

                status = (
                    "PUBLISHED"
                    if ai["risk_level"] == "AUTO"
                    else ai["risk_level"]
                )

                record = {

                    "id": article["id"],

                    "title": ai[
                        "headline_1"
                    ],

                    "alternative_headlines": [
                        ai["headline_2"],
                        ai["headline_3"]
                    ],

                    "summary": ai[
                        "summary"
                    ],

                    "deep_dive": ai[
                        "deep_dive"
                    ],

                    "category": article[
                        "category"
                    ],

                    "source": article[
                        "source"
                    ],

                    "source_url": article[
                        "source_url"
                    ],

                    "source_website": article[
                        "source_website"
                    ],

                    "original_rss_title": article[
                        "feed_title"
                    ],

                    "published_at": article[
                        "published"
                    ],

                    "snippet24_status": status,

                    "risk_level": ai[
                        "risk_level"
                    ],

                    "risk_reasons": ai[
                        "risk_reasons"
                    ],

                    "created_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )
                }

                new_articles.append(
                    record
                )

                existing_ids.add(
                    article["id"]
                )

                log(
                    f"Created article "
                    f"status={status}"
                )

                if len(
                    new_articles
                ) >= MAX_TOTAL_ARTICLES:

                    break

            if len(
                new_articles
            ) >= MAX_TOTAL_ARTICLES:

                break

        except Exception as error:

            log(
                f"Source error "
                f"{source.get('name', 'Unknown')}: "
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

    published_count = sum(
        1
        for article in combined
        if article.get(
            "snippet24_status"
        ) == "PUBLISHED"
    )

    review_count = sum(
        1
        for article in combined
        if article.get(
            "snippet24_status"
        ) == "REVIEW"
    )

    block_count = sum(
        1
        for article in combined
        if article.get(
            "snippet24_status"
        ) == "BLOCK"
    )

    log(
        "============================================"
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
        f"Published: "
        f"{published_count}"
    )

    log(
        f"Review: "
        f"{review_count}"
    )

    log(
        f"Blocked: "
        f"{block_count}"
    )

    log(
        "articles.json saved successfully."
    )

    log(
        "=========== SNIPPET24 CURATOR END =========="
    )


if __name__ == "__main__":
    process()