import "dotenv/config";

import express from "express";
import Parser from "rss-parser";
import OpenAI from "openai";

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const app = express();

const PORT = Number(process.env.PORT || 3000);

const ROOT = process.cwd();

const PUBLIC_DIR = path.join(
  ROOT,
  "public"
);

const DATA_DIR = path.join(
  ROOT,
  "data"
);

const DATA_FILE = path.join(
  DATA_DIR,
  "stories.json"
);

const IMAGE_DIR = path.join(
  PUBLIC_DIR,
  "generated"
);


/* =========================================================
   OPENAI
========================================================= */

const openai =
  process.env.OPENAI_API_KEY
    ? new OpenAI({
        apiKey:
          process.env.OPENAI_API_KEY
      })
    : null;


const TEXT_MODEL =
  process.env.TEXT_MODEL ||
  "gpt-5.6-luna";


const IMAGE_MODEL =
  process.env.IMAGE_MODEL ||
  "gpt-image-2";


const GENERATE_IMAGES =
  String(
    process.env.GENERATE_IMAGES
  ).toLowerCase() === "true";


/* =========================================================
   RSS
========================================================= */

const parser =
  new Parser({
    timeout: 20000,

    headers: {
      "User-Agent":
        "Snippet24 News Bot/1.0"
    }
  });


/* =========================================================
   LANGUAGES
========================================================= */

const LANGS = {

  en: "English",

  ta: "Tamil",

  te: "Telugu",

  kn: "Kannada",

  ml: "Malayalam",

  hi: "Hindi"

};


/* =========================================================
   CATEGORIES
========================================================= */

const CATEGORIES = [

  "In India",

  "Global",

  "Security & Peace",

  "Law Around Us",

  "Science & Development",

  "Business & Economy",

  "Society & Culture",

  "Human & Environment",

  "Tech & AI",

  "Sports"

];


/* =========================================================
   EXPRESS
========================================================= */

app.use(
  express.json({
    limit: "2mb"
  })
);


app.use(
  express.urlencoded({
    extended: true
  })
);


app.use(
  express.static(
    PUBLIC_DIR
  )
);


/* =========================================================
   FILE SYSTEM
========================================================= */

async function ensureFiles() {

  await fs.mkdir(
    DATA_DIR,
    {
      recursive: true
    }
  );


  await fs.mkdir(
    IMAGE_DIR,
    {
      recursive: true
    }
  );


  try {

    await fs.access(
      DATA_FILE
    );

  } catch {

    await fs.writeFile(
      DATA_FILE,
      "[]",
      "utf8"
    );

  }

}


async function readStories() {

  await ensureFiles();


  try {

    const raw =
      await fs.readFile(
        DATA_FILE,
        "utf8"
      );


    const data =
      JSON.parse(raw);


    return Array.isArray(data)
      ? data
      : [];

  } catch (error) {

    console.error(
      "Unable to read stories:",
      error.message
    );


    return [];

  }

}


async function writeStories(
  stories
) {

  await ensureFiles();


  await fs.writeFile(

    DATA_FILE,

    JSON.stringify(
      stories,
      null,
      2
    ),

    "utf8"

  );

}


/* =========================================================
   HELPERS
========================================================= */

function clean(value) {

  return String(
    value || ""
  )

    .replace(
      /<[^>]*>/g,
      " "
    )

    .replace(
      /&nbsp;/gi,
      " "
    )

    .replace(
      /&amp;/gi,
      "&"
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
      /\s+/g,
      " "
    )

    .trim();

}


function makeId() {

  return crypto
    .randomUUID();

}


