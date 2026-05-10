"""
High-level similarity API for country trees.

Given two country trees, returns:
  - overall similarity in [0, 1]   (1.0 = identical, 0.0 = maximally different)
  - per-leaf cost breakdown        (which fields drove the difference)
  - raw tree edit distance         (for debugging)
"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

from leaf_costs import leaf_cost, calibrate_from_trees
from ted import tree_edit_distance, max_possible_distance


@dataclass
class SimilarityResult:
    country_a: str
    country_b: str
    similarity: float                 # [0, 1], higher = more similar
    distance: float                   # raw TED
    max_distance: float               # upper bound used for normalization
    leaf_breakdown: list[tuple[str, float]]   # [(leaf_name, cost), ...]

    def __repr__(self) -> str:
        return (f"SimilarityResult({self.country_a} ↔ {self.country_b}: "
                f"similarity={self.similarity:.3f}, distance={self.distance:.3f})")


def _walk_leaves(node, prefix: str = "", is_root: bool = True) -> list:
    """Yield (path, leaf_node) pairs for every leaf in the tree.
    The root (country name) is excluded from the path so that paths like
    'Demographics/Population' match across different country trees.
    """
    if node.is_leaf:
        return [(f"{prefix}/{node.name}".lstrip("/"), node)]
    # Skip the root's name in the path; include all internal nodes below it
    new_prefix = prefix if is_root else f"{prefix}/{node.name}".lstrip("/")
    out = []
    for c in node.children:
        out.extend(_walk_leaves(c, new_prefix, is_root=False))
    return out


def _leaf_breakdown(tree_a, tree_b) -> list[tuple[str, float]]:
    """Direct per-leaf cost comparison.
    Country trees share the same skeleton, so we can pair leaves by their path
    (Demographics/Population, Economy/HDI, etc.) and report each one's
    contribution. This is what the UI's right-hand panel will display.
    """
    leaves_a = {path: node for path, node in _walk_leaves(tree_a)}
    leaves_b = {path: node for path, node in _walk_leaves(tree_b)}

    rows = []
    for path in sorted(leaves_a.keys() | leaves_b.keys()):
        node_a = leaves_a.get(path)
        node_b = leaves_b.get(path)
        if node_a is None or node_b is None:
            cost = 1.0
        else:
            cost = leaf_cost(node_a, node_b)
        rows.append((path, cost))
    return rows


def compare(tree_a, tree_b) -> SimilarityResult:
    """Compute full similarity result between two country trees."""
    distance = tree_edit_distance(tree_a, tree_b)
    max_dist = max_possible_distance(tree_a, tree_b)
    similarity = 1.0 - (distance / max_dist) if max_dist > 0 else 1.0
    similarity = max(0.0, min(1.0, similarity))

    return SimilarityResult(
        country_a=tree_a.name,
        country_b=tree_b.name,
        similarity=similarity,
        distance=distance,
        max_distance=max_dist,
        leaf_breakdown=_leaf_breakdown(tree_a, tree_b),
    )


def initialize(trees: dict) -> None:
    """Calibrate numerical normalization ranges from the dataset.
    Call once at startup before computing any similarities.
    """
    calibrate_from_trees(trees)