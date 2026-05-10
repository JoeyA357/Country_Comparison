# Development tool — not part of the production pipeline; may be outdated.

"""
Show the most similar AND least similar countries to a given target,
plus the per-leaf cost breakdown for the least-similar pair.
"""
from tree_builder import load_trees_json
from similarity import compare, initialize

TARGET = "NOR"
TOP_K = 10
BOTTOM_K = 10


def main():
    trees = load_trees_json()
    initialize(trees)

    if TARGET not in trees:
        print(f"{TARGET} not in dataset"); return

    target_tree = trees[TARGET]
    scores = []
    for code, tree in trees.items():
        if code == TARGET:
            continue
        result = compare(target_tree, tree)
        scores.append((code, tree.name, result.similarity, result))
    scores.sort(key=lambda x: -x[2])

    print(f"=== Top {TOP_K} most similar to {TARGET} ({target_tree.name}) ===")
    for code, name, sim, _ in scores[:TOP_K]:
        bar = "█" * int(sim * 30)
        print(f"  {sim:.3f}  {bar:30s}  {code}  {name}")

    print(f"\n=== Bottom {BOTTOM_K} LEAST similar to {TARGET} ===")
    for code, name, sim, _ in scores[-BOTTOM_K:]:
        bar = "█" * int(sim * 30)
        print(f"  {sim:.3f}  {bar:30s}  {code}  {name}")

    print(f"\n=== Range ===")
    print(f"  Most similar:  {scores[0][2]:.3f}  ({scores[0][0]} {scores[0][1]})")
    print(f"  Least similar: {scores[-1][2]:.3f}  ({scores[-1][0]} {scores[-1][1]})")
    print(f"  Spread: {scores[0][2] - scores[-1][2]:.3f}")

    # Show the breakdown for the least-similar pair
    print(f"\n=== Per-leaf breakdown: {TARGET} vs {scores[-1][0]} ===")
    least = scores[-1][3]
    print(f"  Overall similarity: {least.similarity:.3f}")
    print(f"  Raw distance: {least.distance:.3f}")
    print(f"  Max possible distance: {least.max_distance:.3f}")
    for path, cost in sorted(least.leaf_breakdown, key=lambda x: -x[1]):
        bar = "█" * int(cost * 20)
        print(f"    {cost:.3f}  {bar:20s}  {path}")


if __name__ == "__main__":
    main()
