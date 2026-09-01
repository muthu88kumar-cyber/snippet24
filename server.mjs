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
  timeout: 15000
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

const LANGS = {
  en: "English",
  ta: "Tamil",
  te: "Telugu",
  kn: "Kannada",
  ml: "Malayalam",
  hi: "Hindi"
};

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

app.use(
  express.json({
    limit: "1mb"
  })
);

app.use(
  express.static(
    path.join(ROOT, "public")
  )
);

/* ---------------------------------------
   FILE SYSTEM
--------------------------------------- */

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

    await fs.access(DATA_FILE);

  } catch {

    await fs.writeFile(
      DATA_FILE,
      "[]"
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

    return JSON.parse(data);

  } catch {

    return [];
  }
}


async function writeStories(stories) {

  await fs.writeFile(
    DATA_FILE,
    JSON.stringify(
      stories,
      null,
      2
    )
  );
}


/* ---------------------------------------
   HELPERS
--------------------------------------- */

function clean(value) {

  return String(
    value || ""
  )
    .replace(
      /<[^>]*>/g,
      " "
    )
    .replace(
      /\s+/g,
      " "
    )
    .trim();
}


function parseJSON(text) {

  return JSON.parse(
    String(text)
      .replace(
        /^```json/i,
        ""
      )
      .replace(
        /^```/i,
        ""
      )
      .replace(
        /```$/i,
        ""
      )
      .trim()
  );
}


/* ---------------------------------------
   AI NEWS REWRITER
--------------------------------------- */

async function rewriteNews(source) {

  if (!openai) {

    throw new Error(
      "OPENAI_API_KEY is not configured."
    );
  }

  const prompt = `

You are the senior AI editor for Snippet24.

Snippet24 is an independent multilingual news platform.

Your job is to create a completely original news presentation from the supplied source metadata.

IMPORTANT RULES:

1. Do NOT copy the source article.
2. Do NOT reproduce source sentences.
3. Do NOT invent facts.
4. Do NOT add unsupported claims.
5. Preserve uncertainty when the source is uncertain.
6. Create an original concise headline.
7. Create an original 60-90 word summary.
8. Create 3 useful key points.
9. Assign exactly ONE category from the allowed category list.
10. Translate the content naturally into the requested Indian languages.
11. The translations must read like native-language journalism.
12. Create an image prompt for a NEW AI editorial illustration.
13. Never request an exact copy of a news photograph.
14. Never use publisher logos.
15. Never use watermarks.
16. Do not create text inside the image.

Return ONLY valid JSON.

Use this exact structure:

{
  "headline": "Original English headline",
  "summary": "Original 60-90 word English summary",
  "keyPoints": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ],
  "category": "One allowed category",
  "location": "Best-supported location or empty string",
  "imagePrompt": "Detailed prompt for a new editorial illustration",
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

SOURCE INFORMATION:

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
        "gpt-5.5",

      input: prompt

    });

  return parseJSON(
    response.output_text
  );
}


/* ---------------------------------------
   AI IMAGE GENERATOR
--------------------------------------- */