function parseJSON(
  text
) {

  let cleaned =
    String(text || "")
      .trim();


  cleaned =
    cleaned.replace(
      /^```json\s*/i,
      ""
    );


  cleaned =
    cleaned.replace(
      /^```\s*/i,
      ""
    );


  cleaned =
    cleaned.replace(
      /\s*```$/i,
      ""
    );


  return JSON.parse(
    cleaned
  );

}


function safeDate(
  value
) {

  const date =
    new Date(value);


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return new Date();

  }


  return date;

}


function getStoryText(
  story,
  language
) {

  return (
    story?.translations?.[
      language
    ] ||

    story?.translations?.en ||

    {

      headline:
        story?.snippet24
          ?.headline ||
        "",

      summary:
        story?.snippet24
          ?.summary ||
        "",

      keyPoints:
        story?.snippet24
          ?.keyPoints ||
        []

    }

  );

}


/* =========================================================
   AI NEWS EDITOR
========================================================= */

async function rewriteNews(
  source
) {

  if (!openai) {

    throw new Error(
      "OPENAI_API_KEY is not configured."
    );

  }


  const prompt = `

You are the senior AI editor of Snippet24.

Snippet24 is an independent multilingual news platform.

Create an ORIGINAL editorial presentation based ONLY on the supplied source information.

IMPORTANT:

- Do not copy the source article.
- Do not reproduce source sentences.
- Do not invent facts.
- Do not add unsupported claims.
- Do not exaggerate.
- Preserve uncertainty.
- Write an original headline.
- Write an original 60-90 word summary.
- Create exactly 3 useful key points.
- Select exactly ONE category.
- Provide the best-supported location.
- Translate naturally into Indian languages.
- Translations must read like professional native journalism.
- Create a completely new AI editorial illustration prompt.
- The illustration must NOT recreate an existing news photograph.
- Do not include logos.
- Do not include watermarks.
- Do not put words or captions inside the image.

Allowed categories:

${CATEGORIES.join(", ")}

Return ONLY valid JSON.

Required structure:

{
  "headline": "",
  "summary": "",
  "keyPoints": [
    "",
    "",
    ""
  ],
  "category": "",
  "location": "",
  "imagePrompt": "",
  "translations": {
    "en": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    },
    "ta": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    },
    "te": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    },
    "kn": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    },
    "ml": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    },
    "hi": {
      "headline": "",
      "summary": "",
      "keyPoints": ["", "", ""]
    }
  }
}

SOURCE TITLE:
${source.title}

SOURCE DESCRIPTION:
${source.description}

SOURCE NAME:
${source.sourceName}

SOURCE URL:
${source.sourceUrl}

PUBLISHED:
${source.publishedAt}

`;


  const response =
    await openai.responses.create({

      model:
        TEXT_MODEL,

      input:
        prompt

    });


  if (
    !response ||
    !response.output_text
  ) {

    throw new Error(
      "OpenAI returned no text."
    );

  }


  const result =
    parseJSON(
      response.output_text
    );


  if (
    !result.headline ||
    !result.summary
  ) {

    throw new Error(
      "AI response is missing headline or summary."
    );

  }


  if (
    !CATEGORIES.includes(
      result.category
    )
  ) {

    result.category =
      "Global";

  }


  return result;

}


/* =========================================================
   AI IMAGE GENERATOR
========================================================= */

async function generateNewsImage(
  imagePrompt,
  storyId
) {

  if (!openai) {

    console.log(
      "Image generation skipped: OpenAI not configured."
    );

    return null;

  }


  if (!GENERATE_IMAGES) {

    console.log(
      "Image generation disabled."
    );

    return null;

  }


  const prompt = `

Create an original editorial illustration for the news platform Snippet24.

SUBJECT:

${imagePrompt}

STYLE:

Professional contemporary news editorial illustration.

REQUIREMENTS:

- Landscape 16:9 composition.
- Strong visual storytelling.
- Visually related to the subject.
- Suitable for a premium news website.
- Realistic editorial artwork.
- Use original composition.
- Do not recreate any existing news photograph.
- Do not copy a journalist's photograph.
- Do not use publisher logos.
- Do not use brand logos.
- No watermark.
- No captions.
- No written words.
- No fake newspaper headlines.
- No fake signs.
- No political propaganda.
- Do not depict identifiable private individuals.
- The image must clearly function as an editorial illustration.

