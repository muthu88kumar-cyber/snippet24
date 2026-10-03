// ============================================================
// SNIPPET24 — LIVE NEWS INTELLIGENCE WORKER
// Cloudflare Workers + D1 + Gemini
// Version: 1.0
//
// Flow:
//
// Approved Sources
//      ↓
// RSS / API
//      ↓
// Duplicate Check
//      ↓
// Gemini AI Editor
//      ↓
// 3–4 line story
//      ↓
// How it affects you
//      ↓
// Category + Location + Languages
//      ↓
// D1
//      ↓
// /api/stories
//
// IMPORTANT:
// GEMINI_API_KEY must be stored as a Cloudflare Secret.
// Never put the API key in GitHub code.
// ============================================================

import {
  SOURCES,
  CATEGORIES,
  LANGUAGES,
  getApprovedSources,
  isValidCategory
} from "./sources.js";


// ============================================================
// CONFIGURATION
// ============================================================

const DEFAULT_GEMINI_MODEL = "gemini-3.6-flash";

const MAX_STORIES = 200;

const FETCH_TIMEOUT_MS = 20000;

const USER_AGENT =
  "SNIPPET24/1.0 (+https://snippet24.in)";


// ============================================================
// MAIN HTTP HANDLER
// ============================================================

export default {

  async fetch(request, env, ctx) {

    const url = new URL(request.url);

    try {

      // --------------------------------------------------------
      // HEALTH
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname === "/api/health"
      ) {

        return jsonResponse({
          ok: true,
          service: "SNIPPET24 Live API",
          version: "1.0",
          time: new Date().toISOString()
        });

      }


      // --------------------------------------------------------
      // STORIES
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname === "/api/stories"
      ) {

        return await handleStories(request, env);

      }


      // --------------------------------------------------------
      // SINGLE STORY
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname.startsWith("/api/stories/")
      ) {

        const storyId =
          decodeURIComponent(
            url.pathname.replace("/api/stories/", "")
          );

        return await handleSingleStory(
          storyId,
          env
        );

      }


      // --------------------------------------------------------
      // MANUAL REFRESH
      // --------------------------------------------------------

      if (
        request.method === "POST" &&
        url.pathname === "/api/refresh"
      ) {

        if (!isAuthorized(request, env)) {

          return jsonResponse(
            {
              ok: false,
              error: "Unauthorized"
            },
            401
          );

        }

        const result =
          await refreshNews(env);

        return jsonResponse(result);

      }


      // --------------------------------------------------------
      // SOURCE STATUS
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname === "/api/source-status"
      ) {

        if (!isAuthorized(request, env)) {

          return jsonResponse(
            {
              ok: false,
              error: "Unauthorized"
            },
            401
          );

        }

        return await handleSourceStatus(env);

      }


      // --------------------------------------------------------
      // 404
      // --------------------------------------------------------

      return jsonResponse(
        {
          ok: false,
          error: "Not found"
        },
        404
      );

    } catch (error) {

      console.error(
        "SNIPPET24 API ERROR:",
        error
      );

      return jsonResponse(
        {
          ok: false,
          error: "Internal server error"
        },
        500
      );

    }

  },


  // ==========================================================
  // CLOUDFLARE CRON
  // ==========================================================

  async scheduled(event, env, ctx) {

    ctx.waitUntil(
      refreshNews(env)
        .catch(error => {
          console.error(
            "Scheduled refresh failed:",
            error
          );
        })
    );

  }

};


// ============================================================
// STORIES API
// ============================================================

