-- Content Artifact Schema v1.0 — SQLite DDL
-- Source of truth: specs/content-artifact-schema-v1.0.md
-- Generated: 2026-07-31
--
-- Tables
--   content_artifacts      — one row per published platform artifact
--   performance_snapshots  — one or more rows per artifact (point-in-time)
--
-- Enum enforcement via CHECK constraints.
-- NULL vs 0: missing metrics stored as NULL, never 0.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- content_artifacts
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS content_artifacts (
    -- Identity
    artifact_id     TEXT        NOT NULL,
    content_id      TEXT        NOT NULL,

    -- Platform & Format (Required enums)
    platform        TEXT        NOT NULL,
    format          TEXT        NOT NULL,

    -- Content Classification (Required enums)
    topic_type      TEXT        NOT NULL,
    structure       TEXT        NOT NULL,

    -- Hook (Required)
    hook_pattern    TEXT        NOT NULL,
    hook_text       TEXT        NOT NULL,   -- exact published text, not draft

    -- Optional fields
    secondary_topics TEXT,                  -- JSON array of topic_type values, e.g. '["ai","systems"]'
    length          INTEGER,               -- seconds (video) or slide count (carousel)
    cta             TEXT,
    series          TEXT,
    language        TEXT        DEFAULT 'zh',
    publish_time    TEXT,                  -- ISO 8601
    notes           TEXT,

    created_at      TEXT        NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),

    -- Primary key
    PRIMARY KEY (artifact_id),

    -- V-01: content_id format CNT-YYYY-NNN
    CHECK (content_id GLOB 'CNT-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'),

    -- V-02: artifact_id must start with content_id
    CHECK (artifact_id LIKE content_id || '-%'),

    -- V-03: platform enum
    CHECK (platform IN ('xiaohongshu', 'instagram')),

    -- V-04: topic_type enum (single value enforced; secondary_topics handles multiples)
    CHECK (topic_type IN ('ai', 'business', 'founder', 'content', 'systems', 'personal_growth')),

    -- V-05: structure enum
    CHECK (structure IN (
        'observation', 'story', 'framework', 'contrarian', 'breakdown',
        'process', 'lesson', 'prediction', 'comparison', 'principle',
        'playbook', 'review'
    )),

    -- V-06: hook_pattern enum
    CHECK (hook_pattern IN (
        'result_first', 'contradiction', 'contrarian_claim', 'question',
        'command', 'problem', 'observation', 'story_open', 'comparison',
        'curiosity_gap'
    )),

    -- V-07: hook_text must be non-empty
    CHECK (length(trim(hook_text)) > 0),

    -- V-08: format enum
    CHECK (format IN ('video_short', 'video_long', 'carousel', 'single_image', 'text')),

    -- V-10: language enum (when provided)
    CHECK (language IS NULL OR language IN ('zh', 'en'))
);

-- ---------------------------------------------------------------------------
-- performance_snapshots
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS performance_snapshots (
    -- Identity
    id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    artifact_id     TEXT        NOT NULL REFERENCES content_artifacts(artifact_id),

    -- V-11: captured_at required on all performance records (ISO 8601)
    captured_at     TEXT        NOT NULL,

    -- Cross-platform Required
    views           INTEGER     NOT NULL,

    -- Optional — Engagement (NULL = not available or not collected; 0 = platform confirmed zero)
    likes           INTEGER,
    comments        INTEGER,
    shares          INTEGER,
    saves           INTEGER,
    followers_gained INTEGER,

    -- Optional — Video
    watch_time          INTEGER,   -- total seconds watched
    average_watch_time  REAL,      -- seconds
    retention_rate      REAL,      -- 0.0–1.0
    completion_rate     REAL,      -- 0.0–1.0

    -- Optional — Carousel / Image
    impressions     INTEGER,
    engagements     INTEGER,

    -- V-09: rates must be in valid range when provided
    CHECK (retention_rate IS NULL OR (retention_rate >= 0.0 AND retention_rate <= 1.0)),
    CHECK (completion_rate IS NULL OR (completion_rate >= 0.0 AND completion_rate <= 1.0)),

    -- views must be non-negative
    CHECK (views >= 0)
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary analysis dimensions: topic_type × structure × hook_pattern × platform
CREATE INDEX IF NOT EXISTS idx_artifacts_topic     ON content_artifacts(topic_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_structure ON content_artifacts(structure);
CREATE INDEX IF NOT EXISTS idx_artifacts_hook      ON content_artifacts(hook_pattern);
CREATE INDEX IF NOT EXISTS idx_artifacts_platform  ON content_artifacts(platform);
CREATE INDEX IF NOT EXISTS idx_artifacts_content   ON content_artifacts(content_id);

-- Performance lookups by artifact and time
CREATE INDEX IF NOT EXISTS idx_snapshots_artifact  ON performance_snapshots(artifact_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_time      ON performance_snapshots(captured_at);

-- ---------------------------------------------------------------------------
-- Validation view (spot-check constraint coverage against spec)
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_artifact_summary AS
SELECT
    a.artifact_id,
    a.content_id,
    a.platform,
    a.topic_type,
    a.structure,
    a.hook_pattern,
    a.format,
    a.publish_time,
    COUNT(p.id)             AS snapshot_count,
    MAX(p.captured_at)      AS latest_snapshot,
    MAX(p.views)            AS peak_views,
    MAX(p.saves)            AS peak_saves,
    MAX(p.completion_rate)  AS peak_completion_rate
FROM content_artifacts a
LEFT JOIN performance_snapshots p ON p.artifact_id = a.artifact_id
GROUP BY a.artifact_id;
