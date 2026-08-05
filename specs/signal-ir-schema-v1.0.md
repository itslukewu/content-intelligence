# Signal IR Schema v1.0

**Status:** Frozen
**Version:** 1.0
**Date:** 2026-08-05
**Scope:** Content Intelligence — all research signals entering the Opportunity Engine

---

## Design Principles (Governing This Schema)

1. **Source Agnosticism** — The Opportunity Engine must operate only on Signal IR. It must never read raw source data directly.
2. **Atomic Statements** — One signal, one observation. A source that yields multiple observations produces multiple signals.
3. **Evidence Before Score** — Scores summarize evidence; they do not replace it. Every signal must carry a human-readable `evidence.summary`.
4. **Extensibility Without Breaking** — New signal types, source platforms, and optional fields may be added in `1.x` without breaking downstream consumers.

---

## Architectural Invariant

> Signal Extractors may depend on Sources.
> The Opportunity Engine may depend on Signal IR.
> **The Opportunity Engine must never depend directly on Sources.**

Any implementation that allows the Opportunity Engine to read Reddit comments, `performance_snapshots` rows, Daily Review files, or creator-platform exports directly violates this architecture.

---

## Layer Model

```
Sources
    ↓
Signal Extractors     (one per source type; only component that knows source format)
    ↓
Signal IR             (this schema)
    ↓
Opportunity Engine
    ↓
Candidate Topics
```

---

## Core Signal Object

```json
{
  "signal_id": "sig_01JXYZ...",
  "schema_version": "1.0",

  "source_type": "audience",
  "source_platform": "reddit",
  "source_ref": "https://...",
  "extractor": "audience_signal_extractor_v1",

  "signal_type": "question",
  "statement": "How is Claude Code different from Cursor?",

  "topic": "AI coding tools",
  "subtopic": "Claude Code vs Cursor",
  "entities": ["Claude Code", "Cursor"],

  "audience": ["developers", "AI builders"],

  "evidence": {
    "summary": "Users repeatedly ask how Claude Code differs from Cursor.",
    "excerpt": "What is the real difference between Claude Code and Cursor?",
    "evidence_count": 14
  },

  "metrics": {
    "frequency": 14,
    "engagement": 286,
    "growth_rate": null,
    "performance_lift": null
  },

  "scores": {
    "confidence": 0.88,
    "relevance": 0.91,
    "novelty": 0.62,
    "urgency": 0.73
  },

  "observed_at": "2026-08-05T10:30:00-04:00",
  "extracted_at": "2026-08-05T11:00:00-04:00",
  "valid_until": null,

  "metadata": {}
}
```

---

## Required Fields

| Field               | Type     | Description                                       |
|---------------------|----------|---------------------------------------------------|
| `signal_id`         | string   | Globally unique signal identifier                 |
| `schema_version`    | string   | Signal IR schema version                          |
| `source_type`       | enum     | High-level intelligence source (see §Source Types)|
| `extractor`         | string   | Extractor name and version that generated signal  |
| `signal_type`       | enum     | Semantic type of signal (see §Signal Types)       |
| `statement`         | string   | Atomic, human-readable claim or observation       |
| `topic`             | string   | Primary normalized topic                          |
| `evidence`          | object   | Evidence supporting the signal (see §Evidence)    |
| `scores.confidence` | number   | 0.0–1.0; extraction reliability                   |
| `observed_at`       | datetime | When the underlying signal was observed (ISO 8601)|
| `extracted_at`      | datetime | When the Signal IR object was created (ISO 8601)  |

A signal missing any required field must not enter the Opportunity Engine.

---

## Source Types

`source_type` describes the Intelligence category, not the specific platform.

| Value         | Description                                                                      |
|---------------|----------------------------------------------------------------------------------|
| `creator`     | Patterns observed in content published by other creators                         |
| `audience`    | Questions, pains, objections, desires, or language from the audience             |
| `founder`     | Insights from the creator's own work, decisions, mistakes, or experience         |
| `knowledge`   | Ideas derived from books, papers, courses, frameworks, or reports                |
| `trend`       | Emerging external developments, releases, policy changes, or market shifts       |
| `performance` | Patterns derived from historical content performance                             |

