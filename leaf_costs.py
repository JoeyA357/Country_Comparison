"""
Cost functions for comparing leaf nodes in country trees.

v3 changes (vs v2):
  - Replaces log-scale normalization with PERCENTILE-based normalization.
    Each numerical value is mapped to its rank percentile within the dataset,
    and cost = |rank_a - rank_b|. Robust to outliers, stretches dynamic range,
    and produces a uniform cost distribution.
  - Adds cost function for the new 'single_categorical' leaf type.
  - New weights for the expanded 14-leaf schema.
"""
from __future__ import annotations
import math
import bisect
from typing import Optional

# Penalty applied when one or both leaves have a missing value
MISSING_PENALTY = 0.5


# ─────────────────────────────────────────────────────────────────────
# Per-leaf weights for the new 14-leaf schema.
#
# Rationale:
#   - GDPperCapita gets full weight: best single development indicator.
#   - HDI full weight: composite human development.
#   - Memberships full weight: rich, very discriminating.
#   - DrivingSide full weight: clean binary signal.
#   - GDPNominal/Population/Area at 0.7 each: still useful, but redundant
#     with GDPperCapita (which combines GDP and population).
#   - LifeExpectancy at 0.6: overlaps with HDI.
#   - Continents at 0.4: kept low to allow cross-continental clustering.
#   - Currencies at 0.5: correlates with continent and memberships.
#   - LandBorders at 0.5: small but useful geographic signal.
#   - InceptionYear at 0.6: era is a meaningful but secondary signal.
# ─────────────────────────────────────────────────────────────────────
LEAF_WEIGHTS: dict[str, float] = {
    "Area":           0.7,
    "Population":     0.7,
    "GDPNominal":     0.7,
    "GDPperCapita":   1.0,
    "HDI":            1.0,
    "LifeExpectancy": 0.6,
    "InceptionYear":  0.6,
    "LandBorders":    0.5,
    "Continents":     0.4,
    "Currencies":     0.5,
    "Languages":      1.0,
    "Governments":    1.0,
    "Memberships":    1.0,
    "DrivingSide":    1.0,
}


# ─────────────────────────────────────────────────────────────────────
# Percentile lookup tables — populated by calibrate_from_trees() at startup.
# For each numerical leaf, we store the sorted list of values across all
# countries so we can map any value to its percentile rank in O(log n).
# ─────────────────────────────────────────────────────────────────────
SORTED_VALUES: dict[str, list[float]] = {}


def calibrate_from_trees(trees) -> None:
    """Walk every tree, collect numerical values per leaf name, sort them.
    These sorted lists become the basis for percentile-rank lookups.
    """
    values: dict[str, list[float]] = {}

    def walk(node):
        if node.is_leaf and node.leaf_type == "numerical" and node.value is not None:
            values.setdefault(node.name, []).append(float(node.value))
        for c in node.children:
            walk(c)

    for tree in trees.values():
        walk(tree)

    for name, vals in values.items():
        SORTED_VALUES[name] = sorted(vals)


def _percentile_rank(name: str, value: float) -> float:
    """Return the percentile rank of `value` within the dataset for `name`,
    in [0.0, 1.0]. Uses bisect for O(log n) lookup.
    Returns 0.5 (neutral) if calibration data missing.
    """
    sorted_vals = SORTED_VALUES.get(name)
    if not sorted_vals:
        return 0.5
    n = len(sorted_vals)
    # bisect_left gives the count of values strictly less than `value`,
    # bisect_right the count of values <= value. Average them for fractional ranks.
    lo = bisect.bisect_left(sorted_vals, value)
    hi = bisect.bisect_right(sorted_vals, value)
    rank = (lo + hi) / 2.0
    return rank / n if n > 0 else 0.5


# ─────────────────────────────────────────────────────────────────────
# Cost functions
# ─────────────────────────────────────────────────────────────────────
def numerical_cost(name: str, a: Optional[float], b: Optional[float]) -> float:
    """Distance between two numerical values via percentile rank difference.
    Range: [0.0, 1.0]. The two countries furthest apart in rank get cost 1.0.
    """
    if a is None or b is None:
        return MISSING_PENALTY
    if a == b:
        return 0.0
    rank_a = _percentile_rank(name, a)
    rank_b = _percentile_rank(name, b)
    return abs(rank_a - rank_b)


def jaccard_distance(a: Optional[list], b: Optional[list]) -> float:
    """1 - Jaccard similarity between two sets."""
    if a is None or b is None:
        return MISSING_PENALTY
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    intersection = set_a & set_b
    return 1.0 - len(intersection) / len(union)


def set_cost(a: Optional[list], b: Optional[list]) -> float:
    return jaccard_distance(a, b)


def single_categorical_cost(a: Optional[str], b: Optional[str]) -> float:
    """Match (0) or no match (1) for binary categorical fields."""
    if a is None or b is None:
        return MISSING_PENALTY
    return 0.0 if a == b else 1.0


def leaf_cost(node_a, node_b) -> float:
    """Dispatch on leaf_type and return the WEIGHTED cost between two leaves
    of the same name. Weight scales how much this leaf contributes to TED.
    """
    if node_a.leaf_type != node_b.leaf_type:
        return 1.0 * LEAF_WEIGHTS.get(node_a.name, 1.0)
    weight = LEAF_WEIGHTS.get(node_a.name, 1.0)
    if node_a.leaf_type == "numerical":
        return weight * numerical_cost(node_a.name, node_a.value, node_b.value)
    if node_a.leaf_type == "set":
        return weight * set_cost(node_a.value, node_b.value)
    if node_a.leaf_type == "single_categorical":
        return weight * single_categorical_cost(node_a.value, node_b.value)
    return weight