async function generateNewsImage(
  imagePrompt,
  storyId
) {

  if (!openai) {

    return null;
  }

  if (
    String(
      process.env.GENERATE_IMAGES
    ).toLowerCase() !== "true"
  ) {

    return null;
  }

  const finalPrompt = `

${imagePrompt}

Create a completely new editorial illustration for Snippet24.

Requirements:

- landscape composition
- suitable for a professional news website
- visually connected to the news subject
- realistic editorial artwork
- strong visual storytelling
- no newspaper logos
- no publisher logos
- no watermark
- no text
- do not recreate an existing photograph
- do not imply this is the original event photograph
- no fake captions
- no identifiable private individuals

`;

  const response =
    await openai.images.generate({

      model:
        process.env.IMAGE_MODEL ||
        "gpt-image-1",

      prompt:
        finalPrompt,

      size:
        "1536x1024",

      quality:
        "medium"
    });

  const base64 =
    response?.data?.[0]?.b64_json;

  if (!base64) {

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
}


/* ---------------------------------------
   PROCESS ONE STORY
--------------------------------------- */

async function processStory(item) {

  const id =
    crypto.randomUUID();

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
        ""
      ),

    sourceName:
      clean(
        item.creator ||
        item.author ||
        item.feedTitle ||
        "Source"
      ),

    sourceUrl:
      item.link ||
      "",

    publishedAt:
      item.isoDate ||
      item.pubDate ||
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


  const imageUrl =
    await generateNewsImage(
      ai.imagePrompt,
      id
    );


  return {

    id,

    createdAt:
      new Date().toISOString(),

    source,

    snippet24: {

      headline:
        ai.headline,

      summary:
        ai.summary,

      keyPoints:
        ai.keyPoints,

      category:
        CATEGORIES.includes(
          ai.category
        )
          ? ai.category
          : "Global",

      location:
        ai.location || "",

      imagePrompt:
        ai.imagePrompt
    },

    translations:
      ai.translations,

    imageUrl,

    imageGenerated:
      Boolean(imageUrl)
  };
}


/* ---------------------------------------
   RSS INGESTION
--------------------------------------- */

async function ingestNews() {

  const feeds =
    String(
      process.env.RSS_FEEDS ||
      ""
    )
      .split(",")
      .map(
        x => x.trim()
      )
      .filter(Boolean);


  if (!feeds.length) {

    throw new Error(
      "No RSS_FEEDS configured."
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

      const feed =
        await parser.parseURL(
          feedUrl
        );


      const items =
        (feed.items || [])
          .slice(0, 10);


      for (
        const item of items
      ) {

        if (
          !item.link ||
          seenUrls.has(
            item.link
          )
        ) {

          continue;
        }


        try {

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
            item.link
          );

        } catch (error) {

          errors.push(
            `${item.title || "item"}: ${error.message}`
          );
        }
      }

    } catch (error) {

      errors.push(
        `${feedUrl}: ${error.message}`
      );
    }
  }


  const merged = [

    ...added,

    ...oldStories

  ]
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


/* ---------------------------------------
   HEALTH
--------------------------------------- */

app.get(
  "/api/health",
  (req, res) => {

    res.json({

      ok: true,

      aiConfigured:
        Boolean(openai),

      imageGeneration:
        String(
          process.env.GENERATE_IMAGES
        ).toLowerCase() ===
        "true"
    });
  }
);


/* ---------------------------------------
   STORIES API
--------------------------------------- */

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
        req.query.category ||
        "all";


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

              const text =
                story.translations?.[
                  language
                ] ||
                story.translations?.en ||
                {};

              return `

                ${text.headline || ""}

                ${text.summary || ""}

                ${story.snippet24?.category || ""}

              `
                .toLowerCase()
                .includes(search);
            }
          );
      }


      res.json({

        language,

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

      res.status(500).json({

        error:
          error.message
      });
    }
  }
);


/* ---------------------------------------
   SINGLE STORY
--------------------------------------- */

app.get(
  "/api/story/:id",
  async (req, res) => {

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
  }
);


/* ---------------------------------------
   INGEST
--------------------------------------- */

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

      res.status(500).json({

        error:
          error.message
      });
    }
  }
);


/* ---------------------------------------
   MANUAL STORY
--------------------------------------- */

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
        stories.slice(
          0,
          500
        )
      );


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


/* ---------------------------------------
   PAGES
--------------------------------------- */

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


/* ---------------------------------------
   HOME
--------------------------------------- */

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


/* ---------------------------------------
   START
--------------------------------------- */

await ensureFiles();


app.listen(
  PORT,
  () => {

    console.log(
      `Snippet24 running at http://localhost:${PORT}`
    );

  }
);