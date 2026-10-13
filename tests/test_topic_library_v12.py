import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.topic_library import (
    AIBriefValidationError,
    QUALITY,
    PRIORITY,
    connect,
    create,
    create_from_signal,
    gate_result,
    generate_ai_brief,
    init,
    link,
    score,
    transition,
    update_brief,
    validate_ai_brief,
)
from pipeline.artifacts import insert_artifact_for_topic


VALID_SCORES = {
    "audience_relevance": 4,
    "information_gain": 3,
    "evidence_quality": 3,
    "clarity": 4,
    "share_motivation": 3,
    "narrative_tension": 3,
    "account_fit": 4,
    "demand": 2,
    "business_value": 2,
    "feasibility": 2,
}


def db_at(tmp_path):
    path = tmp_path / "content_pipeline.db"
    db = connect(path)
    init(db)
    return db


def test_fresh_database_initialization(tmp_path):
    db = db_at(tmp_path)
    tables = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"content_artifacts", "performance_snapshots", "topics", "topic_scores", "topic_status_history", "topic_artifact_links"} <= tables
    assert "score_reasoning" in {r["name"] for r in db.execute("PRAGMA table_info(topics)")}


def test_migration_against_existing_database_preserves_records(tmp_path):
    db = connect(tmp_path / "legacy.db")
    init(db)
    db.execute(
        "INSERT INTO content_artifacts(artifact_id,content_id,platform,format,topic_type,structure,hook_pattern,hook_text) VALUES(?,?,?,?,?,?,?,?)",
        ("CNT-2026-001-XHS-01", "CNT-2026-001", "xiaohongshu", "video_short", "ai", "process", "problem", "hook"),
    )
    before = db.execute("SELECT COUNT(*) AS n FROM content_artifacts").fetchone()["n"]
    init(db)
    after = db.execute("SELECT COUNT(*) AS n FROM content_artifacts").fetchone()["n"]
    assert after == before
    assert db.execute("SELECT 1 FROM topic_status_history").fetchone() is None


