"""Content artifact persistence helpers."""
import datetime
import sqlite3

from pipeline.constants import PLATFORMS
from pipeline.settings import DB_PATH
from pipeline.topic_library import link as link_topic_artifact


def get_db(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def next_content_id(conn) -> str:
    year = datetime.date.today().year
    row = conn.execute(
        "SELECT content_id FROM content_artifacts "
        "WHERE content_id LIKE ? "
        "ORDER BY content_id DESC LIMIT 1",
        (f"CNT-{year}-%",),
    ).fetchone()
    seq = int(row["content_id"].split("-")[2]) + 1 if row else 1
    return f"CNT-{year}-{seq:03d}"


def platform_code(platform: str) -> str:
    mapping = {"xiaohongshu": "XHS", "instagram": "IG"}
    if platform not in mapping or platform not in PLATFORMS:
        raise ValueError(f"Unknown platform '{platform}'.")
    return mapping[platform]


def insert_artifact_with_conn(conn, artifact: dict) -> str:
    content_id = next_content_id(conn)
    artifact_id = f"{content_id}-{platform_code(artifact['platform'])}-01"
    conn.execute(
        """INSERT INTO content_artifacts (
            artifact_id, content_id, platform, format,
            topic_type, structure, hook_pattern, hook_text,
            secondary_topics, length, cta, series,
            language, publish_time, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            artifact_id,
            content_id,
            artifact["platform"],
            artifact["format"],
            artifact["topic_type"],
            artifact["structure"],
            artifact["hook_pattern"],
            artifact["hook_text"],
            artifact.get("secondary_topics"),
            artifact.get("length"),
            artifact.get("cta"),
            artifact.get("series"),
            artifact.get("language", "zh"),
            artifact.get("publish_time"),
            artifact.get("notes"),
        ),
    )
    return artifact_id


def insert_artifact(artifact: dict, db_path=None) -> str:
    with get_db(db_path) as conn:
        return insert_artifact_with_conn(conn, artifact)


def insert_artifact_for_topic(artifact: dict, topic_id=None, db_path=None) -> str:
    with get_db(db_path) as conn:
        artifact_id = insert_artifact_with_conn(conn, artifact)
        if topic_id:
            link_topic_artifact(conn, topic_id, artifact_id)
        return artifact_id
