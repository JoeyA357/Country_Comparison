"""
Cluster the 194 country trees using agglomerative clustering on the
TED-derived distance matrix.

Why agglomerative instead of HDBSCAN:
  HDBSCAN's "noise" category was assigning ~40% of countries to no cluster.
  For a country-comparison UI we want every country in *some* cluster, even
  if its membership is loose. Agglomerative gives us a clean partition,
  a hierarchy (dendrogram), and a tunable cluster count via threshold or k.

Pipeline:
  1. Load trees
  2. Compute or load the cached 194x194 similarity matrix
  3. Convert similarity -> distance (1 - similarity)
  4. Run agglomerative clustering (average linkage) for chosen k
  5. Print clusters and save results to JSON
"""
from __future__ import annotations
from pathlib import Path
from itertools import combinations
import json
import time

import numpy as np

from tree_builder import load_trees_json
from similarity import compare, initialize

DATA_DIR = Path("data")
SIM_MATRIX_NPZ = DATA_DIR / "similarity_matrix.npz"
CLUSTERS_JSON = DATA_DIR / "clusters.json"
LINKAGE_NPZ = DATA_DIR / "linkage.npz"

N_CLUSTERS = 14              # how many clusters to extract from the hierarchy
LINKAGE_METHOD = "average"   # 'average' | 'complete' | 'single'


# ─────────────────────────────────────────────────────────────────────
# Similarity matrix — compute once, cache to disk
# ─────────────────────────────────────────────────────────────────────
def compute_similarity_matrix(trees: dict) -> tuple[list[str], np.ndarray]:
    codes = sorted(trees.keys())
    n = len(codes)
    matrix = np.ones((n, n), dtype=np.float32)

    print(f"Computing similarity matrix ({n}x{n}, {n*(n-1)//2:,} pairs)...")
    start = time.time()
    code_to_idx = {c: i for i, c in enumerate(codes)}
    count = 0
    for a, b in combinations(codes, 2):
        sim = compare(trees[a], trees[b]).similarity
        i, j = code_to_idx[a], code_to_idx[b]
        matrix[i, j] = sim
        matrix[j, i] = sim
        count += 1
        if count % 4000 == 0:
            elapsed = time.time() - start
            rate = count / elapsed
            print(f"  {count:,}/{n*(n-1)//2:,} pairs done ({rate:,.0f}/s)")
    print(f"  Done in {time.time() - start:.1f}s")
    return codes, matrix


def load_or_compute_similarity(trees: dict, force: bool = False) -> tuple[list[str], np.ndarray]:
    if SIM_MATRIX_NPZ.exists() and not force:
        print(f"Loading cached similarity matrix from {SIM_MATRIX_NPZ}")
        data = np.load(SIM_MATRIX_NPZ, allow_pickle=True)
        return list(data["codes"]), data["matrix"]
    codes, matrix = compute_similarity_matrix(trees)
    np.savez_compressed(SIM_MATRIX_NPZ, codes=np.array(codes), matrix=matrix)
    print(f"  Cached to {SIM_MATRIX_NPZ}")
    return codes, matrix


