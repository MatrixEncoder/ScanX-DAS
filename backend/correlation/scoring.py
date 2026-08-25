"""
scoring.py — Configurable correlation scoring mechanism.

Default weights (engineering defaults, not scientifically validated):
  Exact route match:      +40
  HTTP method match:      +20
  Exact route reference:  +20
  Parameter match:        +10
  Framework route match:  +10

Normalized to 0-100 with labels:
  0-39    Low
  40-69   Medium
  70-89   High
  90-100  Very High
"""

# Configurable weights
WEIGHTS = {
    "exact_route_match": 40,
    "method_match": 20,
    "exact_route_reference": 20,
    "param_match": 10,
    "framework_route_match": 10,
}

MAX_SCORE = sum(WEIGHTS.values())  # 100


def compute_score(evidence_items: list[dict]) -> tuple[int, str]:
    """
    Compute normalized confidence score from evidence items.

    Args:
        evidence_items: list of dicts with keys: signal_type, matched (bool)

    Returns:
        (score, label) where score is 0-100 and label is low/medium/high/very_high
    """
    raw = 0
    for item in evidence_items:
        if item.get("matched"):
            raw += WEIGHTS.get(item.get("signal_type", ""), 0)

    score = min(round((raw / MAX_SCORE) * 100), 100)

    if score >= 90:
        label = "very_high"
    elif score >= 70:
        label = "high"
    elif score >= 40:
        label = "medium"
    else:
        label = "low"

    return score, label