`source_platform` is an open string — not a closed enum — so new sources can be added without schema changes. Examples:

```
reddit, youtube, xiaohongshu, linkedin, x, tiktok,
daily_review, conversation, performance_snapshots,
book, research_paper, google_trends, manual
```

---

## Signal Types

`signal_type` describes what the signal means. The list is extensible; the Opportunity Engine must handle unknown values gracefully (skip or log, not error).

### Audience signals
```
question, pain, confusion, objection, aspiration,
desire, resistance, misconception, language_pattern
```

### Creator and trend signals
```
emerging_topic, saturated_topic, content_pattern,
narrative, contrarian_view, consensus, format_pattern,
hook_pattern
```

### Founder and knowledge signals
```
insight, lesson, decision, mistake, observation,
framework, principle, case_study, analogy
```

### Performance signals
```
validated_pattern, anti_pattern, performance_anomaly,
audience_preference, topic_performance, format_performance,
hook_performance
```

---

## Atomic Statement Rule

`statement` must contain exactly one observation.

**Good:**
```
Users are confused about how Claude Code differs from Cursor.
```

**Bad:**
```
Users are confused about Claude Code, Cursor, AI agents, pricing, and whether coding will disappear.
```

A single raw source may and should produce multiple Signal IR objects. Each atomic observation becomes its own signal with its own `signal_id`.

**Example decomposition:**
```
Raw Reddit thread
    ↓
Signal 1: Users do not understand the difference between Claude Code and Cursor.
Signal 2: Users assume Claude Code requires strong programming skills.
Signal 3: Users are worried about Claude Code token costs.
```

---

## Evidence Object

```json
{
  "summary": "Short explanation of the evidence supporting the signal.",
  "excerpt": "Optional short excerpt preserving audience language.",
  "evidence_count": 14,
  "artifact_ids": ["artifact_123"],
  "source_items": [
    { "source_item_id": "reddit_post_123", "source_ref": "https://..." }
  ]
}
```

**Required:** `summary`
**Optional:** `excerpt`, `evidence_count`, `artifact_ids`, `source_items`

`excerpt` must be short. Its purpose is to preserve original audience language, not to store source content. The system must not store entire source documents inside Signal IR.

---

## Metrics Object

All fields optional. Not every signal has quantitative evidence.

```json
{
  "frequency": 14,
  "engagement": 286,
  "growth_rate": 0.42,
  "performance_lift": 0.18,
  "sample_size": 22,
  "completion_rate": 0.71,
  "save_rate": 0.094,
  "share_rate": null,
  "comment_rate": null
}
```

Source-specific metrics that are not broadly useful must remain inside `metadata`, not `metrics`.

---

## Scores Object

All scores: `0.0` to `1.0`. Only `confidence` is required in v1.0.

| Score        | Meaning                                                                        |
|--------------|--------------------------------------------------------------------------------|
| `confidence` | How reliably was the signal extracted? (extraction quality, not opportunity quality) |
| `relevance`  | How relevant is this to the creator's content pillars and target audience?     |
| `novelty`    | How different is this from existing signals and published content?             |
| `urgency`    | How quickly will this signal lose value if not acted on?                       |

`relevance`, `novelty`, and `urgency` may be computed by the Opportunity Engine rather than the Extractor.

---

## Topic Normalization

```json
{
  "topic": "AI coding tools",
  "subtopic": "Claude Code vs Cursor",
  "entities": ["Claude Code", "Cursor"]
}
```

`topic` must be a reusable semantic category, not a description of the source item.

**Bad:** `That Reddit post about Claude Code`
**Good:** `AI coding tools`

`entities` should identify products, people, companies, frameworks, or concepts referenced in the signal.

---

## Time Fields

```json
{
  "observed_at": "2026-08-05T10:30:00-04:00",
  "extracted_at": "2026-08-05T11:00:00-04:00",
  "valid_until": null
}
```