async function handleStories(request, env) {

  const url = new URL(request.url);

  const category =
    cleanText(
      url.searchParams.get("category")
    );

  const location =
    cleanText(
      url.searchParams.get("location")
    );

  const language =
    cleanText(
      url.searchParams.get("language")
    ) || "en";

  let limit =
    Number(
      url.searchParams.get("limit") || 50
    );

  if (
    !Number.isFinite(limit) ||
    limit < 1
  ) {

    limit = 50;

  }

  limit =
    Math.min(
      limit,
      MAX_STORIES
    );


  let sql = `
    SELECT
      id,
      event_key,
      category,
      subcategory,
      location,
      country,
      title,
      summary,
      impact,
      publisher,
      source_url,
      source_type,
      published_at,
      updated_at,
      verification_status,
      verification_note,
      rights_status,
      language,
      translations_json,
      image_url,
      story_status,
      correction_version,
      created_at
    FROM stories
    WHERE rights_status = 'approved'
      AND story_status IN ('published', 'developing')
  `;

  const bindings = [];


  // ----------------------------------------------------------
  // CATEGORY FILTER
  // ----------------------------------------------------------

  if (
    category &&
    category !== "All"
  ) {

    sql += `
      AND category = ?
    `;

    bindings.push(category);

  }


  // ----------------------------------------------------------
  // LOCATION FILTER
  // ----------------------------------------------------------

  if (location) {

    sql += `
      AND (
        LOWER(location) LIKE LOWER(?)
        OR LOWER(country) LIKE LOWER(?)
      )
    `;

    bindings.push(
      `%${location}%`,
      `%${location}%`
    );

  }


  // ----------------------------------------------------------
  // SORT
  // ----------------------------------------------------------

  sql += `
    ORDER BY
      datetime(published_at) DESC
    LIMIT ?
  `;

  bindings.push(limit);


  const result =
    await env.DB
      .prepare(sql)
      .bind(...bindings)
      .all();


  const stories =
    (result.results || [])
      .map(
        story =>
          normalizeStory(
            story,
            language
          )
      );


  return jsonResponse({

    ok: true,

    count: stories.length,

    updated_at:
      new Date().toISOString(),

    stories

  });

}


// ============================================================
// SINGLE STORY
// ============================================================

async function handleSingleStory(
  storyId,
  env
) {

  const result =
    await env.DB
      .prepare(`
        SELECT *
        FROM stories
        WHERE id = ?
          AND rights_status = 'approved'
        LIMIT 1
      `)
      .bind(storyId)
      .first();


  if (!result) {

    return jsonResponse(
      {
        ok: false,
        error: "Story not found"
      },
      404
    );

  }


  return jsonResponse({
    ok: true,
    story:
      normalizeStory(
        result,
        "en"
      )
  });

}


// ============================================================
// NORMALIZE STORY FOR FRONTEND
// ============================================================

function normalizeStory(
  story,
  requestedLanguage
) {

  let translations = {};

  try {

    translations =
      story.translations_json
        ? JSON.parse(
            story.translations_json
          )
        : {};

  } catch {

    translations = {};

  }


  const translated =
    translations[
      requestedLanguage
    ];


  const finalTitle =
    translated?.title ||
    story.title;

  const finalSummary =
    translated?.summary ||
    story.summary;

  const finalImpact =
    translated?.impact ||
    story.impact;


  return {

    id: story.id,

    event_key:
      story.event_key,

    category:
      story.category,

    subcategory:
      story.subcategory || "",

    location:
      story.location || "",

    country:
      story.country || "",

    title:
      finalTitle,

    summary:
      finalSummary,

    impact:
      finalImpact,

    publisher:
      story.publisher,

    source:
      story.publisher,

    source_url:
      story.source_url,

    source_type:
      story.source_type,

    published_at:
      story.published_at,

    updated_at:
      story.updated_at,

    verification_status:
      story.verification_status,

    verification_note:
      story.verification_note || "",

    rights_status:
      story.rights_status,

    language:
      requestedLanguage,

    translations,

    image_url:
      story.image_url || null,

    story_status:
      story.story_status,

    correction_version:
      story.correction_version || 0

  };

}


// ============================================================
// NEWS REFRESH
// ============================================================

