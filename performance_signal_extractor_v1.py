#!/usr/bin/env python3
"""
performance_signal_extractor_v1.py

Reads content performance data from SQLite, aggregates by:
    hook_pattern × topic_type

Produces Signal IR v1.0 JSONL records suitable for the Opportunity Engine.

Design invariant:
    This extractor may read raw performance_snapshots rows.
    The Opportunity Engine must read only the generated Signal IR.

Example:
    python performance_signal_extractor_v1.py \
        --db data/content_pipeline.db \
        --schema specs/signal-ir-schema-v1.0.json \
        --output signals/performance_signals.jsonl \
        --min-sample-size 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: jsonschema. Install with: pip install jsonschema"
    ) from exc


EXTRACTOR_NAME = "performance_signal_extractor_v1"
SCHEMA_VERSION = "1.0"
SOURCE_TYPE = "performance"
SOURCE_PLATFORM = "performance_snapshots"

# Logical metric -> acceptable database column names.
METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "completion_rate": (
        "completion_rate",
        "video_completion_rate",
        "avg_completion_rate",
    ),
    "saves": (
        "saves",
        "save_count",
        "saved",
    ),
    "save_rate": (
        "save_rate",
        "saves_rate",
    ),
    "shares": (
        "shares",
        "share_count",
    ),
    "share_rate": (
        "share_rate",
        "shares_rate",
    ),
    "comments": (
        "comments",
        "comment_count",
    ),
    "comment_rate": (
        "comment_rate",
        "comments_rate",
    ),
    "views": (
        "views",
        "view_count",
        "plays",
        "impressions",
    ),
}

DIMENSION_ALIASES: dict[str, tuple[str, ...]] = {
    "artifact_id": (
        "artifact_id",
        "content_artifact_id",
        "content_id",
        "post_id",
    ),
    "hook_pattern": (
        "hook_pattern",
        "hook_type",
        "hook_category",
    ),
    "topic_type": (
        "topic_type",
        "topic",
        "content_topic",
        "topic_category",
    ),
    "snapshot_at": (
        "snapshot_at",
        "captured_at",
        "measured_at",
        "recorded_at",
        "created_at",
        "date",
    ),
}


@dataclass(frozen=True)
class ColumnMap:
    artifact_id: str
    hook_pattern: str
    topic_type: str
    snapshot_at: str | None
    metrics: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert performance_snapshots into Signal IR v1.0 JSONL."
    )
    parser.add_argument("--db", required=True, help="Path to SQLite database.")
    parser.add_argument(
        "--schema",
        required=True,
        help="Path to signal-ir-schema-v1.0.json.",
    )
    parser.add_argument(
        "--output",
        default="signals/performance_signals.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--table",
        default="performance_snapshots",
        help="Performance table name.",
    )
    parser.add_argument(
        "--min-sample-size",
        type=int,
        default=3,
        help="Minimum distinct artifacts required per pattern group.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.60,
        help="Signals below this threshold are skipped.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of replacing output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print signals but do not write output.",
    )
    return parser.parse_args()


def quote_identifier(identifier: str) -> str:
    if not identifier or "\x00" in identifier:
        raise ValueError("Invalid SQLite identifier.")
    return '"' + identifier.replace('"', '""') + '"'


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    query = f"PRAGMA table_info({quote_identifier(table)})"
    rows = conn.execute(query).fetchall()
    if not rows:
        raise RuntimeError(f"Table not found or has no columns: {table}")
    return [str(row[1]) for row in rows]


def resolve_alias(
    columns: Sequence[str],
    aliases: Sequence[str],
    *,
    required: bool,
    logical_name: str,
) -> str | None:
    by_lower = {column.lower(): column for column in columns}
    for alias in aliases:
        if alias.lower() in by_lower:
            return by_lower[alias.lower()]
    if required:
        raise RuntimeError(
            f"Could not resolve required field '{logical_name}'. "
            f"Expected one of {list(aliases)}; available columns: {list(columns)}"
        )
    return None


def build_column_map(columns: Sequence[str]) -> ColumnMap:
    artifact_id = resolve_alias(
        columns,
        DIMENSION_ALIASES["artifact_id"],
        required=True,
        logical_name="artifact_id",
    )
    hook_pattern = resolve_alias(
        columns,
        DIMENSION_ALIASES["hook_pattern"],
        required=True,
        logical_name="hook_pattern",
    )
    topic_type = resolve_alias(
        columns,
        DIMENSION_ALIASES["topic_type"],
        required=True,
        logical_name="topic_type",
    )
    snapshot_at = resolve_alias(
        columns,
        DIMENSION_ALIASES["snapshot_at"],
        required=False,
        logical_name="snapshot_at",
    )

    metrics: dict[str, str] = {}
    for logical_name, aliases in METRIC_ALIASES.items():
        resolved = resolve_alias(
            columns,
            aliases,
            required=False,
            logical_name=logical_name,
        )
        if resolved:
            metrics[logical_name] = resolved

    if not metrics:
        raise RuntimeError(
            "No supported performance metric columns found. "
            f"Supported aliases: {METRIC_ALIASES}"
        )

    return ColumnMap(
        artifact_id=artifact_id,
        hook_pattern=hook_pattern,
        topic_type=topic_type,
        snapshot_at=snapshot_at,
        metrics=metrics,
    )


def fetch_latest_rows(
    conn: sqlite3.Connection,
    table: str,
    columns: ColumnMap,
) -> list[dict[str, Any]]:
    """
    Returns one latest snapshot per artifact when a snapshot timestamp exists.
    Otherwise returns all rows.
    """
    select_parts = [
        f"{quote_identifier(columns.artifact_id)} AS artifact_id",
        f"{quote_identifier(columns.hook_pattern)} AS hook_pattern",
        f"{quote_identifier(columns.topic_type)} AS topic_type",
    ]

    if columns.snapshot_at:
        select_parts.append(
            f"{quote_identifier(columns.snapshot_at)} AS snapshot_at"
        )
    else:
        select_parts.append("NULL AS snapshot_at")

    for logical_name, physical_name in columns.metrics.items():
        select_parts.append(
            f"{quote_identifier(physical_name)} AS {quote_identifier(logical_name)}"
        )

    table_q = quote_identifier(table)
    artifact_q = quote_identifier(columns.artifact_id)

    if columns.snapshot_at:
        snapshot_q = quote_identifier(columns.snapshot_at)
        query = f"""
            WITH ranked AS (
                SELECT
                    {", ".join(select_parts)},
                    ROW_NUMBER() OVER (
                        PARTITION BY {artifact_q}
                        ORDER BY {snapshot_q} DESC
                    ) AS rn
                FROM {table_q}
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
        """
    else:
        query = f"SELECT {', '.join(select_parts)} FROM {table_q}"

    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query).fetchall()]


def to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_rate(value: Any) -> float | None:
    number = to_number(value)
    if number is None:
        return None
    # Accept both 0–1 and 0–100 source formats.
    if number > 1 and number <= 100:
        number /= 100
    if number < 0:
        return None
    return min(number, 1.0)


def avg(values: Iterable[float | None]) -> float | None:
    cleaned = [value for value in values if value is not None]
    return mean(cleaned) if cleaned else None


def stable_signal_id(hook_pattern: str, topic_type: str) -> str:
    payload = f"{SCHEMA_VERSION}|{SOURCE_PLATFORM}|{hook_pattern}|{topic_type}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"sig_perf_{digest}"


def confidence_for_sample(sample_size: int) -> float:
    """
    Conservative deterministic confidence:
      3 samples -> 0.60
      5 samples -> 0.70
      10 samples -> 0.85
      20+ samples -> 0.95
    """
    if sample_size < 3:
        return 0.0
    return round(min(0.95, 0.50 + 0.05 * sample_size), 2)


def group_rows(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], list[Mapping[str, Any]]]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        hook = str(row.get("hook_pattern") or "").strip()
        topic = str(row.get("topic_type") or "").strip()
        artifact_id = str(row.get("artifact_id") or "").strip()
        if not hook or not topic or not artifact_id:
            continue
        groups.setdefault((hook, topic), []).append(row)
    return groups


def latest_observed_at(rows: Sequence[Mapping[str, Any]]) -> str:
    values = [
        str(row["snapshot_at"])
        for row in rows
        if row.get("snapshot_at") not in (None, "")
    ]
    if values:
        # ISO timestamps sort lexicographically when consistently formatted.
        return max(values)

    return datetime.now(timezone.utc).isoformat()


def calculate_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    artifact_ids = sorted({str(row["artifact_id"]) for row in rows})
    metrics: dict[str, Any] = {"sample_size": len(artifact_ids)}

    completion = avg(normalize_rate(row.get("completion_rate")) for row in rows)
    if completion is not None:
        metrics["completion_rate"] = round(completion, 6)

    save_rate_values = [
        normalize_rate(row.get("save_rate")) for row in rows
    ]
    save_rate = avg(save_rate_values)

    if save_rate is None:
        derived = []
        for row in rows:
            saves = to_number(row.get("saves"))
            views = to_number(row.get("views"))
            if saves is not None and views and views > 0:
                derived.append(saves / views)
        save_rate = avg(derived)

    if save_rate is not None:
        metrics["save_rate"] = round(min(save_rate, 1.0), 6)

    share_rate = avg(normalize_rate(row.get("share_rate")) for row in rows)
    if share_rate is None:
        derived = []
        for row in rows:
            shares = to_number(row.get("shares"))
            views = to_number(row.get("views"))
            if shares is not None and views and views > 0:
                derived.append(shares / views)
        share_rate = avg(derived)
    if share_rate is not None:
        metrics["share_rate"] = round(min(share_rate, 1.0), 6)

    comment_rate = avg(normalize_rate(row.get("comment_rate")) for row in rows)
    if comment_rate is None:
        derived = []
        for row in rows:
            comments = to_number(row.get("comments"))
            views = to_number(row.get("views"))
            if comments is not None and views and views > 0:
                derived.append(comments / views)
        comment_rate = avg(derived)
    if comment_rate is not None:
        metrics["comment_rate"] = round(min(comment_rate, 1.0), 6)

    saves = [to_number(row.get("saves")) for row in rows]
    saves_clean = [value for value in saves if value is not None]
    if saves_clean:
        metrics["average_saves"] = round(mean(saves_clean), 4)

    return metrics


def build_signal(
    hook_pattern: str,
    topic_type: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    artifact_ids = sorted({str(row["artifact_id"]) for row in rows})
    metrics = calculate_metrics(rows)
    sample_size = int(metrics["sample_size"])
    confidence = confidence_for_sample(sample_size)
    extracted_at = datetime.now(timezone.utc).isoformat()

    metric_phrases = []
    if "completion_rate" in metrics:
        metric_phrases.append(
            f"average completion rate {metrics['completion_rate']:.1%}"
        )
    if "save_rate" in metrics:
        metric_phrases.append(f"average save rate {metrics['save_rate']:.1%}")
    if "average_saves" in metrics:
        metric_phrases.append(
            f"average saves {metrics['average_saves']:.2f}"
        )

    metric_summary = (
        ", ".join(metric_phrases)
        if metric_phrases
        else "available performance metrics"
    )

    return {
        "signal_id": stable_signal_id(hook_pattern, topic_type),
        "schema_version": SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "source_platform": SOURCE_PLATFORM,
        "source_ref": f"performance_snapshots:{hook_pattern}:{topic_type}",
        "extractor": EXTRACTOR_NAME,
        "signal_type": "hook_performance",
        "statement": (
            f'The "{hook_pattern}" hook pattern has measurable performance '
            f'for "{topic_type}" content.'
        ),
        "topic": "content strategy",
        "subtopic": f"{hook_pattern} × {topic_type}",
        "entities": [],
        "evidence": {
            "summary": (
                f"{sample_size} distinct content artifacts using the "
                f'"{hook_pattern}" hook pattern in the "{topic_type}" topic '
                f"group produced {metric_summary}."
            ),
            "evidence_count": sample_size,
            "artifact_ids": artifact_ids,
        },
        "metrics": metrics,
        "scores": {
            "confidence": confidence,
            "relevance": None,
            "novelty": None,
            "urgency": 0.30,
        },
        "observed_at": latest_observed_at(rows),
        "extracted_at": extracted_at,
        "valid_until": None,
        "metadata": {
            "group_dimensions": ["hook_pattern", "topic_type"],
            "hook_pattern": hook_pattern,
            "topic_type": topic_type,
        },
    }


def load_validator(schema_path: Path) -> Draft202012Validator:
    with schema_path.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    return Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )


def validate_signal(
    validator: Draft202012Validator,
    signal: Mapping[str, Any],
) -> None:
    errors = sorted(validator.iter_errors(signal), key=lambda error: list(error.path))
    if not errors:
        return

    details = []
    for error in errors:
        path = ".".join(str(part) for part in error.path) or "<root>"
        details.append(f"{path}: {error.message}")
    raise ValueError(
        f"Signal {signal.get('signal_id')} failed schema validation:\n"
        + "\n".join(details)
    )


def main() -> int:
    args = parse_args()

    db_path = Path(args.db)
    schema_path = Path(args.schema)
    output_path = Path(args.output)

    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    if not schema_path.exists():
        raise SystemExit(f"Schema not found: {schema_path}")
    if args.min_sample_size < 1:
        raise SystemExit("--min-sample-size must be >= 1")
    if not 0 <= args.confidence_threshold <= 1:
        raise SystemExit("--confidence-threshold must be between 0 and 1")

    validator = load_validator(schema_path)

    with sqlite3.connect(db_path) as conn:
        columns = get_columns(conn, args.table)
        column_map = build_column_map(columns)
        rows = fetch_latest_rows(conn, args.table, column_map)

    groups = group_rows(rows)
    signals: list[dict[str, Any]] = []

    for (hook_pattern, topic_type), grouped_rows in sorted(groups.items()):
        distinct_artifacts = {
            str(row["artifact_id"]) for row in grouped_rows
        }
        if len(distinct_artifacts) < args.min_sample_size:
            continue

        signal = build_signal(hook_pattern, topic_type, grouped_rows)
        if signal["scores"]["confidence"] < args.confidence_threshold:
            continue

        validate_signal(validator, signal)
        signals.append(signal)

    if args.dry_run:
        for signal in signals:
            print(json.dumps(signal, ensure_ascii=False))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        with output_path.open(mode, encoding="utf-8") as file:
            for signal in signals:
                file.write(json.dumps(signal, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "extractor": EXTRACTOR_NAME,
                "table": args.table,
                "source_rows": len(rows),
                "groups_found": len(groups),
                "signals_emitted": len(signals),
                "output": None if args.dry_run else str(output_path),
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