| Field        | Description                                                       |
|--------------|-------------------------------------------------------------------|
| `observed_at`  | When the underlying event, question, or pattern occurred        |
| `extracted_at` | When the extractor created this Signal IR object                |
| `valid_until`  | Optional. Opportunity Engine may penalize expired signals.      |

All time fields: ISO 8601.

---

## Metadata

```json
{
  "metadata": {
    "platform_post_id": "abc123",
    "language": "en",
    "country": "US"
  }
}
```

**Rules:**
1. Source-specific fields stay in `metadata` unless multiple source types need them.
2. Opportunity Engine logic must not depend on `metadata` fields.
3. `metadata` must not become a hidden second schema.

---

## Validation Rules

A Signal IR object is valid only when:

1. `signal_id` is unique across all signals.
2. `schema_version` is supported.
3. `source_type` matches an allowed value.
4. `statement` is non-empty and atomic.
5. `topic` is non-empty.
6. `evidence.summary` is non-empty.
7. `scores.confidence` is between `0.0` and `1.0`.
8. Time fields use ISO 8601.
9. Raw source content is not stored beyond what evidence requires.
10. Source-specific data is confined to `metadata`.

**Quality gates (recommended):**
```
confidence          >= 0.60     (below threshold: store but do not auto-enter Opportunity Engine)
statement           <= 300 chars
evidence.summary    <= 1,000 chars
excerpt             <= 500 chars
```

---

## Storage Model

```
signals/
├── creator_signals.jsonl
├── audience_signals.jsonl
├── founder_signals.jsonl
├── knowledge_signals.jsonl
├── trend_signals.jsonl
└── performance_signals.jsonl
```

The Opportunity Engine may consume `signals/*.jsonl` individually or a materialized:
```
unified_signals.jsonl
```

**JSONL over JSON array** — supports append-only writes, incremental processing, streaming, partial regeneration by source, and large datasets without full rewrites.

---

## Deduplication

Signals must not be deduplicated by exact text match alone.

Semantic identity for deduplication:
```
normalized topic + signal type + semantic meaning + time window
```

Multiple similar observations expressing the same idea should be merged. The merged signal retains:
- Combined `evidence_count`
- All `source_items` references
- Earliest `observed_at`, latest update
- Recalculated `confidence`
- All originating `signal_id` values in `metadata`

---

## Relationship to Opportunities

Signals are evidence. They are not yet content ideas.

The Opportunity Engine combines signals:

```
Audience Signal:   Users don't understand how Claude Code differs from Cursor.
Creator Signal:    AI coding tool comparisons are receiving rising engagement.
Founder Signal:    Tool choice matters less than understanding the interaction model.
Performance Signal: Old Definition → New Definition scripts produce high save rates.
    ↓
Opportunity:
  Topic:     Claude Code vs Cursor is the wrong question.
  Angle:     Terminal agent vs editor-native copilot.
  Structure: Old Definition → New Definition
  Hook:      "Claude Code vs Cursor is the wrong comparison."
```

Every opportunity must be traceable back to its supporting `signal_id` values.

---

## Examples

### Founder Intelligence

```json
{
  "signal_id": "sig_founder_001",
  "schema_version": "1.0",
  "source_type": "founder",
  "source_platform": "daily_review",
  "source_ref": "daily_review_2026-08-03",
  "extractor": "founder_signal_extractor_v1",
  "signal_type": "principle",
  "statement": "Unknown does not mean safe.",
  "topic": "systems thinking",
  "subtopic": "data observability",
  "entities": [],
  "audience": ["founders", "AI builders", "operators"],
  "evidence": {
    "summary": "A data pipeline excluded SKUs without sales, causing active advertising spend to disappear from the decision system.",
    "evidence_count": 1,
    "artifact_ids": ["daily_review_2026-08-03"]
  },
  "metrics": { "financial_exposure": 197 },
  "scores": { "confidence": 0.98, "relevance": 0.94, "novelty": 0.86, "urgency": 0.35 },
  "observed_at": "2026-08-03T16:00:00-04:00",
  "extracted_at": "2026-08-03T21:00:00-04:00",
  "valid_until": null,
  "metadata": { "project": "Amazon Data Pipeline", "decision_record": "ADR-001" }
}
```

