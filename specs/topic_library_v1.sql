-- Additive migration: does not modify existing content_artifacts or performance_snapshots.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS topics (
 topic_id TEXT PRIMARY KEY,
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 updated_at TEXT NOT NULL DEFAULT (datetime('now')),
 title TEXT NOT NULL,
 account TEXT NOT NULL CHECK(account IN ('Luke 2.0','Amazon x AI','Unassigned')) DEFAULT 'Unassigned',
 series TEXT,
 pillar TEXT,
 audience TEXT,
 pain_point TEXT,
 core_insight TEXT,
 hook TEXT,
 evidence TEXT,
 source_reference TEXT,
 format TEXT,
 platform TEXT,
 target_action TEXT,
 related_offer TEXT,
 keywords TEXT,
 status TEXT NOT NULL DEFAULT 'idea' CHECK(status IN ('idea','pending_review','approved','scheduled','in_production','qa','published','reviewed','paused')),
 priority TEXT CHECK(priority IN ('P0','P1','P2')),
 difficulty TEXT CHECK(difficulty IN ('low','medium','high')),
 estimated_hours REAL CHECK(estimated_hours >= 0),
 owner TEXT,
 planned_publish_at TEXT,
 actual_publish_at TEXT,
 publish_url TEXT,
 pause_reason TEXT,
 notes TEXT,
 insight_score INTEGER CHECK(insight_score BETWEEN 0 AND 35),
 priority_score INTEGER CHECK(priority_score BETWEEN 3 AND 9)
);
CREATE TABLE IF NOT EXISTS topic_scores (
 topic_id TEXT PRIMARY KEY REFERENCES topics(topic_id) ON DELETE CASCADE,
 audience_relevance INTEGER NOT NULL CHECK(audience_relevance BETWEEN 0 AND 5),
 information_gain INTEGER NOT NULL CHECK(information_gain BETWEEN 0 AND 5),
 evidence_quality INTEGER NOT NULL CHECK(evidence_quality BETWEEN 0 AND 5),
 clarity INTEGER NOT NULL CHECK(clarity BETWEEN 0 AND 5),
 share_motivation INTEGER NOT NULL CHECK(share_motivation BETWEEN 0 AND 5),
 narrative_tension INTEGER NOT NULL CHECK(narrative_tension BETWEEN 0 AND 5),
 account_fit INTEGER NOT NULL CHECK(account_fit BETWEEN 0 AND 5),
 demand INTEGER NOT NULL CHECK(demand BETWEEN 1 AND 3),
 business_value INTEGER NOT NULL CHECK(business_value BETWEEN 1 AND 3),
 feasibility INTEGER NOT NULL CHECK(feasibility BETWEEN 1 AND 3),
 scored_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Deliberately no FK to content_artifacts: legacy PK name is not verified.
CREATE TABLE IF NOT EXISTS topic_artifact_links (
 topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
 artifact_id TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 PRIMARY KEY(topic_id, artifact_id)
);
CREATE INDEX IF NOT EXISTS idx_topics_status_priority ON topics(status, priority);
CREATE INDEX IF NOT EXISTS idx_topics_account_series ON topics(account, series);
CREATE INDEX IF NOT EXISTS idx_topics_publish_date ON topics(planned_publish_at);
CREATE VIEW IF NOT EXISTS v_topic_queue AS
 SELECT topic_id,title,account,series,status,priority,insight_score,priority_score,planned_publish_at,owner
 FROM topics WHERE status IN ('approved','scheduled','in_production','qa');
CREATE VIEW IF NOT EXISTS v_topic_inbox AS
 SELECT * FROM topics WHERE status IN ('idea','pending_review');