`;


  try {

    const response =
      await openai.images.generate({

        model:
          IMAGE_MODEL,

        prompt,

        size:
          "1536x1024"

      });


    const image =
      response?.data?.[0];


    if (!image) {

      console.error(
        "No image returned by OpenAI."
      );

      return null;

    }


    const base64 =
      image.b64_json;


    if (!base64) {

      console.error(
        "Image response did not contain base64 data."
      );

      return null;

    }


    const filename =
      `${storyId}.png`;


    const filePath =
      path.join(
        IMAGE_DIR,
        filename
      );


    await fs.writeFile(

      filePath,

      Buffer.from(
        base64,
        "base64"
      )

    );


    return (
      `/generated/${filename}`
    );


  } catch (error) {

    console.error(
      "Image generation failed:",
      error.message
    );


    return null;

  }

}


/* =========================================================
   PROCESS STORY
========================================================= */

async function processStory(
  item
) {

  const id =
    makeId();


  const source = {

    title:
      clean(
        item.title ||
        "Untitled story"
      ),

    description:
      clean(
        item.contentSnippet ||
        item.content ||
        item.summary ||
        item.description ||
        ""
      ),

    sourceName:
      clean(
        item.creator ||
        item.author ||
        item.feedTitle ||
        item.sourceName ||
        "News Source"
      ),

    sourceUrl:
      item.link ||
      item.sourceUrl ||
      "",

    publishedAt:
      item.isoDate ||
      item.pubDate ||
      item.publishedAt ||
      new Date().toISOString()

  };


  if (
    !source.sourceUrl
  ) {

    throw new Error(
      "Story does not contain an original source URL."
    );

  }


  const ai =
    await rewriteNews(
      source
    );


  const imageUrl =
    await generateNewsImage(

      ai.imagePrompt,

      id

    );


  const story = {

    id,

    createdAt:
      new Date().toISOString(),

    source,

    snippet24: {

      headline:
        clean(
          ai.headline
        ),

      summary:
        clean(
          ai.summary
        ),

      keyPoints:
        Array.isArray(
          ai.keyPoints
        )
          ? ai.keyPoints
              .slice(0, 3)
              .map(clean)
          : [],

      category:
        CATEGORIES.includes(
          ai.category
        )
          ? ai.category
          : "Global",

      location:
        clean(
          ai.location
        ),

      imagePrompt:
        clean(
          ai.imagePrompt
        )

    },

    translations:
      ai.translations,

    imageUrl,

    imageGenerated:
      Boolean(imageUrl)

  };


  return story;

}


/* =========================================================
   RSS INGESTION
========================================================= */

async function ingestNews() {

  const feedString =
    String(
      process.env.RSS_FEEDS ||
      ""
    );


  const feeds =
    feedString

      .split(",")

      .map(
        feed =>
          feed.trim()
      )

      .filter(Boolean);


  if (!feeds.length) {

    throw new Error(
      "RSS_FEEDS is empty. Add RSS feed URLs to .env."
    );

  }


  const existing =
    await readStories();


  const seenUrls =
    new Set(

      existing

        .map(
          story =>
            story?.source?.sourceUrl
        )

        .filter(Boolean)

    );


  const added = [];

  const errors = [];


  for (
    const feedUrl of feeds
  ) {

    try {

      console.log(
        `Reading RSS: ${feedUrl}`
      );


      const feed =
        await parser.parseURL(
          feedUrl
        );


      const items =
        Array.isArray(
          feed.items
        )
          ? feed.items
          : [];


      /*
        Process up to 10 new stories
        from each RSS source.
      */

      const selected =
        items.slice(
          0,
          10
        );


      for (
        const item of selected
      ) {

        const sourceUrl =
          item.link;


        if (
          !sourceUrl
        ) {

          continue;

        }


        if (
          seenUrls.has(
            sourceUrl
          )
        ) {

          continue;

        }


        try {

          console.log(
            `AI processing: ${item.title}`
          );


          const story =
            await processStory({

              ...item,

              feedTitle:
                feed.title ||
                "News Source"

            });


          added.push(
            story
          );


          seenUrls.add(
            sourceUrl
          );


          /*
            Small delay so we don't
            hammer APIs.
          */

          await new Promise(
            resolve =>
              setTimeout(
                resolve,
                500
              )
          );


        } catch (error) {

          console.error(
            `Story failed: ${item.title}`,
            error.message
          );


          errors.push({

            title:
              item.title ||
              "Unknown story",

            error:
              error.message

          });

        }

      }


    } catch (error) {

      console.error(
        `RSS failed: ${feedUrl}`,
        error.message
      );


      errors.push({

        feed:
          feedUrl,

        error:
          error.message

      });

    }

  }


  const merged = [

    ...added,

    ...existing

  ]

    .sort(
      (a, b) =>
        safeDate(
          b.createdAt
        ).getTime() -
        safeDate(
          a.createdAt
        ).getTime()
    )

    .slice(
      0,
      500
    );


  await writeStories(
    merged
  );


  return {

    added:
      added.length,

    total:
      merged.length,

    errors

  };

}


/* =========================================================
   HEALTH
========================================================= */

app.get(
  "/api/health",
  async (
    req,
    res
  ) => {

    const stories =
      await readStories();


    res.json({

      ok:
        true,

      site:
        "Snippet24",

      aiConfigured:
        Boolean(openai),

      textModel:
        TEXT_MODEL,

      imageModel:
        IMAGE_MODEL,

      imageGeneration:
        GENERATE_IMAGES,

      stories:
        stories.length,

      time:
        new Date().toISOString()

    });

  }
);


/* =========================================================
   CATEGORIES API
========================================================= */

app.get(
  "/api/categories",
  (
    req,
    res
  ) => {

    res.json({

      categories:
        CATEGORIES

    });

  }
);


/* =========================================================
   STORIES API
========================================================= */

app.get(
  "/api/stories",
  async (
    req,
    res
  ) => {

    try {

      const stories =
        await readStories();


      const language =
        LANGS[
          req.query.lang
        ]
          ? req.query.lang
          : "en";


      const category =
        String(
          req.query.category ||
          "all"
        );


      const search =
        String(
          req.query.q ||
          ""
        )
          .toLowerCase()
          .trim();


      let filtered =
        stories;


      /*
        CATEGORY FILTER
      */

      if (
        category !== "all"
      ) {

        filtered =
          filtered.filter(

            story =>
              story?.snippet24
                ?.category ===
              category

          );

      }


      /*
        SEARCH FILTER
      */

      if (
        search
      ) {

        filtered =
          filtered.filter(
            story => {

              const text =
                getStoryText(
                  story,
                  language
                );


              const searchable = [

                text.headline,

                text.summary,

                ...(Array.isArray(
                  text.keyPoints
                )
                  ? text.keyPoints
                  : []),

                story?.snippet24
                  ?.category,

                story?.snippet24
                  ?.location,

                story?.source
                  ?.sourceName

              ]

                .join(" ")

                .toLowerCase();


              return searchable
                .includes(
                  search
                );

            }
          );

      }


      /*
        Add display text so
        frontend doesn't have
        to understand storage.
      */

      const output =
        filtered

          .slice(
            0,
            100
          )

          .map(
            story => {

              const text =
                getStoryText(
                  story,
                  language
                );


              return {

                ...story,

                display: {

                  headline:
                    text.headline ||
                    story.snippet24
                      ?.headline ||
                    "",

                  summary:
                    text.summary ||
                    story.snippet24
                      ?.summary ||
                    "",

                  keyPoints:
                    text.keyPoints ||
                    story.snippet24
                      ?.keyPoints ||
                    []

                }

              };

            }
          );


      res.json({

        ok:
          true,

        language,

        languageName:
          LANGS[
            language
          ],

        category,

        categories:
          CATEGORIES,

        count:
          output.length,

        stories:
          output

      });


    } catch (error) {

      console.error(
        "Stories API error:",
        error
      );


      res.status(500).json({

        ok:
          false,

        error:
          error.message

      });

    }

  }
);


/* =========================================================
   SINGLE STORY
========================================================= */

app.get(
  "/api/story/:id",
  async (
    req,
    res
  ) => {

    try {

      const stories =
        await readStories();


      const story =
        stories.find(

          item =>
            item.id ===
            req.params.id

        );


      if (!story) {

        return res
          .status(404)
          .json({

            ok:
              false,

            error:
              "Story not found"

          });

      }


      res.json({

        ok:
          true,

        story

      });


    } catch (error) {

      res
        .status(500)
        .json({

          ok:
            false,

          error:
            error.message

        });

    }

  }
);


/* =========================================================
   TRENDING API
========================================================= */

app.get(
  "/api/trending",
  async (
    req,
    res
  ) => {

    try {

      const stories =
        await readStories();


      const language =
        LANGS[
          req.query.lang
        ]
          ? req.query.lang
          : "en";


      const trending =
        stories

          .slice(
            0,
            10
          )

          .map(
            story => {

              const text =
                getStoryText(
                  story,
                  language
                );


              return {

                id:
                  story.id,

                headline:
                  text.headline ||
                  story.snippet24
                    ?.headline ||
                  "",

                category:
                  story.snippet24
                    ?.category ||
                  "Global",

                source:
                  story.source
                    ?.sourceName ||
                  "",

                publishedAt:
                  story.source
                    ?.publishedAt ||
                  story.createdAt

              };

            }
          );


      res.json({

        ok:
          true,

        stories:
          trending

      });


    } catch (error) {

      res.status(500).json({

        ok:
          false,

        error:
          error.message

      });

    }

  }
);


/* =========================================================
   MANUAL STORY PROCESSOR
========================================================= */

app.post(
  "/api/process",
  async (
    req,
    res
  ) => {

    try {

      const body =
        req.body || {};


      if (
        !body.title ||
        !body.sourceUrl
      ) {

        return res
          .status(400)
          .json({

            ok:
              false,

            error:
              "title and sourceUrl are required"

          });

      }


      const story =
        await processStory({

          title:
            body.title,

          contentSnippet:
            body.description ||
            body.content ||
            "",

          sourceName:
            body.sourceName ||
            "Manual Source",

          link:
            body.sourceUrl,

          publishedAt:
            body.publishedAt ||
            new Date().toISOString()

        });


      const stories =
        await readStories();


      /*
        Prevent duplicate
        source URLs.
      */

      const duplicate =
        stories.find(

          existing =>
            existing?.source
              ?.sourceUrl ===
            story.source.sourceUrl

        );


      if (duplicate) {

        return res.json({

          ok:
            true,

          duplicate:
            true,

          story:
            duplicate

        });

      }


      stories.unshift(
        story
      );


      await writeStories(

        stories.slice(
          0,
          500
        )

      );


      res.json({

        ok:
          true,

        duplicate:
          false,

        story

      });


    } catch (error) {

      console.error(
        "Manual processing error:",
        error
      );


      res.status(500).json({

        ok:
          false,

        error:
          error.message

      });

    }

  }
);


/* =========================================================
   INGEST API
========================================================= */

app.post(
  "/api/ingest",
  async (
    req,
    res
  ) => {

    try {

      const result =
        await ingestNews();


      res.json({

        ok:
          true,

        ...result

      });


    } catch (error) {

      console.error(
        "Ingestion error:",
        error
      );


      res.status(500).json({

        ok:
          false,

        error:
          error.message

      });

    }

  }
);


/* =========================================================
   DELETE ALL STORIES
   ADMIN / DEVELOPMENT ONLY
========================================================= */

app.post(
  "/api/reset",
  async (
    req,
    res
  ) => {

    try {

      await writeStories(
        []
      );


      /*
        Remove generated images.
      */

      try {

        const files =
          await fs.readdir(
            IMAGE_DIR
          );


        for (
          const file of files
        ) {

          if (
            file.endsWith(
              ".png"
            )
          ) {

            await fs.unlink(
              path.join(
                IMAGE_DIR,
                file
              )
            );

          }

        }

      } catch {

        // Ignore image cleanup errors.

      }


      res.json({

        ok:
          true,

        message:
          "All Snippet24 stories were reset."

      });


    } catch (error) {

      res.status(500).json({

        ok:
          false,

        error:
          error.message

      });

    }

  }
);


/* =========================================================
   ARTICLE PAGE
========================================================= */

app.get(
  "/story",
  (
    req,
    res
  ) => {

    res.sendFile(

      path.join(
        PUBLIC_DIR,
        "story.html"
      )

    );

  }
);


/* =========================================================
   ADMIN PAGE
========================================================= */

app.get(
  "/admin",
  (
    req,
    res
  ) => {

    res.sendFile(

      path.join(
        PUBLIC_DIR,
        "admin.html"
      )

    );

  }
);


/* =========================================================
   HOME PAGE
========================================================= */

app.get(
  "/",
  (
    req,
    res
  ) => {

    res.sendFile(

      path.join(
        PUBLIC_DIR,
        "index.html"
      )

    );

  }
);


/* =========================================================
   FALLBACK
========================================================= */

app.get(
  "*splat",
  (
    req,
    res
  ) => {

    /*
      API routes should never
      reach this point.
    */

    if (
      req.path.startsWith(
        "/api/"
      )
    ) {

      return res
        .status(404)
        .json({

          ok:
            false,

          error:
            "API endpoint not found"

        });

    }


    res.sendFile(

      path.join(
        PUBLIC_DIR,
        "index.html"
      )

    );

  }
);


/* =========================================================
   START SERVER
========================================================= */

await ensureFiles();


app.listen(
  PORT,
  () => {

    console.log(
      ""
    );

    console.log(
      "===================================="
    );

    console.log(
      "       SNIPPET24 SERVER"
    );

    console.log(
      "===================================="
    );

    console.log(
      `Website: http://localhost:${PORT}`
    );

    console.log(
      `AI: ${
        openai
          ? "CONFIGURED"
          : "NOT CONFIGURED"
      }`
    );

    console.log(
      `Text model: ${TEXT_MODEL}`
    );

    console.log(
      `Image model: ${IMAGE_MODEL}`
    );

    console.log(
      `AI images: ${
        GENERATE_IMAGES
          ? "ENABLED"
          : "DISABLED"
      }`
    );

    console.log(
      "===================================="
    );

  }
);
