// ============================================================
// SNIPPET24 — LIVE NEWS INTELLIGENCE WORKER
// Cloudflare Workers + D1 + Gemini
// Version: 2.0
//
// FLOW
//
// Approved Source
//      ↓
// RSS / Atom
//      ↓
// Source Item Duplicate Check
//      ↓
// Event Duplicate Check
//      ↓
// Gemini Editorial AI
//      ↓
// Validation
//      ↓
// 3–4 Line Brief
//      ↓
// How it affects you
//      ↓
// Category + Location + Language
//      ↓
// D1
//      ↓
// /api/stories
//
// IMPORTANT
//
// GEMINI_API_KEY must be stored as a Cloudflare Secret.
// ADMIN_TOKEN must also be stored as a Cloudflare Secret.
//
// NEVER put either secret in GitHub.
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

const DEFAULT_GEMINI_MODEL =
  "gemini-3.6-flash";

const MAX_STORIES =
  200;

const MAX_FEED_ITEMS =
  30;

const FETCH_TIMEOUT_MS =
  20000;

const USER_AGENT =
  "SNIPPET24/2.0 (+https://snippet24.in)";


// ============================================================
// MAIN HTTP HANDLER
// ============================================================

export default {

  async fetch(
    request,
    env,
    ctx
  ) {

    const url =
      new URL(request.url);

    try {

      // --------------------------------------------------------
      // HEALTH
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname === "/api/health"
      ) {

        return await handleHealth(
          env
        );

      }


      // --------------------------------------------------------
      // STORIES
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname === "/api/stories"
      ) {

        return await handleStories(
          request,
          env
        );

      }


      // --------------------------------------------------------
      // SINGLE STORY
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname.startsWith(
          "/api/stories/"
        )
      ) {

        const storyId =
          decodeURIComponent(
            url.pathname.replace(
              "/api/stories/",
              ""
            )
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

        if (
          !isAuthorized(
            request,
            env
          )
        ) {

          return jsonResponse(
            {
              ok: false,
              error: "Unauthorized"
            },
            401
          );

        }

        const result =
          await refreshNews(
            env
          );

        return jsonResponse(
          result
        );

      }


      // --------------------------------------------------------
      // SOURCE STATUS
      // --------------------------------------------------------

      if (
        request.method === "GET" &&
        url.pathname ===
          "/api/source-status"
      ) {

        if (
          !isAuthorized(
            request,
            env
          )
        ) {

          return jsonResponse(
            {
              ok: false,
              error: "Unauthorized"
            },
            401
          );

        }

        return await handleSourceStatus(
          env
        );

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
          error:
            String(
              error?.message ||
              error
            ).slice(0, 1000)
        },
        500
      );

    }

  },


  // ==========================================================
  // CLOUDFLARE CRON
  // ==========================================================

  async scheduled(
    event,
    env,
    ctx
  ) {

    ctx.waitUntil(
      refreshNews(
        env
      ).catch(
        error => {

          console.error(
            "SNIPPET24 scheduled refresh failed:",
            error
          );

        }
      )
    );

  }

};


// ============================================================
// HEALTH
// ============================================================

async function handleHealth(
  env
) {

  let database =
    false;

  let storiesCount =
    0;

  let approvedSources =
    0;

  try {

    const result =
      await env.DB
        .prepare(`
          SELECT COUNT(*) AS count
          FROM stories
        `)
        .first();

    storiesCount =
      Number(
        result?.count || 0
      );

    database =
      true;

  } catch (error) {

    console.error(
      "Health database check failed:",
      error
    );

  }


  try {

    const result =
      await env.DB
        .prepare(`
          SELECT COUNT(*) AS count
          FROM sources
          WHERE enabled = 1
            AND rights_status = 'approved'
        `)
        .first();

    approvedSources =
      Number(
        result?.count || 0
      );

  } catch (error) {

    console.error(
      "Health source check failed:",
      error
    );

  }


  return jsonResponse({

    ok:
      database,

    service:
      "SNIPPET24 Live API",

    version:
      "2.0",

    database:
      database
        ? "connected"
        : "error",

    stories:
      storiesCount,

    approved_sources:
      approvedSources,

    configured_sources:
      SOURCES.length,

    gemini:
      env.GEMINI_API_KEY
        ? "configured"
        : "missing",

    time:
      new Date().toISOString()

  });

}