def test_topic_creation_and_editing(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Editable brief")
    update_brief(db, tid, {"audience": "founders", "pain_point": "manual work", "score_reasoning": "good evidence"})
    row = db.execute("SELECT audience,pain_point,score_reasoning FROM topics WHERE topic_id=?", (tid,)).fetchone()
    assert dict(row) == {"audience": "founders", "pain_point": "manual work", "score_reasoning": "good evidence"}


def test_ai_response_validation_and_malformed_json_retry():
    calls = []
    valid = {
        "audience": "ops founders",
        "pain_point": "slow reporting",
        "core_insight": "automate boring checks",
        "hook": "Your report is late before you open it.",
        "evidence": "source note",
        "target_action": "audit one workflow",
        "score_reasoning": "evidence is specific",
        "quality_scores": {k: 3 for k in QUALITY},
        "priority_scores": {k: 2 for k in PRIORITY},
    }

    def ai_call(system, request):
        calls.append((system, request))
        if len(calls) == 1:
            return "```json\n{\"audience\": \"missing scores\"\n```"
        return json.dumps(valid)

    obj, values, responses = generate_ai_brief(ai_call, "system", "request")
    assert obj["audience"] == "ops founders"
    assert values["information_gain"] == 3
    assert len(responses) == 2


def test_ai_validation_rejects_invalid_scores():
    invalid = {
        "audience": "a",
        "pain_point": "b",
        "core_insight": "c",
        "hook": "d",
        "evidence": "e",
        "target_action": "f",
        "score_reasoning": "g",
        "quality_scores": {k: 3 for k in QUALITY} | {"information_gain": 6},
        "priority_scores": {k: 2 for k in PRIORITY},
    }
    with pytest.raises(ValueError, match="information_gain"):
        validate_ai_brief(invalid)


def test_ai_failure_keeps_sanitized_diagnostics():
    def ai_call(system, request):
        if "格式修复器" in system:
            return '{"still": "bad", "authorization": "Bearer sk-ant-retrySECRET"}'
        return 'not json sk-ant-originalSECRET'

    with pytest.raises(AIBriefValidationError) as exc:
        generate_ai_brief(ai_call, "system", "request")
    assert len(exc.value.responses) == 2
    assert "sk-ant-originalSECRET" not in exc.value.responses[0]
    assert "sk-ant-retrySECRET" not in exc.value.responses[1]
    assert "[REDACTED]" in "\n".join(exc.value.responses)


def test_editable_brief_persistence(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Brief persistence")
    update_brief(db, tid, {"hook": "manual hook", "evidence": "manual evidence", "target_action": "comment", "score_reasoning": "manual reasoning"})
    score(db, tid, VALID_SCORES)
    row = db.execute("SELECT hook,evidence,target_action,score_reasoning FROM topics WHERE topic_id=?", (tid,)).fetchone()
    assert row["hook"] == "manual hook"
    assert row["score_reasoning"] == "manual reasoning"


def test_quality_scoring_and_approval_gate(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Gate")
    result = score(db, tid, VALID_SCORES)
    assert result["quality"] == 24
    assert gate_result(db, tid)["eligible"] is True
    transition(db, tid, "pending_review")
    transition(db, tid, "approved")
    assert db.execute("SELECT status FROM topics WHERE topic_id=?", (tid,)).fetchone()["status"] == "approved"


def test_approval_rejection_below_threshold(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Rejected")
    low = VALID_SCORES | {"information_gain": 2, "evidence_quality": 2}
    score(db, tid, low)
    transition(db, tid, "pending_review")
    with pytest.raises(ValueError, match="Approval blocked"):
        transition(db, tid, "approved")


def test_manual_override_and_audit_history(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Override")
    score(db, tid, VALID_SCORES | {"information_gain": 2})
    transition(db, tid, "pending_review")
    transition(db, tid, "approved", override_reason="Founder judgment with external proof")
    row = db.execute("SELECT from_status,to_status,override_reason FROM topic_status_history WHERE topic_id=? ORDER BY id DESC LIMIT 1", (tid,)).fetchone()
    assert row["from_status"] == "pending_review"
    assert row["to_status"] == "approved"
    assert row["override_reason"] == "Founder judgment with external proof"


def test_signal_import_deduplication(tmp_path):
    db = db_at(tmp_path)
    db.execute(
        "INSERT INTO signals(created,source_label,raw_text,topic,pain,conflict,module,priority,reason) VALUES(?,?,?,?,?,?,?,?,?)",
        ("2026-10-13", "notes", "raw", "AI ops", "manual work", "slow", "AI", "高", "reason"),
    )
    signal_id = db.execute("SELECT id FROM signals").fetchone()["id"]
    first = create_from_signal(db, signal_id)
    second = create_from_signal(db, signal_id)
    assert first[1] is True
    assert second == (first[0], False)


def test_topic_to_artifact_linking_supports_multiple_artifacts(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Production handoff")
    for seq, suffix, platform in [(1, "XHS", "xiaohongshu"), (2, "IG", "instagram")]:
        content_id = f"CNT-2026-{seq:03d}"
        artifact = f"{content_id}-{suffix}-01"
        db.execute(
            "INSERT INTO content_artifacts(artifact_id,content_id,platform,format,topic_type,structure,hook_pattern,hook_text) VALUES(?,?,?,?,?,?,?,?)",
            (artifact, content_id, platform, "video_short", "ai", "process", "problem", "hook"),
        )
        link(db, tid, artifact)
    assert db.execute("SELECT COUNT(*) AS n FROM topic_artifact_links WHERE topic_id=?", (tid,)).fetchone()["n"] == 2


def test_legacy_topic_artifact_links_migration_reports_invalid_rows(tmp_path):
    db = connect(tmp_path / "legacy-links.db")
    init(db)
    db.execute("PRAGMA foreign_keys=OFF")
    db.executescript("""
        DROP TABLE topic_artifact_links;
        CREATE TABLE topic_artifact_links(topic_id TEXT NOT NULL REFERENCES topics(topic_id), artifact_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY(topic_id, artifact_id));
        INSERT INTO topics(topic_id,title) VALUES('T-good','Good');
        INSERT INTO content_artifacts(artifact_id,content_id,platform,format,topic_type,structure,hook_pattern,hook_text)
        VALUES('CNT-2026-001-XHS-01','CNT-2026-001','xiaohongshu','video_short','ai','process','problem','hook');
        INSERT INTO topic_artifact_links(topic_id,artifact_id) VALUES('T-good','CNT-2026-001-XHS-01');
        INSERT INTO topic_artifact_links(topic_id,artifact_id) VALUES('T-good','missing-artifact');
    """)
    db.execute("PRAGMA foreign_keys=ON")
    result = init(db)
    fks = {(r["from"], r["table"], r["to"]) for r in db.execute("PRAGMA foreign_key_list(topic_artifact_links)")}
    assert result["migrated"] is True
    assert ("artifact_id", "content_artifacts", "artifact_id") in fks
    assert db.execute("SELECT COUNT(*) AS n FROM topic_artifact_links").fetchone()["n"] == 1
    issue = db.execute("SELECT artifact_id,reason FROM topic_artifact_link_migration_issues").fetchone()
    assert issue["artifact_id"] == "missing-artifact"
    assert "missing artifact" in issue["reason"]


def test_atomic_artifact_linking_rolls_back_orphan_on_link_failure(tmp_path):
    db = db_at(tmp_path)
    artifact = {
        "platform": "xiaohongshu",
        "format": "video_short",
        "topic_type": "ai",
        "structure": "process",
        "hook_pattern": "problem",
        "hook_text": "hook",
    }
    with pytest.raises(ValueError, match="Unknown topic ID"):
        insert_artifact_for_topic(artifact, "T-missing", tmp_path / "content_pipeline.db")
    assert db.execute("SELECT COUNT(*) AS n FROM content_artifacts").fetchone()["n"] == 0


def test_invalid_state_transition(tmp_path):
    db = db_at(tmp_path)
    tid = create(db, "Bad transition")
    with pytest.raises(ValueError, match="Invalid transition"):
        transition(db, tid, "published")
