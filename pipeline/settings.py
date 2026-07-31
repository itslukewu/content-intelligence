"""
pipeline/settings.py
--------------------
Single source of truth for runtime configuration shared across
content_pipeline_app.py and all pipeline modules.

DB_PATH resolves relative to the repo root so the app works regardless
of the working directory, as long as it is launched from repo root:

    cd ~/Desktop/AI\ workflow/content-intelligence
    streamlit run content_pipeline_app.py
"""

import os
from pathlib import Path

# Repo root: two levels up from this file (pipeline/settings.py → pipeline/ → repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Database path — override with PIPELINE_DB env var for local dev
DB_PATH = Path(
    os.environ.get(
        "PIPELINE_DB",
        str(PROJECT_ROOT / "data" / "content_pipeline.db"),
    )
)

# Model used for hook scoring
# Switch to claude-haiku-4-5-20251001 to reduce cost at high volume
SCORER_MODEL = "claude-sonnet-4-6"
