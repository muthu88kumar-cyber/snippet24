import os
import json
import hashlib
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

import feedparser
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

ARTICLES_FILE = "articles.json"
SOURCES_FILE = "sources.json"

MAX_ARTICLES_PER_SOURCE = 10
MAX_TOTAL_ARTICLES = 30
MAX_STORED_ARTICLES = 500

RSS_TIMEOUT = 30


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[SNIPPET24] {message}")


# ============================================================
# JSON HELPERS
# ============================================================

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


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = str(text)

    # Remove HTML
    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # Remove excessive whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ARTICLE ID
# ============================================================

def make_id(title, url):
    value = f"{title}|{url}".encode("utf-8")

    return hashlib.sha256(
        value
    ).hexdigest()[:20]


# ============================================================
# LOAD APPROVED SOURCES
# ============================================================

def load_sources():

    sources = load_json(
        SOURCES_FILE,
        []
    )

    if not isinstance(sources, list):
        log("sources.json is not a list.")
        return []

    valid = []

    for source in sources:

        if not isinstance(source, dict):
            continue

        if not source.get(
            "reuse_policy_checked",
            False
        ):
            continue

        if not source.get(
            "allow_publish",
            False
        ):
            continue

        if not source.get(
            "feed_url"
        ):
            continue

        valid.append(source)

    return valid


# ============================================================
# FETCH RSS FEED
# ============================================================

def fetch_feed(source):

    source_name = source.get(
        "name",
        "Unknown source"
    )

    feed_url = source.get(
        "feed_url",
        ""
    )

    log(f"Reading RSS: {source_name}")
    log(f"RSS URL: {feed_url}")

    articles = []

    try:

        request = urllib.request.Request(
            feed_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; Snippet24/1.0; "
                    "+https://snippet24.in/)"
                ),
                "Accept": (
                    "application/rss+xml, "
                    "application/xml, "
                    "text/xml, "
                    "*/*"
                )
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=RSS_TIMEOUT
        ) as response:

            data = response.read()

        feed = feedparser.parse(data)

    except urllib.error.URLError as error:

        log(
            f"RSS connection error for "
            f"{source_name}: {error}"
        )

        return []

    except Exception as error:

        log(
            f"RSS error for "
            f"{source_name}: {error}"
        )

        return []

    if feed.bozo:

        log(
            f"RSS warning for "
            f"{source_name}: "
            f"{feed.bozo_exception}"
        )

    entries = feed.entries

    log(
        f"RSS entries found for "
        f"{source_name}: {len(entries)}"
    )

    for item in entries[
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

        if not title:
            continue

        if not link:
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

            "source": source_name,

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

    return articles


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(article):

    return f"""
You are the editorial AI for Snippet24.

IMPORTANT RULES:

1. Do NOT copy sentences from the source.
2. Do NOT reproduce the source article.
3. Do NOT pretend Snippet24 is the original publisher.
4. Write genuinely original wording.
5. Use ONLY facts explicitly present in the supplied RSS information.
6. Do NOT add facts from your own knowledge.
7. If the supplied information is insufficient, say so.
8. Do not invent names, numbers, dates, quotes or events.
9. Do not create direct quotations.
10. Keep the source URL unchanged.
11. Do not create facts merely to reach 30 lines.
12. Do not make unsupported claims.

SOURCE INFORMATION:

Source:
{article["source"]}

Original RSS headline:
{article["feed_title"]}

RSS summary:
{article["feed_summary"]}

Original source URL:
{article["source_url"]}

Return ONLY valid JSON.

Required structure:

{{
  "headline_1": "",
  "headline_2": "",
  "headline_3": "",

  "summary": "",

  "deep_dive": [
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ""
  ],

  "risk_level": "AUTO",
  "risk_reasons": []
}}

HEADLINES:

Create three substantially different original headlines.

SUMMARY:

Write a concise original summary based ONLY on the supplied RSS information.

DEEP DIVE:

Write exactly 30 short numbered-information lines.

Every line must be based only on the supplied RSS information.

If there are not enough facts for 30 lines, clearly state that additional verified information is not available rather than inventing facts.

RISK LEVEL:

Use AUTO only when:

- information is straightforward;
- no allegations are being made;
- no private personal information appears;
- no obvious defamation issue exists;
- no medical emergency advice is involved;
- no unverified accusation appears.

Use REVIEW for:

- allegations;
- crime accusations;
- political controversy;
- named individuals accused of wrongdoing;
- deaths or serious injuries;
- medical claims;
- financial claims;
- potentially defamatory statements;
- uncertain factual information;
- sensitive personal information.

Use BLOCK for:

- clearly unsafe content;
- private personal information;
- content that appears malicious or fabricated;
- instructions for wrongdoing;
- content that should not be published.

Never use a source quote.
"""


# ============================================================
# SAFE FALLBACK
# ============================================================

def fallback_article(article):

    summary = article.get(
        "feed_summary",
        ""
    )

    if not summary:

        summary = (
            "The available RSS information "
            "does not contain enough detail "
            "for a full summary."
        )

    lines = []

    for i in range(30):

        if i == 0:

            lines.append(
                "The source reports: "
                + summary[:250]
            )

        else:

            lines.append(
                "Additional verified detail is "
                "not available in the supplied "
                "RSS information."
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
            "What we know about "
            + article["feed_title"]
        ),

        "summary": summary[:1000],

        "deep_dive": lines,

        "risk_level": "REVIEW",

        "risk_reasons": [
            "AI generation was unavailable."
        ]
    }


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_ai(article):

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        log(
            "GEMINI_API_KEY is missing."
        )

        return fallback_article(
            article
        )

    try:

        log(
            f"Generating AI article: "
            f"{article['feed_title']}"
        )

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

        if not text:

            raise ValueError(
                "Gemini returned empty response."
            )

        # Remove Markdown JSON fences
        if text.startswith("```"):

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

        # ----------------------------------------------------
        # HEADLINES
        # ----------------------------------------------------

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

        if not all(headlines):

            raise ValueError(
                "One or more headlines are missing."
            )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary = str(
            result.get(
                "summary",
                ""
            )
        ).strip()

        if not summary:

            raise ValueError(
                "AI summary is empty."
            )

        # ----------------------------------------------------
        # DEEP DIVE
        # ----------------------------------------------------

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

        if len(deep_dive) != 30:

            raise ValueError(
                "Deep dive must contain "
                "exactly 30 lines."
            )

        deep_dive = [

            str(x).strip()

            for x in deep_dive
        ]

        if not all(deep_dive):

            raise ValueError(
                "Deep dive contains "
                "an empty line."
            )

        # ----------------------------------------------------
        # RISK LEVEL
        # ----------------------------------------------------

        risk_level = str(
            result.get(
                "risk_level",
                "REVIEW"
            )
        ).upper().strip()

        if risk_level not in [
            "AUTO",
            "REVIEW",
            "BLOCK"
        ]:

            risk_level = "REVIEW"

        # ----------------------------------------------------
        # RISK REASONS
        # ----------------------------------------------------

        risk_reasons = result.get(
            "risk_reasons",
            []
        )

        if not isinstance(
            risk_reasons,
            list
        ):

            risk_reasons = []

        risk_reasons = [

            str(x).strip()

            for x in risk_reasons

            if str(x).strip()
        ]

        return {

            "headline_1": headlines[0],

            "headline_2": headlines[1],

            "headline_3": headlines[2],

            "summary": summary,

            "deep_dive": deep_dive,

            "risk_level": risk_level,

            "risk_reasons": risk_reasons
        }

    except Exception as error:

        log(
            f"AI generation failed: "
            f"{error}"
        )

        return fallback_article(
            article
        )


