# Content Artifact Schema v1.0

**Status**: Frozen  
**Date**: 2026-07-31  
**Scope**: Creator Intelligence — all content artifacts published to any platform

---

## Design Principles (Governing This Schema)

1. **Deterministic Before Generative** — Candidates come from rules; explanations come from LLMs. No field may contain numeric precision without a defined, verifiable source.
2. **Evidence Before Recommendation** — Recommendations must be traceable to explicit, inspectable signals.
3. **Learning Requires Governance** — Systems may suggest rule changes automatically, but persistent knowledge changes require Founder Review.
4. **Capture Once, Analyze Forever** — Collect sufficient metadata at creation time so future analyses never require retrospective reconstruction.

---

## Identity Model

A single creative idea (`content_id`) may produce multiple platform-specific published versions (`artifact_id`). All performance data attaches to the artifact, not the content.

```
content_id: CNT-2026-001
    └── artifact_id: CNT-2026-001-XHS-01   (platform: xiaohongshu)
    └── artifact_id: CNT-2026-001-IG-01    (platform: instagram)
```

**ID Format**
- `content_id`: `CNT-YYYY-NNN` (e.g. `CNT-2026-001`)
- `artifact_id`: `{content_id}-{PLATFORM_CODE}-{VERSION}` (e.g. `CNT-2026-001-XHS-01`)

**Platform Codes**
- `XHS` → xiaohongshu
- `IG` → instagram

---

## Content Metadata Schema

Captured at creation/publishing time. All Required fields must exist before an artifact enters the pipeline.

### Required

```yaml
content_id:       string        # CNT-YYYY-NNN
artifact_id:      string        # CNT-YYYY-NNN-PLATFORM-VERSION
platform:         enum          # see Platform enum
format:           enum          # see Format enum
topic_type:       enum          # see Topic Type enum
structure:        enum          # see Structure enum
hook_pattern:     enum          # see Hook Pattern enum
hook_text:        string        # exact text of the published hook (not draft)
```

### Optional

```yaml
secondary_topics: list[enum]    # additional topic_type values; Pattern Analysis uses topic_type only
length:           integer       # seconds (video) or slides (carousel); may differ post-edit
cta:              string        # call to action text if present
series:           string        # series name if part of a series
language:         enum          # zh / en (default: zh)
publish_time:     datetime      # ISO 8601; only known after actual publish
notes:            string        # free-form creator notes
```

---

## Enum Definitions

### Platform
```yaml
values:
  - xiaohongshu
  - instagram
```
*Extensible. New platforms added via Governance.*

### Format
```yaml
values:
  - video_short      # ≤ 60s vertical video
  - video_long       # > 60s
  - carousel         # multi-image / slide
  - single_image
  - text
```

### Topic Type
```yaml
values:
  - ai               # AI tools, agents, automation, development workflows
  - business         # Products, brands, operations, ads, sales, profit, market — including but not limited to Amazon
  - founder          # Startup process, decisions, Building in Public
  - content          # Content creation, Creator Economy, personal brand
  - systems          # Systems thinking, workflows, decision architecture, Founder OS
  - personal_growth  # Learning, cognition, life observations, personal development
```

**Classification Rule**: Classify by what the content primarily helps the audience *understand*, not by which business unit the source material came from.

**Examples**:
- Amazon ad structure optimization → `business`
- Founder OS architecture → `systems`
- One person running 4 brands with Claude Agents → `ai` if the primary claim is about AI workflow; `founder` or `business` if the primary claim is about running the operation

**Validation**: Exactly one `topic_type` per artifact. Use `secondary_topics` for additional classifications.

### Structure
```yaml
values:
  - observation
  - story
  - framework
  - contrarian
  - breakdown
  - process
  - lesson
  - prediction
  - comparison
  - principle
  - playbook
  - review
```

### Hook Pattern
```yaml
values:
  - result_first       # Lead with outcome or achievement
  - contradiction      # Juxtapose two apparently conflicting facts
  - contrarian_claim   # Directly challenge a widely held belief
  - question           # Open with a direct question
  - command            # Open with an action, instruction, or live demonstration
  - problem            # Open by stating a concrete pain point
  - observation        # Open with a real-world observation
  - story_open         # Open with a person, time, or event
  - comparison         # Directly contrast two options
  - curiosity_gap      # Imply an outcome without revealing the reason
```

**Validation**: `hook_pattern` must match a value in this enum. `hook_text` must be the exact published version, not the draft.

**Multi-hook Rule**: If the same content is published with different hooks (A/B test), create separate artifact records:
```
CNT-2026-001-XHS-01   (hook version A)
CNT-2026-001-XHS-02   (hook version B)
```

---

## Performance Metadata Schema

Captured post-publish during periodic performance review. Attached to `artifact_id`.

### Required (all platforms)
```yaml
artifact_id:      string        # links back to content artifact
captured_at:      datetime      # ISO 8601; when metrics were recorded
views:            integer
```

### Optional — Engagement (platform-dependent)
```yaml
likes:            integer | null
comments:         integer | null
shares:           integer | null
saves:            integer | null
followers_gained: integer | null
```

### Optional — Video
```yaml
watch_time:           integer | null    # total seconds watched
average_watch_time:   float | null      # seconds
retention_rate:       float | null      # 0.0–1.0
completion_rate:      float | null      # 0.0–1.0
```

### Optional — Carousel / Image
```yaml
impressions:    integer | null
engagements:    integer | null
```

### Null vs Zero Rule
```
null  → metric not available from platform, or not collected this cycle
0     → platform explicitly shows the value as zero
```
**Never substitute `null` with `0`. Unknown ≠ Zero.**

---

## Validation Rules

| Rule | Field | Constraint |
|---|---|---|
| V-01 | `content_id` | Format: `CNT-YYYY-NNN` |
| V-02 | `artifact_id` | Format: `{content_id}-{PLATFORM_CODE}-{VERSION}` |
| V-03 | `platform` | Must match platform enum |
| V-04 | `topic_type` | Exactly one value; must match enum |
| V-05 | `structure` | Must match structure enum |
| V-06 | `hook_pattern` | Must match hook pattern enum |
| V-07 | `hook_text` | Non-empty string; must be published version |
| V-08 | `format` | Must match format enum |
| V-09 | Performance `null` | Use `null` for unavailable metrics, never `0` |
| V-10 | `secondary_topics` | Optional; values must match topic_type enum; must not duplicate `topic_type` |
| V-11 | `captured_at` | Required on all performance records |

---

## Pattern Analysis Notes

- Primary grouping dimensions: `topic_type × structure × hook_pattern × platform`
- Initial review trigger: every 20 published artifacts
- Pattern findings must disclose sample size and remain provisional until Founder Review
- No automatic rule update is permitted based solely on reaching a fixed sample threshold
- `secondary_topics` excluded from default Pattern Analysis; available for ad-hoc queries
- Performance snapshots are point-in-time; `captured_at` is required to track metric growth over time
- Rule changes derived from Pattern Analysis require Founder Review before updating any Knowledge Base (per Principle 3: Learning Requires Governance)

---

## Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-07-31 | Initial frozen schema |
