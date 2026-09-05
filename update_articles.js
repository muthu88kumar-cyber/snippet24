const {
  addArticle,
  updateArticle,
  deleteArticle,
  loadDatabase
} = require("./article-engine");


/*
=====================================================
ADD NEW ARTICLE

Replace ONLY the values below when publishing
a verified article.
=====================================================
*/


const newArticle = {

  category:
    "In India",

  headline:
    "YOUR VERIFIED HEADLINE",

  snippet_lines: [

    "WHAT HAPPENED — verified from the source.",

    "WHY IT MATTERS — only if supported by the source.",

    "WHAT HAPPENS NEXT — only if supported by the source."

  ],

  summary:
    "Short factual summary based only on the source.",

  publisher:
    "Official Source",

  source_type:
    "PUBLIC_BROADCASTER",

  source_label:
    "Public Broadcaster",

  source_url:
    "https://example.com",

  original_source_url:
    "https://example.com",

  image_url:
    "",

  location: {

    state:
      "",

    district:
      "",

    city:
      "",

    taluk:
      "",

    locality:
      ""
  },

  reading: {

    "10_sec":
      "WHAT HAPPENED IN ONE SENTENCE.",

    "60_sec": {

      what_happened:
        "WHAT HAPPENED.",

      why_it_matters:
        "WHY IT MATTERS, IF SUPPORTED."
    },

    "3_min": {

      what_happened:
        "THE CORE DEVELOPMENT.",

      why_it_matters:
        "THE SIGNIFICANCE.",

      who_is_affected:
        "WHO IS AFFECTED, IF SUPPORTED.",

      whats_next:
        "WHAT HAPPENS NEXT, IF SUPPORTED."
    }
  },

  ai_rewritten:
    true
};


/*
=====================================================
ADD
=====================================================
*/

const result =
  addArticle(
    newArticle
  );


console.log(
  JSON.stringify(
    result,
    null,
    2
  )
);


/*
=====================================================
CURRENT DATABASE SIZE
=====================================================
*/

const database =
  loadDatabase();

console.log(
  `Snippet24 now contains ${database.total} articles.`
);