### Audience Intelligence

```json
{
  "signal_id": "sig_audience_001",
  "schema_version": "1.0",
  "source_type": "audience",
  "source_platform": "youtube_comments",
  "source_ref": "video_123",
  "extractor": "audience_signal_extractor_v1",
  "signal_type": "confusion",
  "statement": "Users do not understand how AI fluency differs from prompt engineering.",
  "topic": "AI education",
  "subtopic": "AI fluency",
  "entities": ["AI Fluency"],
  "audience": ["AI beginners", "knowledge workers"],
  "evidence": {
    "summary": "Multiple comments describe AI learning primarily as collecting better prompts.",
    "excerpt": "Isn't AI fluency basically just knowing what prompts to use?",
    "evidence_count": 9
  },
  "metrics": { "frequency": 9 },
  "scores": { "confidence": 0.91, "relevance": 0.96, "novelty": 0.58, "urgency": 0.46 },
  "observed_at": "2026-08-04T12:00:00-04:00",
  "extracted_at": "2026-08-05T09:00:00-04:00",
  "valid_until": null,
  "metadata": { "language": "en" }
}
```

### Performance Intelligence

```json
{
  "signal_id": "sig_performance_001",
  "schema_version": "1.0",
  "source_type": "performance",
  "source_platform": "performance_snapshots",
  "source_ref": "pattern_report_2026-08-01",
  "extractor": "performance_signal_extractor_v1",
  "signal_type": "hook_performance",
  "statement": "Replacement hooks outperform question hooks for founder-system content.",
  "topic": "content strategy",
  "subtopic": "hook patterns",
  "entities": [],
  "audience": ["founders", "AI builders"],
  "evidence": {
    "summary": "Posts using replacement hooks produced higher average completion and save rates than posts using question hooks.",
    "evidence_count": 12,
    "artifact_ids": ["artifact_011", "artifact_017", "artifact_024"]
  },
  "metrics": {
    "sample_size": 12,
    "completion_rate": 0.71,
    "save_rate": 0.094,
    "performance_lift": 0.18
  },
  "scores": { "confidence": 0.74, "relevance": 0.97, "novelty": 0.51, "urgency": 0.30 },
  "observed_at": "2026-08-01T23:00:00-04:00",
  "extracted_at": "2026-08-02T08:00:00-04:00",
  "valid_until": null,
  "metadata": { "comparison_group": "question_hook", "minimum_sample_threshold": 5 }
}
```

---

## Minimum Viable Implementation

Phase 1 extractors (sufficient to establish the interface contract):
```
creator_signal_extractor     ← creator_intelligence.json
founder_signal_extractor     ← daily_review / conversations.md
performance_signal_extractor ← performance_snapshots DB
```

Phase 2:
```
audience_signal_extractor    ← manual inputs, Reddit, comments
```

Phase 3 (post Asset Extraction Agent unlock):
```
knowledge_signal_extractor
trend_signal_extractor
```

---

## Non-Goals of v1.0

This schema does not define:
- Raw source schemas or extractor implementation details
- Complete topic or audience taxonomies
- Opportunity scoring formulas
- Content artifact schemas (see `content-artifact-schema-v1.0.md`)
- Publishing or analytics storage schemas

Its only responsibility: the interface between Signal Extractors and the Opportunity Engine.

---

## Versioning Policy

**Backward-compatible (1.x):** new optional fields, new `signal_type` values, new `source_platform` strings, new `metadata` fields.

**Breaking (→ 2.0):** removing required fields, renaming core fields, changing field semantics, changing score ranges, changing required types.

Every persisted signal must retain its original `schema_version`.

---

## Changelog

| Version | Date       | Change               |
|---------|------------|----------------------|
| v1.0    | 2026-08-05 | Initial frozen schema |