async function refreshNews(env) {

  const startedAt =
    new Date().toISOString();


  const approvedSources =
    getApprovedSources();


  if (
    approvedSources.length === 0
  ) {

    console.log(
      "SNIPPET24: No approved sources enabled."
    );

    await updateSystemState(
      env,
      "backend_status",
      "waiting_for_approved_sources"
    );

    return {

      ok: true,

      status:
        "waiting_for_approved_sources",

      sources_checked: 0,

      stories_created: 0,

      time: startedAt

    };

  }


  let totalFound = 0;
  let totalNew = 0;
  let totalCreated = 0;
  let totalSkipped = 0;


  await updateSystemState(
    env,
    "backend_status",
    "refreshing"
  );


  // ----------------------------------------------------------
  // PROCESS EACH APPROVED SOURCE
  // ----------------------------------------------------------

  for (
    const source
    of approvedSources
  ) {

    const logId =
      crypto.randomUUID();


    await createIngestionLog(
      env,
      logId,
      source.id,
      startedAt
    );


    try {

      const feed =
        await fetchFeed(
          source.feed_url
        );


      const items =
        parseFeed(
          feed,
          source
        );


      totalFound +=
        items.length;


      let sourceNew = 0;
      let sourceCreated = 0;
      let sourceSkipped = 0;


      for (
        const item
        of items
      ) {

        try {

          const itemKey =
            await makeHash(
              normalizeKey(
                source.id +
                "|" +
                item.title +
                "|" +
                item.link
              )
            );


          // --------------------------------------------------
          // SOURCE ITEM DUPLICATE CHECK
          // --------------------------------------------------

          const existingItem =
            await env.DB
              .prepare(`
                SELECT id
                FROM source_items
                WHERE item_key = ?
                LIMIT 1
              `)
              .bind(itemKey)
              .first();


          if (existingItem) {

            sourceSkipped++;

            continue;

          }


          // --------------------------------------------------
          // EVENT DUPLICATE CHECK
          // --------------------------------------------------

          const eventKey =
            await makeHash(
              normalizeKey(
                source.name +
                "|" +
                item.title +
                "|" +
                item.link
              )
            );


          const existingStory =
            await env.DB
              .prepare(`
                SELECT id
                FROM stories
                WHERE event_key = ?
                LIMIT 1
              `)
              .bind(eventKey)
              .first();


          // Save source item even if an existing event exists.

          const sourceItemId =
            crypto.randomUUID();


          await env.DB
            .prepare(`
              INSERT INTO source_items (
                id,
                source_id,
                item_key,
                title,
                source_url,
                published_at,
                description,
                processed,
                rejected,
                story_id
              )
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `)
            .bind(
              sourceItemId,
              source.id,
              itemKey,
              item.title,
              item.link,
              item.published_at,
              item.description || "",
              existingStory ? 1 : 0,
              existingStory ? 0 : 0,
              existingStory?.id || null
            )
            .run();


          sourceNew++;
          totalNew++;


          if (existingStory) {

            sourceSkipped++;

            continue;

          }


          // --------------------------------------------------
          // AI EDITOR
          // --------------------------------------------------

          const aiStory =
            await createAIStory(
              item,
              source,
              env
            );


          if (!aiStory) {

            await markSourceItemRejected(
              env,
              itemKey,
              "AI processing failed"
            );

            sourceSkipped++;

            continue;

          }


          // --------------------------------------------------
          // VALIDATE AI OUTPUT
          // --------------------------------------------------

          const validated =
            validateAIStory(
              aiStory,
              source,
              item
            );


          if (!validated.ok) {

            await markSourceItemRejected(
              env,
              itemKey,
              validated.error
            );

            sourceSkipped++;

            continue;

          }


          // --------------------------------------------------
          // SAVE STORY
          // --------------------------------------------------

          const storyId =
            crypto.randomUUID();


          await env.DB
            .prepare(`
              INSERT INTO stories (
                id,
                event_key,
                category,
                subcategory,
                location,
                country,
                title,
                summary,
                impact,
                publisher,
                source_url,
                source_type,
                published_at,
                updated_at,
                verification_status,
                verification_note,
                rights_status,
                language,
                translations_json,
                image_url,
                story_status,
                ai_processed,
                correction_version
              )
              VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?
              )
            `)
            .bind(
              storyId,
              eventKey,
              validated.story.category,
              validated.story.subcategory,
              validated.story.location,
              validated.story.country,
              validated.story.title,
              validated.story.summary,
              validated.story.impact,
              source.publisher,
              item.link,
              source.source_type,
              item.published_at ||
                new Date().toISOString(),
              new Date().toISOString(),
              "verified",
              "Generated from an approved source feed and reviewed by the SNIPPET24 editorial AI layer.",
              "approved",
              "en",
              JSON.stringify(
                validated.story.translations
              ),
              null,
              "published",
              1,
              0
            )
            .run();


          // --------------------------------------------------
          // LINK SOURCE TO STORY
          // --------------------------------------------------

          await env.DB
            .prepare(`
              INSERT INTO story_sources (
                id,
                story_id,
                publisher,
                source_url,
                source_type,
                published_at,
                verification_status
              )
              VALUES (?, ?, ?, ?, ?, ?, ?)
            `)
            .bind(
              crypto.randomUUID(),
              storyId,
              source.publisher,
              item.link,
              source.source_type,
              item.published_at,
              "verified"
            )
            .run();


          // --------------------------------------------------
          // UPDATE SOURCE ITEM
          // --------------------------------------------------

          await env.DB
            .prepare(`
              UPDATE source_items
              SET
                processed = 1,
                story_id = ?
              WHERE item_key = ?
            `)
            .bind(
              storyId,
              itemKey
            )
            .run();


          sourceCreated++;
          totalCreated++;


        } catch (itemError) {

          console.error(
            `Item processing failed for ${source.id}:`,
            itemError
          );

          sourceSkipped++;

        }

      }


      // ------------------------------------------------------
      // SOURCE SUCCESS
      // ------------------------------------------------------

      await updateSourceSuccess(
        env,
        source.id
      );


      await finishIngestionLog(
        env,
        logId,
        "success",
        items.length,
        sourceNew,
        sourceCreated,
        sourceSkipped,
        null
      );


    } catch (sourceError) {

      console.error(
        `Source failed: ${source.id}`,
        sourceError
      );


      await updateSourceError(
        env,
        source.id,
        String(
          sourceError?.message ||
          sourceError
        )
      );


      await finishIngestionLog(
        env,
        logId,
        "error",
        0,
        0,
        0,
        0,
        String(
          sourceError?.message ||
          sourceError
        )
      );

    }

  }


  const finishedAt =
    new Date().toISOString();


  await updateSystemState(
    env,
    "last_refresh_at",
    finishedAt
  );


  if (totalCreated > 0) {

    await updateSystemState(
      env,
      "last_successful_refresh_at",
      finishedAt
    );

  }


  await updateSystemState(
    env,
    "backend_status",
    "ready"
  );


  return {

    ok: true,

    status: "completed",

    sources_checked:
      approvedSources.length,

    items_found:
      totalFound,

    new_items:
      totalNew,

    stories_created:
      totalCreated,

    stories_skipped:
      totalSkipped,

    finished_at:
      finishedAt

  };

}


