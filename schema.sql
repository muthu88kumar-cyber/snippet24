-- ============================================================
-- SNIPPET24 — LIVE NEWS INTELLIGENCE DATABASE
-- Database: Cloudflare D1 / SQLite
-- Version: 1.0
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. STORIES
-- Main published SNIPPET24 stories
-- ============================================================

CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,

    -- Duplicate/event control
    event_key TEXT NOT NULL UNIQUE,

    -- Editorial classification
    category TEXT NOT NULL,
    subcategory TEXT,
    location TEXT,
    country TEXT,

    -- Story content
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    impact TEXT NOT NULL,

    -- Source information
    publisher TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'rss',

    -- Timing
    published_at TEXT NOT NULL,
    updated_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Editorial / verification
    verification_status TEXT NOT NULL DEFAULT 'verified',
    verification_note TEXT,

    -- Rights / licensing
    rights_status TEXT NOT NULL DEFAULT 'approved',

    -- Original language
    language TEXT NOT NULL DEFAULT 'en',

    -- AI-generated translations
    translations_json TEXT,

    -- Optional media
    image_url TEXT,

    -- Development state
    story_status TEXT NOT NULL DEFAULT 'published',

    -- AI/editorial metadata
    ai_processed INTEGER NOT NULL DEFAULT 1,
    correction_version INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- STORY INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_stories_published
ON stories(published_at DESC);

CREATE INDEX IF NOT EXISTS idx_stories_category
ON stories(category);

CREATE INDEX IF NOT EXISTS idx_stories_location
ON stories(location);

CREATE INDEX IF NOT EXISTS idx_stories_country
ON stories(country);

CREATE INDEX IF NOT EXISTS idx_stories_status
ON stories(story_status);

CREATE INDEX IF NOT EXISTS idx_stories_rights
ON stories(rights_status);

CREATE INDEX IF NOT EXISTS idx_stories_publisher
ON stories(publisher);


-- ============================================================
-- 2. SOURCES
-- Controlled registry of news sources
-- Only approved + enabled sources may be ingested.
-- ============================================================

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,

    name TEXT NOT NULL,

    feed_url TEXT NOT NULL UNIQUE,

    source_type TEXT NOT NULL DEFAULT 'rss',

    -- approved / review_required / rejected
    rights_status TEXT NOT NULL DEFAULT 'review_required',

    enabled INTEGER NOT NULL DEFAULT 0,

    -- Source reliability metadata
    verification_level TEXT NOT NULL DEFAULT 'standard',

    country TEXT,

    language TEXT DEFAULT 'en',

    last_checked_at TEXT,

    last_success_at TEXT,

    last_error TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_enabled
ON sources(enabled);

CREATE INDEX IF NOT EXISTS idx_sources_rights
ON sources(rights_status);


-- ============================================================
-- 3. SOURCE ITEMS
-- Keeps track of individual RSS/API items before publication.
-- Helps prevent repeated ingestion.
-- ============================================================

CREATE TABLE IF NOT EXISTS source_items (
    id TEXT PRIMARY KEY,

    source_id TEXT NOT NULL,

    item_key TEXT NOT NULL UNIQUE,

    title TEXT,

    source_url TEXT NOT NULL,

    published_at TEXT,

    description TEXT,

    processed INTEGER NOT NULL DEFAULT 0,

    rejected INTEGER NOT NULL DEFAULT 0,

    rejection_reason TEXT,

    story_id TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_id)
        REFERENCES sources(id)
        ON DELETE CASCADE,

    FOREIGN KEY (story_id)
        REFERENCES stories(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_source_items_source
ON source_items(source_id);

CREATE INDEX IF NOT EXISTS idx_source_items_processed
ON source_items(processed);

CREATE INDEX IF NOT EXISTS idx_source_items_published
ON source_items(published_at DESC);


-- ============================================================
-- 4. STORY SOURCES
-- Allows one story/event to reference multiple publishers.
-- Important for future duplicate-event merging.
-- ============================================================

CREATE TABLE IF NOT EXISTS story_sources (
    id TEXT PRIMARY KEY,

    story_id TEXT NOT NULL,

    publisher TEXT NOT NULL,

    source_url TEXT NOT NULL,

    source_type TEXT NOT NULL DEFAULT 'rss',

    published_at TEXT,

    verification_status TEXT NOT NULL DEFAULT 'unverified',

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (story_id)
        REFERENCES stories(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_story_sources_story
ON story_sources(story_id);

CREATE INDEX IF NOT EXISTS idx_story_sources_publisher
ON story_sources(publisher);


-- ============================================================
-- 5. STORY CORRECTIONS
-- Keeps an audit trail when a published story changes.
-- ============================================================

CREATE TABLE IF NOT EXISTS story_corrections (
    id TEXT PRIMARY KEY,

    story_id TEXT NOT NULL,

    version INTEGER NOT NULL,

    previous_title TEXT,

    previous_summary TEXT,

    previous_impact TEXT,

    correction_reason TEXT NOT NULL,

    corrected_by TEXT NOT NULL DEFAULT 'system',

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (story_id)
        REFERENCES stories(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_story_corrections_story
ON story_corrections(story_id);


-- ============================================================
-- 6. SYSTEM STATE
-- Stores global backend state and operational information.
-- ============================================================

CREATE TABLE IF NOT EXISTS system_state (
    key TEXT PRIMARY KEY,

    value TEXT,

    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 7. INGESTION LOG
-- Records each scheduled source refresh.
-- Useful for diagnosing failed feeds.
-- ============================================================

CREATE TABLE IF NOT EXISTS ingestion_log (
    id TEXT PRIMARY KEY,

    source_id TEXT,

    started_at TEXT NOT NULL,

    finished_at TEXT,

    status TEXT NOT NULL,

    items_found INTEGER NOT NULL DEFAULT 0,

    items_new INTEGER NOT NULL DEFAULT 0,

    stories_created INTEGER NOT NULL DEFAULT 0,

    stories_skipped INTEGER NOT NULL DEFAULT 0,

    error_message TEXT,

    FOREIGN KEY (source_id)
        REFERENCES sources(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_source
ON ingestion_log(source_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_started
ON ingestion_log(started_at DESC);


-- ============================================================
-- 8. DEFAULT SYSTEM STATE
-- ============================================================

INSERT OR IGNORE INTO system_state (key, value)
VALUES ('schema_version', '1.0');

INSERT OR IGNORE INTO system_state (key, value)
VALUES ('last_refresh_at', '');

INSERT OR IGNORE INTO system_state (key, value)
VALUES ('last_successful_refresh_at', '');

INSERT OR IGNORE INTO system_state (key, value)
VALUES ('backend_status', 'initializing');


-- ============================================================
-- END OF SNIPPET24 DATABASE SCHEMA
-- ============================================================