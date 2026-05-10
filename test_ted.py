"""
Sanity tests for the TED similarity engine.

Checks:
  1. A country compared to itself has similarity = 1.0
  2. Symmetric: similarity(A, B) == similarity(B, A)
  3. Sensible relative ordering on hand-picked pairs:
       France vs Germany should be MORE similar than France vs North Korea
       Japan vs South Korea should be MORE similar than Japan vs Brazil
  4. Per-leaf breakdown looks reasonable
  5. Performance check: how long does it take to compare all 18,721 pairs?
"""
from __future__ import annotations
import time
from itertools import combinations

from tree_builder import load_trees_json
from leaf_costs import calibrate_from_trees
from similarity import compare, initialize


def test_self_similarity(trees) -> None:
    print("\n=== Test 1: self-similarity should be 1.0 ===")
    for code in ["FRA", "JPN", "USA", "BRA"]:
        if code not in trees:
            continue
        result = compare(trees[code], trees[code])
        status = "PASS" if abs(result.similarity - 1.0) < 1e-9 else "FAIL"
        print(f"  [{status}] {result.country_a:20s} vs itself: "
              f"similarity={result.similarity:.6f}, distance={result.distance:.6f}")


def test_symmetry(trees) -> None:
    print("\n=== Test 2: symmetry — sim(A, B) == sim(B, A) ===")
    pairs = [("FRA", "DEU"), ("JPN", "KOR"), ("USA", "CAN"), ("BRA", "ARG")]
    for a, b in pairs:
        if a not in trees or b not in trees:
            continue
        s_ab = compare(trees[a], trees[b]).similarity
        s_ba = compare(trees[b], trees[a]).similarity
        status = "PASS" if abs(s_ab - s_ba) < 1e-9 else "FAIL"
        print(f"  [{status}] sim({a},{b})={s_ab:.6f}  sim({b},{a})={s_ba:.6f}")


def test_relative_ordering(trees) -> None:
    print("\n=== Test 3: relative ordering on hand-picked pairs ===")
    cases = [
        # (close_pair, far_pair, description)
        (("FRA", "DEU"), ("FRA", "PRK"), "France-Germany should beat France-NorthKorea"),
        (("JPN", "KOR"), ("JPN", "BRA"), "Japan-SouthKorea should beat Japan-Brazil"),
        (("USA", "CAN"), ("USA", "AFG"), "USA-Canada should beat USA-Afghanistan"),
        (("NOR", "SWE"), ("NOR", "EGY"), "Norway-Sweden should beat Norway-Egypt"),
    ]
    for (a1, b1), (a2, b2), desc in cases:
        if any(c not in trees for c in [a1, b1, a2, b2]):
            print(f"  [SKIP] {desc} (missing tree)")
            continue
        s_close = compare(trees[a1], trees[b1]).similarity
        s_far   = compare(trees[a2], trees[b2]).similarity
        status = "PASS" if s_close > s_far else "FAIL"
        print(f"  [{status}] {desc}")
        print(f"          sim({a1},{b1})={s_close:.3f}   sim({a2},{b2})={s_far:.3f}")


def test_breakdown(trees) -> None:
    print("\n=== Test 4: per-leaf breakdown for France vs Japan ===")
    if "FRA" not in trees or "JPN" not in trees:
        print("  [SKIP] missing trees")
        return
    result = compare(trees["FRA"], trees["JPN"])
    print(f"  Overall similarity: {result.similarity:.3f}")
    print(f"  Raw distance: {result.distance:.3f}")
    print(f"  Max possible distance: {result.max_distance:.3f}")
    print(f"  Per-leaf costs:")
    for path, cost in sorted(result.leaf_breakdown, key=lambda x: -x[1]):
        bar = "█" * int(cost * 20)
        print(f"    {cost:.3f}  {bar:20s}  {path}")


def test_performance(trees) -> None:
    print("\n=== Test 5: full pairwise computation timing ===")
    codes = sorted(trees.keys())
    n_pairs = len(codes) * (len(codes) - 1) // 2
    print(f"  Computing all {n_pairs:,} pairs over {len(codes)} countries...")
    start = time.time()
    count = 0
    for a, b in combinations(codes, 2):
        compare(trees[a], trees[b])
        count += 1
        if count % 2000 == 0:
            elapsed = time.time() - start
            rate = count / elapsed
            eta = (n_pairs - count) / rate
            print(f"    {count:,} pairs done ({rate:,.0f}/s, ETA {eta:.1f}s)")
    elapsed = time.time() - start
    print(f"  Total: {count:,} pairs in {elapsed:.2f}s ({count/elapsed:,.0f}/s)")


def show_top_similar(trees, target: str = "FRA", k: int = 10) -> None:
    print(f"\n=== Top {k} most similar countries to {target} ===")
    if target not in trees:
        print(f"  {target} not in trees")
        return
    target_tree = trees[target]
    scores = []
    for code, tree in trees.items():
        if code == target:
            continue
        result = compare(target_tree, tree)
        scores.append((code, tree.name, result.similarity))
    scores.sort(key=lambda x: -x[2])
    for code, name, sim in scores[:k]:
        bar = "█" * int(sim * 30)
        print(f"  {sim:.3f}  {bar:30s}  {code}  {name}")


def main() -> None:
    print("Loading trees...")
    trees = load_trees_json()
    print(f"Loaded {len(trees)} trees")

    print("Calibrating numerical ranges from dataset...")
    initialize(trees)

    test_self_similarity(trees)
    test_symmetry(trees)
    test_relative_ordering(trees)
    test_breakdown(trees)

    show_top_similar(trees, target="FRA", k=10)
    show_top_similar(trees, target="JPN", k=10)

    test_performance(trees)


if __name__ == "__main__":
    main()
