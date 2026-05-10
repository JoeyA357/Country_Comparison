/**
 * One row in the per-leaf breakdown.
 *
 * `path` — e.g. "Demographics/Languages"
 * `cost` — float in [0, ~1]; the WEIGHTED cost (already includes leaf weight)
 *
 * Visual:
 *   - The path label on the left, in dim mono
 *   - A bar that fills from left to right based on cost
 *   - Numerical cost on the right
 *   - Color: low cost = cyan, high cost = amber → red
 */

function colorForCost(cost) {
  // Map cost ∈ [0, 1] to a color
  // 0.0 = green, 0.4 = amber, 1.0 = red
  if (cost < 0.3) return "#00ff88";
  if (cost < 0.6) return "#ff8c42";
  return "#ff3860";
}

export default function BreakdownBar({ path, cost, maxCost }) {
  // Normalize bar width relative to max cost in the breakdown
  const widthPct = maxCost > 0 ? Math.min(100, 100 * cost / maxCost) : 0;
  const color = colorForCost(cost);

  // Strip the top-level branch ("Geography/", "Demographics/", etc.) for cleanliness
  // but keep it as a small label
  const [branch, ...rest] = path.split("/");
  const leafName = rest.join("/") || branch;

  return (
    <div className="py-1">
      <div className="flex items-baseline justify-between mb-0.5">
        <div className="flex items-baseline gap-2">
          <span className="text-hud-textDim" style={{ fontSize: "9px" }}>
            {branch.toUpperCase()}
          </span>
          <span className="text-hud-text text-xs">{leafName}</span>
        </div>
        <span className="text-xs font-mono" style={{ color }}>
          {cost.toFixed(3)}
        </span>
      </div>
      <div className="h-1 bg-hud-grid relative overflow-hidden">
        <div
          className="h-full transition-all"
          style={{
            width: `${widthPct}%`,
            background: color,
            boxShadow: cost > 0.5 ? `0 0 4px ${color}` : "none",
          }}
        />
      </div>
    </div>
  );
}