// ============================================================
// SNIPPET24 — CONTROLLED NEWS SOURCE REGISTRY
// Version: 1.0
//
// IMPORTANT:
// A source remains disabled until its feed/API terms and
// commercial usage rights have been reviewed and approved.
// ============================================================

export const SOURCES = [

  // ==========================================================
  // OFFICIAL / PRIMARY SOURCES
  // ==========================================================

  {
    id: "nasa-news",
    name: "NASA",
    publisher: "NASA",

    feed_url: "https://www.nasa.gov/news-release/feed/",

    source_type: "rss",

    country: "United States",
    language: "en",

    rights_status: "review_required",
    enabled: false,

    verification_level: "primary",

    categories: [
      "Science",
      "Technology & AI",
      "World",
      "Climate"
    ]
  },

  {
    id: "nasa-jpl",
    name: "NASA Jet Propulsion Laboratory",
    publisher: "NASA JPL",

    feed_url: "https://www.jpl.nasa.gov/feeds/news/",

    source_type: "rss",

    country: "United States",
    language: "en",

    rights_status: "review_required",
    enabled: false,

    verification_level: "primary",

    categories: [
      "Science",
      "Technology & AI"
    ]
  },

  {
    id: "nasa-cneos",
    name: "NASA Center for Near Earth Object Studies",
    publisher: "NASA CNEOS",

    feed_url: "https://cneos.jpl.nasa.gov/feed/news.xml",

    source_type: "rss",

    country: "United States",
    language: "en",

    rights_status: "review_required",
    enabled: false,

    verification_level: "primary",

    categories: [
      "Science",
      "Technology & AI",
      "World"
    ]
  },

  // ==========================================================
  // WORLD HEALTH
  // ==========================================================

  {
    id: "who-news",
    name: "World Health Organization",
    publisher: "WHO",

    feed_url: "https://www.who.int/rss-feeds/news-english.xml",

    source_type: "rss",

    country: "International",
    language: "en",

    rights_status: "review_required",
    enabled: false,

    verification_level: "primary",

    categories: [
      "Health",
      "World",
      "Science"
    ]
  },

  // ==========================================================
  // ADDITIONAL SOURCES
  //
  // These remain disabled until we verify:
  // 1. Feed availability
  // 2. Terms of use
  // 3. Commercial usage
  // 4. Redistribution rights
  // ==========================================================

  {
    id: "example-source-01",
    name: "Future Approved Source",
    publisher: "Future Publisher",

    feed_url: "",

    source_type: "rss",

    country: "",
    language: "en",

    rights_status: "review_required",
    enabled: false,

    verification_level: "standard",

    categories: []
  }

];


// ============================================================
// ALLOWED EDITORIAL CATEGORIES
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


// ============================================================
// SUPPORTED LANGUAGES
// ============================================================

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
// SOURCE VALIDATION
// ============================================================

export function getApprovedSources() {

  return SOURCES.filter(
    source =>
      source.enabled === true &&
      source.rights_status === "approved" &&
      source.feed_url
  );

}


// ============================================================
// FIND SOURCE BY ID
// ============================================================

export function getSourceById(id) {

  return SOURCES.find(
    source => source.id === id
  );

}


// ============================================================
// CHECK WHETHER A SOURCE CAN BE USED
// ============================================================

export function isSourceApproved(source) {

  if (!source) {
    return false;
  }

  return (
    source.enabled === true &&
    source.rights_status === "approved" &&
    Boolean(source.feed_url)
  );

}


// ============================================================
// CATEGORY VALIDATION
// ============================================================

export function isValidCategory(category) {

  return CATEGORIES.includes(category);

}


// ============================================================
// LANGUAGE VALIDATION
// ============================================================

export function isSupportedLanguage(language) {

  return LANGUAGES.some(
    item => item.code === language
  );

}