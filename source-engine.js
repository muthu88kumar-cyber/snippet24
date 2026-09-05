const {
  addArticle
} = require("./article-engine");


/*
=====================================================
SNIPPET24 SOURCE ENGINE

This file prepares a verified source record
for the Snippet24 editorial engine.

It deliberately does NOT invent facts.

The content supplied to this function must come
from an approved source.
=====================================================
*/


const APPROVED_SOURCE_TYPES = [
  "GOVERNMENT",
  "PUBLIC_BROADCASTER",
  "OFFICIAL_TV",
  "OFFICIAL_YOUTUBE"
];


function isApprovedSource(
  sourceType
) {

  return APPROVED_SOURCE_TYPES
    .includes(
      String(sourceType || "")
        .toUpperCase()
    );
}


function createArticleFromSource({
  sourceType,
  publisher,
  category,
  headline,
  facts,
  summary,
  sourceUrl,
  imageUrl,
  location
}) {

  if (
    !isApprovedSource(
      sourceType
    )
  ) {

    throw new Error(
      "Source rejected: source type is not approved."
    );
  }

  if (!sourceUrl) {

    throw new Error(
      "Source rejected: original source URL is required."
    );
  }

  if (!headline) {

    throw new Error(
      "Headline is required."
    );
  }

  if (
    !Array.isArray(facts) ||
    facts.length === 0
  ) {

    throw new Error(
      "Verified source facts are required."
    );
  }


  /*
   * Only verified facts supplied by the source
   * are used.
   */

  const first =
    facts[0] || headline;

  const second =
    facts[1] || "";

  const third =
    facts[2] || "";


  const article = {

    category:
      category || "In India",

    headline,

    snippet_lines: [
      first,
      second,
      third
    ],

    summary:
      summary || first,

    publisher:
      publisher || "",

    source_type:
      sourceType,

    source_label:
      sourceType,

    source_url:
      sourceUrl,

    original_source_url:
      sourceUrl,

    image_url:
      imageUrl || "",

    image_usage:
      imageUrl
        ? "SOURCE"
        : "NONE",

    location:
      location || {},

    ai_rewritten:
      true
  };


  /*
   * The reading fields should be populated
   * from verified source facts.
   *
   * No unsupported claims are generated.
   */

  article.reading = {

    "10_sec":
      first,

    "60_sec": {

      what_happened:
        first,

      why_it_matters:
        second
    },

    "3_min": {

      what_happened:
        first,

      why_it_matters:
        second,

      who_is_affected:
        "",

      whats_next:
        third
    }
  };


  return addArticle(
    article
  );
}


module.exports = {
  isApprovedSource,
  createArticleFromSource
};