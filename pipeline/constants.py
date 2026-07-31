"""
pipeline/constants.py
---------------------
Schema v1.0 enum values as Python constants.
Single source of truth for all dropdowns, validation, and DB constraints.

Source of truth: specs/content-artifact-schema-v1.0.md
Do not add values here without updating the spec and schema_v1.0.sql.
"""

TOPIC_TYPES = [
    "ai",
    "business",
    "founder",
    "content",
    "systems",
    "personal_growth",
]

STRUCTURES = [
    "observation",
    "story",
    "framework",
    "contrarian",
    "breakdown",
    "process",
    "lesson",
    "prediction",
    "comparison",
    "principle",
    "playbook",
    "review",
]

HOOK_PATTERNS = [
    "result_first",
    "contradiction",
    "contrarian_claim",
    "question",
    "command",
    "problem",
    "observation",
    "story_open",
    "comparison",
    "curiosity_gap",
]

# Definitions shown in Hook Generator prompt so the model uses correct enum values
HOOK_PATTERN_DEFINITIONS = """
Hook pattern enum values and their definitions:
- result_first: Lead with outcome or achievement
- contradiction: Juxtapose two apparently conflicting facts
- contrarian_claim: Directly challenge a widely held belief
- question: Open with a direct question
- command: Open with an action, instruction, or live demonstration
- problem: Open by stating a concrete pain point
- observation: Open with a real-world observation
- story_open: Open with a person, time, or event
- comparison: Directly contrast two options
- curiosity_gap: Imply an outcome without revealing the reason
"""

PLATFORMS = [
    "xiaohongshu",
    "instagram",
]

FORMATS = [
    "video_short",
    "video_long",
    "carousel",
    "single_image",
    "text",
]

LANGUAGES = ["zh", "en"]
