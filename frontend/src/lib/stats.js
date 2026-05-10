/**
 * Compute the percentile rank of a similarity score within all pairs.
 * Cached on first call so we don't sort 18,721 numbers per render.
 */
let cachedSorted = null;

export function similarityPercentile(score, pairs) {
  if (cachedSorted === null) {
    cachedSorted = Object.values(pairs)
      .map(p => p.similarity)
      .sort((a, b) => a - b);
  }
  // Find how many pairs have similarity ≤ score
  let lo = 0, hi = cachedSorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (cachedSorted[mid] <= score) lo = mid + 1;
    else hi = mid;
  }
  return lo / cachedSorted.length; // 0..1
}

export function clearStatsCache() {
  cachedSorted = null;
}