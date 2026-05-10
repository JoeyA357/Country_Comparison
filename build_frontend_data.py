"""
Generate static JSON dumps the React frontend will consume.

Reads:
  data/country_trees.json
  data/clusters.json
  data/similarity_matrix.npz   (used to extract pair similarities fast)

Writes (to frontend/public/data/):
  countries.json   — per-country metadata + tree
  clusters.json    — cluster-level info (id, color, members, label)
  pairs.json       — precomputed pairwise similarity + breakdown for all ordered pairs

Run after any change to trees, weights, or clustering.
"""
from __future__ import annotations
from pathlib import Path
from itertools import combinations
import json
import time

import numpy as np

from tree_builder import load_trees_json, TreeNode
from similarity import compare, initialize

# ─────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
TREES_JSON = DATA_DIR / "country_trees.json"
CLUSTERS_JSON = DATA_DIR / "clusters.json"
SIM_MATRIX_NPZ = DATA_DIR / "similarity_matrix.npz"

OUT_DIR = Path("frontend/public/data")
OUT_COUNTRIES = OUT_DIR / "countries.json"
OUT_CLUSTERS = OUT_DIR / "clusters.json"
OUT_PAIRS = OUT_DIR / "pairs.json"


# ─────────────────────────────────────────────────────────────────────
# Cluster colors (military HUD palette — high contrast on dark bg)
# ─────────────────────────────────────────────────────────────────────
HUD_PALETTE = [
    "#00ff88",  # green
    "#ff8c42",  # amber
    "#7d5cff",  # violet
    "#ff3860",  # red
    "#3edd6e",  # green
    "#ffd23f",  # gold
    "#5fb0ff",  # blue
    "#ff5fb0",  # magenta
    "#a0e890",  # light green
    "#e890a0",  # pink
    "#90b0e8",  # periwinkle
    "#e8d490",  # tan
    "#90e8d4",  # mint
    "#d490e8",  # lavender
    "#e89090",  # coral
    "#909090",  # grey (for catch-all / micro-clusters)
]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def load_clusters() -> dict:
    with open(CLUSTERS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def cluster_label(member_names: list[str]) -> str:
    """Generate a short human-readable label for a cluster.
    For now: the names of the top 3 most-prototypical members joined.
    The frontend can override this with custom labels later.
    """
    if not member_names:
        return "Empty"
    sample = ", ".join(member_names[:3])
    if len(member_names) > 3:
        sample += f" + {len(member_names) - 3} more"
    return sample


# ─────────────────────────────────────────────────────────────────────
# Build countries.json
# ─────────────────────────────────────────────────────────────────────
def build_countries(trees: dict[str, TreeNode], cluster_data: dict) -> list[dict]:
    """Per-country payload. Includes the full tree so the right panel
    can render the breakdown without another file."""
    membership = {c["iso3"]: c for c in cluster_data["countries"]}
    out = []
    for iso3, tree in sorted(trees.items()):
        m = membership.get(iso3, {})
        out.append({
            "iso3": iso3,
            "name": tree.name,
            "cluster": m.get("cluster"),
            "probability": m.get("probability"),
            "tree": tree.to_dict(),
        })
    return out


# ─────────────────────────────────────────────────────────────────────
# Build clusters.json
# ─────────────────────────────────────────────────────────────────────
def build_clusters(trees: dict[str, TreeNode], cluster_data: dict) -> list[dict]:
    by_cluster: dict[int, list[dict]] = {}
    for c in cluster_data["countries"]:
        by_cluster.setdefault(c["cluster"], []).append(c)

    out = []
    for cid in sorted(by_cluster.keys()):
        members = sorted(by_cluster[cid], key=lambda x: -x["probability"])
        member_iso3s = [m["iso3"] for m in members]
        member_names = [m["name"] for m in members]
        out.append({
            "id": cid,
            "color": HUD_PALETTE[cid % len(HUD_PALETTE)],
            "size": len(members),
            "label": cluster_label(member_names),
            "members": member_iso3s,
        })
    return out


# ─────────────────────────────────────────────────────────────────────
# Build pairs.json
# ─────────────────────────────────────────────────────────────────────
def build_pairs(trees: dict[str, TreeNode]) -> dict:
    """Precompute every ordered pair's similarity + breakdown.
    Storage format is keyed by 'iso3_a:iso3_b' (lexicographic order, no duplicates)
    to keep the file size manageable. Frontend will look up either order.
    """
    codes = sorted(trees.keys())
    n = len(codes)
    print(f"Building pairs ({n*(n-1)//2:,} unordered pairs)...")
    start = time.time()
    pairs: dict[str, dict] = {}
    count = 0
    for a, b in combinations(codes, 2):
        result = compare(trees[a], trees[b])
        key = f"{a}:{b}"
        # Round to 4 decimals to keep file size down without losing meaningful precision
        pairs[key] = {
            "similarity": round(result.similarity, 4),
            "distance": round(result.distance, 4),
            "max_distance": round(result.max_distance, 4),
            "breakdown": [
                {"path": path, "cost": round(cost, 4)}
                for path, cost in result.leaf_breakdown
            ],
        }
        count += 1
        if count % 4000 == 0:
            elapsed = time.time() - start
            rate = count / elapsed
            print(f"  {count:,}/{n*(n-1)//2:,} ({rate:,.0f}/s)")
    print(f"  Done in {time.time() - start:.1f}s")
    return pairs


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading trees...")
    trees = load_trees_json()
    initialize(trees)
    print(f"  {len(trees)} trees")

    print("Loading clusters...")
    cluster_data = load_clusters()
    print(f"  {cluster_data['n_clusters']} clusters")

    print("\nBuilding countries.json...")
    countries = build_countries(trees, cluster_data)
    with open(OUT_COUNTRIES, "w", encoding="utf-8") as f:
        json.dump(countries, f, ensure_ascii=False)
    print(f"  Wrote {OUT_COUNTRIES} ({OUT_COUNTRIES.stat().st_size:,} bytes)")

    print("\nBuilding clusters.json...")
    clusters = build_clusters(trees, cluster_data)
    with open(OUT_CLUSTERS, "w", encoding="utf-8") as f:
        json.dump(clusters, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {OUT_CLUSTERS} ({OUT_CLUSTERS.stat().st_size:,} bytes)")

    print("\nBuilding pairs.json...")
    pairs = build_pairs(trees)
    with open(OUT_PAIRS, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False)
    print(f"  Wrote {OUT_PAIRS} ({OUT_PAIRS.stat().st_size:,} bytes)")

    print("\nDone. Frontend data ready in", OUT_DIR)


if __name__ == "__main__":
    main()
