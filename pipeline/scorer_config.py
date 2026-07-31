"""
pipeline/scorer_config.py
-------------------------
Hook scoring thresholds.

Status: EXPERIMENTAL
These values are founder-defined initial hypotheses, not statistically
validated thresholds. They control when a hook passes the gate and may
be adjusted based on Founder Review after sufficient data is collected.

Per architecture principle: Learning Requires Governance.
No threshold update is permitted without explicit Founder Review.
"""

# ---------------------------------------------------------------------------
# Gate thresholds
# Each dimension is scored 0-3 by the model. Max total = 15.
# ---------------------------------------------------------------------------

# Minimum total score across all five dimensions to pass the gate
GATE_MIN_TOTAL = 10          # EXPERIMENTAL — adjust after reviewing first 20 hooks

# Minimum score for 落差 (gap / counter-intuition strength)
# Primary lever for "does one person want to share this"
GATE_MIN_LUODI = 2           # EXPERIMENTAL

# Minimum score for 普世度 (universality of the challenged assumption)
# Primary lever for "how many people will be hit by this"
GATE_MIN_UNIVERSAL = 2       # EXPERIMENTAL

# Rationale: 落差 × 普世度 ≈ transmission ceiling.
# These two dimensions have individual floors; the rest are covered by total.