# ============================================================
# MAIN PROCESS
# ============================================================

def process():

    log(
        "========== SNIPPET24 CURATOR START =========="
    )

    # --------------------------------------------------------
    # LOAD SOURCES
    # --------------------------------------------------------

    sources = load_sources()

    log(
        f"Approved sources loaded: "
        f"{len(sources)}"
    )

    if not sources:

        log(
            "No approved sources found."
        )

        return

    # --------------------------------------------------------
    # LOAD EXISTING ARTICLES
    # --------------------------------------------------------

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

        if isinstance(
            item,
            dict
        )

        and item.get("id")
    }

    new_articles = []

    # --------------------------------------------------------
    # PROCESS SOURCES
    # --------------------------------------------------------

    for source in sources:

        try:

            feed_articles = fetch_feed(
                source
            )

            if not feed_articles:

                log(
                    f"No RSS articles found: "
                    f"{source.get('name', 'Unknown')}"
                )

                continue

            for article in feed_articles:

                # ------------------------------------------------
                # DUPLICATE CHECK
                # ------------------------------------------------

                if article["id"] in existing_ids:

                    log(
                        f"Skipping duplicate: "
                        f"{article['feed_title']}"
                    )

                    continue

                # ------------------------------------------------
                # AI PERMISSION CHECK
                # ------------------------------------------------

                if not article[
                    "allow_ai_rewrite"
                ]:

                    log(
                        f"AI rewrite disabled: "
                        f"{article['feed_title']}"
                    )

                    continue

                # ------------------------------------------------
                # GENERATE ARTICLE
                # ------------------------------------------------

                ai = generate_ai(
                    article
                )

                # ------------------------------------------------
                # PUBLICATION STATUS
                # ------------------------------------------------

                if ai[
                    "risk_level"
                ] == "AUTO":

                    status = "PUBLISHED"

                else:

                    status = ai[
                        "risk_level"
                    ]

                # ------------------------------------------------
                # CREATE RECORD
                # ------------------------------------------------

                record = {

                    "id": article[
                        "id"
                    ],

                    "title": ai[
                        "headline_1"
                    ],

                    "alternative_headlines": [

                        ai[
                            "headline_2"
                        ],

                        ai[
                            "headline_3"
                        ]
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
                    f"Article created: "
                    f"{record['title']}"
                )

                # ------------------------------------------------
                # MAX NEW ARTICLES
                # ------------------------------------------------

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
                f"Source processing error "
                f"for {source.get('name', 'Unknown')}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # COMBINE ARTICLES
    # --------------------------------------------------------

    combined = (
        new_articles
        + existing
    )

    # Keep latest 500
    combined = combined[
        :MAX_STORED_ARTICLES
    ]

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_json(
        ARTICLES_FILE,
        combined
    )

    log(
        f"New articles: "
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


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    process()