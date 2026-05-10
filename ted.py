"""
Nierman & Jagadish Tree Edit Distance (TED) for country trees.

Algorithm overview:
  Given two rooted, ordered trees A and B, find the minimum-cost sequence
  of edit operations (insert subtree, delete subtree, relabel node) to
  transform A into B.

  Three edit operations:
    1. Relabel  — change a node's label/value. Cost given by the leaf
                  cost function (for leaves) or 0/1 for internal nodes
                  (0 if labels match, 1 otherwise).
    2. Delete   — remove a subtree from A entirely. Cost = sum of
                  delete costs of all nodes in the subtree.
    3. Insert   — add a subtree to A. Cost = sum of insert costs.

  We use the standard convention: insert and delete of a single node
  each cost 1.0 by default for internal nodes. Leaves cost MISSING_PENALTY
  when matched against "nothing" (an insertion or deletion).

Recurrence:
  dist(A, B) = min(
      dist(A_children, B_children) + relabel(root_A, root_B),
      dist(empty, B) + delete_cost(A),
      dist(A, empty) + insert_cost(B),
  )

  dist over child sequences uses a forest-edit-distance recurrence:
      dist([], [])           = 0
      dist([a, ...A'], [])   = delete(a) + dist(A', [])
      dist([], [b, ...B'])   = insert(b) + dist([], B')
      dist([a, ...A'], [b, ...B']) = min(
          dist(a, b) + dist(A', B'),                          # match
          delete(a) + dist(A', [b, ...B']),                   # skip a
          insert(b) + dist([a, ...A'], B'),                   # skip b
      )

  Memoized with @lru_cache via id-based keys.

Cost configuration:
  Internal node relabel: 0 if names match, 1 otherwise.
  Internal node insert/delete: 1 (one per node).
  Leaf insert/delete: MISSING_PENALTY (treated like comparing against missing).
  Leaf relabel: leaf_cost() from leaf_costs.py.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Optional

from leaf_costs import leaf_cost, MISSING_PENALTY

# Cost of inserting/deleting a single internal node (per node)
INTERNAL_NODE_OP_COST = 1.0


# ─────────────────────────────────────────────────────────────────────
# Per-node insert/delete costs
# ─────────────────────────────────────────────────────────────────────
def node_op_cost(node) -> float:
    """Cost to insert or delete a single node (not its subtree)."""
    if node.is_leaf:
        return MISSING_PENALTY
    return INTERNAL_NODE_OP_COST


def subtree_delete_cost(node) -> float:
    """Total cost to delete an entire subtree rooted at `node`."""
    cost = node_op_cost(node)
    for c in node.children:
        cost += subtree_delete_cost(c)
    return cost


# Insert cost mirrors delete cost (symmetric)
def subtree_insert_cost(node) -> float:
    return subtree_delete_cost(node)


# ─────────────────────────────────────────────────────────────────────
# Relabel cost between two roots (not their subtrees)
# ─────────────────────────────────────────────────────────────────────
def relabel_cost(a, b) -> float:
    if a.is_leaf and b.is_leaf:
        return leaf_cost(a, b)
    if a.is_leaf != b.is_leaf:
        # Mismatched node types (leaf vs internal) — treat as fully different
        return 1.0
    # Both internal
    return 0.0 if a.name == b.name else 1.0


# ─────────────────────────────────────────────────────────────────────
# Tree edit distance with memoization
# ─────────────────────────────────────────────────────────────────────
def tree_edit_distance(tree_a, tree_b) -> float:
    """Compute TED between two trees. Uses memoization keyed on object id.
    Each call to this function gets its own cache, so don't worry about
    caching across different tree pairs.
    """
    # Use id-based memoization: trees are immutable for the duration of one call
    memo_tree: dict = {}
    memo_forest: dict = {}

    def dist_tree(a, b) -> float:
        if a is None and b is None:
            return 0.0
        if a is None:
            return subtree_insert_cost(b)
        if b is None:
            return subtree_delete_cost(a)

        key = (id(a), id(b))
        if key in memo_tree:
            return memo_tree[key]

        # Option 1: match the roots, then align children
        match_cost = relabel_cost(a, b) + dist_forest(tuple(a.children), tuple(b.children))

        # Option 2: delete root of a (and consider just one of its children
        #           against all of b — this handles the case where a's root
        #           is "extra"). Standard Zhang-Shasha-style formulation.
        delete_a = subtree_delete_cost(a) + dist_tree(None, b)
        insert_b = dist_tree(a, None) + subtree_insert_cost(b)
        # The match_cost option is usually the cheapest for our country trees
        # (same skeleton), but we keep all three for correctness.

        result = min(match_cost, delete_a, insert_b)
        memo_tree[key] = result
        return result

    def dist_forest(a_children: tuple, b_children: tuple) -> float:
        """Edit distance between two ordered forests (sequences of trees)."""
        if not a_children and not b_children:
            return 0.0

        key = (tuple(id(c) for c in a_children), tuple(id(c) for c in b_children))
        if key in memo_forest:
            return memo_forest[key]

        if not a_children:
            # Insert all of b_children
            cost = sum(subtree_insert_cost(c) for c in b_children)
            memo_forest[key] = cost
            return cost
        if not b_children:
            cost = sum(subtree_delete_cost(c) for c in a_children)
            memo_forest[key] = cost
            return cost

        a_head, *a_rest = a_children
        b_head, *b_rest = b_children

        # Three options for the first slot
        match  = dist_tree(a_head, b_head) + dist_forest(tuple(a_rest), tuple(b_rest))
        skip_a = subtree_delete_cost(a_head) + dist_forest(tuple(a_rest), b_children)
        skip_b = subtree_insert_cost(b_head) + dist_forest(a_children, tuple(b_rest))

        result = min(match, skip_a, skip_b)
        memo_forest[key] = result
        return result

    return dist_tree(tree_a, tree_b)


# ─────────────────────────────────────────────────────────────────────
# Maximum possible distance — used for normalization to similarity in [0, 1]
# ─────────────────────────────────────────────────────────────────────
def max_possible_distance(tree_a, tree_b) -> float:
    """Upper bound on TED: the cost of fully deleting A and fully inserting B.
    Used as the denominator when normalizing distance to similarity.
    """
    return subtree_delete_cost(tree_a) + subtree_insert_cost(tree_b)
