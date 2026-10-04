// ============================================================
// SNIPPET24 — SOURCE REGISTRY
// ============================================================
//
// IMPORTANT:
// A source is NOT enabled until its feed/API usage rights
// have been reviewed and approved for SNIPPET24.
//
// Never treat "publicly accessible" as automatically meaning
// "licensed for commercial republication."
// ============================================================

export const CATEGORIES = [
  "Around You",
  "India",
  "World",
  "Business",
  "Money",
  "Health",
  "Food",
  "Technology & AI",
  "Sports",
  "Culture",
  "Science",
  "Climate"
];

export const LANGUAGES = [
  {
    code: "en",
    name: "English"
  },
  {
    code: "ta",
    name: "Tamil"
  },
  {
    code: "hi",
    name: "Hindi"
  },
  {
    code: "te",
    name: "Telugu"
  },
  {
    code: "kn",
    name: "Kannada"
  },
  {
    code: "ml",
    name: "Malayalam"
  },
  {
    code: "bn",
    name: "Bengali"
  },
  {
    code: "mr",
    name: "Marathi"
  },
  {
    code: "gu",
    name: "Gujarati"
  },
  {
    code: "pa",
    name: "Punjabi"
  }
];


// ============================================================
// SOURCE REGISTRY
// ============================================================
//
// enabled: false until rights_status becomes "approved"
//
// verification_level:
// standard | authoritative
//
// source_type:
// rss | api
// ============================================================

export const SOURCES = [

  {
    id: "nasa-jpl",
    name: "NASA JPL",
    publisher: "NASA JPL",

    feed_url:
      "https://www.jpl.nasa.gov/feeds/news/",

    source_type: "rss",

    rights_status:
      "review_required",

    enabled:
      false,

    verification_level:
      "authoritative",

    country:
      "United States",

    language:
      "en"
  },


  {
    id: "nasa-cneos",
    name: "NASA CNEOS",
    publisher: "NASA CNEOS",

    feed_url:
      "https://cneos.jpl.nasa.gov/feed/news.xml",

    source_type: "rss",

    rights_status:
      "review_required",

    enabled:
      false,

    verification_level:
      "authoritative",

    country:
      "United States",

    language:
      "en"
  }

];


// ============================================================
// APPROVED SOURCES
// ============================================================

export function getApprovedSources() {

  return SOURCES.filter(
    source =>
      source.enabled === true &&
      source.rights_status === "approved"
  );

}


// ============================================================
// CATEGORY VALIDATION
// ============================================================

export function isValidCategory(
  category
) {

  return CATEGORIES.includes(
    category
  );

}


// ============================================================
// LANGUAGE VALIDATION
// ============================================================

export function isValidLanguage(
  language
) {

  return LANGUAGES.some(
    item =>
      item.code === language
  );

}


// ============================================================
// SOURCE LOOKUP
// ============================================================

export function getSourceById(
  id
) {

  return SOURCES.find(
    source =>
      source.id === id
  ) || null;

}