// ============================================================
// FETCH RSS / ATOM
// ============================================================

async function fetchFeed(feedUrl) {

  if (!feedUrl) {

    throw new Error(
      "Source feed URL is empty"
    );

  }


  const controller =
    new AbortController();


  const timeout =
    setTimeout(
      () =>
        controller.abort(),
      FETCH_TIMEOUT_MS
    );


  try {

    const response =
      await fetch(
        feedUrl,
        {
          method: "GET",

          headers: {
            "User-Agent":
              USER_AGENT,

            "Accept":
              "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
          },

          signal:
            controller.signal
        }
      );


    if (!response.ok) {

      throw new Error(
        `Feed returned HTTP ${response.status}`
      );

    }


    return await response.text();

  } finally {

    clearTimeout(timeout);

  }

}


// ============================================================
// RSS / ATOM PARSER
// ============================================================

function parseFeed(
  xml,
  source
) {

  if (!xml) {

    return [];

  }


  const items = [];


  // ----------------------------------------------------------
  // RSS <item>
  // ----------------------------------------------------------

  const rssMatches =
    xml.match(
      /<item\b[\s\S]*?<\/item>/gi
    ) || [];


  for (
    const block
    of rssMatches
  ) {

    const title =
      extractTag(
        block,
        "title"
      );

    const link =
      extractLink(
        block
      );

    const description =
      extractTag(
        block,
        "description"
      ) ||
      extractTag(
        block,
        "content:encoded"
      );


    const published =
      extractTag(
        block,
        "pubDate"
      ) ||
      extractTag(
        block,
        "dc:date"
      );


    if (!title || !link) {

      continue;

    }


    items.push({

      title:
        cleanText(title),

      link:
        cleanUrl(link),

      description:
        cleanText(
          description || ""
        ),

      published_at:
        normalizeDate(
          published
        )

    });

  }


  // ----------------------------------------------------------
  // ATOM <entry>
  // ----------------------------------------------------------

  const atomMatches =
    xml.match(
      /<entry\b[\s\S]*?<\/entry>/gi
    ) || [];


  for (
    const block
    of atomMatches
  ) {

    const title =
      extractTag(
        block,
        "title"
      );


    const link =
      extractAtomLink(
        block
      );


    const description =
      extractTag(
        block,
        "summary"
      ) ||
      extractTag(
        block,
        "content"
      );


    const published =
      extractTag(
        block,
        "published"
      ) ||
      extractTag(
        block,
        "updated"
      );


    if (!title || !link) {

      continue;

    }


    items.push({

      title:
        cleanText(title),

      link:
        cleanUrl(link),

      description:
        cleanText(
          description || ""
        ),

      published_at:
        normalizeDate(
          published
        )

    });

  }


  // ----------------------------------------------------------
  // REMOVE DUPLICATES
  // ----------------------------------------------------------

  const unique =
    new Map();


  for (
    const item
    of items
  ) {

    const key =
      normalizeKey(
        item.link ||
        item.title
      );


    if (!unique.has(key)) {

      unique.set(
        key,
        item
      );

    }

  }


  return Array.from(
    unique.values()
  )
  .slice(0, 30);

}