// ============================================================
// STORIES API
// ============================================================

async function handleStories(
  request,
  env
) {

  const url =
    new URL(request.url);


  const category =
    cleanText(
      url.searchParams.get(
        "category"
      )
    );


  const location =
    cleanText(
      url.searchParams.get(
        "location"
      )
    );


  const language =
    cleanText(
      url.searchParams.get(
        "language"
      )
    ) || "en";


  let limit =
    Number(
      url.searchParams.get(
        "limit"
      ) || 50
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
      AND story_status IN (
        'published',
        'developing'
      )
  `;


  const bindings = [];


  // ----------------------------------------------------------
  // CATEGORY
  // ----------------------------------------------------------

  if (
    category &&
    category !== "All"
  ) {

    sql += `
      AND category = ?
    `;

    bindings.push(
      category
    );

  }


  // ----------------------------------------------------------
  // LOCATION
  // ----------------------------------------------------------

  if (location) {

    sql += `
      AND (
        LOWER(location)
          LIKE LOWER(?)
        OR
        LOWER(country)
          LIKE LOWER(?)
      )
    `;

    bindings.push(
      `%${location}%`,
      `%${location}%`
    );

  }


  // ----------------------------------------------------------
  // NEWEST FIRST
  // ----------------------------------------------------------

  sql += `
    ORDER BY
      datetime(published_at) DESC
    LIMIT ?
  `;


  bindings.push(
    limit
  );


  const result =
    await env.DB
      .prepare(sql)
      .bind(...bindings)
      .all();


  const stories =
    (
      result.results || []
    ).map(
      story =>
        normalizeStory(
          story,
          language
        )
    );


  return jsonResponse({

    ok: true,

    count:
      stories.length,

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
      .bind(
        storyId
      )
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
// NORMALIZE STORY
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

    id:
      story.id,

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

    translations:
      translations,

    image_url:
      story.image_url || null,

    story_status:
      story.story_status,

    correction_version:
      Number(
        story.correction_version || 0
      )

  };

}


// ============================================================
// NEWS REFRESH
// ============================================================

async function refreshNews(
  env
) {

  const startedAt =
    new Date().toISOString();


  // ----------------------------------------------------------
  // SYNC CONFIGURED SOURCES INTO D1
  // ----------------------------------------------------------

  await syncSourcesToDatabase(
    env
  );


  const approvedSources =
    getApprovedSources();


  // ----------------------------------------------------------
  // NO APPROVED SOURCES
  // ----------------------------------------------------------

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


    await updateSystemState(
      env,
      "last_refresh_at",
      startedAt
    );


    return {

      ok: true,

      status:
        "waiting_for_approved_sources",

      sources_checked:
        0,

      items_found:
        0,

      stories_created:
        0,

      time:
        startedAt

    };

  }


  let totalFound =
    0;

  let totalNew =
    0;

  let totalCreated =
    0;

  let totalSkipped =
    0;


  await updateSystemState(
    env,
    "backend_status",
    "refreshing"
  );


  // ----------------------------------------------------------
  // PROCESS SOURCES
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
          feed
        );


      totalFound +=
        items.length;


      let sourceNew =
        0;

      let sourceCreated =
        0;

      let sourceSkipped =
        0;


      // ------------------------------------------------------
      // PROCESS FEED ITEMS
      // ------------------------------------------------------

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
          // SOURCE ITEM DUPLICATE
          // --------------------------------------------------

          const existingItem =
            await env.DB
              .prepare(`
                SELECT
                  id,
                  processed,
                  rejected,
                  story_id
                FROM source_items
                WHERE item_key = ?
                LIMIT 1
              `)
              .bind(
                itemKey
              )
              .first();


          if (
            existingItem
          ) {

            sourceSkipped++;
            totalSkipped++;

            continue;

          }


          // --------------------------------------------------
          // EVENT KEY
          // --------------------------------------------------

          const eventKey =
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
          // EXISTING STORY
          // --------------------------------------------------

          const existingStory =
            await env.DB
              .prepare(`
                SELECT
                  id
                FROM stories
                WHERE event_key = ?
                LIMIT 1
              `)
              .bind(
                eventKey
              )
              .first();


          // --------------------------------------------------
          // CREATE SOURCE ITEM
          // --------------------------------------------------

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
                rejection_reason,
                story_id
              )
              VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
              )
            `)
            .bind(

              sourceItemId,

              source.id,

              itemKey,

              item.title,

              item.link,

              item.published_at,

              item.description || "",

              existingStory
                ? 1
                : 0,

              0,

              null,

              existingStory?.id ||
                null

            )
            .run();


          sourceNew++;
          totalNew++;


          // --------------------------------------------------
          // EXISTING EVENT
          // --------------------------------------------------

          if (
            existingStory
          ) {

            sourceSkipped++;
            totalSkipped++;

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
            totalSkipped++;

            continue;

          }


          // --------------------------------------------------
          // VALIDATE AI
          // --------------------------------------------------

          const validated =
            validateAIStory(
              aiStory
            );


          if (
            !validated.ok
          ) {

            await markSourceItemRejected(
              env,
              itemKey,
              validated.error
            );

            sourceSkipped++;
            totalSkipped++;

            continue;

          }


          // --------------------------------------------------
          // CREATE STORY
          // --------------------------------------------------

          const storyId =
            crypto.randomUUID();


          const publishedAt =
            item.published_at ||
            new Date().toISOString();


          const updatedAt =
            new Date().toISOString();


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

              publishedAt,

              updatedAt,

              "source_confirmed",

              "Processed from an approved source feed by the SNIPPET24 editorial AI layer.",

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
          // SOURCE LINK
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
              VALUES (
                ?, ?, ?, ?, ?, ?, ?
              )
            `)
            .bind(

              crypto.randomUUID(),

              storyId,

              source.publisher,

              item.link,

              source.source_type,

              publishedAt,

              "source_confirmed"

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


        } catch (
          itemError
        ) {

          console.error(
            `SNIPPET24 item failed for ${source.id}:`,
            itemError
          );

          sourceSkipped++;
          totalSkipped++;

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


    } catch (
      sourceError
    ) {

      console.error(
        `SNIPPET24 source failed: ${source.id}`,
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


  if (
    totalCreated > 0
  ) {

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

    status:
      "completed",

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
// SYNC SOURCE CONFIGURATION INTO D1
// ============================================================

async function syncSourcesToDatabase(
  env
) {

  for (
    const source
    of SOURCES
  ) {

    await env.DB
      .prepare(`
        INSERT INTO sources (
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
        )
        VALUES (
          ?, ?, ?, ?, ?, ?, ?, ?, ?,
          NULL, NULL, NULL,
          CURRENT_TIMESTAMP,
          CURRENT_TIMESTAMP
        )
        ON CONFLICT(id)
        DO UPDATE SET
          name = excluded.name,
          feed_url = excluded.feed_url,
          source_type = excluded.source_type,
          rights_status = excluded.rights_status,
          enabled = excluded.enabled,
          verification_level =
            excluded.verification_level,
          country = excluded.country,
          language = excluded.language,
          updated_at =
            CURRENT_TIMESTAMP
      `)
      .bind(

        source.id,

        source.name,

        source.feed_url,

        source.source_type,

        source.rights_status,

        source.enabled
          ? 1
          : 0,

        source.verification_level ||
          "standard",

        source.country ||
          null,

        source.language ||
          "en"

      )
      .run();

  }

}


// ============================================================
// FETCH RSS / ATOM
// ============================================================

async function fetchFeed(
  feedUrl
) {

  if (!feedUrl) {

    throw new Error(
      "Source feed URL is empty"
    );

  }


  const controller =
    new AbortController();


  const timeout =
    setTimeout(
      () => {
        controller.abort();
      },
      FETCH_TIMEOUT_MS
    );


  try {

    const response =
      await fetch(
        feedUrl,
        {
          method:
            "GET",

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


    if (
      !response.ok
    ) {

      throw new Error(
        `Feed returned HTTP ${response.status}`
      );

    }


    return await response.text();

  } finally {

    clearTimeout(
      timeout
    );

  }

}


// ============================================================
// RSS / ATOM PARSER
// ============================================================

function parseFeed(
  xml
) {

  if (!xml) {

    return [];

  }


  const items = [];


  // ----------------------------------------------------------
  // RSS
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


    if (
      !title ||
      !link
    ) {

      continue;

    }


    items.push({

      title:
        cleanText(
          title
        ),

      link:
        cleanUrl(
          link
        ),

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
  // ATOM
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


    if (
      !title ||
      !link
    ) {

      continue;

    }


    items.push({

      title:
        cleanText(
          title
        ),

      link:
        cleanUrl(
          link
        ),

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
  // DEDUPLICATE
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


    if (
      !unique.has(
        key
      )
    ) {

      unique.set(
        key,
        item
      );

    }

  }


  return Array
    .from(
      unique.values()
    )
    .slice(
      0,
      MAX_FEED_ITEMS
    );

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

SNIPPET24 is a premium international news-intelligence
product called:

"Know More. In Less."

Transform the supplied source-feed item into a concise,
original SNIPPET24 news brief.

SOURCE INFORMATION

Publisher:
${source.publisher}

Country:
${source.country || "Unknown"}

Language:
${source.language || "en"}

HEADLINE

${item.title}

SOURCE DESCRIPTION

${item.description || "No description provided."}

SOURCE URL

${item.link}


EDITORIAL RULES

1. Use ONLY information supported by the supplied source data.

2. Do not invent facts.

3. Do not invent names.

4. Do not invent numbers.

5. Do not invent dates.

6. Do not invent quotes.

7. Do not infer motives.

8. Do not sensationalize.

9. Do not reproduce the source article.

10. Do not reproduce long source text.

11. Create an original concise summary.

12. Main summary must contain 3–4 short sentences.

13. Impact must explain "How it affects you" in one concise
sentence.

14. Do not provide medical diagnosis.

15. Do not provide investment advice.

16. Do not present AI as the original source.

17. If location is unknown, return an empty location.

18. If country is unknown, return an empty country.

19. Category must be one of the allowed categories.

20. Translations must preserve the same meaning.

21. If the source description does not contain enough
information, remain conservative rather than guessing.

22. Use neutral international English.

23. The story should be suitable for a premium global news
feed.


ALLOWED CATEGORIES

${CATEGORIES.join(", ")}


SUPPORTED LANGUAGES

${LANGUAGES
  .filter(
    language =>
      language.code !== "en"
  )
  .map(
    language =>
      `${language.code} = ${language.name}`
  )
  .join(", ")}


RETURN ONLY VALID JSON.

REQUIRED JSON STRUCTURE

{
  "title": "",
  "summary": "",
  "impact": "",
  "category": "",
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
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
      model
    )}:generateContent`;


  const response =
    await fetch(
      endpoint,
      {

        method:
          "POST",

        headers: {

          "Content-Type":
            "application/json",

          "x-goog-api-key":
            apiKey

        },

        body:
          JSON.stringify({

            contents: [

              {

                role:
                  "user",

                parts: [

                  {
                    text:
                      prompt
                  }

                ]

              }

            ],

            generationConfig: {

              temperature:
                0.2,

              responseMimeType:
                "application/json"

            }

          })

      }
    );


  if (
    !response.ok
  ) {

    const errorText =
      await response.text();


    throw new Error(
      `Gemini API error ${response.status}: ${errorText.slice(
        0,
        500
      )}`
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
// GEMINI RESPONSE
// ============================================================

function extractGeminiText(
  data
) {

  try {

    return (
      data
        ?.candidates?.[0]
        ?.content?.parts
        ?.map(
          part =>
            part.text || ""
        )
        .join("")
        .trim() ||
      ""
    );

  } catch {

    return "";

  }

}


// ============================================================
// VALIDATE AI STORY
// ============================================================

function validateAIStory(
  aiStory
) {

  if (
    !aiStory ||
    typeof aiStory !== "object"
  ) {

    return {

      ok: false,

      error:
        "Empty or invalid AI story"

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


  const rawImpact =
    cleanText(
      aiStory.impact
    );


  let category =
    cleanText(
      aiStory.category
    );


  if (
    !isValidCategory(
      category
    )
  ) {

    category =
      "World";

  }


  if (!title) {

    return {

      ok: false,

      error:
        "AI story has no title"

    };

  }


  if (!summary) {

    return {

      ok: false,

      error:
        "AI story has no summary"

    };

  }


  if (!rawImpact) {

    return {

      ok: false,

      error:
        "AI story has no impact"

    };

  }


  if (
    title.length > 220
  ) {

    return {

      ok: false,

      error:
        "Title too long"

    };

  }


  if (
    summary.length > 1200
  ) {

    return {

      ok: false,

      error:
        "Summary too long"

    };

  }


  if (
    rawImpact.length > 400
  ) {

    return {

      ok: false,

      error:
        "Impact too long"

    };

  }


  const impact =
    rawImpact.startsWith(
      "How it affects you"
    )
      ? rawImpact
      : `How it affects you: ${rawImpact}`;


  return {

    ok: true,

    story: {

      title,

      summary,

      impact,

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
    typeof translations !==
      "object"
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
      typeof value !==
        "object"
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

  await syncSourcesToDatabase(
    env
  );


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
// SOURCE SUCCESS
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


// ============================================================
// SOURCE ERROR
// ============================================================

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

      String(
        error
      ).slice(
        0,
        2000
      ),

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
      VALUES (
        ?, ?, ?, ?
      )
    `)
    .bind(

      id,

      sourceId,

      startedAt,

      "running"

    )
    .run();

}


// ============================================================
// FINISH INGESTION LOG
// ============================================================

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
// REJECT SOURCE ITEM
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

      String(
        reason
      ).slice(
        0,
        1000
      ),

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
      VALUES (
        ?, ?, ?
      )
      ON CONFLICT(key)
      DO UPDATE SET
        value = excluded.value,
        updated_at = excluded.updated_at
    `)
    .bind(

      key,

      String(
        value
      ),

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
    escapeRegExp(
      tag
    );


  const regex =
    new RegExp(
      `<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`,
      "i"
    );


  const match =
    xml.match(
      regex
    );


  return match
    ? decodeXML(
        match[1]
      )
    : "";

}


// ============================================================
// RSS LINK
// ============================================================

function extractLink(
  block
) {

  const direct =
    extractTag(
      block,
      "link"
    );


  if (
    direct
  ) {

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


// ============================================================
// ATOM LINK
// ============================================================

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
      (
        !rel ||
        rel === "alternate"
      )
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
    String(
      value
    )
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


// ============================================================
// XML DECODE
// ============================================================

function decodeXML(
  value
) {

  return String(
    value || ""
  )
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
      (
        _,
        code
      ) =>
        String.fromCharCode(
          Number(
            code
          )
        )
    )
    .replace(
      /&#x([0-9a-f]+);/gi,
      (
        _,
        code
      ) =>
        String.fromCharCode(
          parseInt(
            code,
            16
          )
        )
    );

}


// ============================================================
// URL
// ============================================================

function cleanUrl(
  value
) {

  return String(
    value || ""
  ).trim();

}


// ============================================================
// NORMALIZE KEY
// ============================================================

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


// ============================================================
// NORMALIZE DATE
// ============================================================

function normalizeDate(
  value
) {

  if (!value) {

    return new Date()
      .toISOString();

  }


  const date =
    new Date(
      value
    );


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


// ============================================================
// REGEX ESCAPE
// ============================================================

function escapeRegExp(
  value
) {

  return String(
    value
  ).replace(
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
    String(
      text || ""
    )
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
      cleaned.indexOf(
        "{"
      );


    const last =
      cleaned.lastIndexOf(
        "}"
      );


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
// SHA-256
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
      new Uint8Array(
        hash
      )
    )
    .map(
      byte =>
        byte
          .toString(16)
          .padStart(
            2,
            "0"
          )
    )
    .join("");

}


// ============================================================
// ADMIN AUTHENTICATION
// ============================================================

function isAuthorized(
  request,
  env
) {

  const configuredToken =
    env.ADMIN_TOKEN;


  if (
    !configuredToken
  ) {

    return false;

  }


  const authorization =
    request.headers.get(
      "Authorization"
    );


  if (
    !authorization
  ) {

    return false;

  }


  return (
    authorization ===
    `Bearer ${configuredToken}`
  );

}


// ============================================================
// JSON RESPONSE
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