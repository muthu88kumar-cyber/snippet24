import "dotenv/config";

import express from "express";
import Parser from "rss-parser";
import OpenAI from "openai";

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const app = express();

const PORT = Number(process.env.PORT || 3000);

const parser = new Parser({
  timeout: 20000
});

const openai = process.env.OPENAI_API_KEY
  ? new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    })
  : null;

const ROOT = process.cwd();

const DATA_FILE = path.join(
  ROOT,
  "data",
  "stories.json"
);

const IMAGE_DIR = path.join(
  ROOT,
  "public",
  "generated"
);


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
    path.join(ROOT, "public")
  )
);


/* =========================================================
   FILE SYSTEM
========================================================= */

async function ensureFiles() {

  await fs.mkdir(
    path.dirname(DATA_FILE),
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

    const data =
      await fs.readFile(
        DATA_FILE,
        "utf8"
      );

    const parsed =
      JSON.parse(data);

    return Array.isArray(parsed)
      ? parsed
      : [];

  } catch (error) {

    console.error(
      "Could not read stories.json:",
      error.message
    );

    return [];
  }
}


async function writeStories(
  stories
) {

  await ensureFiles();

  const temporaryFile =
    `${DATA_FILE}.tmp`;

  await fs.writeFile(
    temporaryFile,
    JSON.stringify(
      stories,
      null,
      2
    ),
    "utf8"
  );

  await fs.rename(
    temporaryFile,
    DATA_FILE
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


function safeText(
  value,
  fallback = ""
) {

  const result =
    clean(value);

  return result || fallback;
}


function parseJSON(
  text
) {

  let cleaned =
    String(
      text || ""
    ).trim();

  cleaned =
    cleaned
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

  const first =
    cleaned.indexOf("{");

  const last =
    cleaned.lastIndexOf("}");

  if (
    first !== -1 &&
    last !== -1 &&
    last > first
  ) {

    cleaned =
      cleaned.slice(
        first,
        last + 1
      );
  }

  return JSON.parse(
    cleaned
  );
}


function normalizeKeyPoints(
  points
) {

  if (!Array.isArray(points)) {

    return [];
  }

  return points
    .map(
      point =>
        clean(point)
    )
    .filter(Boolean)
    .slice(0, 3);
}


function normalizeTranslations(
  translations,
  fallback
) {

  const result = {};

  for (
    const lang of Object.keys(LANGS)
  ) {

    const item =
      translations?.[lang] || {};

    result[lang] = {

      headline:
        safeText(
          item.headline,
          fallback.headline
        ),

      summary:
        safeText(
          item.summary,
          fallback.summary
        ),

      keyPoints:
        normalizeKeyPoints(
          item.keyPoints
        )
    };

    if (
      result[lang].keyPoints.length === 0
    ) {

      result[lang].keyPoints =
        fallback.keyPoints;
    }
  }

  return result;
}


/* =========================================================
   AI NEWS REWRITER
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

You are the senior AI editor for Snippet24.

Snippet24 is an independent multilingual news platform.

Your task is to create an ORIGINAL editorial presentation from the supplied source information.

IMPORTANT:

- Do not copy sentences from the source.
- Do not reproduce the source article.
- Do not invent facts.
- Do not add facts that are not reasonably supported by the supplied information.
- Preserve uncertainty.
- Do not exaggerate.
- Do not fabricate quotes.
- Do not fabricate statistics.
- Do not fabricate people.
- Do not fabricate locations.
- Write like a professional digital newsroom.
- Keep the English summary between 60 and 90 words.
- Create exactly 3 useful key points.
- Assign exactly ONE category.
- Translate naturally into Indian-language journalism.
- Do not translate word-for-word.
- Tamil must be natural Tamil journalism.
- Telugu must be natural Telugu journalism.
- Kannada must be natural Kannada journalism.
- Malayalam must be natural Malayalam journalism.
- Hindi must be natural Hindi journalism.

IMAGE:

Create an ORIGINAL editorial illustration concept.

The image must:
- visually represent the subject
- be different from the source photograph
- not reproduce an existing news photograph
- not contain logos
- not contain watermarks
- not contain text
- not contain fake captions
- not make the illustration look like the original event photograph
- use symbolic/editorial visual storytelling where appropriate

Return ONLY valid JSON.

Use exactly this structure:

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

Allowed categories:

${CATEGORIES.join(", ")}

SOURCE INFORMATION

Title:
${source.title}

Description:
${source.description}

Source:
${source.sourceName}

Original URL:
${source.sourceUrl}

Published:
${source.publishedAt || ""}

`;


  const response =
    await openai.responses.create({

      model:
        process.env.TEXT_MODEL ||
        "gpt-5.6-luna",

      input:
        prompt
    });


  return parseJSON(
    response.output_text
  );
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


  const enabled =
    String(
      process.env.GENERATE_IMAGES ||
      "false"
    ).toLowerCase() ===
    "true";


  if (!enabled) {

    console.log(
      "Image generation disabled."
    );

    return null;
  }


  const finalPrompt = `

Create a completely NEW editorial illustration for Snippet24.

NEWS SUBJECT:
${imagePrompt}

STYLE:

- premium digital-news editorial illustration
- realistic but clearly editorial
- cinematic composition
- strong visual storytelling
- professional news website quality
- landscape 3:2 composition
- no text
- no captions
- no logos
- no publisher branding
- no watermark
- no newspaper front page
- no copied photograph
- do not recreate an existing news photograph
- do not make this look like an actual press photograph
- no fake documentary evidence
- avoid identifiable private individuals

The result should visually communicate the story through
people, places, objects, symbols, architecture, environment
or conceptual editorial elements.

`;


  try {

    const response =
      await openai.images.generate({

        model:
          process.env.IMAGE_MODEL ||
          "gpt-image-2",

        prompt:
          finalPrompt,

        size:
          process.env.IMAGE_SIZE ||
          "1536x1024",

        quality:
          process.env.IMAGE_QUALITY ||
          "medium"
      });


    const base64 =
      response?.data?.[0]?.b64_json;


    if (!base64) {

      console.error(
        "Image API returned no image data."
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


    return `/generated/${filename}`;

  } catch (error) {

    console.error(
      "IMAGE GENERATION ERROR:",
      error.message
    );

    return null;
  }
}


/* =========================================================
   PROCESS ONE STORY
========================================================= */

async function processStory(
  item
) {

  const id =
    crypto.randomUUID();


  const source = {

    title:
      safeText(
        item.title,
        "Untitled story"
      ),

    description:
      safeText(
        item.contentSnippet ||
        item.content ||
        item.summary ||
        item.description ||
        ""
      ),

    sourceName:
      safeText(
        item.creator ||
        item.author ||
        item.feedTitle ||
        item.sourceName ||
        "Source"
      ),

    sourceUrl:
      String(
        item.link ||
        item.sourceUrl ||
        ""
      ).trim(),

    publishedAt:
      item.isoDate ||
      item.pubDate ||
      item.publishedAt ||
      new Date().toISOString()
  };


  if (!source.sourceUrl) {

    throw new Error(
      "Source item has no original URL."
    );
  }


  const ai =
    await rewriteNews(
      source
    );


  const fallback = {

    headline:
      safeText(
        ai.headline,
        source.title
      ),

    summary:
      safeText(
        ai.summary,
        source.description
      ),

    keyPoints:
      normalizeKeyPoints(
        ai.keyPoints
      )
  };


  const category =
    CATEGORIES.includes(
      ai.category
    )
      ? ai.category
      : "Global";


  const translations =
    normalizeTranslations(
      ai.translations,
      fallback
    );


  const imageUrl =
    await generateNewsImage(
      ai.imagePrompt,
      id
    );


  return {

    id,

    createdAt:
      new Date().toISOString(),

    source: {

      title:
        source.title,

      description:
        source.description,

      sourceName:
        source.sourceName,

      sourceUrl:
        source.sourceUrl,

      publishedAt:
        source.publishedAt
    },


    snippet24: {

      headline:
        fallback.headline,

      summary:
        fallback.summary,

      keyPoints:
        fallback.keyPoints,

      category,

      location:
        safeText(
          ai.location
        ),

      imagePrompt:
        safeText(
          ai.imagePrompt
        )
    },


    translations,

    imageUrl,

    imageGenerated:
      Boolean(imageUrl)
  };
}


/* =========================================================
   RSS INGESTION
========================================================= */

async function ingestNews() {

  const feeds =
    String(
      process.env.RSS_FEEDS ||
      ""
    )
      .split(",")
      .map(
        feed =>
          feed.trim()
      )
      .filter(Boolean);


  if (!feeds.length) {

    throw new Error(
      "No RSS_FEEDS configured in .env"
    );
  }


  const oldStories =
    await readStories();


  const seenUrls =
    new Set(
      oldStories
        .map(
          story =>
            story.source?.sourceUrl
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
        Array.isArray(feed.items)
          ? feed.items.slice(
              0,
              Number(
                process.env.MAX_ITEMS_PER_FEED ||
                10
              )
            )
          : [];


      for (
        const item of items
      ) {

        const url =
          String(
            item.link ||
            ""
          ).trim();


        if (!url) {

          continue;
        }


        if (
          seenUrls.has(
            url
          )
        ) {

          continue;
        }


        try {

          console.log(
            `Processing: ${item.title || "Untitled"}`
          );


          const story =
            await processStory({

              ...item,

              feedTitle:
                feed.title
            });


          added.push(
            story
          );


          seenUrls.add(
            url
          );


        } catch (error) {

          console.error(
            `Story error: ${item.title || "item"}`,
            error.message
          );


          errors.push(
            `${item.title || "item"}: ${error.message}`
          );
        }
      }


    } catch (error) {

      console.error(
        `Feed error: ${feedUrl}`,
        error.message
      );


      errors.push(
        `${feedUrl}: ${error.message}`
      );
    }
  }


  const merged = [

    ...added,

    ...oldStories

  ]
    .filter(
      (story, index, array) => {

        const url =
          story.source?.sourceUrl;

        if (!url) {
          return true;
        }

        return (
          index ===
          array.findIndex(
            item =>
              item.source?.sourceUrl ===
              url
          )
        );
      }
    )
    .sort(
      (a, b) =>
        new Date(
          b.createdAt
        ) -
        new Date(
          a.createdAt
        )
    )
    .slice(
      0,
      Number(
        process.env.MAX_STORIES ||
        500
      )
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
  (req, res) => {

    res.json({

      ok: true,

      aiConfigured:
        Boolean(openai),

      textModel:
        process.env.TEXT_MODEL ||
        "gpt-5.6-luna",

      imageGeneration:
        String(
          process.env.GENERATE_IMAGES ||
          "false"
        ).toLowerCase() ===
        "true",

      imageModel:
        process.env.IMAGE_MODEL ||
        "gpt-image-2",

      timestamp:
        new Date().toISOString()
    });
  }
);


/* =========================================================
   STORIES API
========================================================= */

app.get(
  "/api/stories",
  async (req, res) => {

    try {

      const stories =
        await readStories();


      const language =
        LANGS[req.query.lang]
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
        category === "all"
          ? stories
          : stories.filter(
              story =>
                story.snippet24
                  ?.category ===
                category
            );


      if (search) {

        filtered =
          filtered.filter(
            story => {

              const translated =
                story.translations?.[
                  language
                ] ||
                story.translations?.en ||
                {};


              const text = [

                translated.headline,

                translated.summary,

                ...(translated.keyPoints || []),

                story.snippet24?.category,

                story.snippet24?.location

              ]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();


              return text.includes(
                search
              );
            }
          );
      }


      res.json({

        language,

        languages:
          LANGS,

        categories:
          CATEGORIES,

        count:
          filtered.length,

        stories:
          filtered.slice(
            0,
            100
          )
      });


    } catch (error) {

      console.error(
        error
      );


      res.status(500).json({

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
  async (req, res) => {

    try {

      const stories =
        await readStories();


      const language =
        LANGS[req.query.lang]
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

              const translated =
                story.translations?.[
                  language
                ] ||
                story.translations?.en ||
                {};


              return {

                id:
                  story.id,

                headline:
                  translated.headline ||
                  story.snippet24?.headline ||
                  "",

                category:
                  story.snippet24?.category ||
                  "",

                sourceName:
                  story.source?.sourceName ||
                  "",

                publishedAt:
                  story.source?.publishedAt ||
                  story.createdAt
              };
            }
          );


      res.json({
        trending
      });


    } catch (error) {

      res.status(500).json({

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
  async (req, res) => {

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

        return res.status(404).json({

          error:
            "Story not found"
        });
      }


      res.json(
        story
      );


    } catch (error) {

      res.status(500).json({

        error:
          error.message
      });
    }
  }
);


/* =========================================================
   MANUAL INGEST
========================================================= */

app.post(
  "/api/ingest",
  async (req, res) => {

    try {

      const result =
        await ingestNews();


      res.json(
        result
      );


    } catch (error) {

      console.error(
        error
      );


      res.status(500).json({

        error:
          error.message
      });
    }
  }
);


/* =========================================================
   MANUAL STORY PROCESSING
========================================================= */

app.post(
  "/api/process",
  async (req, res) => {

    try {

      const body =
        req.body || {};


      if (
        !body.title ||
        !body.sourceUrl
      ) {

        return res.status(400).json({

          error:
            "title and sourceUrl are required"
        });
      }


      const story =
        await processStory({

          title:
            body.title,

          contentSnippet:
            body.description,

          creator:
            body.sourceName,

          link:
            body.sourceUrl,

          publishedAt:
            body.publishedAt ||
            new Date().toISOString()
        });


      const stories =
        await readStories();


      stories.unshift(
        story
      );


      await writeStories(

        stories
          .filter(
            (item, index, array) => {

              const url =
                item.source?.sourceUrl;

              return (
                !url ||
                index ===
                array.findIndex(
                  x =>
                    x.source?.sourceUrl ===
                    url
                )
              );
            }
          )
          .slice(
            0,
            Number(
              process.env.MAX_STORIES ||
              500
            )
          )
      );


      res.json(
        story
      );


    } catch (error) {

      console.error(
        error
      );


      res.status(500).json({

        error:
          error.message
      });
    }
  }
);


/* =========================================================
   ADMIN PAGE
========================================================= */

app.get(
  "/admin",
  (req, res) => {

    res.sendFile(
      path.join(
        ROOT,
        "public",
        "admin.html"
      )
    );
  }
);


/* =========================================================
   STORY PAGE
========================================================= */

app.get(
  "/story",
  (req, res) => {

    res.sendFile(
      path.join(
        ROOT,
        "public",
        "story.html"
      )
    );
  }
);


/* =========================================================
   HOME PAGE
========================================================= */

app.get(
  "*splat",
  (req, res) => {

    res.sendFile(
      path.join(
        ROOT,
        "public",
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
      "======================================"
    );

    console.log(
      "        SNIPPET24 SERVER"
    );

    console.log(
      "======================================"
    );

    console.log(
      `Running on port ${PORT}`
    );

    console.log(
      `AI: ${
        openai
          ? "CONFIGURED"
          : "NOT CONFIGURED"
      }`
    );

    console.log(
      `Text model: ${
        process.env.TEXT_MODEL ||
        "gpt-5.6-luna"
      }`
    );

    console.log(
      `Images: ${
        String(
          process.env.GENERATE_IMAGES ||
          "false"
        ).toLowerCase() ===
        "true"
          ? "ENABLED"
          : "DISABLED"
      }`
    );

    console.log(
      `Image model: ${
        process.env.IMAGE_MODEL ||
        "gpt-image-2"
      }`
    );

    console.log(
      "======================================"
    );
  }
);