// ============================================================
// AI STORY GENERATION
// ============================================================

async function createAIStory(
  item,
  source,
  env
) {

  const apiKey =
    env.GEMINI_API_KEY;


  if (!apiKey) {

    throw new Error(
      "GEMINI_API_KEY is not configured"
    );

  }


  const model =
    env.GEMINI_MODEL ||
    DEFAULT_GEMINI_MODEL;


  const prompt = `
You are the editorial intelligence engine for SNIPPET24.

SNIPPET24 is a concise international news-intelligence product.

Your task is to transform a source-feed item into an original,
fact-based SNIPPET24 news brief.

SOURCE:
Publisher: ${source.publisher}
Country: ${source.country || "Unknown"}
Language: ${source.language || "en"}

HEADLINE:
${item.title}

SOURCE DESCRIPTION:
${item.description || "No description provided."}

SOURCE URL:
${item.link}

EDITORIAL RULES:

1. Do not copy the source article.
2. Do not reproduce long source text.
3. Use only facts supported by the supplied source information.
4. Do not invent names, numbers, quotes, locations, dates or causes.
5. Do not speculate about motives.
6. Do not sensationalize.
7. Do not provide medical diagnosis.
8. Do not provide investment advice.
9. Keep the main summary to 3–4 short sentences.
10. The impact field must explain "How it affects you" in one concise sentence.
11. Use neutral international English.
12. Identify the most appropriate SNIPPET24 category.
13. If location is unclear, return an empty location.
14. If country is unclear, return an empty country.
15. Translations must preserve the same meaning.
16. Do not add facts merely because they are commonly known.
17. Do not pretend the AI itself is a source.

ALLOWED CATEGORIES:

${CATEGORIES.join(", ")}

SUPPORTED TRANSLATIONS:

${LANGUAGES
  .filter(language => language.code !== "en")
  .map(language =>
    `${language.code} = ${language.name}`
  )
  .join(", ")}

Return ONLY valid JSON.

Required structure:

{
  "title": "short factual headline",
  "summary": "3–4 short factual sentences",
  "impact": "How it affects you: ...",
  "category": "one allowed category",
  "subcategory": "",
  "location": "",
  "country": "",
  "translations": {
    "ta": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "hi": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "te": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "kn": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "ml": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "bn": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "mr": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "gu": {
      "title": "",
      "summary": "",
      "impact": ""
    },
    "pa": {
      "title": "",
      "summary": "",
      "impact": ""
    }
  }
}
`;


  const endpoint =
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;


  const response =
    await fetch(
      endpoint,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",

          "x-goog-api-key":
            apiKey
        },

        body: JSON.stringify({

          contents: [
            {
              role: "user",

              parts: [
                {
                  text: prompt
                }
              ]
            }
          ],

          generationConfig: {

            temperature: 0.2,

            responseMimeType:
              "application/json"

          }

        })
      }
    );


  if (!response.ok) {

    const errorText =
      await response.text();

    throw new Error(
      `Gemini API error ${response.status}: ${errorText.slice(0, 500)}`
    );

  }


  const data =
    await response.json();


  const text =
    extractGeminiText(
      data
    );


  if (!text) {

    throw new Error(
      "Gemini returned empty output"
    );

  }


  return parseJSON(
    text
  );

}