# ─────────────────────────────────────────────────────────────────────
# Agglomerative clustering
# ─────────────────────────────────────────────────────────────────────
def run_agglomerative(distance_matrix: np.ndarray, n_clusters: int) -> dict:
    """Run agglomerative clustering on a precomputed distance matrix.
    Returns labels and the linkage matrix (for dendrograms / hierarchical UI).
    """
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform

    # scipy expects a condensed (1D) distance vector
    condensed = squareform(distance_matrix, checks=False)

    # Compute linkage matrix — the full hierarchy
    Z = linkage(condensed, method=LINKAGE_METHOD)

    # Extract a flat clustering with the desired number of clusters
    labels = fcluster(Z, t=n_clusters, criterion="maxclust")
    labels = labels - 1  # scipy uses 1-indexed; convert to 0-indexed

    # Compute a "membership probability" — distance from a country to its
    # cluster's centroid, normalized. This is a post-hoc proxy since
    # agglomerative doesn't give probabilities natively. Higher = more central.
    n = len(labels)
    probs = np.zeros(n, dtype=np.float32)
    for cid in set(labels):
        members = np.where(labels == cid)[0]
        if len(members) == 1:
            probs[members[0]] = 1.0
            continue
        # mean intra-cluster distance for each member -> closer to cluster mean = higher prob
        sub = distance_matrix[np.ix_(members, members)]
        mean_dists = sub.mean(axis=1)
        # invert and normalize within the cluster
        max_d = mean_dists.max() if mean_dists.max() > 0 else 1.0
        probs[members] = 1.0 - (mean_dists / max_d) * 0.5  # range [0.5, 1.0]

    return {"labels": labels, "probabilities": probs, "linkage": Z}


# ─────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────
def report_clusters(codes: list[str], trees: dict,
                    labels: np.ndarray, probs: np.ndarray) -> None:
    print("\n" + "=" * 60)
    print(f"Cluster summary (agglomerative, {LINKAGE_METHOD} linkage, k={N_CLUSTERS})")
    print("=" * 60)
    print(f"  Clusters: {len(set(labels))}")
    print(f"  Countries: {len(labels)} (no noise — every country assigned)")

    groups: dict[int, list[tuple[str, str, float]]] = {}
    for code, label, prob in zip(codes, labels, probs):
        groups.setdefault(int(label), []).append((code, trees[code].name, float(prob)))

    # Sort clusters by size (largest first)
    for label in sorted(groups.keys(), key=lambda k: -len(groups[k])):
        members = sorted(groups[label], key=lambda x: -x[2])
        print(f"\n--- Cluster {label} ({len(members)} countries) ---")
        for code, name, prob in members:
            print(f"  {prob:.2f}  {code}  {name}")


def save_clusters(codes: list[str], trees: dict,
                  labels: np.ndarray, probs: np.ndarray, linkage_Z: np.ndarray) -> None:
    out = {
        "method": "agglomerative",
        "linkage": LINKAGE_METHOD,
        "n_clusters": int(len(set(labels))),
        "countries": [
            {
                "iso3": code,
                "name": trees[code].name,
                "cluster": int(label),
                "probability": float(prob),
            }
            for code, label, prob in zip(codes, labels, probs)
        ],
    }
    with open(CLUSTERS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSaved clusters to {CLUSTERS_JSON}")

    # Save linkage for future dendrogram visualization
    np.savez_compressed(LINKAGE_NPZ, codes=np.array(codes), linkage=linkage_Z)
    print(f"Saved linkage matrix to {LINKAGE_NPZ}")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main():
    import sys
    force = "--refresh" in sys.argv

    # Allow overriding k from the command line: python cluster.py --k=12
    global N_CLUSTERS
    for arg in sys.argv:
        if arg.startswith("--k="):
            N_CLUSTERS = int(arg.split("=", 1)[1])

    trees = load_trees_json()
    initialize(trees)
    print(f"Loaded {len(trees)} trees")

    codes, sim_matrix = load_or_compute_similarity(trees, force=force)

    dist_matrix = 1.0 - sim_matrix
    np.fill_diagonal(dist_matrix, 0.0)
    dist_matrix = np.clip(dist_matrix, 0.0, 1.0).astype(np.float64)

    print(f"\nRunning agglomerative clustering "
          f"(k={N_CLUSTERS}, linkage={LINKAGE_METHOD})...")
    result = run_agglomerative(dist_matrix, n_clusters=N_CLUSTERS)

    report_clusters(codes, trees, result["labels"], result["probabilities"])
    save_clusters(codes, trees, result["labels"], result["probabilities"],
                  result["linkage"])


if __name__ == "__main__":
    main()