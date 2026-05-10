# Development tool — not part of the production pipeline; may be outdated.

"""
Diagnose the distribution of similarity scores.
If similarities are all squashed into a narrow band, no clustering algorithm
will produce coherent clusters — the data simply doesn't have enough spread.
"""
import numpy as np
from pathlib import Path

data = np.load("data/similarity_matrix.npz", allow_pickle=True)
codes = list(data["codes"])
matrix = data["matrix"]

# Get only the upper triangle (unique pairs, exclude diagonal)
n = len(codes)
i, j = np.triu_indices(n, k=1)
sims = matrix[i, j]

print(f"Number of pairs: {len(sims):,}")
print(f"\nSimilarity distribution:")
print(f"  min:    {sims.min():.3f}")
print(f"  1%ile:  {np.percentile(sims, 1):.3f}")
print(f"  5%ile:  {np.percentile(sims, 5):.3f}")
print(f"  25%ile: {np.percentile(sims, 25):.3f}")
print(f"  median: {np.percentile(sims, 50):.3f}")
print(f"  mean:   {sims.mean():.3f}")
print(f"  75%ile: {np.percentile(sims, 75):.3f}")
print(f"  95%ile: {np.percentile(sims, 95):.3f}")
print(f"  99%ile: {np.percentile(sims, 99):.3f}")
print(f"  max:    {sims.max():.3f}")
print(f"  std:    {sims.std():.3f}")

# Histogram (text-based)
print("\nHistogram of pairwise similarities:")
bins = np.linspace(sims.min(), sims.max(), 21)
hist, edges = np.histogram(sims, bins=bins)
max_h = hist.max()
for k in range(len(hist)):
    bar = "█" * int(40 * hist[k] / max_h)
    print(f"  [{edges[k]:.3f} - {edges[k+1]:.3f}] {hist[k]:5d} {bar}")

# How many pairs have very high similarity (potential cluster cores)?
print(f"\nPairs with similarity > 0.85: {(sims > 0.85).sum():,}  ({100*(sims>0.85).mean():.1f}%)")
print(f"Pairs with similarity > 0.90: {(sims > 0.90).sum():,}  ({100*(sims>0.90).mean():.1f}%)")
print(f"Pairs with similarity > 0.95: {(sims > 0.95).sum():,}  ({100*(sims>0.95).mean():.1f}%)")

# What's the top similarity in the dataset?
print("\nTop 15 most-similar country pairs:")
top_idx = np.argsort(-sims)[:15]
for idx in top_idx:
    a, b = codes[i[idx]], codes[j[idx]]
    print(f"  {sims[idx]:.4f}  {a} - {b}")