// ============================================================
// GEMINI RESPONSE EXTRACTION
// ============================================================

function extractGeminiText(
  data
) {

  try {

    return (
      data
        ?.candidates?.[0]
        ?.content
        ?.parts?.map(
          part => part.text || ""
        )
        .join("")
        .trim() || ""
    );

  } catch {

    return "";

  }

}


// ============================================================
// VALIDATE AI STORY
// ============================================================

function validateAIStory(
  aiStory,
  source,
  item
) {

  if (!aiStory) {

    return {
      ok: false,
      error: "Empty AI story"
    };

  }


  const title =
    cleanText(
      aiStory.title
    );


  const summary =
    cleanText(
      aiStory.summary
    );


  const impact =
    cleanText(
      aiStory.impact
    );


  let category =
    cleanText(
      aiStory.category
    );


  if (
    !isValidCategory(category)
  ) {

    category = "World";

  }


  if (!title) {

    return {
      ok: false,
      error: "AI story has no title"
    };

  }


  if (!summary) {

    return {
      ok: false,
      error: "AI story has no summary"
    };

  }


  if (!impact) {

    return {
      ok: false,
      error: "AI story has no impact"
    };

  }


  if (
    title.length > 220
  ) {

    return {
      ok: false,
      error: "Title too long"
    };

  }


  if (
    summary.length > 1200
  ) {

    return {
      ok: false,
      error: "Summary too long"
    };

  }


  if (
    impact.length > 400
  ) {

    return {
      ok: false,
      error: "Impact too long"
    };

  }


  return {

    ok: true,

    story: {

      title,

      summary,

      impact:
        impact.startsWith(
          "How it affects you"
        )
          ? impact
          : `How it affects you: ${impact}`,

      category,

      subcategory:
        cleanText(
          aiStory.subcategory
        ),

      location:
        cleanText(
          aiStory.location
        ),

      country:
        cleanText(
          aiStory.country
        ),

      translations:
        validateTranslations(
          aiStory.translations
        )

    }

  };

}


// ============================================================
// TRANSLATIONS
// ============================================================

function validateTranslations(
  translations
) {

  const result = {};


  if (
    !translations ||
    typeof translations !== "object"
  ) {

    return result;

  }


  for (
    const language
    of LANGUAGES
  ) {

    if (
      language.code === "en"
    ) {

      continue;

    }


    const value =
      translations[
        language.code
      ];


    if (
      !value ||
      typeof value !== "object"
    ) {

      continue;

    }


    const title =
      cleanText(
        value.title
      );

    const summary =
      cleanText(
        value.summary
      );

    const impact =
      cleanText(
        value.impact
      );


    if (
      title &&
      summary &&
      impact
    ) {

      result[
        language.code
      ] = {

        title,

        summary,

        impact

      };

    }

  }


  return result;

}


// ============================================================
// SOURCE STATUS
// ============================================================

async function handleSourceStatus(
  env
) {

  const result =
    await env.DB
      .prepare(`
        SELECT
          id,
          name,
          feed_url,
          source_type,
          rights_status,
          enabled,
          verification_level,
          country,
          language,
          last_checked_at,
          last_success_at,
          last_error,
          created_at,
          updated_at
        FROM sources
        ORDER BY name ASC
      `)
      .all();


  return jsonResponse({

    ok: true,

    sources:
      result.results || [],

    configured_sources:
      SOURCES.length,

    approved_sources:
      getApprovedSources().length

  });

}


