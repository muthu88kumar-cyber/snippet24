const fs = require("fs");
const crypto = require("crypto");

const FILE = "./articles.json";

const AI_DISCLOSURE =
  "Snippet24 uses an AI-assisted editorial process to condense and rephrase source material. The original source remains the authority for the complete report.";

const EDITORIAL_NOTE =
  "Rephrased from the original source for clarity.";


/* ==================================================
   DATABASE
================================================== */

function loadDatabase() {

  if (!fs.existsSync(FILE)) {

    return {
      site: "Snippet24",
      site_url: "https://snippet24.in",
      version: "2.0",
      total: 0,
      articles: []
    };
  }

  const data =
    JSON.parse(
      fs.readFileSync(
        FILE,
        "utf8"
      )
    );

  if (!Array.isArray(data.articles)) {
    data.articles = [];
  }

  return data;
}


/* ==================================================
   ID
================================================== */

function createId() {

  return crypto
    .randomBytes(10)
    .toString("hex");
}


/* ==================================================
   READING
================================================== */

function buildReading(article) {

  const lines =
    Array.isArray(article.snippet_lines)
      ? article.snippet_lines.filter(Boolean)
      : [];

  const headline =
    article.headline ||
    article.title ||
    lines[0] ||
    "Untitled story";

  const reading =
    article.reading || {};

  return {

    "10_sec":
      reading["10_sec"] ||
      lines[0] ||
      headline,

    "60_sec": {

      what_happened:
        reading["60_sec"]?.what_happened ||
        lines[0] ||
        headline,

      why_it_matters:
        reading["60_sec"]?.why_it_matters ||
        lines[1] ||
        ""
    },

    "3_min": {

      what_happened:
        reading["3_min"]?.what_happened ||
        lines[0] ||
        headline,

      why_it_matters:
        reading["3_min"]?.why_it_matters ||
        lines[1] ||
        "",

      who_is_affected:
        reading["3_min"]?.who_is_affected ||
        "",

      whats_next:
        reading["3_min"]?.whats_next ||
        ""
    }
  };
}


/* ==================================================
   NORMALIZE
================================================== */

function normalizeArticle(article) {

  const headline =
    article.headline ||
    article.title ||
    "Untitled story";

  const lines =
    Array.isArray(article.snippet_lines)
      ? article.snippet_lines
      : [];

  const normalizedLines = [
    lines[0] || headline,
    lines[1] || "",
    lines[2] || ""
  ];

  return {

    id:
      article.id ||
      createId(),

    category:
      article.category ||
      "In India",

    headline,

    reading:
      buildReading(article),

    snippet:
      normalizedLines
        .filter(Boolean)
        .join("\n"),

    snippet_lines:
      normalizedLines,

    summary:
      article.summary ||
      headline,

    publisher:
      article.publisher ||
      "",

    source_type:
      article.source_type ||
      "OFFICIAL",

    source_label:
      article.source_label ||
      "Official Source",

    importance:
      article.importance ||
      "MEDIUM",

    published_at:
      article.published_at ||
      new Date().toISOString(),

    source_url:
      article.source_url ||
      article.original_source_url ||
      "",

    original_source_url:
      article.original_source_url ||
      article.source_url ||
      "",

    image_url:
      article.image_url ||
      "",

    image_usage:
      article.image_usage ||
      "NONE",

    location:
      article.location || {
        state: "",
        district: "",
        city: "",
        taluk: "",
        locality: ""
      },

    ai_rewritten:
      article.ai_rewritten ?? true,

    ai_disclosure:
      true,

    ai_disclosure_text:
      AI_DISCLOSURE,

    editorial_note:
      EDITORIAL_NOTE,

    attribution_required:
      true,

    copyright_status:
      article.copyright_status ||
      "THIRD_PARTY_SOURCE",

    correction_available:
      true,

    grievance_available:
      true,

    translations:
      article.translations || {}
  };
}


/* ==================================================
   METADATA
================================================== */

function rebuildMetadata(data) {

  data.updated_at =
    new Date().toISOString();

  /*
   * UNLIMITED
   *
   * This always reflects the actual
   * number of articles.
   */

  data.total =
    data.articles.length;

  data.categories = {};

  data.source_types = {};

  for (
    const article of data.articles
  ) {

    const category =
      article.category ||
      "In India";

    const sourceType =
      article.source_type ||
      "UNKNOWN";

    data.categories[category] =
      (data.categories[category] || 0) + 1;

    data.source_types[sourceType] =
      (data.source_types[sourceType] || 0) + 1;
  }

  data.editorial_engine =
    "Snippet24 AI Editorial";

  data.ai_disclosure =
    AI_DISCLOSURE;

  data.editorial_note =
    EDITORIAL_NOTE;
}


/* ==================================================
   SAVE
================================================== */

function saveDatabase(data) {

  rebuildMetadata(data);

  fs.writeFileSync(
    FILE,
    JSON.stringify(
      data,
      null,
      2
    ),
    "utf8"
  );
}


/* ==================================================
   ADD
================================================== */

function addArticle(article) {

  const data =
    loadDatabase();

  const normalized =
    normalizeArticle(article);

  const duplicate =
    data.articles.find(
      item =>
        item.id === normalized.id ||
        (
          normalized.original_source_url &&
          item.original_source_url ===
          normalized.original_source_url
        )
    );

  if (duplicate) {

    return {
      success: false,
      reason: "duplicate",
      article: duplicate
    };
  }

  data.articles.unshift(
    normalized
  );

  saveDatabase(data);

  return {
    success: true,
    article: normalized,
    total: data.total
  };
}


/* ==================================================
   UPDATE
================================================== */

function updateArticle(
  id,
  changes
) {

  const data =
    loadDatabase();

  const index =
    data.articles.findIndex(
      article =>
        article.id === id
    );

  if (index === -1) {

    return {
      success: false,
      reason: "not_found"
    };
  }

  data.articles[index] =
    normalizeArticle({
      ...data.articles[index],
      ...changes,
      id
    });

  saveDatabase(data);

  return {
    success: true,
    article:
      data.articles[index]
  };
}


/* ==================================================
   DELETE
================================================== */

function deleteArticle(id) {

  const data =
    loadDatabase();

  const before =
    data.articles.length;

  data.articles =
    data.articles.filter(
      article =>
        article.id !== id
    );

  if (
    data.articles.length ===
    before
  ) {

    return {
      success: false,
      reason: "not_found"
    };
  }

  saveDatabase(data);

  return {
    success: true,
    total: data.total
  };
}


/* ==================================================
   EXPORT
================================================== */

module.exports = {
  loadDatabase,
  addArticle,
  updateArticle,
  deleteArticle,
  normalizeArticle
};