// ============================================================
// DATABASE SOURCE STATUS
// ============================================================

async function updateSourceSuccess(
  env,
  sourceId
) {

  const now =
    new Date().toISOString();


  await env.DB
    .prepare(`
      UPDATE sources
      SET
        last_checked_at = ?,
        last_success_at = ?,
        last_error = NULL,
        updated_at = ?
      WHERE id = ?
    `)
    .bind(
      now,
      now,
      now,
      sourceId
    )
    .run();

}


async function updateSourceError(
  env,
  sourceId,
  error
) {

  const now =
    new Date().toISOString();


  await env.DB
    .prepare(`
      UPDATE sources
      SET
        last_checked_at = ?,
        last_error = ?,
        updated_at = ?
      WHERE id = ?
    `)
    .bind(
      now,
      String(error).slice(0, 2000),
      now,
      sourceId
    )
    .run();

}


// ============================================================
// INGESTION LOG
// ============================================================

async function createIngestionLog(
  env,
  id,
  sourceId,
  startedAt
) {

  await env.DB
    .prepare(`
      INSERT INTO ingestion_log (
        id,
        source_id,
        started_at,
        status
      )
      VALUES (?, ?, ?, ?)
    `)
    .bind(
      id,
      sourceId,
      startedAt,
      "running"
    )
    .run();

}


async function finishIngestionLog(
  env,
  id,
  status,
  itemsFound,
  itemsNew,
  storiesCreated,
  storiesSkipped,
  errorMessage
) {

  await env.DB
    .prepare(`
      UPDATE ingestion_log
      SET
        finished_at = ?,
        status = ?,
        items_found = ?,
        items_new = ?,
        stories_created = ?,
        stories_skipped = ?,
        error_message = ?
      WHERE id = ?
    `)
    .bind(
      new Date().toISOString(),
      status,
      itemsFound,
      itemsNew,
      storiesCreated,
      storiesSkipped,
      errorMessage,
      id
    )
    .run();

}


// ============================================================
// SOURCE ITEM REJECTION
// ============================================================

async function markSourceItemRejected(
  env,
  itemKey,
  reason
) {

  await env.DB
    .prepare(`
      UPDATE source_items
      SET
        processed = 1,
        rejected = 1,
        rejection_reason = ?
      WHERE item_key = ?
    `)
    .bind(
      String(reason).slice(0, 1000),
      itemKey
    )
    .run();

}


// ============================================================
// SYSTEM STATE
// ============================================================

async function updateSystemState(
  env,
  key,
  value
) {

  await env.DB
    .prepare(`
      INSERT INTO system_state (
        key,
        value,
        updated_at
      )
      VALUES (?, ?, ?)
      ON CONFLICT(key)
      DO UPDATE SET
        value = excluded.value,
        updated_at = excluded.updated_at
    `)
    .bind(
      key,
      String(value),
      new Date().toISOString()
    )
    .run();

}


// ============================================================
// XML HELPERS
// ============================================================

function extractTag(
  xml,
  tag
) {

  const escaped =
    escapeRegExp(tag);


  const regex =
    new RegExp(
      `<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`,
      "i"
    );


  const match =
    xml.match(regex);


  return match
    ? decodeXML(match[1])
    : "";

}


function extractLink(
  block
) {

  const direct =
    extractTag(
      block,
      "link"
    );


  if (direct) {

    return direct;

  }


  const match =
    block.match(
      /<link[^>]*href=["']([^"']+)["'][^>]*>/i
    );


  return match
    ? match[1]
    : "";

}


function extractAtomLink(
  block
) {

  const links =
    block.match(
      /<link\b[^>]*>/gi
    ) || [];


  for (
    const link
    of links
  ) {

    const rel =
      link.match(
        /rel=["']([^"']+)["']/i
      )?.[1];


    const href =
      link.match(
        /href=["']([^"']+)["']/i
      )?.[1];


    if (
      href &&
      (!rel || rel === "alternate")
    ) {

      return href;

    }

  }


  return "";

}


// ============================================================
// TEXT CLEANING
// ============================================================

function cleanText(
  value
) {

  if (
    value === null ||
    value === undefined
  ) {

    return "";

  }


  return decodeXML(
    String(value)
  )
    .replace(
      /<script[\s\S]*?<\/script>/gi,
      " "
    )
    .replace(
      /<style[\s\S]*?<\/style>/gi,
      " "
    )
    .replace(
      /<[^>]+>/g,
      " "
    )
    .replace(
      /\s+/g,
      " "
    )
    .trim();

}


function decodeXML(
  value
) {

  return String(value || "")
    .replace(
      /&amp;/gi,
      "&"
    )
    .replace(
      /&lt;/gi,
      "<"
    )
    .replace(
      /&gt;/gi,
      ">"
    )
    .replace(
      /&quot;/gi,
      '"'
    )
    .replace(
      /&#39;/gi,
      "'"
    )
    .replace(
      /&#x27;/gi,
      "'"
    )
    .replace(
      /&#(\d+);/g,
      (_, code) =>
        String.fromCharCode(
          Number(code)
        )
    )
    .replace(
      /&#x([0-9a-f]+);/gi,
      (_, code) =>
        String.fromCharCode(
          parseInt(code, 16)
        )
    );

}


function cleanUrl(
  value
) {

  return String(
    value || ""
  ).trim();

}


function normalizeKey(
  value
) {

  return String(
    value || ""
  )
    .toLowerCase()
    .replace(
      /\s+/g,
      " "
    )
    .trim();

}


function normalizeDate(
  value
) {

  if (!value) {

    return new Date()
      .toISOString();

  }


  const date =
    new Date(value);


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return new Date()
      .toISOString();

  }


  return date.toISOString();

}


function escapeRegExp(
  value
) {

  return String(value)
    .replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&"
    );

}


// ============================================================
// JSON PARSING
// ============================================================

function parseJSON(
  text
) {

  const cleaned =
    String(text || "")
      .trim()
      .replace(
        /^```json\s*/i,
        ""
      )
      .replace(
        /^```\s*/i,
        ""
      )
      .replace(
        /\s*```$/i,
        ""
      )
      .trim();


  try {

    return JSON.parse(
      cleaned
    );

  } catch {

    const first =
      cleaned.indexOf("{");

    const last =
      cleaned.lastIndexOf("}");


    if (
      first !== -1 &&
      last > first
    ) {

      return JSON.parse(
        cleaned.slice(
          first,
          last + 1
        )
      );

    }


    throw new Error(
      "Invalid JSON returned by AI"
    );

  }

}


// ============================================================
// SHA-256 HASH
// ============================================================

async function makeHash(
  value
) {

  const data =
    new TextEncoder()
      .encode(
        value
      );


  const hash =
    await crypto.subtle.digest(
      "SHA-256",
      data
    );


  return Array
    .from(
      new Uint8Array(hash)
    )
    .map(
      byte =>
        byte
          .toString(16)
          .padStart(2, "0")
    )
    .join("");

}


// ============================================================
// AUTHENTICATION
// ============================================================

function isAuthorized(
  request,
  env
) {

  const configuredToken =
    env.ADMIN_TOKEN;


  if (!configuredToken) {

    return false;

  }


  const authorization =
    request.headers.get(
      "Authorization"
    );


  if (!authorization) {

    return false;

  }


  const expected =
    `Bearer ${configuredToken}`;


  return authorization === expected;

}


// ============================================================
// RESPONSE
// ============================================================

function jsonResponse(
  data,
  status = 200
) {

  return new Response(
    JSON.stringify(
      data,
      null,
      2
    ),
    {
      status,

      headers: {
        "Content-Type":
          "application/json; charset=utf-8",

        "Cache-Control":
          "no-store",

        "Access-Control-Allow-Origin":
          "*",

        "Access-Control-Allow-Headers":
          "Content-Type, Authorization"
      }
    }
  );

}